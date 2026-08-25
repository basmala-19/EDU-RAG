from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class ChunkMetadata(BaseModel):
    model_config = ConfigDict(extra="allow")
    curriculum_id: str
    version: str
    subject: str | None = None
    grade: str | int | None = None
    term: str | int | None = None
    language: str = "mixed"
    source: str | None = None
    source_type: str | None = None
    page: int | None = None
    file_reference_id: str | None = None
    parser: str | None = None
    heading: str | None = None
    heading_level: int | None = None
    heading_path: list[str] = Field(default_factory=list)
    chapter: str | None = None
    lesson: str | None = None
    section: str | None = None
    topic: str | None = None
    content_type: str | None = None
    parent_chunk_id: str | None = None
    chunk_role: str | None = None


class RAGChunk(BaseModel):
    chunk_id: str
    raw_text: str = Field(min_length=1)
    normalized_text: str | None = None
    metadata: ChunkMetadata
    parent_chunk_id: str | None = None


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1)
    file_reference_id: str = Field(min_length=1)
    session_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)
    filters: dict[str, Any] = Field(default_factory=dict)


class RetrievalResult(BaseModel):
    chunk_id: str
    raw_text: str
    score: float
    metadata: dict[str, Any]


class RetrievalResponse(BaseModel):
    results: list[RetrievalResult]


class LessonSessionContext(BaseModel):
    """Optional learning-session context supplied by the client/UI."""
    subject: str | None = Field(default=None, description="Subject currently being studied.")
    grade: str | int | None = Field(default=None, description="Grade currently being studied.")
    chapter: str | None = Field(default=None, description="Current chapter/lesson-group label.")
    lesson: str | None = Field(default=None, description="Current lesson label.")
    section: str | None = Field(default=None, description="Current section/topic label.")


class UploadInput(BaseModel):
    """Logical input contract for upload; the actual transport is multipart/form-data file-only."""
    model_config = ConfigDict(json_schema_extra={"example": {"file": "ICT_Ar_Sec1_T1.pdf"}})


class ResponseRequest(BaseModel):
    """Client-owned input for the single retrieval + generation operation.

    Only the FIRST call of a learning session (no session_id yet, or a session_id the
    backend has never seen) needs to carry file_reference_id / lesson_context. The
    backend binds them to the new session_id it returns; every follow-up call in that
    session only needs session_id + query — file_reference_id and lesson_context are
    remembered server-side and must not be re-typed by the client.
    """
    model_config = ConfigDict(json_schema_extra={"example": {
        "query": "ما هو التعلم الآلي؟",
        "file_reference_id": "04e447216124c10119e07f56924cca51",
        "session_id": None,
        "lesson_context": {"chapter": "الذكاء الاصطناعي", "lesson": "التعلم الآلي"},
        "top_k": 5,
    }})
    query: str = Field(min_length=1, description="Student's current question to answer from the selected curriculum file.", examples=["ما هو التعلم الآلي؟"])
    file_reference_id: str | None = Field(
        default=None,
        min_length=1,
        description=(
            "Isolation boundary: retrieval is restricted to this exact uploaded file. "
            "Required only to START a new learning session (session_id omitted, or not "
            "yet known to the backend). Omit it on every follow-up call that reuses an "
            "existing session_id — the backend already has it bound to that session and "
            "will reuse it automatically. If you send it anyway on a follow-up, it must "
            "match the file the session was started with, or the call fails with 400."
        ),
        examples=["file_example"],
    )
    session_id: str | None = Field(default=None, description="Learning-session ID. Omit on the first call; the backend generates one and returns it. Send it back on every follow-up question in the same learning session.", examples=["sess_123"])
    lesson_context: LessonSessionContext | None = Field(
        default=None,
        description=(
            "Current chapter/lesson from the learning platform's UI, used (a) to narrow "
            "retrieval to that part of the file when the file covers more than one lesson, "
            "and (b) to disambiguate short follow-up questions (e.g. 'اديني مثال'). "
            "Only needed when starting a session or when the student navigates to a "
            "different lesson mid-session; the backend remembers the last value per "
            "session, so it is NOT required on every turn."
        ),
    )
    top_k: int = Field(default=5, ge=1, le=10, description="Number of top evidence candidates used after retrieval and reranking.", examples=[5])


class ResponseSource(BaseModel):
    chunk_id: str
    page: int | None = None
    source: str | None = None
    heading: str | None = None
    chapter: str | None = None
    lesson: str | None = None
    section: str | None = None
    topic: str | None = None
    heading_path: list[str] | None = None
    content_type: str | None = None
    parent_chunk_id: str | None = None
    score: float = 0.0
    retrieval_confidence: float | None = None
    reranker_score: float | None = None
    retrieval_channels: list[str] = Field(default_factory=list)
    context_expanded: bool = Field(
        default=False,
        description="True if this source's full parent-chunk context was used; False means only the short child chunk was available (parent-expansion miss).",
    )
    raw_text: str | None = Field(
        default=None,
        description="The exact chunk/context text the answer was grounded on, for evidence display.",
    )
    metadata: dict = Field(
        default_factory=dict,
        description="Full raw metadata dict for this chunk (everything the retriever/chunker attached), for callers that need fields beyond the typed ones above.",
    )


class RetrievalSummary(BaseModel):
    mode: Literal["hybrid"] = "hybrid"
    query_used: str
    candidate_count: int
    top_score: float
    grounding_threshold: float
    semantic_score: float = 0.0
    keyword_score: float = 0.0
    question_score: float = 0.0
    rrf_score: float = 0.0
    reranker_score: float = 0.0
    retrieval_confidence: float = 0.0


class ResponsePayload(BaseModel):
    """Backend-owned output contract for the response endpoint."""
    session_id: str = Field(description="Learning-session ID used for this turn. Generated or reused by the backend.")
    curriculum_id: str = Field(description="Curriculum identity resolved by the backend from the indexed document.")
    version: str = Field(description="Indexed curriculum version resolved by the backend.")
    file_reference_id: str = Field(description="The exact uploaded file used as the retrieval boundary.")
    answer: str = Field(description="Grounded answer generated from retrieved curriculum evidence.")
    answer_status: Literal["answered", "insufficient_evidence", "grounding_failed"] = "answered"
    grounded: bool = True
    sources: list[ResponseSource] = Field(default_factory=list, description="Evidence references used to build the answer.")
    retrieval: RetrievalSummary | None = None
    session_metadata: dict[str, Any] = Field(default_factory=dict, description="Learning-session state relevant to this response; not document metadata.")


class DocumentMetadataResponse(BaseModel):
    document_title: str | None = None
    subject: str | None = None
    grade: str | int | None = None
    term: str | int | None = None
    language: str | None = None
    text_quality_warning: str | None = Field(
        default=None,
        description="Set (e.g. 'arabic_font_ligature_corruption') when the source PDF's embedded font is known to garble text extraction, signalling the admin should re-upload via OCR instead of trusting this book's extracted text.",
    )
    sources: dict[str, str | None] = Field(default_factory=dict)
    confidence: dict[str, float] = Field(default_factory=dict)
    evidence: dict[str, str | None] = Field(default_factory=dict)


class IngestionResponse(BaseModel):
    curriculum_id: str
    version: str
    files_processed: int
    chunks_created: int
    indexed_chunks: int
    indexed_question_count: int = 0
    language_counts: dict[str, int]
    metadata_coverage: dict[str, float] = Field(default_factory=dict)
    document_metadata: DocumentMetadataResponse | None = None


class UploadResponse(IngestionResponse):
    """Backend-owned result returned after a file is parsed and indexed."""
    file_reference_id: str = Field(description="Unique file identity generated by the backend.")
    file_name: str = Field(description="Original safe filename supplied by the client.")
    size_bytes: int = Field(description="Uploaded file size in bytes.")
    status: str = Field(default="indexed", description="Indexing status.")
    duplicate: bool = Field(
        default=False,
        description="True if this exact file content was already ingested before (by content hash, regardless of filename) and re-ingestion was skipped. The returned curriculum_id/file_reference_id are the original ones. Pass ?force_reingest=true to re-ingest anyway.",
    )


class SubjectStructure(BaseModel):
    subject: str
    grades: list[str] = Field(default_factory=list)


class ChapterStructure(BaseModel):
    chapter: str
    lessons: list[str] = Field(default_factory=list)


class CurriculumStructureResponse(BaseModel):
    """Progressive discovery of what's actually indexed: subjects -> grades -> chapters ->
    lessons, in whatever language and spelling the source book used. Call with no params to
    list subjects; add subject to list its grades; add both to get the chapter/lesson tree."""
    subject: str | None = None
    grade: str | None = None
    subjects: list[SubjectStructure] | None = None
    grades: list[str] | None = None
    chapters: list[ChapterStructure] | None = None


class ErrorResponse(BaseModel):
    """Stable error envelope returned by the API."""
    detail: str = Field(description="Safe client-facing error message.")


class HealthResponse(BaseModel):
    status: str
    embedding_backend: str
    vector_store_backend: str
