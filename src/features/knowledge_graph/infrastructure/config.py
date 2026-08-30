"""Environment-backed configuration for the knowledge_graph feature.

Deliberately self-contained (reads env vars directly, no imports from other
features) so knowledge_graph can sit underneath question_bank, rag, or any
future feature without ever depending back on them.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_MODEL = "deepseek/deepseek-v4-flash-0731"
DEFAULT_STORAGE_DIR = PROJECT_ROOT / "data" / "knowledge_graph"


def get_llm_model() -> str:
    """Model used to extract the graph from a document's text.

    Shares the ``LLM_MODEL`` env var with the rest of the app rather than
    introducing a separate variable, since there's no current need for the
    graph-extraction model to differ from the question-generation model.
    """
    return os.getenv("LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def get_openrouter_api_key() -> str:
    """Return the API key or raise a clear error before an API request."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Copy .env.example to .env and set it."
        )
    return api_key


def get_storage_dir() -> Path:
    """Where generated graph JSON/HTML files and the cache registry live."""
    raw = os.getenv("KNOWLEDGE_GRAPH_STORAGE_DIR", "").strip()
    return Path(raw) if raw else DEFAULT_STORAGE_DIR
