from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class ChunkMetadata(BaseModel):
    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "curriculum_id": "cur_8b5d7f5edb84",
                "version": "v1",
                "subject": "تكنولوجيا المعلومات والاتصالات",
                "grade": "الأول",
                "term": 1,
                "language": "ar",
                "source": "ICT_Ar_Sec1_T1.pdf",
                "page": 8,
                "heading": "البيانات، المعلومات، المعرفة",
                "heading_path": ["1-1 المعلومات والوسائط", "البيانات، المعلومات، المعرفة"],
                "chapter": "1-1 المعلومات والوسائط",
                "lesson": "النقاط الرئيسية",
                "parser": "llamaparse",
            }
        },
    )
    curriculum_id: str = Field(description="Unique identity of the curriculum document.")
    version: str = Field(description="Curriculum index version.")
    subject: str | None = Field(default=None, description="Academic subject name.")
    grade: str | int | None = Field(default=None, description="Target educational grade level.")
    term: str | int | None = Field(default=None, description="School term or semester.")
    language: str = Field(default="mixed", description="Detected language code ('ar', 'en', or 'mixed').")
    source: str | None = Field(default=None, description="Original source filename.")
    source_type: str | None = Field(default=None, description="File extension ('pdf', 'docx', 'txt').")
    page: int | None = Field(default=None, description="Original page number in source PDF.")
    file_reference_id: str | None = Field(default=None, description="Unique upload reference ID.")
    parser: str | None = Field(default=None, description="Parser backend used ('llamaparse' or 'pymupdf').")
    heading: str | None = Field(default=None, description="Immediate section heading.")
    heading_level: int | None = Field(default=None, description="Heading level in document tree.")
    heading_path: list[str] = Field(default_factory=list, description="Full structural hierarchy path.")
    chapter: str | None = Field(default=None, description="Chapter title.")
    lesson: str | None = Field(default=None, description="Lesson title.")
    section: str | None = Field(default=None, description="Section title.")
    topic: str | None = Field(default=None, description="Topic title.")
    content_type: str | None = Field(default=None, description="Content classification ('definition', 'exercise', 'paragraph').")
    parent_chunk_id: str | None = Field(default=None, description="Parent chunk ID for parent-child retrieval expansion.")
    chunk_role: str | None = Field(default=None, description="Role of chunk in hierarchy ('child' or 'parent').")


class RAGChunk(BaseModel):
    chunk_id: str = Field(description="Unique 16-char SHA1 identifier of the chunk.")
    raw_text: str = Field(min_length=1, description="Raw chunk text content.")
    normalized_text: str | None = Field(default=None, description="Normalized Arabic/English text for vector matching.")
    metadata: ChunkMetadata = Field(description="Rich chunk metadata.")
    parent_chunk_id: str | None = Field(default=None, description="Parent chunk ID if child chunk.")


class RetrievalRequest(BaseModel):
    query: str = Field(min_length=1, description="Search query string.")
    file_reference_id: str = Field(min_length=1, description="Target file reference ID.")
    session_id: str | None = Field(default=None, description="Optional active session ID.")
    top_k: int = Field(default=5, ge=1, le=20, description="Top K candidates to return.")
    filters: dict[str, Any] = Field(default_factory=dict, description="Metadata key-value filters.")


class RetrievalResult(BaseModel):
    chunk_id: str = Field(description="Chunk ID.")
    raw_text: str = Field(description="Chunk text.")
    score: float = Field(description="Final hybrid rerank score.")
    metadata: dict[str, Any] = Field(description="Chunk metadata.")


class RetrievalResponse(BaseModel):
    results: list[RetrievalResult] = Field(description="List of retrieved evidence chunks.")


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
    """Client-owned input for the single retrieval + generation operation."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "query": "ما هو البث التجريبي للراديو وما هي المعرفة؟",
        "file_reference_id": "0567486a32785a3d6e708f40dbf2cff7",
        "session_id": "sess_12345",
        "lesson_context": {"chapter": "معلومات ووسائط", "lesson": "النقاط الرئيسية"},
        "top_k": 5,
    }})
    query: str = Field(min_length=1, description="Student's current question to answer from the selected curriculum file.", examples=["ما هي المعرفة؟"])
    file_reference_id: str | None = Field(
        default=None,
        min_length=1,
        description="Isolation boundary: retrieval is restricted to this exact uploaded file reference ID.",
        examples=["0567486a32785a3d6e708f40dbf2cff7"],
    )
    session_id: str | None = Field(default=None, description="Learning-session ID for conversational context tracking.", examples=["sess_12345"])
    lesson_context: LessonSessionContext | None = Field(default=None, description="Current chapter/lesson from the learning platform's UI.")
    top_k: int = Field(default=5, ge=1, le=10, description="Number of top evidence candidates used after retrieval and reranking.", examples=[5])


class ResponseSource(BaseModel):
    chunk_id: str = Field(description="Unique chunk ID.")
    page: int | None = Field(default=None, description="Page number in PDF.")
    source: str | None = Field(default=None, description="Source PDF filename.")
    heading: str | None = Field(default=None, description="Nearest section heading.")
    chapter: str | None = Field(default=None, description="Chapter title.")
    lesson: str | None = Field(default=None, description="Lesson title.")
    section: str | None = Field(default=None, description="Section title.")
    topic: str | None = Field(default=None, description="Topic title.")
    heading_path: list[str] | None = Field(default=None, description="Full structural breadcrumb path.")
    content_type: str | None = Field(default=None, description="Detected content type ('paragraph', 'exercise', 'definition').")
    parent_chunk_id: str | None = Field(default=None, description="Parent chunk ID if expanded.")
    score: float = Field(default=0.0, description="Composite hybrid rank score.")
    retrieval_confidence: float | None = Field(default=None, description="Confidence score for this candidate (0.0 to 1.0).")
    reranker_score: float | None = Field(default=None, description="Cross-encoder reranker score.")
    retrieval_channels: list[str] = Field(default_factory=list, description="Channels that matched this chunk ('semantic', 'keyword', 'question').")
    context_expanded: bool = Field(default=False, description="True if expanded to full parent chunk context.")
    raw_text: str | None = Field(default=None, description="The exact chunk text used for grounding.")
    metadata: dict = Field(default_factory=dict, description="Complete metadata dictionary.")


class RetrievalSummary(BaseModel):
    mode: Literal["hybrid"] = "hybrid"
    query_used: str = Field(description="Query string used after contextual rewrite.")
    candidate_count: int = Field(description="Number of candidate chunks evaluated.")
    top_score: float = Field(description="Top candidate's hybrid rank score.")
    grounding_threshold: float = Field(description="Configured grounding threshold.")
    semantic_score: float = Field(default=0.0, description="Vector similarity score (1 - cosine distance).")
    keyword_score: float = Field(default=0.0, description="BM25 keyword match score.")
    question_score: float = Field(default=0.0, description="Question index match score.")
    rrf_score: float = Field(default=0.0, description="Reciprocal Rank Fusion score.")
    reranker_score: float = Field(default=0.0, description="Cross-encoder reranker score.")
    retrieval_confidence: float = Field(default=0.0, description="Overall confidence score (0.0 to 1.0).")


class EvaluationMetrics(BaseModel):
    """RAG Evaluation Metrics suite (RAG Triad & RAGAS standards)."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "faithfulness_score": 0.9500,
        "context_precision": 0.8800,
        "context_recall": 0.9000,
        "answer_relevance": 0.9200,
        "overall_ragas_score": 0.9150,
        "verdict": "PASS",
        "details": {"context_chunks_count": 5, "reranker_score": 0.6816, "retrieval_confidence": 0.7256}
    }})
    faithfulness_score: float = Field(description="Measures if the generated answer is strictly grounded in retrieved evidence (0.0 to 1.0).")
    context_precision: float = Field(description="Measures the signal-to-noise ratio in retrieved context chunks (0.0 to 1.0).")
    context_recall: float = Field(description="Measures how completely the retrieved context covers the query/ground-truth (0.0 to 1.0).")
    answer_relevance: float = Field(description="Measures how directly the generated answer addresses the student's question (0.0 to 1.0).")
    overall_ragas_score: float = Field(description="Composite weighted RAGAS score across all sub-metrics (0.0 to 1.0).")
    verdict: Literal["PASS", "NEEDS_IMPROVEMENT", "FAIL"] = Field(description="Automatic quality verdict classification.")
    details: dict[str, Any] = Field(default_factory=dict, description="Detailed diagnostic evaluation metadata.")


class EvaluationRequest(BaseModel):
    """Payload to trigger on-demand RAG evaluation."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "query": "ما هي المعرفة؟",
        "answer": "المعرفة هي المعلومات التي تم تحليلها وتنظيمها بشكل منهجي للمساعدة في حل المشكلات.",
        "context_texts": [
            "المعرفة (Knowledge): هي المعلومات التي تم تحليلها وتنظيمها بشكل منهجي للمساعدة في حل المشكلات."
        ],
        "ground_truth": "المعرفة هي المعلومات المحللة والمنظمة لحل المشكلات.",
        "reranker_score": 0.6750,
        "retrieval_confidence": 0.8050
    }})
    query: str = Field(min_length=1, description="Student query string.")
    answer: str = Field(min_length=1, description="Generated answer to evaluate.")
    context_texts: list[str] = Field(default_factory=list, description="List of raw context strings retrieved for grounding.")
    ground_truth: str | None = Field(default=None, description="Optional ideal reference answer for exact recall benchmark.")
    reranker_score: float = Field(default=0.0, description="Reranker score of top chunk.")
    retrieval_confidence: float = Field(default=0.0, description="Retrieval confidence score.")


class EvaluationResponse(BaseModel):
    """Response envelope for on-demand RAG evaluation."""
    query: str = Field(description="Evaluated query.")
    answer: str = Field(description="Evaluated answer.")
    metrics: EvaluationMetrics = Field(description="Calculated RAG evaluation metrics.")


class ResponsePayload(BaseModel):
    """Backend-owned output contract for the response endpoint."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "session_id": "sess_12345",
        "curriculum_id": "cur_8b5d7f5edb84",
        "version": "v1",
        "file_reference_id": "0567486a32785a3d6e708f40dbf2cff7",
        "answer": "المعرفة هي المعلومات التي تم تحليلها وتنظيمها بشكل منهجي لتساعد في حل المشكلات.",
        "answer_status": "answered",
        "grounded": True,
        "sources": [],
        "retrieval": {
            "mode": "hybrid",
            "query_used": "ما هي المعرفة",
            "candidate_count": 5,
            "top_score": 0.7907,
            "grounding_threshold": 0.44,
            "semantic_score": 0.5857,
            "keyword_score": 7.057,
            "question_score": 0.9109,
            "rrf_score": 0.9841,
            "reranker_score": 0.6750,
            "retrieval_confidence": 0.8050
        },
        "evaluation": {
            "faithfulness_score": 0.9650,
            "context_precision": 0.8900,
            "context_recall": 0.9200,
            "answer_relevance": 0.9500,
            "overall_ragas_score": 0.9350,
            "verdict": "PASS"
        },
        "session_metadata": {"session_turn": 1}
    }})
    session_id: str = Field(description="Learning-session ID used for this turn. Generated or reused by the backend.")
    curriculum_id: str = Field(description="Curriculum identity resolved by the backend from the indexed document.")
    version: str = Field(description="Indexed curriculum version resolved by the backend.")
    file_reference_id: str = Field(description="The exact uploaded file used as the retrieval boundary.")
    answer: str = Field(description="Grounded answer generated from retrieved curriculum evidence.")
    answer_status: Literal["answered", "insufficient_evidence", "grounding_failed"] = Field(default="answered", description="Status of answer generation.")
    grounded: bool = Field(default=True, description="True if evidence grounding criteria were satisfied.")
    sources: list[ResponseSource] = Field(default_factory=list, description="Evidence references used to build the answer.")
    retrieval: RetrievalSummary | None = Field(default=None, description="Retrieval performance summary.")
    evaluation: EvaluationMetrics | None = Field(default=None, description="Automatic RAG evaluation metrics (RAGAS / Faithfulness / Relevancy / Precision / Recall).")
    session_metadata: dict[str, Any] = Field(default_factory=dict, description="Learning-session state relevant to this response.")


class DocumentMetadataResponse(BaseModel):
    document_title: str | None = None
    subject: str | None = None
    grade: str | int | None = None
    term: str | int | None = None
    language: str | None = None
    text_quality_warning: str | None = Field(
        default=None,
        description="Set (e.g. 'arabic_font_ligature_corruption') when the source PDF's embedded font is known to garble text extraction.",
    )
    sources: dict[str, str | None] = Field(default_factory=dict)
    confidence: dict[str, float] = Field(default_factory=dict)
    evidence: dict[str, str | None] = Field(default_factory=dict)


class IngestionResponse(BaseModel):
    curriculum_id: str = Field(description="Resolved curriculum ID.")
    version: str = Field(description="Curriculum version.")
    files_processed: int = Field(description="Number of files processed.")
    chunks_created: int = Field(description="Number of child/parent chunks created.")
    indexed_chunks: int = Field(description="Number of vector indexed chunks.")
    indexed_question_count: int = Field(default=0, description="Number of indexed hypothetical questions.")
    language_counts: dict[str, int] = Field(description="Language distribution.")
    metadata_coverage: dict[str, float] = Field(default_factory=dict, description="Metadata extraction completeness percentages.")
    document_metadata: DocumentMetadataResponse | None = Field(default=None, description="Document metadata.")


class UploadResponse(IngestionResponse):
    """Backend-owned result returned after a file is parsed and indexed."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "file_reference_id": "0567486a32785a3d6e708f40dbf2cff7",
        "file_name": "ICT_Ar_Sec1_T1.pdf",
        "size_bytes": 14258900,
        "status": "indexed",
        "duplicate": False,
        "curriculum_id": "cur_8b5d7f5edb84",
        "version": "v1",
        "files_processed": 1,
        "chunks_created": 128,
        "indexed_chunks": 128,
        "indexed_question_count": 384,
        "language_counts": {"ar": 115, "mixed": 13}
    }})
    file_reference_id: str = Field(description="Unique file identity generated by the backend.")
    file_name: str = Field(description="Original safe filename supplied by the client.")
    size_bytes: int = Field(description="Uploaded file size in bytes.")
    status: str = Field(default="indexed", description="Indexing status.")
    duplicate: bool = Field(
        default=False,
        description="True if this exact file content was already ingested before (by content hash, regardless of filename) and re-ingestion was skipped.",
    )


class IngestionJobResponse(BaseModel):
    """Asynchronous ingestion job returned immediately after the file upload finishes."""
    job_id: str = Field(description="Asynchronous ingestion job ID.")
    status: Literal["queued", "processing", "completed", "failed"] = Field(description="Current job lifecycle status.")
    file_reference_id: str = Field(description="File reference ID.")
    file_name: str = Field(description="File name.")
    size_bytes: int = Field(description="Size in bytes.")
    result: UploadResponse | None = Field(default=None, description="Completed upload response payload.")
    error: str | None = Field(default=None, description="Error message if job failed.")


class ErrorResponse(BaseModel):
    """Stable error envelope returned by the API."""
    detail: str = Field(description="Safe client-facing error message.")


class HealthResponse(BaseModel):
    status: str = Field(description="Service health status ('healthy' or 'unhealthy').")
    embedding_backend: str = Field(description="Configured embedding backend name.")
    vector_store_backend: str = Field(description="Configured vector store backend name.")
