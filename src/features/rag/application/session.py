from __future__ import annotations

import re
import secrets
import time
from collections import OrderedDict
from typing import Any

from src.features.rag.infrastructure.config import get_settings


class LearningSessionStore:
    def __init__(self) -> None:
        self.settings = get_settings()
        # OrderedDict so we can cheaply evict the least-recently-touched session when
        # max_sessions is exceeded (move_to_end() on every touch keeps it ordered by
        # recency). Previously a plain defaultdict grew forever for the life of the
        # process — on a long-running server that's an unbounded memory leak.
        self._sessions: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
        self._last_seen: dict[str, float] = {}

    def _touch(self, sid: str) -> None:
        self._last_seen[sid] = time.monotonic()
        if sid in self._sessions:
            self._sessions.move_to_end(sid)

    def sweep(self) -> int:
        """Evict sessions idle past the TTL, then enforce the hard size cap (LRU).

        Cheap to call often: called lazily from ensure()/get() so idle sessions get
        cleaned up during normal traffic even without the background task, and also
        called periodically from app.py's startup-scheduled sweep task so purely idle
        deployments (no incoming requests) still free memory.
        """
        now = time.monotonic()
        ttl = self.settings.session_ttl_seconds
        expired = [sid for sid, last in self._last_seen.items() if now - last > ttl]
        for sid in expired:
            self._sessions.pop(sid, None)
            self._last_seen.pop(sid, None)
        removed = len(expired)
        while len(self._sessions) > self.settings.max_sessions:
            oldest_sid, _ = self._sessions.popitem(last=False)
            self._last_seen.pop(oldest_sid, None)
            removed += 1
        return removed

    def ensure(self, session_id: str | None, *, file_reference_id: str, curriculum_id: str, version: str, lesson_context: dict[str, Any] | None = None) -> str:
        self.sweep()
        sid = session_id or f"sess_{secrets.token_hex(8)}"
        if sid not in self._sessions:
            self._sessions[sid] = {}
        state = self._sessions[sid]
        self._touch(sid)
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
        sid = session_id or ""
        self.sweep()
        if sid in self._sessions:
            self._touch(sid)
        return self._sessions.get(sid, {})

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
        is_followup = bool(
            len(current_query.split()) <= 4
            or re.search(r"(?:^|\s)(?:هو|هي|هما|هم|عليه|عليها|عنه|عنها|بينهما|منهما|به|بها|طب|طيب|ليه|ازاي|مثال|وضح|فسر|قارن|اكتر|it|its|this|that|them|they|why|more|example)(?:$|\s)", current_query, re.IGNORECASE)
        )
        if turns and is_followup:
            parts.append(str(turns[-1].get("user", "")))
            parts.append(str(turns[-1].get("assistant", ""))[:300])
        if hint:
            parts.append(f"سياق الدرس: {hint}")
        return "\n".join(dict.fromkeys(x for x in parts if x))

    def history(self, session_id: str | None) -> list[dict[str, str]]:
        return list(self.get(session_id).get("turns", []))

    def append(self, session_id: str, user: str, assistant: str) -> None:
        if session_id not in self._sessions:
            self._sessions[session_id] = {}
        state = self._sessions[session_id]
        self._touch(session_id)
        state.setdefault("turns", []).append({"user": user, "assistant": assistant})
        state["turns"] = state["turns"][-self.settings.max_session_turns:]
