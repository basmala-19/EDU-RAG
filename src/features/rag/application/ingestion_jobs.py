"""Small in-process ingestion queue for local/single-instance deployments."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import logging
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from src.features.rag.application.ingestion_service import IngestionService
from src.features.rag.infrastructure.ingest_registry import IngestRegistry

logger = logging.getLogger(__name__)


@dataclass
class _Job:
    job_id: str
    file_reference_id: str
    file_name: str
    size_bytes: int
    status: str = "queued"
    result: dict[str, Any] | None = None
    error: str | None = None

    def public(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "file_reference_id": self.file_reference_id,
            "file_name": self.file_name,
            "size_bytes": self.size_bytes,
            "result": self.result,
            "error": self.error,
        }


class IngestionJobService:
    def __init__(self, ingestion_service: IngestionService, registry: IngestRegistry, workers: int = 1) -> None:
        self.ingestion_service = ingestion_service
        self.registry = registry
        self._jobs: dict[str, _Job] = {}
        self._lock = Lock()
        self._executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="ingestion")

    def submit(self, *, source: Path, file_reference_id: str, file_name: str, size_bytes: int, content_hash: str) -> _Job:
        job = _Job(job_id=uuid4().hex, file_reference_id=file_reference_id, file_name=file_name, size_bytes=size_bytes)
        with self._lock:
            self._jobs[job.job_id] = job
        self._executor.submit(self._run, job.job_id, source, content_hash)
        return job

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.public() if job else None

    def _run(self, job_id: str, source: Path, content_hash: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "processing"
        try:
            result = self.ingestion_service.ingest(source, None, "v1", file_reference_id=job.file_reference_id, extra_metadata={})
            result_dump = result.model_dump()
            self.registry.register(content_hash, {
                "file_reference_id": job.file_reference_id,
                "file_name": job.file_name,
                "curriculum_id": result_dump["curriculum_id"],
                "version": result_dump["version"],
                "chunks_created": result_dump["chunks_created"],
                "indexed_chunks": result_dump["indexed_chunks"],
                "indexed_question_count": result_dump["indexed_question_count"],
                "language_counts": result_dump["language_counts"],
                "metadata_coverage": result_dump["metadata_coverage"],
                "document_metadata": result_dump["document_metadata"],
            })
            with self._lock:
                job.result = {"file_reference_id": job.file_reference_id, "file_name": job.file_name, "size_bytes": job.size_bytes, "status": "indexed", "duplicate": False, **result_dump}
                job.status = "completed"
        except Exception:
            logger.exception("Ingestion job failed (job_id=%s, file=%s)", job_id, source.name)
            source.unlink(missing_ok=True)
            with self._lock:
                job.status = "failed"
                job.error = "Upload processing failed. Check server logs for details."
