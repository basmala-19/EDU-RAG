from functools import lru_cache
from pathlib import Path
import os
import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    log_level: str = "INFO"
    cors_origins: str = "http://127.0.0.1:8000,http://localhost:8000"
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
    candidate_multiplier: int = 8
    # Floor on the raw dense-search fetch size, independent of top_k/candidate_multiplier.
    # Before this existed, a request at the default top_k=5 only pulled candidate_k=40
    # raw dense hits (5*8) - a page-level chunk with a degraded embedding (e.g. from
    # OCR/ligature-corrupted source text) can rank just outside a window that narrow, so
    # it gets dropped before RRF/rerank ever sees it, even though it scores #1 once it
    # does get evaluated. This only affects the cheap initial fetch - the expensive
    # CrossEncoder stage stays capped separately by reranker_candidates regardless.
    min_candidate_k: int = 160
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
    # Lightweight deterministic reranking.
    semantic_weight: float = 0.30
    question_weight: float = 0.10
    keyword_weight: float = 0.40
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
    min_reranker_score_floor: float = 0.15
    min_retrieval_confidence_floor: float = 0.15
    # When the plain (un-augmented) query already retrieves with confidence at or above
    # this bar, skip the second, history/lesson-context-augmented retrieval entirely —
    # a clearly strong direct match is extremely unlikely to be beaten by the augmented
    # query, so paying for a second embed + dense/keyword/question query + rerank pass
    # buys nothing in that case. Only genuinely ambiguous follow-ups (which score below
    # this on the plain query) still pay for the second retrieval, which is exactly the
    # case where it actually changes the answer.
    skip_contextual_retrieval_confidence: float = 0.75
    reranker_enabled: bool = True
    reranker_backend: str = "openrouter"
    reranker_model: str = "cohere/rerank-v3.5"
    reranker_candidates: int = 60
    embedding_allow_hash_fallback: bool = True
    # Question index is enabled by default.
    question_index_enabled: bool = True
    max_questions_per_chunk: int = 4
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
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def load_yaml_config(path: str = "config/default.yaml") -> dict:
    p = Path(path)
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
