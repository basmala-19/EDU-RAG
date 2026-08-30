"""Tracks books that have gone through the full process pipeline (Knowledge
Graph + RAG indexing + question generation), so the UI can offer a picker
("use an existing book" vs "upload a new one") instead of requiring a PDF
re-upload for every session.

Deliberately simple (one JSON file, keyed by content hash) - matches the
storage style already used by the other registries in this project
(``knowledge_graph/infrastructure/graph_registry.py``,
``rag/infrastructure/ingest_registry.py``).
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_PATH = PROJECT_ROOT / "data" / "question_bank" / "books_registry.json"


def hash_file(path: str | Path) -> str:
    """Same sha256-of-content approach used by the RAG and Knowledge Graph
    registries, so a book's identity is consistent across all three."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load() -> dict[str, Any]:
    if not REGISTRY_PATH.is_file():
        return {}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(data: dict[str, Any]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = REGISTRY_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(REGISTRY_PATH)


def list_books() -> list[dict[str, Any]]:
    """Most recently processed first."""
    books = list(_load().values())
    books.sort(key=lambda book: book.get("processed_at", ""), reverse=True)
    return books


def get_book(content_hash: str) -> dict[str, Any] | None:
    return _load().get(content_hash)


def register_book(
    *,
    content_hash: str,
    filename: str,
    grade: str,
    subject: str,
    rag_file_reference_id: str,
    indexed_chunks: int,
    knowledge_graph: dict[str, Any],
    entity_count: int,
    topics_generated: int,
) -> None:
    data = _load()
    data[content_hash] = {
        "content_hash": content_hash,
        "filename": filename,
        "grade": grade,
        "subject": subject,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "rag_file_reference_id": rag_file_reference_id,
        "indexed_chunks": indexed_chunks,
        "knowledge_graph": knowledge_graph,
        "entity_count": entity_count,
        "topics_generated": topics_generated,
    }
    _save(data)
