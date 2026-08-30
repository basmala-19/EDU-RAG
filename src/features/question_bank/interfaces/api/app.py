"""Mobile app-facing HTTP API.

A thin orchestration layer over the in-process features
(``question_bank``, ``knowledge_graph``, ``rag``, ``assessment``) - the
same features the internal Streamlit tool (``main.py`` /
``question_bank/app.py``) already drives directly, just exposed over HTTP
for a real client instead of a server-rendered admin page.

Endpoints:
    POST   /books                          Upload + process a book (async, returns a job_id)
    GET    /books/jobs/{job_id}            Poll a book-processing job
    GET    /books                          List already-processed books (feeds the book picker)
    GET    /books/{content_hash}/topics    Topics available for one processed book
    POST   /exams                          Start an exam: {student_id, grade, subject, content_hash}
    POST   /exams/{exam_id}/answers        Submit an answer -> next question or final results
    GET    /exams/{exam_id}/report         Final LLM-generated report

``POST /books`` deliberately never blocks on the underlying Knowledge Graph
+ RAG + question-generation pipeline (5-8 minutes end to end). See
``book_jobs.py`` for why, and for the status state machine
(queued -> generating_kg -> indexing -> generating_questions -> done/failed).
"""

from __future__ import annotations

import logging
import re
import secrets
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.features.assessment.application.assessment_service import get_assessment_service
from src.features.question_bank import book_library, get_graph_entities, get_questions
from src.features.question_bank.config import get_openrouter_api_key
from src.features.question_bank.interfaces.api.book_jobs import get_book_processing_job_service
from src.features.question_bank.interfaces.api.schemas import (
    BookJobResponse,
    BooksListResponse,
    BookSummary,
    ErrorResponse,
    ExamFlowPayload,
    ExamReportResponse,
    StartExamRequest,
    SubmitAnswerRequest,
    TopicInfo,
    TopicsResponse,
)

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Educational Platform — Mobile API",
    version="1.0.0",
    description=(
        "HTTP surface for the mobile app: process a book as a background job, "
        "list previously processed books, list a book's topics, and run the "
        "adaptive exam flow (start -> answer -> report)."
    ),
    openapi_tags=[
        {"name": "books", "description": "Upload/process books (async) and browse the book library."},
        {"name": "exams", "description": "Start an exam, submit answers, and fetch the final report."},
    ],
)

# Permissive by default, same as the RAG API - tighten allow_origins for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ROOT = Path(__file__).resolve().parents[5]
UPLOAD_DIR = PROJECT_ROOT / "data" / "question_bank" / "uploads"
MAX_UPLOAD_BYTES = 100 * 1024 * 1024

book_jobs = get_book_processing_job_service()


# ---------------------------------------------------------------------------
# Mapping helpers (internal record/dict -> response schema)
# ---------------------------------------------------------------------------
def _book_summary(record: dict[str, Any]) -> BookSummary:
    return BookSummary(
        content_hash=record["content_hash"],
        filename=record["filename"],
        grade=record["grade"],
        subject=record["subject"],
        processed_at=record["processed_at"],
        rag_file_reference_id=record["rag_file_reference_id"],
        indexed_chunks=record.get("indexed_chunks", 0),
        entity_count=record.get("entity_count", 0),
        topics_generated=record.get("topics_generated", 0),
    )


def _job_response(job: dict[str, Any]) -> BookJobResponse:
    return BookJobResponse(
        job_id=job["job_id"],
        status=job["status"],
        stage_detail=job.get("stage_detail"),
        filename=job["filename"],
        grade=job["grade"],
        subject=job["subject"],
        content_hash=job.get("content_hash"),
        result=_book_summary(job["result"]) if job.get("result") else None,
        error=job.get("error"),
    )


def _exam_error(exc: ValueError) -> HTTPException:
    """Map the assessment service's ValueError messages to HTTP status codes."""
    message = str(exc)
    if message.startswith("Unknown exam_id"):
        return HTTPException(status_code=404, detail=message)
    if "not finished yet" in message:
        return HTTPException(status_code=409, detail=message)
    return HTTPException(status_code=400, detail=message)


# ---------------------------------------------------------------------------
# Books
# ---------------------------------------------------------------------------
@app.post(
    "/books",
    response_model=BookJobResponse,
    status_code=202,
    tags=["books"],
    summary="Upload and process a new book (async)",
    description=(
        "Saves the PDF and immediately returns a job_id — it does not wait for the "
        "Knowledge Graph + RAG indexing + question-generation pipeline (typically "
        "5-8 minutes). Poll GET /books/jobs/{job_id} until status is 'done' or "
        "'failed'. If this exact file content was already processed before "
        "(by content hash, regardless of filename), the job completes almost "
        "immediately by reusing the existing book instead of reprocessing it."
    ),
    responses={
        202: {"description": "Job accepted and queued."},
        415: {"model": ErrorResponse, "description": "Only PDF files are supported."},
        422: {"model": ErrorResponse, "description": "grade/subject missing or file missing."},
        500: {"model": ErrorResponse, "description": "OPENROUTER_API_KEY missing, or the upload could not be saved."},
    },
)
async def process_book(
    file: UploadFile = File(..., description="Book PDF"),
    grade: str = Form(..., description='Example: "Grade 5"'),
    subject: str = Form(..., description='Example: "Mathematics"'),
) -> BookJobResponse:
    if not grade.strip() or not subject.strip():
        raise HTTPException(status_code=422, detail="grade and subject are required.")
    try:
        get_openrouter_api_key()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    original_name = Path(file.filename or "book.pdf").name
    if Path(original_name).suffix.lower() != ".pdf":
        raise HTTPException(status_code=415, detail=f"Unsupported file type: only PDF is supported (got '{original_name}').")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    # Random suffix (not just the original name) so two concurrent uploads of
    # files with the same name can never collide on disk before hashing.
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(original_name).stem).strip("._") or "book"
    destination = UPLOAD_DIR / f"{safe_stem}_{secrets.token_hex(8)}.pdf"

    size = 0
    try:
        with destination.open("wb") as out:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="File exceeds 100 MB limit")
                out.write(chunk)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception as exc:
        destination.unlink(missing_ok=True)
        logger.exception("Failed to save uploaded book")
        raise HTTPException(status_code=500, detail="Failed to save the uploaded file. Check server logs for details.") from exc
    finally:
        await file.close()

    job = book_jobs.submit(pdf_path=destination, filename=original_name, grade=grade.strip(), subject=subject.strip())
    logger.info(
        "Queued book-processing job=%s file=%s grade=%s subject=%s",
        job.job_id, original_name, grade, subject,
    )
    return _job_response(job.public())


@app.get(
    "/books/jobs/{job_id}",
    response_model=BookJobResponse,
    tags=["books"],
    summary="Poll a book-processing job",
    description=(
        "Status progresses queued -> generating_kg -> indexing -> "
        "generating_questions -> done (or -> failed from any stage). "
        "Once status is 'done', 'result' has the same shape as an entry in "
        "GET /books and content_hash is ready to use for POST /exams."
    ),
    responses={404: {"model": ErrorResponse, "description": "Unknown job_id."}},
)
def get_book_job(job_id: str) -> BookJobResponse:
    job = book_jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Unknown job_id.")
    return _job_response(job)


@app.get(
    "/books",
    response_model=BooksListResponse,
    tags=["books"],
    summary="List already-processed books",
    description="Feeds the mobile app's book picker: books already run through the full pipeline, most recent first.",
)
def list_books() -> BooksListResponse:
    return BooksListResponse(books=[_book_summary(record) for record in book_library.list_books()])


@app.get(
    "/books/{content_hash}/topics",
    response_model=TopicsResponse,
    tags=["books"],
    summary="List a book's topics",
    description=(
        "Topics come from the book's Knowledge Graph. has_questions reports "
        "whether that topic already has saved questions in the Question Bank "
        "(it always will for a book returned by GET /books, since processing "
        "generates questions for every topic — this is here for completeness "
        "and for books whose graph was later extended)."
    ),
    responses={404: {"model": ErrorResponse, "description": "Unknown content_hash."}},
)
def list_book_topics(content_hash: str) -> TopicsResponse:
    book = book_library.get_book(content_hash)
    if book is None:
        raise HTTPException(status_code=404, detail="Unknown content_hash. Check GET /books for available books.")

    entities = get_graph_entities(book["knowledge_graph"])
    topics = [
        TopicInfo(
            id=entity["id"],
            name=entity["name"],
            has_questions=bool(get_questions(book["grade"], book["subject"], entity["id"])),
        )
        for entity in entities
    ]
    return TopicsResponse(
        content_hash=content_hash,
        filename=book["filename"],
        grade=book["grade"],
        subject=book["subject"],
        topics=topics,
    )


# ---------------------------------------------------------------------------
# Exams
# ---------------------------------------------------------------------------
@app.post(
    "/exams",
    tags=["exams"],
    summary="Start an exam",
    description=(
        "Resolves content_hash to a processed book's Knowledge Graph, then "
        "starts the adaptive exam for student_id. Returns the first question. "
        "grade/subject must match how the book was processed (see GET /books)."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "grade/subject mismatch, or no topic has saved questions yet."},
        404: {"model": ErrorResponse, "description": "Unknown content_hash."},
    },
)
def start_exam(request: StartExamRequest) -> ExamFlowPayload:
    book = book_library.get_book(request.content_hash)
    if book is None:
        raise HTTPException(status_code=404, detail="Unknown content_hash. Check GET /books for available books.")

    if (
        book["grade"].strip().casefold() != request.grade.strip().casefold()
        or book["subject"].strip().casefold() != request.subject.strip().casefold()
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"grade/subject does not match this book: it was processed as "
                f"grade={book['grade']!r} subject={book['subject']!r}."
            ),
        )

    try:
        return get_assessment_service().start_exam_from_knowledge_graph(
            student_id=request.student_id.strip(),
            grade=book["grade"],
            subject=book["subject"],
            knowledge_graph=book["knowledge_graph"],
        )
    except ValueError as exc:
        raise _exam_error(exc) from exc


@app.get(
    "/exams/{exam_id}",
    tags=["exams"],
    summary="Get current exam state",
    description=(
        "Read-only - never advances the exam. Lets a client that reopened "
        "the app (or that just wants to poll) find out where an exam "
        "currently stands: either the question the student is still on "
        "(status 'in_progress') or the final results if it already ended "
        "(status 'exam_ended')."
    ),
    responses={404: {"model": ErrorResponse, "description": "Unknown exam_id."}},
)
def get_exam_state(exam_id: str) -> ExamFlowPayload:
    try:
        return get_assessment_service().get_exam_state(exam_id)
    except ValueError as exc:
        raise _exam_error(exc) from exc


@app.post(
    "/exams/{exam_id}/answers",
    tags=["exams"],
    summary="Submit an answer",
    description=(
        "Grades the submitted answer and drives the adaptive state machine: "
        "returns either the next question (status 'next_question' or "
        "'next_topic_first_question') or, once every topic is done, the "
        "final per-topic results (status 'exam_ended')."
    ),
    responses={404: {"model": ErrorResponse, "description": "Unknown exam_id or question_id."}},
)
def submit_answer(exam_id: str, request: SubmitAnswerRequest) -> ExamFlowPayload:
    try:
        return get_assessment_service().process_answer(exam_id, request.question_id, request.answer)
    except ValueError as exc:
        raise _exam_error(exc) from exc


@app.get(
    "/exams/{exam_id}/report",
    response_model=ExamReportResponse,
    tags=["exams"],
    summary="Get the final LLM report",
    description=(
        "Only available once the exam has ended (status 'exam_ended' from "
        "POST /exams/{exam_id}/answers). The report is generated once and "
        "cached for the life of the exam session."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Unknown exam_id."},
        409: {"model": ErrorResponse, "description": "Exam has not finished yet."},
    },
)
def get_exam_report(exam_id: str) -> ExamReportResponse:
    try:
        report = get_assessment_service().get_report(exam_id)
    except ValueError as exc:
        raise _exam_error(exc) from exc
    return ExamReportResponse(exam_id=exam_id, report=report)
