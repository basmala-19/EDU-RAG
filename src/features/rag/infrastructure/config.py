from functools import lru_cache
from pathlib import Path
import os
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    app_env: str = "local"
    log_level: str = "INFO"
    cors_origins: str = "http://127.0.0.1:8000,http://localhost:8000"
    rag_upload_dir: str = "data/raw/uploads"
    embedding_backend: str = "openrouter"
    embedding_model: str = "baai/bge-m3"
    embedding_device: str = "cpu"
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_timeout: int = 90
    vector_store: str = "chroma"
    chroma_path: str = "data/vector_store/chroma"
    # Disable Chroma's anonymous product telemetry by default. It is unnecessary for
    # local deployments and avoids background telemetry errors from old Chroma clients.
    chroma_anonymized_telemetry: bool = False
    top_k: int = 5
    # SPEED: lowered from 8 → 6. This only widens/narrows the pool RRF fusion picks
    # from locally (Chroma query + in-process ranking) before the network-bound
    # reranker step ever runs — it does NOT change how many candidates get sent to
    # the OpenRouter rerank API (that's capped separately by reranker_candidates
    # below), so this trims local compute/IO with negligible recall risk.
    candidate_multiplier: int = 6
    # Floor on the raw dense-search fetch size, independent of top_k/candidate_multiplier.
    # Before this existed, a request at the default top_k=5 only pulled candidate_k=40
    # raw dense hits (5*8) - a page-level chunk with a degraded embedding (e.g. from
    # OCR/ligature-corrupted source text) can rank just outside a window that narrow, so
    # it gets dropped before RRF/rerank ever sees it, even though it scores #1 once it
    # does get evaluated. This only affects the cheap initial fetch - the expensive
    # CrossEncoder stage stays capped separately by reranker_candidates regardless.
    # SPEED: lowered from 160 → 100. Same local-only pool as candidate_multiplier
    # above; 100 is still far wider than top_k*candidate_multiplier ever needs to be
    # for a single-book retrieval scope, so this is a pure local-latency trim.
    min_candidate_k: int = 100
    # Parent/child retrieval: children for matching, parents for generation context.
    parent_chunk_size: int = 1600
    child_chunk_size: int = 650
    child_chunk_overlap: int = 80
    child_chunk_min_size: int = 220
    heading_max_length: int = 180
    max_context_chars: int = 6000
    max_history_chars: int = 3500
    max_session_turns: int = 6
    # In-memory session store bounds. Sessions idle longer than session_ttl_seconds are
    # evicted (both lazily on access and by a periodic background sweep started at app
    # startup); max_sessions is a hard cap enforced via LRU eviction as a safety net so
    # a burst of session creation can never grow the store unbounded even inside the TTL
    # window. This store is per-process/in-memory — if you ever run more than one worker
    # or replica, sessions won't be shared across them and you'd want an external store
    # (e.g. Redis) instead; not needed for a single-instance deployment.
    session_ttl_seconds: int = 3600
    max_sessions: int = 10000
    session_sweep_interval_seconds: int = 300
    # Lightweight deterministic reranking (local RRF fusion, before the network reranker).
    # QUALITY: rebalanced semantic vs. keyword. keyword_weight (literal word overlap) was
    # dominating semantic_weight (meaning-based similarity) 0.40 vs 0.30, which favors
    # exact-wording matches over paraphrased student questions. Nudged toward semantic so
    # a reworded question still surfaces the right chunk, while keyword matching still
    # carries the single highest individual weight for precise terminology/definitions.
    semantic_weight: float = 0.34
    question_weight: float = 0.10
    keyword_weight: float = 0.36
    heading_weight: float = 0.12
    content_type_weight: float = 0.08
    lexical_candidate_k: int = 64
    min_grounding_score: float = 0.44
    # Pre-generation gate: only skip the (costly) generation call for retrieval that is
    # catastrophically irrelevant. Kept far below min_grounding_score/0.42 on purpose —
    # bge-reranker-v2-m3 is calibrated on English and scores equally relevant Arabic
    # passages ~0.20-0.25 lower than comparable English ones, so a flat 0.42/0.44 cutoff
    # here silenced valid Arabic answers before the model ever saw the evidence. The real
    # grounding verdict comes from the model's self-reported status, not this pre-check.
    # NOTE: this deployment's reranker_backend is "openrouter" (cohere/rerank-v3.5), not
    # the local bge-reranker-v2-m3 this comment was originally calibrated against — cohere's
    # multilingual scores may not carry the same Arabic penalty. Left unchanged here
    # deliberately: tightening/loosening a grounding gate without labeled examples risks
    # trading unnoticed hallucinations for unnoticed false "insufficient evidence" answers
    # in either direction. Recalibrate this once you have a labeled sample of real Q&A
    # pairs scored by cohere/rerank-v3.5, not by guesswork.
    min_reranker_score_floor: float = 0.15
    min_retrieval_confidence_floor: float = 0.15
    # When the plain (un-augmented) query already retrieves with confidence at or above
    # this bar, skip the second, history/lesson-context-augmented retrieval entirely —
    # a clearly strong direct match is extremely unlikely to be beaten by the augmented
    # query, so paying for a second embed + dense/keyword/question query + rerank pass
    # buys nothing in that case. Only genuinely ambiguous follow-ups (which score below
    # this on the plain query) still pay for the second retrieval, which is exactly the
    # case where it actually changes the answer.
    # SPEED: lowered from 0.75 → 0.62. With both embedding and reranking now going over
    # the network (OpenRouter), a full contextual retry duplicates two network round-trips,
    # not just cheap local compute — 0.75 was routinely retrying on plain queries that
    # already retrieved a good, if not perfect, match. 0.62 still retries the genuinely
    # ambiguous follow-ups (where the contextual query actually changes the answer) while
    # skipping the retry for a plain query that already landed a solid match.
    skip_contextual_retrieval_confidence: float = 0.62
    reranker_enabled: bool = True
    reranker_backend: str = "openrouter"
    reranker_model: str = "cohere/rerank-v3.5"
    # SPEED: lowered from 60 → 25. This is what actually gets sent in the single
    # OpenRouter /rerank request body — 60 documents in one payload was the single
    # biggest network-latency cost in the whole pipeline. top_k defaults to 5, so 25
    # candidates still leaves 5x headroom for the reranker to reorder into the final
    # top_k*3=15 pre-parent-dedup shortlist; quality impact should be negligible while
    # payload size (and OpenRouter's processing time for it) drops by more than half.
    reranker_candidates: int = 25
    embedding_allow_hash_fallback: bool = True
    # Question index is enabled by default.
    question_index_enabled: bool = True
    # QUALITY: raised from 4 → 6. Only affects ingestion-time cost (more hypothetical
    # questions generated and embedded per chunk when a book is indexed), never
    # query-time latency — more question variants per chunk means a wider net for
    # matching however a student happens to phrase their question.
    max_questions_per_chunk: int = 6
    ingestion_workers: int = 1
    # Generation backend. Defaults to Groq (cloud, fast, no local model to manage).
    # Set to "ollama" to run generation fully local instead.
    generation_backend: str = "groq"
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"
    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = ""
    ollama_timeout: int = 90
    # Optional fallback when Ollama is unavailable.
    allow_extractive_fallback: bool = True
    llama_cloud_api_key: str | None = None
    llama_parse_enabled: bool = True
    # Optional: route LlamaParse's page reconstruction through a vendor multimodal
    # model instead of its own default engine. Empty string keeps LlamaParse's default.
    llama_parse_vendor_model: str = ""
    gemini_api_key: str | None = None
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def load_yaml_config(path: str = "config/default.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
