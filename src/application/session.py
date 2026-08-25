from __future__ import annotations

import secrets
from collections import defaultdict
from typing import Any

from src.infrastructure.config import get_settings


class LearningSessionStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._sessions: dict[str, dict[str, Any]] = defaultdict(dict)

    def ensure(self, session_id: str | None, *, file_reference_id: str, curriculum_id: str, version: str, lesson_context: dict[str, Any] | None = None) -> str:
        sid = session_id or f"sess_{secrets.token_hex(8)}"
        state = self._sessions[sid]
        if state and state.get("file_reference_id") != file_reference_id:
            raise ValueError("session_id is already bound to another file_reference_id")
        state.setdefault("session_id", sid)
        state.setdefault("file_reference_id", file_reference_id)
        state.setdefault("curriculum_id", curriculum_id)
        state.setdefault("version", version)
        if lesson_context:
            state["lesson_context"] = {k: v for k, v in lesson_context.items() if v not in (None, "")}
        state.setdefault("turns", [])
        return sid

    def get(self, session_id: str | None) -> dict[str, Any]:
        return self._sessions.get(session_id or "", {})

    def build_query(self, session_id: str | None, current_query: str, lesson_context: dict[str, Any] | None = None) -> str:
        """Expand the raw student query into the text actually sent to the embedder.

        lesson_context (request-supplied, falling back to whatever was bound to the
        session) is folded in as a light text hint so that short/ambiguous follow-ups
        ("طيب اديني مثال عليه") retrieve from the right part of the document instead of
        matching on the bare words alone. This previously accepted the parameter but
        never used it, which is why lesson_context had no visible effect on answers.
        """
        state = self.get(session_id)
        turns = state.get("turns", [])
        ctx = lesson_context or state.get("lesson_context") or {}
        hint = " - ".join(v for v in (ctx.get("chapter"), ctx.get("lesson"), ctx.get("section")) if v)
        parts = [current_query.strip()]
        # No word-count gate here: whether history actually helps is decided by
        # comparing retrieval_confidence between the plain and contextual query in
        # app.py, not by guessing from query length (which breaks across languages
        # with different average word lengths, e.g. Arabic vs. English).
        if turns:
            parts.append(str(turns[-1].get("user", "")))
            parts.append(str(turns[-1].get("assistant", ""))[:500])
        if hint:
            parts.append(f"سياق الدرس: {hint}")
        return "\n".join(dict.fromkeys(x for x in parts if x))

    def history(self, session_id: str | None) -> list[dict[str, str]]:
        return list(self.get(session_id).get("turns", []))

    def append(self, session_id: str, user: str, assistant: str) -> None:
        state = self._sessions[session_id]
        state.setdefault("turns", []).append({"user": user, "assistant": assistant})
        state["turns"] = state["turns"][-self.settings.max_session_turns:]
