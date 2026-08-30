"""Environment-backed configuration for the assessment feature.

Self-contained (reads env vars directly), matching
``knowledge_graph/infrastructure/config.py`` and
``rag/infrastructure/config.py``. Report generation reuses
``question_bank``'s existing OpenRouter-backed LLM client (see
``application/assessment_service.py``) rather than the standalone engine's
original multi-provider (Anthropic/Groq/OpenRouter) client, since this
project has already standardized on OpenRouter everywhere else. Swap that
back in later if multi-provider support is ever needed.
"""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(PROJECT_ROOT / ".env")


def _get_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def get_cooldown_duration() -> timedelta:
    """How long a question stays out of rotation after being asked, globally."""
    return timedelta(days=_get_int("ASSESSMENT_COOLDOWN_DURATION_DAYS", 14))


def get_question_timeout_seconds() -> int:
    return _get_int("ASSESSMENT_QUESTION_TIMEOUT_SECONDS", 60)
