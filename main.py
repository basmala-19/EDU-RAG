"""Single Streamlit entrypoint for the Question Bank application."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent
RAG_DATA_DIR = ROOT / "data" / "rag"
QUESTION_BANK_DATA_DIR = ROOT / "data" / "question_bank"

# One environment file and stable data locations, independent of where the
# Streamlit command was launched from.
load_dotenv(ROOT / ".env")
os.environ.setdefault("CHROMA_PATH", str(RAG_DATA_DIR / "vector_store" / "chroma"))
os.environ.setdefault("RAG_UPLOAD_DIR", str(QUESTION_BANK_DATA_DIR / "uploads"))

# The UI code lives in `app.render()`, not at module import time: Streamlit
# reruns this script on every interaction, but a plain `import` only executes
# a module's top-level code once per process. Calling render() explicitly
# here means the page actually redraws on every rerun. RAG is called
# directly by this feature through its application-layer adapter, with no
# HTTP boundary.
from src.features.question_bank import app as _question_bank_app  # noqa: E402

_question_bank_app.render()
