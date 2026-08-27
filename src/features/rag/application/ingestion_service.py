from __future__ import annotations

from collections import Counter
from hashlib import sha1
from pathlib import Path
from typing import Any

from src.features.rag.domain.schemas import ChunkMetadata, DocumentMetadataResponse, IngestionResponse, RAGChunk
from src.features.rag.application.chunking import HierarchyAwareParentChildChunker
from src.features.rag.infrastructure.document_loader import discover_files, load_file
from src.features.rag.infrastructure.config import get_settings
from src.features.rag.infrastructure.embeddings import get_embedding_service
from src.features.rag.application.metadata import clean_optional, detect_language, split_heading_path
from src.features.rag.application.document_metadata import extract_document_metadata, resolve_curriculum_identity
from src.features.rag.application.hypothetical_questions import generate_questions
from src.features.rag.infrastructure.vector_store import VectorStore
from src.features.rag.utils.validators import validate_chunk


class IngestionService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.chunker = HierarchyAwareParentChildChunker(
            parent_size=self.settings.parent_chunk_size,
            child_size=self.settings.child_chunk_size,
            overlap=self.settings.child_chunk_overlap,
            min_size=self.settings.child_chunk_min_size,
            heading_max_length=self.settings.heading_max_length,
        )
        self.embedder = get_embedding_service()
        self.store = VectorStore()

    def ingest(self, source: Path, curriculum_id: str | None = None, version: str | None = None, *, file_reference_id: str | None = None, extra_metadata: dict[str, Any] | None = None) -> IngestionResponse:
        files = discover_files(source)
        all_chunks: list[RAGChunk] = []
        all_parents: dict[str, dict[str, Any]] = {}
        lang_counts: Counter[str] = Counter()
        coverage_counts: Counter[str] = Counter()
        coverage_total = 0
        resolved_curriculum = ""
        resolved_version = str(clean_optional(version) or "v1")
        last_doc_meta: dict[str, Any] | None = None

        for file in files:
            clean_extra = {k: clean_optional(v) for k, v in (extra_metadata or {}).items() if k in {"subject", "grade"}}
            clean_extra = {k: v for k, v in clean_extra.items() if v is not None}
            loaded_docs = load_file(file, extra_metadata=clean_extra, file_reference_id=file_reference_id)
            metadata_source_text = None
            if loaded_docs:
                metadata_source_text = loaded_docs[0].metadata.pop("_metadata_source_text", None)
            joined = metadata_source_text or "\n".join(d.text for d in loaded_docs[:8])
            doc_meta = extract_document_metadata(joined, file_name=file.name, parser_language=loaded_docs[0].metadata.get("language") if loaded_docs else None, overrides=clean_extra)
            last_doc_meta = doc_meta
            resolved_curriculum = resolve_curriculum_identity(doc_meta, curriculum_id)

            for doc_idx, loaded in enumerate(loaded_docs):
                base = {
                    **loaded.metadata,
                    "curriculum_id": resolved_curriculum,
                    "version": resolved_version,
                    "file_reference_id": file_reference_id or loaded.metadata.get("file_reference_id"),
                    "document_title": doc_meta.get("document_title"),
                    "subject": doc_meta.get("subject"),
                    "grade": doc_meta.get("grade"),
                    "term": doc_meta.get("term"),
                    "language": doc_meta.get("language") or loaded.metadata.get("language"),
                }
                for idx, chunk in enumerate(self.chunker.split(loaded.text, base)):
                    md = {
                        **base,
                        **(chunk.metadata or {}),
                        "curriculum_id": resolved_curriculum,
                        "version": resolved_version,
                        "language": detect_language(chunk.raw_text),
                        "source": loaded.metadata.get("source", file.name),
                        "source_type": loaded.metadata.get("source_type", file.suffix.lstrip(".")),
                        "page": loaded.metadata.get("page"),
                        "file_reference_id": file_reference_id or loaded.metadata.get("file_reference_id"),
                    }
                    for key, value in list(md.items()):
                        if isinstance(value, str):
                            md[key] = clean_optional(value)
                    md["heading_path"] = split_heading_path(md.get("heading_path"))
                    md["parent_chunk_id"] = chunk.parent_chunk_id
                    meta = ChunkMetadata(**md)
                    chunk_id = sha1(f"{resolved_curriculum}|{resolved_version}|{file.resolve()}|{file_reference_id}|{doc_idx}|{idx}".encode()).hexdigest()[:16]
                    try:
                        validated = validate_chunk(RAGChunk(chunk_id=chunk_id, raw_text=chunk.raw_text, normalized_text=chunk.normalized_text, metadata=meta, parent_chunk_id=chunk.parent_chunk_id))
                    except ValueError:
                        continue
                    all_chunks.append(validated)
                    all_parents[chunk.parent_chunk_id] = {
                        "parent_chunk_id": chunk.parent_chunk_id,
                        "raw_text": chunk.parent_text,
                        "metadata": {**chunk.parent_metadata, "curriculum_id": resolved_curriculum, "version": resolved_version, "file_reference_id": file_reference_id or loaded.metadata.get("file_reference_id")},
                    }
                    lang_counts[validated.metadata.language] += 1
                    coverage_total += 1
                    for field in ("subject", "grade", "heading", "heading_path"):
                        if getattr(validated.metadata, field) not in (None, "", []):
                            coverage_counts[field] += 1

        vectors = self.embedder.encode([c.normalized_text or c.raw_text for c in all_chunks]) if all_chunks else []
        indexed = self.store.upsert(all_chunks, vectors) if all_chunks else 0
        if all_parents:
            self.store.upsert_parents(list(all_parents.values()))

        indexed_question_count = 0
        if self.settings.question_index_enabled and all_chunks:
            rows = [
                {"chunk_id": c.chunk_id, "text": c.raw_text, "heading": c.metadata.heading}
                for c in all_chunks
            ]
            qmap = generate_questions(rows)
            q_rows: list[dict[str, Any]] = []
            q_texts: list[str] = []
            for c in all_chunks:
                for i, q in enumerate(qmap.get(c.chunk_id, [])):
                    q_rows.append({
                        "question_id": f"q::{c.chunk_id}::{i}",
                        "question": q,
                        "metadata": {
                            "file_reference_id": c.metadata.file_reference_id,
                            "curriculum_id": c.metadata.curriculum_id,
                            "version": c.metadata.version,
                            "child_chunk_id": c.chunk_id,
                            "parent_chunk_id": c.parent_chunk_id,
                        },
                    })
                    q_texts.append(q)
            if q_rows:
                qv = self.embedder.encode(q_texts)
                indexed_question_count = self.store.upsert_questions(q_rows, qv)

        coverage = {field: round(coverage_counts[field] / coverage_total * 100, 2) if coverage_total else 0.0 for field in ("subject", "grade", "heading", "heading_path")}
        document_metadata_response = DocumentMetadataResponse(**last_doc_meta) if last_doc_meta else None
        return IngestionResponse(
            curriculum_id=resolved_curriculum,
            version=resolved_version,
            files_processed=len(files),
            chunks_created=len(all_chunks),
            indexed_chunks=indexed,
            indexed_question_count=indexed_question_count,
            language_counts=dict(lang_counts),
            metadata_coverage=coverage,
            document_metadata=document_metadata_response,
        )
