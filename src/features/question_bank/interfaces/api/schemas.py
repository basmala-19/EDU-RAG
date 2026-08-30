"""Request/response models for the mobile API (``interfaces/api/app.py``).

Kept separate from the endpoint module for the same reason ``rag/domain/
schemas.py`` is separate from ``rag/interfaces/api/app.py``: the shapes are
a contract with the mobile client and are easier to review, version, and
reuse (e.g. in tests) when they are not interleaved with route handlers.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

# queued -> generating_kg -> indexing -> generating_questions -> done
# (or -> failed from any non-terminal state)
BookJobStatus = Literal[
    "queued",
    "generating_kg",
    "indexing",
    "generating_questions",
    "done",
    "failed",
]


class BookSummary(BaseModel):
    """One entry in the book picker (``GET /books``). Deliberately excludes
    the full Knowledge Graph JSON, which can be large - fetch topics for a
    specific book via ``GET /books/{content_hash}/topics`` instead."""

    content_hash: str
    filename: str
    grade: str
    subject: str
    processed_at: str = Field(..., description="ISO-8601 UTC timestamp of when processing finished.")
    rag_file_reference_id: str
    indexed_chunks: int
    entity_count: int
    topics_generated: int


class BooksListResponse(BaseModel):
    books: list[BookSummary] = Field(default_factory=list, description="Most recently processed first.")


class BookJobResponse(BaseModel):
    """Returned immediately by ``POST /books`` and again by every poll of
    ``GET /books/jobs/{job_id}``."""

    job_id: str
    status: BookJobStatus
    stage_detail: str | None = Field(None, description="Human-readable description of the current stage.")
    filename: str
    grade: str
    subject: str
    content_hash: str | None = Field(None, description="Known as soon as the Knowledge Graph stage completes.")
    result: BookSummary | None = Field(None, description="Set once status is 'done'.")
    error: str | None = Field(None, description="Set once status is 'failed'.")


class TopicInfo(BaseModel):
    id: str
    name: str
    type: str | None = None
    has_questions: bool = Field(..., description="Whether this topic already has saved questions in the Question Bank.")


class TopicsResponse(BaseModel):
    content_hash: str
    filename: str
    grade: str
    subject: str
    topics: list[TopicInfo]


class StartExamRequest(BaseModel):
    student_id: str = Field(..., min_length=1)
    grade: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    content_hash: str = Field(..., min_length=1, description="content_hash of a book from GET /books.")


class SubmitAnswerRequest(BaseModel):
    question_id: str = Field(..., min_length=1)
    answer: str | list[str] | None = Field(
        None, description="Option key for MCQ, list of option keys for MSQ, or null for a timeout/skip."
    )


class ExamReportResponse(BaseModel):
    exam_id: str
    report: str = Field(..., description="LLM-generated, student/parent-readable report (Markdown).")


class ErrorResponse(BaseModel):
    detail: str


# `question`, `results`, and the exam-flow payloads below intentionally stay
# as plain dicts (Dict[str, Any]) rather than pydantic models in app.py: the
# assessment_service response shape genuinely varies by outcome
# (next_question / next_topic_first_question / exam_ended), and it is
# already stable, tested application-layer output - re-modeling it here
# would just be a second, easy-to-drift copy of the same contract.
ExamFlowPayload = dict[str, Any]
