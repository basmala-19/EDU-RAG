"""In-process RAG adapter for the Question Bank feature."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import secrets
from typing import Any

from src.features.rag.application.ingestion_service import IngestionService
from src.features.rag.application.retrieval_service import RetrievalService
from src.features.rag.infrastructure.ingest_registry import IngestRegistry


class QuestionBankRAG:
    """Index books and retrieve topic evidence without an HTTP boundary."""

    def __init__(self, *, registry_path: str | Path | None = None) -> None:
        self.ingestion = IngestionService()
        self.retrieval = RetrievalService()
        project_root = Path(__file__).resolve().parents[4]
        self.registry = IngestRegistry(
            registry_path or project_root / "data" / "rag" / "ingest_registry.json"
        )

    def index_file(self, source: str | Path) -> dict[str, Any]:
        path = Path(source)
        if not path.is_file():
            raise FileNotFoundError(f"Uploaded book does not exist: {path}")
        if path.suffix.casefold() != ".pdf":
            raise ValueError("Only PDF books are supported by the Question Bank UI.")

        content_hash = self._hash_file(path)
        existing = self.registry.lookup(content_hash)
        if existing and self.ingestion.store.get_all_metadata({"file_reference_id": existing["file_reference_id"]}):
            return {"status": "duplicate_skipped", "duplicate": True, "file_name": path.name, **existing}

        file_reference_id = secrets.token_hex(16)
        result = self.ingestion.ingest(path, None, "v1", file_reference_id=file_reference_id).model_dump()
        record = {"file_reference_id": file_reference_id, "file_name": path.name, **result}
        self.registry.register(content_hash, record)
        return {"status": "indexed", "duplicate": False, **record}

    def retrieve_topic(self, topic: str, file_reference_id: str, *, top_k: int = 10) -> dict[str, Any]:
        response = self.retrieval.retrieve(topic, {"file_reference_id": file_reference_id}, top_k)
        sources = [item.model_dump() for item in response.results]
        chunks = [item["raw_text"] for item in sources if item.get("raw_text")]
        if not chunks:
            raise RuntimeError(f"RAG found no source material for topic '{topic}'.")
        return {"topic": topic, "file_reference_id": file_reference_id, "retriever": "internal-curriculum-rag", "relevant_count": len(chunks), "chunks": chunks, "sources": sources}

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
