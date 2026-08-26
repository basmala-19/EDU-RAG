"""Persistent, per-session conversation history.

Purpose: after every /api/rag/response turn, record enough detail — which book, the
question, the model's answer, the retrieved evidence chunks, and the RAG evaluation
scores — to reconstruct and audit that exact turn later, from a fresh process/browser.

This is deliberately separate from LearningSessionStore: that store is an in-memory,
TTL/LRU-evicted cache that exists only to build the contextual query for follow-up
retrieval, and forgets everything on restart. This store is the durable log a user
actually wants to come back to.

One JSON file per conversation (keyed by session_id) under data/conversations/,
matching this project's existing plain filesystem + JSON storage style (see
ingest_registry.py) — no new dependency, easy to inspect by hand, safe under this
project's low-concurrency single-instance deployment model. One file per conversation
(rather than one giant file for all conversations, as ingest_registry.py uses) because
conversations carry full retrieved chunk text and can grow large; keeping them apart
avoids rewriting every other conversation's data on every single turn.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ConversationStore:
    def __init__(self, base_dir: Path | str = Path("data/conversations")) -> None:
        self.base_dir = Path(base_dir)
        self._lock = threading.Lock()

    # -- helpers -----------------------------------------------------------------
    def _path(self, session_id: str) -> Path:
        # session_id is backend-generated ("sess_" + hex) so it's already filesystem-safe,
        # but sanitize defensively before ever using it to build a path on disk.
        safe = "".join(c for c in session_id if c.isalnum() or c in ("_", "-")) or "session"
        return self.base_dir / f"{safe}.json"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _read(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A corrupted conversation file should never take the API down — treat it
            # as empty and let the next turn rewrite it cleanly.
            return {}

    def _write(self, path: Path, data: dict[str, Any]) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    # -- public API ----------------------------------------------------------------
    def append_turn(
        self,
        session_id: str,
        *,
        file_reference_id: str,
        file_name: str,
        curriculum_id: str,
        version: str,
        query: str,
        answer: str,
        answer_status: str,
        grounded: bool,
        sources: list[dict[str, Any]],
        retrieval: dict[str, Any],
        evaluation: dict[str, Any],
    ) -> None:
        with self._lock:
            path = self._path(session_id)
            record = self._read(path)
            if not record:
                record = {
                    "session_id": session_id,
                    "created_at": self._now(),
                    "turns": [],
                }
            # A session is bound to exactly one file for its lifetime (enforced in
            # app.py), so these are stable across turns — refreshed here anyway in
            # case the very first write ever raced with a stale partial record.
            record["file_reference_id"] = file_reference_id
            record["file_name"] = file_name
            record["curriculum_id"] = curriculum_id
            record["version"] = version
            record["updated_at"] = self._now()
            record.setdefault("turns", []).append({
                "turn": len(record["turns"]) + 1,
                "timestamp": self._now(),
                "query": query,
                "answer": answer,
                "answer_status": answer_status,
                "grounded": grounded,
                "sources": sources,
                "retrieval": retrieval,
                "evaluation": evaluation,
            })
            self._write(path, record)

    def list_conversations(self) -> list[dict[str, Any]]:
        """Lightweight summaries (no chunk text) for a browsable list, most-recently
        updated first."""
        if not self.base_dir.exists():
            return []
        summaries: list[dict[str, Any]] = []
        for path in self.base_dir.glob("*.json"):
            record = self._read(path)
            if not record:
                continue
            turns = record.get("turns", [])
            summaries.append({
                "session_id": record.get("session_id"),
                "file_reference_id": record.get("file_reference_id"),
                "file_name": record.get("file_name"),
                "curriculum_id": record.get("curriculum_id"),
                "version": record.get("version"),
                "created_at": record.get("created_at"),
                "updated_at": record.get("updated_at"),
                "turn_count": len(turns),
                "last_query": turns[-1]["query"] if turns else None,
            })
        summaries.sort(key=lambda s: s.get("updated_at") or "", reverse=True)
        return summaries

    def get_conversation(self, session_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._read(self._path(session_id))
        return record or None
