"""Environment-backed configuration shared by the generation pipeline."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(PROJECT_ROOT / ".env")

DEFAULT_MODEL = "deepseek/deepseek-v4-flash-0731"
DEFAULT_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def get_llm_model() -> str:
    """Return the model selected in ``.env``."""
    return os.getenv("LLM_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def get_openrouter_api_key() -> str:
    """Return the API key or raise a clear error before an API request."""
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing. Copy .env.example to .env and set it."
        )
    return api_key


def get_openrouter_base_url() -> str:
    return os.getenv("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_BASE_URL).strip() or DEFAULT_OPENROUTER_BASE_URL


def get_question_counts_by_difficulty() -> dict[int, int]:
    """Read and validate the requested count for each difficulty level."""
    counts: dict[int, int] = {}
    for difficulty in range(1, 6):
        variable = f"QUESTION_COUNT_DIFFICULTY_{difficulty}"
        raw_value = os.getenv(variable, "5").strip()
        try:
            count = int(raw_value)
        except ValueError as exc:
            raise ValueError(f"{variable} must be a whole number >= 0, got {raw_value!r}.") from exc
        if count < 0:
            raise ValueError(f"{variable} must be a whole number >= 0, got {count}.")
        counts[difficulty] = count
    return counts
