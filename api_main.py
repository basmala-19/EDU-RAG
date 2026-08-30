"""Entrypoint for the mobile app-facing HTTP API.

Companion to ``main.py`` (the Streamlit admin tool): same project, same
``.env``, same data directories, but exposes the pipeline over HTTP for a
real mobile client instead of a server-rendered page. Run with:

    uv run python api_main.py

or directly with uvicorn (equivalent, once the env below is already set):

    uvicorn api_main:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
RAG_DATA_DIR = ROOT / "data" / "rag"
QUESTION_BANK_DATA_DIR = ROOT / "data" / "question_bank"

# Same one environment file and stable data locations as main.py, so both
# entrypoints agree on where books, the vector store, and the question bank
# live regardless of which one is launched first or where it's launched from.
load_dotenv(ROOT / ".env")
os.environ.setdefault("CHROMA_PATH", str(RAG_DATA_DIR / "vector_store" / "chroma"))
os.environ.setdefault("RAG_UPLOAD_DIR", str(QUESTION_BANK_DATA_DIR / "uploads"))

from src.features.question_bank.interfaces.api.app import app  # noqa: E402

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
