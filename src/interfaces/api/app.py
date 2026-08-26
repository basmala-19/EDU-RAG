from __future__ import annotations

import asyncio
import logging
import re
import secrets
from hashlib import sha256
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

from src.domain.schemas import (
    ConversationDetail,
    ConversationListResponse,
    ConversationSummary,
    ErrorResponse,
    EvaluationMetrics,
    EvaluationRequest,
    EvaluationResponse,
    HealthResponse,
    IngestionJobResponse,
    LibraryEntry,
    LibraryResponse,
    ResponsePayload,
    ResponseRequest,
    ResponseSource,
    RetrievalSummary,
    UploadResponse,
)
from src.infrastructure.document_loader import SUPPORTED_EXTENSIONS
from src.application.ingestion_service import IngestionService
from src.application.ingestion_jobs import IngestionJobService
from src.application.generation import build_context, generate_with_provider
from src.application.retrieval_service import RetrievalService
from src.application.evaluation import RAGEvaluator
from src.infrastructure.config import get_settings
from src.infrastructure.health import health
from src.infrastructure.ingest_registry import IngestRegistry
from src.infrastructure.conversation_store import ConversationStore
from src.application.metadata import clean_optional, split_heading_path
from src.application.session import LearningSessionStore

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Curriculum RAG API — Production Educational Intelligence",
    version="2.0.0",
    description=(
        "### Enterprise-Grade Multilingual Educational RAG Engine & Evaluation Platform\n\n"
        "Engineered for Arabic, English, and Mixed curriculum textbooks with **Agentic OCR repair**, "
        "**Hybrid Dense/BM25/QA Retrieval**, **Cross-Encoder Reranking**, **Parent-Child Context Expansion**, "
        "and **Calibrated RAGAS Quality Metrics**.\n\n"
        "🔗 **Interactive Playground Console**: [`/console`](/console)\n"
        "📑 **Core Architecture**: LlamaParse Tier 2 OCR + ChromaDB Vector Index + Cohere Rerank-v3.5"
    ),
    contact={"name": "Curriculum RAG Engineering Team"},
    openapi_tags=[
        {"name": "response", "description": "Grounded question answering with page-level evidence and RAGAS metrics."},
        {"name": "ingestion", "description": "Curriculum document uploading, LlamaParse OCR, and background indexing."},
        {"name": "library", "description": "Manage and query previously indexed curriculum books."},
        {"name": "evaluation", "description": "On-demand RAGAS quality benchmarks and diagnostic metrics."},
        {"name": "conversations", "description": "Persistent multi-turn conversation logs and audit trails."},
        {"name": "system", "description": "Service readiness, vector store status, and health checks."},
    ],
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": 2,
        "displayRequestDuration": True,
        "filter": True,
        "tryItOutEnabled": True,
        "persistAuthorization": True,
        "syntaxHighlight.theme": "monokai",
    },
)

# Permissive by default so the bundled /console (and any local admin UI) can call the API
# from a different origin/port during development. Tighten allow_origins for production.
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

ingestion_service = IngestionService()
retrieval_service = RetrievalService()
session_store = LearningSessionStore()
rag_evaluator = RAGEvaluator()
ingest_registry = IngestRegistry()
conversation_store = ConversationStore()
ingestion_jobs = IngestionJobService(ingestion_service, ingest_registry, settings.ingestion_workers)
UPLOAD_DIR = Path("data/raw/uploads")
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


@app.on_event("startup")
async def _warm_up_models() -> None:
    """Load the embedding model and reranker once at boot instead of on the first
    real request. Without this, whichever user's request happens to be first pays
    the full multi-second model-load cost (and, under concurrent first requests,
    risks loading the same model twice). Runs in the threadpool so it never blocks
    the event loop, and failures here are logged but never crash startup — /api/rag/health
    already surfaces embedding/model availability, so we don't duplicate that here.
    """
    def _load() -> None:
        try:
            retrieval_service.embedder.encode(["warm-up"])
        except Exception:
            logger.exception("Embedding model warm-up failed")
        try:
            settings = get_settings()
            if settings.reranker_enabled and settings.reranker_backend.casefold() == "local":
                from src.infrastructure.ranking import _get_reranker
                ce = _get_reranker(settings.reranker_model, settings.embedding_device)
                ce.predict([("warm-up", "warm-up")], show_progress_bar=False)
        except Exception:
            logger.exception("Reranker warm-up failed")

    await run_in_threadpool(_load)
    settings = get_settings()
    asyncio.create_task(_session_sweep_loop(settings.session_sweep_interval_seconds))


async def _session_sweep_loop(interval_seconds: int) -> None:
    """Periodically evict idle/expired sessions even when there's no incoming traffic
    to trigger the lazy sweep in LearningSessionStore.get()/ensure(). Runs for the life
    of the process; failures are logged and never crash the loop or the app."""
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            removed = session_store.sweep()
            if removed:
                logger.info("session_sweep removed=%d", removed)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Session sweep iteration failed")


@app.get("/api/rag/health", response_model=HealthResponse, tags=["system"], summary="Health check", description="Returns the readiness status of embeddings and the vector store.")
def rag_health() -> HealthResponse:
    return health()


_CONSOLE_PATH = Path(__file__).resolve().parent / "static" / "console.html"


@app.get("/console", response_class=HTMLResponse, include_in_schema=False, tags=["system"])
def rag_console() -> HTMLResponse:
    """Self-contained testing console: upload a book, chat with it, and inspect the exact
    evidence (raw chunk text) behind every answer — click a [n] source chip under an answer
    to jump straight to that evidence card. No build step; pure HTML/JS calling this API."""
    if not _CONSOLE_PATH.exists():
        raise HTTPException(status_code=404, detail="Console asset missing")
    return HTMLResponse(_CONSOLE_PATH.read_text(encoding="utf-8"))


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/console")


@app.post(
    "/api/rag/upload",
    response_model=UploadResponse | IngestionJobResponse,
    tags=["ingestion"],
    summary="Upload a curriculum file and queue indexing",
    description=(
        "Client sends only the file. The backend creates file_reference_id, curriculum_id, and version, "
        "then queues parsing, metadata extraction, chunking, embedding, and indexing. Poll the returned job_id "
        "at GET /api/rag/ingestion-jobs/{job_id} until status is completed. "
        "If this exact file content (by hash, regardless of filename) was already ingested before, ingestion is "
        "skipped and the original curriculum_id/file_reference_id are returned with duplicate=true — pass "
        "?force_reingest=true to re-index anyway."
    ),
    responses={
        200: {
            "model": UploadResponse,
            "description": "File uploaded, parsed, and indexed successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "file_reference_id": "file_example",
                        "file_name": "ICT_Ar_Sec1_T1.pdf",
                        "size_bytes": 7460363,
                        "curriculum_id": "cur_example",
                        "version": "v1",
                        "files_processed": 1,
                        "chunks_created": 1456,
                        "indexed_chunks": 1456,
                        "indexed_question_count": 4228,
                        "language_counts": {"ar": 1089, "mixed": 213, "en": 115, "unknown": 39},
                        "metadata_coverage": {"subject": 100, "grade": 100, "heading": 100, "heading_path": 100},
                        "document_metadata": {"document_title": "البرمجة والذكاء الاصطناعي", "subject": "تكنولوجيا المعلومات والاتصالات", "grade": "الأول", "language": "ar", "sources": {}, "confidence": {}, "evidence": {}},
                        "status": "indexed"
                    }
                }
            }
        },
        413: {"model": ErrorResponse, "description": "File is larger than the configured upload limit."},
        415: {"model": ErrorResponse, "description": "Unsupported file type."},
        422: {"model": ErrorResponse, "description": "Request validation error."},
        500: {"model": ErrorResponse, "description": "Safe processing error; internal details are logged server-side."},
    },
)
async def rag_upload(file: UploadFile = File(..., description="Document to index"), force_reingest: bool = False) -> UploadResponse | IngestionJobResponse:
    original_name = Path(file.filename or "uploaded_file").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"Unsupported file type: {suffix}")
    file_reference_id = secrets.token_hex(16)
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(original_name).stem).strip("._") or "file"
    # Uniqueness comes from a per-file_reference_id directory, not from prefixing the
    # filename itself. This keeps `target.name` (and therefore `source` in every response,
    # plus parse_filename_metadata()) as the clean book name, while still guaranteeing two
    # uploads — even of files with the identical name — can never collide on disk.
    file_dir = UPLOAD_DIR / file_reference_id
    target = file_dir / f"{safe_stem}{suffix}"
    file_dir.mkdir(parents=True, exist_ok=True)
    size = 0
    hasher = sha256()
    try:
        with target.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File exceeds 100 MB limit")
                hasher.update(chunk)
                out.write(chunk)
        content_hash = hasher.hexdigest()

        existing = None if force_reingest else ingest_registry.lookup(content_hash)
        if existing:
            # The registry (a plain JSON file) and the vector store (Chroma) are two
            # independent persistence stores with nothing keeping them in sync. If the
            # vector store ever gets reset/recreated (fresh deploy, cleared volume, disk
            # issue) while ingest_registry.json survives, a registry hit alone is a lie:
            # it would keep returning "duplicate_skipped" with an old file_reference_id
            # that has zero chunks behind it, and every subsequent /api/rag/response call
            # for that file would silently 404 with "No relevant evidence found" forever,
            # since nothing here would ever trigger the retry to actually re-index it.
            # So confirm the data is really still there before trusting the shortcut.
            existing_has_data = bool(
                ingestion_service.store.get_all_metadata({"file_reference_id": existing["file_reference_id"]})
            )
            if existing_has_data:
                # Same content already indexed before (possibly under a different filename) —
                # skip re-ingesting it and don't keep a second copy of the file on disk.
                target.unlink(missing_ok=True)
                try:
                    file_dir.rmdir()
                except OSError:
                    pass
                return UploadResponse(
                    file_reference_id=existing["file_reference_id"],
                    file_name=original_name,
                    size_bytes=size,
                    status="duplicate_skipped",
                    duplicate=True,
                    curriculum_id=existing["curriculum_id"],
                    version=existing["version"],
                    files_processed=1,
                    chunks_created=existing.get("chunks_created", 0),
                    indexed_chunks=existing.get("indexed_chunks", 0),
                    indexed_question_count=existing.get("indexed_question_count", 0),
                    language_counts=existing.get("language_counts", {}),
                    metadata_coverage=existing.get("metadata_coverage", {}),
                    document_metadata=existing.get("document_metadata"),
                )
            # Registry says indexed, vector store disagrees — the registry entry is stale.
            # Re-ingest for real, but keep the same file_reference_id from the stale
            # record so any file_reference_id/session already handed out to a caller
            # keeps working once this re-ingest completes, instead of silently minting
            # a new id that nothing already in flight knows about.
            logger.warning(
                "ingest_registry_stale content_hash=%s file_reference_id=%s — registry has a record but the "
                "vector store has no chunks for it; re-ingesting instead of returning a phantom duplicate",
                content_hash, existing["file_reference_id"],
            )
            file_reference_id = existing["file_reference_id"]
            ingest_registry.forget(content_hash)

        if force_reingest:
            ingest_registry.forget(content_hash)

        job = ingestion_jobs.submit(
            source=target,
            file_reference_id=file_reference_id,
            file_name=original_name,
            size_bytes=size,
            content_hash=content_hash,
        )
        return IngestionJobResponse(**job.public())
    except HTTPException:
        target.unlink(missing_ok=True)
        raise
    except Exception as exc:
        logger.exception("Upload processing failed")
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="Upload processing failed. Check server logs for details.") from exc
    finally:
        await file.close()


@app.get("/api/rag/ingestion-jobs/{job_id}", response_model=IngestionJobResponse, tags=["ingestion"])
def ingestion_job_status(job_id: str) -> IngestionJobResponse:
    job = ingestion_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Ingestion job not found")
    return IngestionJobResponse(**job)


@app.get(
    "/api/rag/books",
    response_model=LibraryResponse,
    tags=["library"],
    summary="List previously uploaded books",
    description=(
        "Returns every book already ingested and still on record (most recent first), "
        "so a client can let the user pick a previously uploaded book by its "
        "file_reference_id and start querying it directly via POST /api/rag/response "
        "instead of uploading the file again."
    ),
)
@app.get(
    "/api/rag/documents",
    response_model=LibraryResponse,
    tags=["library"],
    summary="List previously uploaded documents (alias for /api/rag/books)",
    include_in_schema=True,
)
def list_books() -> LibraryResponse:
    records = ingest_registry.list_all()
    return LibraryResponse(books=[LibraryEntry(**record) for record in records])


@app.get(
    "/api/rag/conversations",
    response_model=ConversationListResponse,
    tags=["conversations"],
    summary="List saved conversations",
    description=(
        "Lightweight, most-recently-updated-first listing of every persisted conversation "
        "(book used, turn count, last question) without the retrieved chunk text — use "
        "GET /api/rag/conversations/{session_id} for the full detail of one conversation."
    ),
)
def list_conversations() -> ConversationListResponse:
    return ConversationListResponse(
        conversations=[ConversationSummary(**c) for c in conversation_store.list_conversations()]
    )


@app.get(
    "/api/rag/conversations/{session_id}",
    response_model=ConversationDetail,
    tags=["conversations"],
    summary="Get a saved conversation",
    description=(
        "Full persisted conversation: the book it's bound to, and every turn's question, "
        "answer, retrieved evidence chunks, and evaluation scores, in chronological order."
    ),
    responses={404: {"model": ErrorResponse, "description": "No conversation recorded under this session_id."}},
)
def get_conversation(session_id: str) -> ConversationDetail:
    record = conversation_store.get_conversation(session_id)
    if not record:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(**record)


@app.get("/api/rag/files/{file_reference_id}", include_in_schema=False, tags=["ingestion"])
def get_uploaded_file(file_reference_id: str) -> FileResponse:
    """Serves the indexed file for inline PDF viewing at specific page anchors."""
    file_dir = UPLOAD_DIR / file_reference_id
    if not file_dir.exists():
        raise HTTPException(status_code=404, detail="File directory not found")
    target_files = list(file_dir.glob("*.*"))
    if not target_files:
        raise HTTPException(status_code=404, detail="File not found in storage")
    target = target_files[0]
    media_type = "application/pdf" if target.suffix.lower() == ".pdf" else "application/octet-stream"
    return FileResponse(
        path=target,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{target.name}"'}
    )


@app.post(
    "/api/rag/response",
    response_model=ResponsePayload,
    operation_id="response",
    tags=["response"],
    summary="Retrieve grounded evidence and generate a lesson response",
    description=(
        "Runs file-isolated retrieval, question-index retrieval, lightweight reranking, parent-context expansion, "
        "learning-session contextualization, and generation in one operation.\n\n"
        "**Session model:** file_reference_id and lesson_context are bound to a session once, on the call that "
        "creates it (session_id omitted or unknown to the backend). Every following call in that session sends "
        "only session_id + query; the backend reuses the bound file_reference_id and the last-known "
        "lesson_context automatically. Send lesson_context again mid-session only when the student actually "
        "moves to a different chapter/lesson inside the same file."
    ),
    responses={
        200: {
            "model": ResponsePayload,
            "description": "Grounded lesson response.",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "sess_123",
                        "curriculum_id": "cur_example",
                        "version": "v1",
                        "file_reference_id": "file_example",
                        "answer": "التعلم الآلي هو تقنية تتعلم فيها أجهزة الكمبيوتر من كميات كبيرة من البيانات لاستخراج الأنماط والقواعد.",
                        "answer_status": "answered",
                        "grounded": True,
                        "retrieval": {"mode": "hybrid", "query_used": "ما هو التعلم الآلي؟", "candidate_count": 5, "top_score": 0.40, "grounding_threshold": 0.18},
                        "sources": [
                            {
                                "chunk_id": "chunk_001", "page": 49, "source": "ICT_Ar_Sec1_T1.pdf",
                                "heading": "الذكاء الاصطناعي", "chapter": "الذكاء الاصطناعي", "lesson": "التعلم الآلي",
                                "section": None, "topic": None, "heading_path": ["الذكاء الاصطناعي", "التعلم الآلي"],
                                "content_type": "definition", "parent_chunk_id": "parent_014",
                                "score": 0.40, "retrieval_confidence": 0.40, "reranker_score": 0.40,
                                "retrieval_channels": ["semantic", "question", "keyword"],
                                "context_expanded": True, "raw_text": "...",
                                "metadata": {"page": 49, "heading": "الذكاء الاصطناعي"},
                            }
                        ],
                        "session_metadata": {"session_turn": 1, "lesson_context": {"chapter": "الذكاء الاصطناعي", "lesson": "التعلم الآلي"}, "retrieval_count": 5, "generation_backend": "ollama", "context_chars": 2100}
                    }
                }
            }
        },
        400: {
            "model": ErrorResponse,
            "description": (
                "Either file_reference_id was omitted while starting a new session "
                "(no session_id, or a session_id the backend has never seen), or a "
                "file_reference_id was sent for an existing session that is already "
                "bound to a different file."
            ),
        },
        404: {"model": ErrorResponse, "description": "No relevant evidence was found for the requested file."},
        422: {"model": ErrorResponse, "description": "Request validation failed or indexed evidence is missing required backend-owned identity fields."},
        500: {"model": ErrorResponse, "description": "Safe processing error; internal details are logged server-side."},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/ResponseRequest"},
                    "examples": {
                        "new_lesson_question": {
                            "summary": "1) Start a session — file_reference_id required, session_id omitted",
                            "value": {
                                "query": "ما هو التعلم الآلي؟",
                                "file_reference_id": "YOUR_FILE_REFERENCE_ID",
                                "lesson_context": {
                                    "chapter": "الذكاء الاصطناعي",
                                    "lesson": "التعلم الآلي"
                                },
                                "top_k": 5
                            }
                        },
                        "follow_up_question": {
                            "summary": "2) Follow-up in the same session — only session_id + query, nothing else",
                            "value": {
                                "query": "طيب اديني مثال عليه",
                                "session_id": "sess_123",
                                "top_k": 5
                            }
                        },
                        "switch_lesson_mid_session": {
                            "summary": "3) Same session, student jumped to a different lesson in the same file",
                            "value": {
                                "query": "طب ايه الفرق بينه وبين التعلم العميق؟",
                                "session_id": "sess_123",
                                "lesson_context": {
                                    "chapter": "الذكاء الاصطناعي",
                                    "lesson": "التعلم العميق"
                                }
                            }
                        }
                    }
                }
            }
        }
    },
)
def rag_response(request: ResponseRequest) -> ResponsePayload:
    settings = get_settings()
    try:
        # A session, once created, already knows its own file_reference_id and last
        # lesson_context. The client only has to (re-)send them when starting a new
        # session or when the student switches lesson mid-session — never on every turn.
        existing_session = session_store.get(request.session_id) if request.session_id else {}
        is_new_session = not existing_session

        file_reference_id = request.file_reference_id or existing_session.get("file_reference_id")
        if not file_reference_id:
            raise HTTPException(status_code=400, detail="file_reference_id is required to start a new learning session")
        if not is_new_session and request.file_reference_id and existing_session.get("file_reference_id") != request.file_reference_id:
            raise HTTPException(status_code=400, detail="session_id is already bound to another file_reference_id")

        lesson_ctx = request.lesson_context.model_dump(exclude_none=True) if request.lesson_context else None
        effective_lesson_ctx = lesson_ctx or existing_session.get("lesson_context") or None

        # Retrieve locally; file_reference_id is the hard isolation boundary.
        base_filters = {"file_reference_id": file_reference_id}
        scoped_filters = dict(base_filters)
        if effective_lesson_ctx:
            for key in ("chapter", "lesson"):
                if effective_lesson_ctx.get(key):
                    scoped_filters[key] = effective_lesson_ctx[key]

        def _top_confidence(results: list[dict]) -> float:
            if not results:
                return 0.0
            meta = results[0].get("metadata", {})
            return float(meta.get("retrieval_confidence", results[0].get("score", 0.0)))

        def _run_retrieval(query_text: str) -> list[dict]:
            retrieved = retrieval_service.retrieve(query_text, scoped_filters, request.top_k)
            results = [r.model_dump() for r in retrieved.results]
            if scoped_filters != base_filters:
                scoped_conf = _top_confidence(results)
                if not results or scoped_conf < 0.25:
                    # Metadata for chapter/lesson can be incomplete or overly narrow; don't let
                    # an imperfect ingestion tag hide evidence that's genuinely in the file.
                    base_retrieved = retrieval_service.retrieve(query_text, base_filters, request.top_k)
                    base_results = [r.model_dump() for r in base_retrieved.results]
                    if _top_confidence(base_results) > scoped_conf:
                        results = base_results
            return results

        # Language-agnostic disambiguation between a fresh question and a genuine
        # follow-up: instead of guessing from word count or follow-up phrases (which
        # only ever cover one language at a time), we retrieve with the bare query and,
        # if history exists, also with the history-augmented query, then keep whichever
        # actually scores higher on the model's own retrieval_confidence. A topic switch
        # ("جمع ص8" -> "جمع ص42" mid-session) no longer gets dragged back toward the
        # previous turn's chunks just because the new question happens to be short.
        plain_query = request.query
        contextual_query = session_store.build_query(request.session_id, request.query, effective_lesson_ctx)

        results = _run_retrieval(plain_query)
        best_confidence = _top_confidence(results)
        used_query = plain_query

        if contextual_query != plain_query and best_confidence < settings.skip_contextual_retrieval_confidence:
            ctx_results = _run_retrieval(contextual_query)
            ctx_confidence = _top_confidence(ctx_results)
            if ctx_confidence > best_confidence:
                results, best_confidence, used_query = ctx_results, ctx_confidence, contextual_query

        if not results:
            raise HTTPException(status_code=404, detail="No relevant evidence found for the requested file")

        first_meta = results[0]["metadata"]
        curriculum_id = str(first_meta.get("curriculum_id") or "")
        version = str(first_meta.get("version") or "v1")
        if not curriculum_id:
            raise HTTPException(status_code=422, detail="Indexed evidence is missing curriculum_id")

        session_id = session_store.ensure(
            request.session_id,
            file_reference_id=file_reference_id,
            curriculum_id=curriculum_id,
            version=version,
            lesson_context=effective_lesson_ctx,
        )
        history = session_store.history(session_id)
        context = build_context(results, settings.max_context_chars)
        top_meta = results[0].get("metadata", {})
        reranker_score = float(results[0].get("reranker_score") or top_meta.get("reranker_score") or results[0].get("score", 0.0))
        retrieval_confidence = float(results[0].get("retrieval_confidence") or top_meta.get("retrieval_confidence") or results[0].get("score", 0.0))
        # Pre-generation gate: skip the (costly) generation call only when retrieval is
        # catastrophically irrelevant (near-zero overlap). This must stay well below the
        # 0.42/min_grounding_score bar — that bar is calibrated on English reranker scores,
        # and bge-reranker-v2-m3 systematically scores equally relevant Arabic passages
        # lower, which was closing this gate on valid Arabic evidence before the model ever
        # got a chance to read it. This is NOT the final grounding verdict — that comes from
        # what the model actually says below.
        pre_generation_gate_passed = (
            reranker_score >= settings.min_reranker_score_floor
            and retrieval_confidence >= settings.min_retrieval_confidence_floor
        )
        if pre_generation_gate_passed:
            generation = generate_with_provider(request.query, context, history, results)
        else:
            generation = None

        # Informational bar used only below as a fallback when the model didn't
        # return a parseable self-reported verdict (extractive fallback, or a model that
        # ignored the JSON instruction) and we have no better signal to trust instead.
        retrieval_gate_passed = reranker_score >= 0.30 and retrieval_confidence >= 0.30

        if generation is None:
            answer = "المعلومات المسترجعة من المحتوى غير كافية للإجابة على السؤال بشكل موثوق."
            answer_status = "insufficient_evidence"
            grounded = False
        elif generation.self_reported:
            # Source of truth: what the model itself said about the evidence, not just
            # pre-generation retrieval scores. This is what fixes cases where retrieval
            # scores looked fine but the model's actual answer said "insufficient evidence".
            answer = generation.answer
            answer_status = generation.status
            grounded = generation.status == "answered"
        else:
            # Model call didn't return a parseable structured verdict (extractive fallback,
            # or a model that ignored the JSON instruction) — fall back to the pre-generation
            # retrieval gate since we have no reliable self-report to trust instead.
            answer = generation.answer
            answer_status = generation.status if generation.status == "insufficient_evidence" else ("answered" if retrieval_gate_passed else "grounding_failed")
            grounded = retrieval_gate_passed and generation.status == "answered"
        session_store.append(session_id, request.query, answer)

        expanded_count = sum(1 for item in results if item["metadata"].get("context_expanded"))
        def _clean_src_text(val: Any) -> str | None:
            if not val:
                return None
            from src.infrastructure.ar_text import repair_ocr_artifacts
            s = repair_ocr_artifacts(str(val)).strip()
            s = re.sub(r"\s+", " ", s)
            if re.match(r"^(?:مثلث|دائرة|مربع|مستطيل|[▲▼◄►•▪=><~]+|\s*=\s*[\d.]+\s*[a-zA-Z\d^]+)\s*$", s):
                return None
            return s or None

        sources = [
            ResponseSource(
                chunk_id=item["chunk_id"],
                page=item["metadata"].get("page"),
                source=item["metadata"].get("source"),
                heading=_clean_src_text(item["metadata"].get("heading")),
                chapter=_clean_src_text(item["metadata"].get("chapter")),
                lesson=_clean_src_text(item["metadata"].get("lesson")),
                section=_clean_src_text(item["metadata"].get("section")),
                topic=_clean_src_text(item["metadata"].get("topic")),
                # Chroma flattens list metadata to a " > "-joined string on storage;
                # split_heading_path normalizes either form back to a clean list.
                heading_path=[_clean_src_text(p) for p in (split_heading_path(item["metadata"].get("heading_path")) or []) if _clean_src_text(p)] or None,
                content_type=item["metadata"].get("content_type"),
                parent_chunk_id=item["metadata"].get("parent_chunk_id"),
                score=float(item.get("score", 0.0)),
                retrieval_confidence=item["metadata"].get("retrieval_confidence"),
                reranker_score=item["metadata"].get("reranker_score"),
                retrieval_channels=list(item["metadata"].get("retrieval_channels") or []),
                context_expanded=bool(item["metadata"].get("context_expanded")),
                raw_text=item.get("raw_text"),
                metadata={k: v for k, v in item["metadata"].items() if v is not None and k not in {"chunk_role"}},
            )
            for item in results
        ]
        session = session_store.get(session_id)
        eval_metrics = rag_evaluator.evaluate_response(
            query=used_query,
            answer=answer,
            sources=sources,
            reranker_score=reranker_score,
            retrieval_confidence=retrieval_confidence,
        )
        retrieval_summary = RetrievalSummary(
            mode="hybrid",
            query_used=used_query,
            candidate_count=len(results),
            top_score=float(results[0].get("score", 0.0)),
            grounding_threshold=float(settings.min_grounding_score),
            semantic_score=max(0.0, 1.0 - float(top_meta.get("distance", 1.0))) if top_meta.get("distance") is not None else 0.0,
            keyword_score=float(top_meta.get("keyword_score", 0.0)),
            question_score=max(0.0, 1.0 - float(top_meta.get("question_distance", 1.0))) if top_meta.get("question_distance") is not None else 0.0,
            rrf_score=float(top_meta.get("rrf_score", 0.0)),
            reranker_score=reranker_score,
            retrieval_confidence=retrieval_confidence,
        )

        try:
            # Persist book + question + answer + retrieved chunks + evaluation scores for
            # this turn so the conversation can be browsed/audited later from a fresh
            # session — a failure here must never break the actual student-facing response.
            book_record = ingest_registry.find_by_file_reference_id(file_reference_id)
            conversation_store.append_turn(
                session_id,
                file_reference_id=file_reference_id,
                file_name=(book_record or {}).get("file_name") or file_reference_id,
                curriculum_id=curriculum_id,
                version=version,
                query=request.query,
                answer=answer,
                answer_status=answer_status,
                grounded=grounded,
                sources=[s.model_dump() for s in sources],
                retrieval=retrieval_summary.model_dump(),
                evaluation=eval_metrics.model_dump(),
            )
        except Exception:
            logger.exception("Failed to persist conversation turn (session_id=%s)", session_id)

        return ResponsePayload(
            session_id=session_id,
            curriculum_id=curriculum_id,
            version=version,
            file_reference_id=file_reference_id,
            answer=answer,
            answer_status=answer_status,
            grounded=grounded,
            sources=sources,
            retrieval=retrieval_summary,
            evaluation=eval_metrics,
            session_metadata={
                "session_turn": len(session.get("turns", [])),
                "lesson_context": session.get("lesson_context", {}),
                "retrieval_count": len(results),
                "generation_backend": settings.generation_backend,
                "context_chars": len(context),
                "retrieval_confidence": retrieval_confidence,
                "reranker_score": reranker_score,
                "expanded_sources": expanded_count,
                "expansion_misses": len(results) - expanded_count,
            },
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Response processing failed")
        raise HTTPException(status_code=500, detail="Response processing failed. Check server logs for details.") from exc


@app.post(
    "/api/rag/evaluate",
    response_model=EvaluationResponse,
    tags=["evaluation"],
    summary="Evaluate RAG response quality",
    description=(
        "Computes RAGAS-standard metrics (Faithfulness, Context Precision, Context Recall, "
        "Answer Relevancy, Overall RAGAS Score) for any given query, answer, and retrieved context chunks."
    ),
)
def evaluate_rag(request: EvaluationRequest) -> EvaluationResponse:
    metrics = rag_evaluator.evaluate_response(
        query=request.query,
        answer=request.answer,
        sources=[{"raw_text": t} for t in request.context_texts],
        reranker_score=request.reranker_score,
        retrieval_confidence=request.retrieval_confidence,
        ground_truth=request.ground_truth,
    )
    return EvaluationResponse(
        query=request.query,
        answer=request.answer,
        metrics=metrics,
    )

