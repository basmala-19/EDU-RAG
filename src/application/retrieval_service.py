from __future__ import annotations

from src.domain.schemas import RetrievalRequest, RetrievalResponse, RetrievalResult
from src.infrastructure.embeddings import EmbeddingService
from src.infrastructure.config import get_settings
from src.infrastructure.vector_store import VectorStore
from src.infrastructure.ranking import rerank_and_dedup
from src.utils.logger import get_logger

logger = get_logger(__name__)


class RetrievalService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.embedder = EmbeddingService()
        self.store = VectorStore()

    def retrieve(self, query: str, filters: dict | None = None, top_k: int | None = None) -> RetrievalResponse:
        filters = dict(filters or {})
        if not filters.get("file_reference_id"):
            raise ValueError("file_reference_id is required for retrieval isolation")
        effective_top_k = top_k if top_k is not None else self.settings.top_k
        vector = self.embedder.encode([query])[0]
        candidate_k = max(
            effective_top_k * max(int(self.settings.candidate_multiplier), 8),
            effective_top_k,
            self.settings.min_candidate_k,
        )
        dense = self.store.query(vector, filters, candidate_k)
        question = self.store.query_questions(vector, filters, candidate_k) if self.settings.question_index_enabled and hasattr(self.store, "query_questions") else []
        keyword = self.store.query_keywords(query, filters, max(self.settings.lexical_candidate_k, candidate_k)) if hasattr(self.store, "query_keywords") else []
        merged: list[dict] = []
        by_id: dict[str, dict] = {}
        for item in dense + question + keyword:
            cid = str(item["id"])
            if cid not in by_id:
                by_id[cid] = item
                merged.append(item)
            else:
                if item.get("question_match"):
                    by_id[cid]["question_match"] = True
                    by_id[cid]["question_distance"] = min(float(by_id[cid].get("question_distance", 1.0)), float(item.get("distance", 1.0)))
                if item.get("keyword_match"):
                    by_id[cid]["keyword_match"] = True
                    by_id[cid]["keyword_score"] = max(float(by_id[cid].get("keyword_score", 0.0)), float(item.get("keyword_score", 0.0)))
        # Ask the ranker for more candidates than we need, because the dedup inside
        # rerank_and_dedup only collapses children with near-identical raw text — it
        # can't know two *different* children (e.g. adjacent overlapping windows within
        # the same page) will resolve to the *same* parent once we expand below. Without
        # the extra headroom here, several near-duplicate children of one parent can fill
        # every remaining slot and silently push out a genuinely different parent
        # elsewhere on the same page (e.g. one page-54 section repeated twice in the
        # evidence list while the page-54 section that actually answers the question
        # never appears at all).
        ranked = rerank_and_dedup(merged, effective_top_k * 3, query=query)
        seen_parent_ids: set[str] = set()
        deduped: list[dict] = []
        for item in ranked:
            pid = str(item.get("metadata", {}).get("parent_chunk_id") or item["id"])
            if pid in seen_parent_ids:
                continue
            seen_parent_ids.add(pid)
            deduped.append(item)
            if len(deduped) >= effective_top_k:
                break
        ranked = deduped
        parent_ids = [str(item.get("metadata", {}).get("parent_chunk_id") or item["id"]) for item in ranked]
        parents = self.store.get_parents(parent_ids) if hasattr(self.store, "get_parents") else {}
        out: list[RetrievalResult] = []
        expansion_misses = 0
        for item in ranked:
            meta = dict(item.get("metadata") or {})
            meta["retrieval_channels"] = list(item.get("retrieval_channels") or [])
            for key in ("distance","keyword_score","question_distance","rrf_score","reranker_score","retrieval_confidence","lexical_overlap","heading_overlap","score"):
                if key in item:
                    meta[key] = item[key]
            pid = str(meta.get("parent_chunk_id") or item["id"])
            parent = parents.get(pid)
            raw = item.get("document", "")
            # Explicit flag so a silent parent-expansion miss (e.g. stale ingest data,
            # a parent_chunk_id that no longer resolves) is visible in every response
            # instead of quietly falling back to the short child chunk.
            context_expanded = bool(parent)
            if parent:
                raw = parent.get("document", raw)
                meta = {**meta, **(parent.get("metadata") or {}), "parent_chunk_id": pid, "retrieved_child_chunk_id": item["id"]}
            else:
                expansion_misses += 1
            meta["context_expanded"] = context_expanded
            out.append(RetrievalResult(chunk_id=str(item["id"]), raw_text=raw, score=float(item["score"]), metadata=meta))
        if expansion_misses:
            logger.warning(
                "parent_expansion_miss count=%d of %d results (file_reference_id=%s) — returned short child chunks instead of expanded parent context",
                expansion_misses, len(out), filters.get("file_reference_id"),
            )
        return RetrievalResponse(results=out)

    def retrieve_request(self, request: RetrievalRequest) -> RetrievalResponse:
        filters = dict(request.filters)
        filters["file_reference_id"] = request.file_reference_id
        return self.retrieve(request.query, filters, request.top_k)
