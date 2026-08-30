"""Background job runner for ``POST /books``.

The pipeline this drives (Knowledge Graph -> RAG indexing -> question
generation) is the exact same one ``question_bank/app.py`` already runs
synchronously for the internal Streamlit tool, and it genuinely takes
5-8 minutes end to end. That is fine inside Streamlit, where a human is
watching a spinner in the same open tab. It is not acceptable for a real
HTTP endpoint a mobile app calls: the client, any reverse proxy, and most
mobile HTTP stacks will time the request out long before the pipeline
finishes.

So ``POST /books`` (in ``app.py``) only ever calls :meth:`submit` here,
which hands the work to a background thread and returns a ``job_id``
immediately. The mobile app then polls ``GET /books/jobs/{job_id}``, whose
handler calls :meth:`get`, until ``status`` is ``"done"`` or ``"failed"``.

Mirrors the in-process queue pattern already used for RAG ingestion
(``rag/application/ingestion_jobs.py``): an in-memory dict of jobs behind a
lock, one ``ThreadPoolExecutor``. Jobs do not survive a process restart -
acceptable for a local/single-instance deployment, same tradeoff the RAG
ingestion queue already makes.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any
from uuid import uuid4

from src.features.knowledge_graph.application.graph_service import KnowledgeGraphService
from src.features.question_bank import book_library
from src.features.question_bank.questions_service import generate_questions_from_knowledge_graph
from src.features.rag.application.question_bank_integration import QuestionBankRAG

logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {"done", "failed"}


@dataclass
class BookJob:
    job_id: str
    filename: str
    grade: str
    subject: str
    status: str = "queued"
    stage_detail: str | None = "Waiting for a worker to pick this job up"
    content_hash: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None

    def public(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "stage_detail": self.stage_detail,
            "filename": self.filename,
            "grade": self.grade,
            "subject": self.subject,
            "content_hash": self.content_hash,
            "result": self.result,
            "error": self.error,
        }


class BookProcessingJobService:
    """Runs the book pipeline on a worker thread and tracks job status.

    ``submit()`` is safe to call from an async FastAPI request handler: it
    only enqueues work and returns, it never runs the pipeline itself.
    """

    def __init__(
        self,
        *,
        knowledge_graph_service: KnowledgeGraphService | None = None,
        rag: QuestionBankRAG | None = None,
        workers: int = 1,
    ) -> None:
        # Both services are already safe to share across requests/threads -
        # the same instances the Streamlit tool keeps in st.cache_resource.
        self.knowledge_graph_service = knowledge_graph_service or KnowledgeGraphService()
        self.rag = rag or QuestionBankRAG()
        self._jobs: dict[str, BookJob] = {}
        self._lock = Lock()
        # workers=1 by default: the pipeline is LLM/embedding-heavy and
        # sequential per book already; raise this only if the underlying
        # LLM provider and vector store can actually take concurrent load.
        self._executor = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="book-processing")

    def submit(self, *, pdf_path: Path, filename: str, grade: str, subject: str) -> BookJob:
        job = BookJob(job_id=uuid4().hex, filename=filename, grade=grade, subject=subject)
        with self._lock:
            self._jobs[job.job_id] = job
        self._executor.submit(self._run, job.job_id, pdf_path, grade, subject)
        return job

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.public() if job else None

    def _set(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            for key, value in fields.items():
                setattr(job, key, value)

    def _run(self, job_id: str, pdf_path: Path, grade: str, subject: str) -> None:
        try:
            # --- Step 1/3: Knowledge Graph ----------------------------------
            self._set(job_id, status="generating_kg", stage_detail="Building the Knowledge Graph from the PDF")
            logger.info("[job=%s] Step 1/3: generating Knowledge Graph from '%s'", job_id, pdf_path.name)
            kg_result = self.knowledge_graph_service.generate_from_pdf(pdf_path)
            active_graph = kg_result.graph
            content_hash = kg_result.content_hash
            self._set(job_id, content_hash=content_hash)

            existing = book_library.get_book(content_hash)
            if existing is not None:
                # Same content already went through the full pipeline before
                # (possibly under a different filename/upload) - reuse it
                # instead of re-indexing and re-generating questions.
                logger.info(
                    "[job=%s] content_hash=%s already processed as '%s' - reusing library entry",
                    job_id, content_hash, existing.get("filename"),
                )
                self._set(
                    job_id,
                    status="done",
                    stage_detail="Reused a previously processed book with identical content",
                    result=existing,
                )
                return

            # --- Step 2/3: RAG indexing -------------------------------------
            self._set(job_id, status="indexing", stage_detail="Indexing the book into RAG (chunking, embedding, vector store)")
            logger.info("[job=%s] Step 2/3: indexing '%s' into RAG", job_id, pdf_path.name)
            index_result = self.rag.index_file(pdf_path)
            file_reference_id = str(index_result.get("file_reference_id") or "").strip()
            if not file_reference_id:
                raise RuntimeError("RAG indexing completed without returning file_reference_id.")
            indexed_chunks = index_result.get("indexed_chunks", index_result.get("chunks_created", 0))

            # --- Step 3/3: generate questions for every topic ---------------
            self._set(
                job_id, status="generating_questions",
                stage_detail="Generating questions for every topic in the Knowledge Graph",
            )
            logger.info("[job=%s] Step 3/3: generating questions for every topic", job_id)

            def retriever(topic: str) -> dict[str, Any]:
                return self.rag.retrieve_topic(topic, file_reference_id)

            saved_paths = generate_questions_from_knowledge_graph(
                active_graph, grade, subject,
                rag_file_reference_id=file_reference_id,
                retriever=retriever,
                # entity_ids intentionally omitted: process every topic in the graph.
            )

            entity_count = len(active_graph.get("entities", []))
            book_library.register_book(
                content_hash=content_hash,
                filename=pdf_path.name,
                grade=grade,
                subject=subject,
                rag_file_reference_id=file_reference_id,
                indexed_chunks=indexed_chunks,
                knowledge_graph=active_graph,
                entity_count=entity_count,
                topics_generated=len(saved_paths),
            )
            result = book_library.get_book(content_hash)
            logger.info(
                "[job=%s] Book processing complete: entities=%d indexed_chunks=%s topics_with_questions=%d",
                job_id, entity_count, indexed_chunks, len(saved_paths),
            )
            self._set(job_id, status="done", stage_detail="Book processed end-to-end", result=result)
        except Exception as exc:  # noqa: BLE001 - reported via job.error, never crashes the worker thread
            logger.exception("[job=%s] Book processing failed", job_id)
            self._set(job_id, status="failed", stage_detail=None, error=str(exc))
        finally:
            # The uploaded file only ever needs to exist for this run - RAG
            # indexing and Knowledge Graph generation both persist whatever
            # they need from it independently.
            pdf_path.unlink(missing_ok=True)


_service: BookProcessingJobService | None = None


def get_book_processing_job_service() -> BookProcessingJobService:
    """One shared in-process job service per process (matches
    ``get_rag()``/``get_knowledge_graph_service()`` elsewhere)."""
    global _service
    if _service is None:
        _service = BookProcessingJobService()
    return _service
