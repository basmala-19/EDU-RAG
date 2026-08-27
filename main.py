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

# Importing the UI renders the Streamlit feature. RAG is called directly by
# this feature through its application-layer adapter, with no HTTP boundary.
from src.features.question_bank import app as _question_bank_app  # noqa: E402, F401
