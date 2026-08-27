from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
import numpy as np

from src.features.rag.domain.schemas import RAGChunk
from src.features.rag.infrastructure.config import get_settings
from src.features.rag.infrastructure.ar_text import normalize_ar_token


class VectorStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.backend = "unavailable"
        self.init_error: str | None = None
        self.collection = None
        self.parent_collection = None
        self.question_collection = None
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            self.client = chromadb.PersistentClient(
                path=self.settings.chroma_path,
                settings=ChromaSettings(
                    anonymized_telemetry=self.settings.chroma_anonymized_telemetry,
                ),
            )
            self.collection = self.client.get_or_create_collection("curriculum_chunks", metadata={"hnsw:space": "cosine"})
            self.parent_collection = None
            self.question_collection = self.client.get_or_create_collection("curriculum_questions", metadata={"hnsw:space": "cosine"})
            self.backend = "chromadb"
        except ModuleNotFoundError as exc:
            self.client = None
            self.backend = "local-json"
            self.init_error = f"{type(exc).__name__}: {exc}"
        except Exception as exc:
            self.client = None
            self.backend = "unavailable"
            self.init_error = f"{type(exc).__name__}: {exc}"
        # Keep all fallback/parent data beside the configured Chroma directory.
        # This matters when the unified application is started from the repository
        # root rather than from inside the RAG feature directory.
        storage_root = Path(self.settings.chroma_path).resolve().parent
        self.local_path = storage_root / "local_index.json"
        self.parent_path = storage_root / "parent_index.json"
        self.question_path = storage_root / "question_index.json"
        # Cache of BM25 corpus stats (tokenized docs + df + avgdl) so query_keywords()
        # doesn't retokenize the whole matching corpus and recompute IDF on every
        # single question. Keyed by (filters, corpus size) so it's invalidated
        # automatically whenever new documents are ingested anywhere in the store.
        self._bm25_cache: dict[tuple, tuple[list[dict[str, Any]], list[list[str]], dict[str, int], float]] = {}

    @staticmethod
    def _chroma_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in metadata.items():
            if value is None:
                continue
            if isinstance(value, (str, int, float, bool)):
                out[key] = value
            elif isinstance(value, (list, tuple, set)):
                out[key] = " > ".join(str(v) for v in value)
            else:
                out[key] = str(value)
        return out

    def _safe_batch_size(self) -> int:
        try:
            maximum = int(self.collection._client.get_max_batch_size()) if self.collection is not None else 4000
            return max(1, min(maximum, 4000))
        except Exception:
            return 4000

    def upsert(self, chunks: list[RAGChunk], vectors: np.ndarray) -> int:
        if not chunks:
            return 0
        if self.collection is not None:
            bs = self._safe_batch_size()
            for start in range(0, len(chunks), bs):
                batch = chunks[start:start+bs]
                bv = vectors[start:start+bs]
                self.collection.upsert(ids=[c.chunk_id for c in batch], embeddings=bv.tolist(), documents=[c.raw_text for c in batch], metadatas=[self._chroma_metadata(c.metadata.model_dump(exclude_none=True)) for c in batch])
            return len(chunks)
        payload = json.loads(self.local_path.read_text(encoding="utf-8")) if self.local_path.exists() else []
        by_id = {x["id"]: x for x in payload}
        for chunk, vector in zip(chunks, vectors):
            by_id[chunk.chunk_id] = {"id": chunk.chunk_id, "vector": vector.tolist(), "document": chunk.raw_text, "metadata": chunk.metadata.model_dump(exclude_none=True)}
        self.local_path.parent.mkdir(parents=True, exist_ok=True)
        self.local_path.write_text(json.dumps(list(by_id.values()), ensure_ascii=False), encoding="utf-8")
        return len(chunks)

    def upsert_parents(self, rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        payload = json.loads(self.parent_path.read_text(encoding="utf-8")) if self.parent_path.exists() else []
        by_id = {x["parent_chunk_id"]: x for x in payload}
        by_id.update({x["parent_chunk_id"]: x for x in rows})
        self.parent_path.parent.mkdir(parents=True, exist_ok=True)
        self.parent_path.write_text(json.dumps(list(by_id.values()), ensure_ascii=False), encoding="utf-8")
        return len(rows)

    def get_parents(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        ids = [x for x in ids if x]
        if not ids:
            return {}
        if not self.parent_path.exists():
            return {}
        rows = json.loads(self.parent_path.read_text(encoding="utf-8"))
        wanted = set(ids)
        return {x["parent_chunk_id"]: {"document": x["raw_text"], "metadata": x.get("metadata", {})} for x in rows if x.get("parent_chunk_id") in wanted}

    def upsert_questions(self, rows: list[dict[str, Any]], vectors: np.ndarray) -> int:
        if not rows:
            return 0
        if self.question_collection is not None:
            bs = self._safe_batch_size()
            for start in range(0, len(rows), bs):
                batch = rows[start:start+bs]
                bv = vectors[start:start+bs]
                self.question_collection.upsert(ids=[x["question_id"] for x in batch], embeddings=bv.tolist(), documents=[x["question"] for x in batch], metadatas=[self._chroma_metadata(x["metadata"]) for x in batch])
            return len(rows)
        payload = json.loads(self.question_path.read_text(encoding="utf-8")) if self.question_path.exists() else []
        by_id = {x["id"]: x for x in payload}
        for row, vector in zip(rows, vectors):
            by_id[row["question_id"]] = {"id": row["question_id"], "vector": vector.tolist(), "document": row["question"], "metadata": row["metadata"]}
        self.question_path.parent.mkdir(parents=True, exist_ok=True)
        self.question_path.write_text(json.dumps(list(by_id.values()), ensure_ascii=False), encoding="utf-8")
        return len(rows)

    def get_all_metadata(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """Return chunk metadata dicts matching filters, with no embedding/query involved.

        Used for discovery endpoints (e.g. listing indexed subjects/grades/chapters/lessons)
        rather than for retrieval, so it deliberately skips ranking entirely.
        """
        if self.collection is not None:
            where = self._chroma_where(filters)
            total = self.collection.count()
            if total <= 0:
                return []
            kwargs: dict[str, Any] = {"limit": total, "include": ["metadatas"]}
            if where:
                kwargs["where"] = where
            out = self.collection.get(**kwargs)
            return [m or {} for m in out.get("metadatas", [])]
        if not self.local_path.exists():
            return []
        rows = json.loads(self.local_path.read_text(encoding="utf-8"))
        return [r.get("metadata", {}) for r in rows if self._matches(r.get("metadata", {}), filters)]

    def query(self, vector: np.ndarray, filters: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
        if self.collection is not None:
            where = self._chroma_where(filters)
            available = self.collection.count()
            if available <= 0:
                return []
            n = min(max(top_k, 1), available)
            kwargs = {"query_embeddings": [vector.tolist()], "n_results": n}
            if where:
                kwargs["where"] = where
            out = self.collection.query(**kwargs)
            return [{"id": out["ids"][0][i], "document": out["documents"][0][i], "metadata": out["metadatas"][0][i] or {}, "distance": out["distances"][0][i]} for i in range(len(out["ids"][0]))]
        if not self.local_path.exists():
            return []
        rows = json.loads(self.local_path.read_text(encoding="utf-8"))
        rows = [r for r in rows if self._matches(r.get("metadata", {}), filters)]
        q = np.asarray(vector, dtype=np.float32)
        scored = []
        for r in rows:
            v = np.asarray(r["vector"], dtype=np.float32)
            sim = float(np.dot(q, v) / max(np.linalg.norm(q) * np.linalg.norm(v), 1e-8))
            scored.append({"id": r["id"], "document": r["document"], "metadata": r["metadata"], "distance": 1-sim})
        scored.sort(key=lambda x: x["distance"])
        return scored[:top_k]


    def _bm25_corpus(self, filters: dict[str, Any]) -> tuple[list[dict[str, Any]], list[list[str]], dict[str, int], float]:
        """Build (or reuse from cache) the tokenized corpus + BM25 stats for a filter set."""
        cache_key = (tuple(sorted(filters.items())), self._corpus_size())
        cached = self._bm25_cache.get(cache_key)
        if cached is not None:
            return cached
        if self.collection is not None:
            where = self._chroma_where(filters)
            total = self.collection.count()
            if total <= 0:
                rows: list[dict[str, Any]] = []
            else:
                kwargs: dict[str, Any] = {"limit": total, "include": ["documents", "metadatas"]}
                if where:
                    kwargs["where"] = where
                out = self.collection.get(**kwargs)
                rows = [{"id": out["ids"][i], "document": out["documents"][i], "metadata": (out["metadatas"][i] or {})} for i in range(len(out["ids"]))]
        else:
            if not self.local_path.exists():
                rows = []
            else:
                payload = json.loads(self.local_path.read_text(encoding="utf-8"))
                rows = [r for r in payload if self._matches(r.get("metadata", {}), filters)]
        tokenized = [self._lex_tokens(((r.get("metadata", {}) or {}).get("heading", "") + " ") * 3 + r.get("document", "")) for r in rows]
        df: dict[str, int] = {}
        for terms in tokenized:
            for t in set(terms):
                df[t] = df.get(t, 0) + 1
        n = max(len(rows), 1)
        avgdl = sum(len(t) for t in tokenized) / n if tokenized else 1.0
        result = (rows, tokenized, df, avgdl)
        # Keep the cache from growing unbounded across many distinct filter combos.
        if len(self._bm25_cache) > 64:
            self._bm25_cache.clear()
        self._bm25_cache[cache_key] = result
        return result

    def _corpus_size(self) -> int:
        if self.collection is not None:
            return self.collection.count()
        if not self.local_path.exists():
            return 0
        return len(json.loads(self.local_path.read_text(encoding="utf-8")))

    def query_keywords(self, query: str, filters: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
        """BM25-style lexical retrieval for exact curriculum terminology."""
        rows, tokenized, df, avgdl = self._bm25_corpus(filters)
        q_terms = self._lex_tokens(query)
        if not q_terms or not rows:
            return []
        n = max(len(rows), 1)
        k1, b = 1.2, 0.75
        scored=[]
        for row, terms in zip(rows, tokenized):
            counts: dict[str,int] = {}
            for t in terms: counts[t] = counts.get(t,0)+1
            score=0.0
            for term in q_terms:
                tf=counts.get(term,0)
                if not tf: continue
                d=df.get(term,0)
                idf=float(np.log(1.0+(n-d+0.5)/(d+0.5)))
                denom=tf+k1*(1-b+b*len(terms)/max(avgdl,1.0))
                score += idf*((tf*(k1+1))/max(denom,1e-9))
            if score>0:
                scored.append({**row,"distance":1/(1+score),"keyword_match":True,"keyword_score":score})
        scored.sort(key=lambda x:x["keyword_score"], reverse=True)
        return scored[:max(1,top_k)]

    @staticmethod
    def _lex_tokens(text: str) -> list[str]:
        from src.features.rag.infrastructure.ar_text import _MULTILINGUAL_STOP, repair_ocr_artifacts
        cleaned = repair_ocr_artifacts(text or "")
        cleaned = re.sub(r"[\u061F\u060C\u061B\u064B-\u065F\u0670?.,!;:()\[\]{}\"'/\\«»\-_~+=*#@%$^&|<>`]", " ", cleaned)
        raw = re.findall(r"[a-z0-9][a-z0-9_./+\-]*|[\u0600-\u06FF]+", cleaned.casefold())
        out = []
        for t in raw:
            t = t.replace("ـ", "").strip()
            norm = normalize_ar_token(t)
            if len(norm) > 1 and norm not in _MULTILINGUAL_STOP and t not in _MULTILINGUAL_STOP:
                out.append(norm)
        return out

    def query_questions(self, vector: np.ndarray, filters: dict[str, Any], top_k: int) -> list[dict[str, Any]]:
        if self.question_collection is not None:
            where = self._chroma_where(filters)
            available = self.question_collection.count()
            if available <= 0:
                return []
            n = min(max(top_k, 1), available)
            kwargs = {"query_embeddings": [vector.tolist()], "n_results": n}
            if where:
                kwargs["where"] = where
            out = self.question_collection.query(**kwargs)
            items = [{"id": out["metadatas"][0][i].get("child_chunk_id", out["ids"][0][i]), "document": out["documents"][0][i], "metadata": out["metadatas"][0][i] or {}, "distance": out["distances"][0][i], "question_match": True, "question_distance": out["distances"][0][i]} for i in range(len(out["ids"][0]))]
            child_ids = list(dict.fromkeys(str(x["id"]) for x in items))
            if child_ids and self.collection is not None:
                child_rows = self.collection.get(ids=child_ids, include=["documents", "metadatas"])
                by_id = {child_rows["ids"][i]: i for i in range(len(child_rows.get("ids", [])))}
                for item in items:
                    j = by_id.get(str(item["id"]))
                    if j is not None:
                        item["document"] = child_rows["documents"][j]
                        item["metadata"] = child_rows["metadatas"][j] or item["metadata"]
            return items
        if not self.question_path.exists():
            return []
        rows = json.loads(self.question_path.read_text(encoding="utf-8"))
        rows = [r for r in rows if self._matches(r.get("metadata", {}), filters)]
        q = np.asarray(vector, dtype=np.float32)
        scored=[]
        for r in rows:
            v=np.asarray(r["vector"],dtype=np.float32)
            sim=float(np.dot(q,v)/max(np.linalg.norm(q)*np.linalg.norm(v),1e-8))
            scored.append({"id": r["metadata"].get("child_chunk_id", r["id"]), "document": r["document"], "metadata": r["metadata"], "distance": 1-sim, "question_match": True})
        scored.sort(key=lambda x:x["distance"])
        return scored[:top_k]

    @staticmethod
    def _matches(meta: dict[str, Any], filters: dict[str, Any]) -> bool:
        return all(str(meta.get(k)) == str(v) for k, v in filters.items() if v is not None)

    @staticmethod
    def _chroma_where(filters: dict[str, Any]) -> dict[str, Any] | None:
        clauses = [{k: {"$eq": v}} for k, v in filters.items() if v is not None]
        if not clauses:
            return None
        if len(clauses) == 1:
            return clauses[0]
        return {"$and": clauses}
