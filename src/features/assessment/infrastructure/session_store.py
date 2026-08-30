"""Exam session storage - vendored unchanged from the standalone Diagnostic
Assessment Engine (app/assessment/repository.py). In-memory, MVP; swap for
SQLite/Redis later without touching application/assessment_service.py.
"""

from __future__ import annotations

from typing import Dict, Optional

from ..domain.models import ExamSession


class SessionRepository:
    def __init__(self):
        self._sessions: Dict[str, ExamSession] = {}

    def save(self, session: ExamSession) -> None:
        self._sessions[session.exam_id] = session

    def get(self, exam_id: str) -> Optional[ExamSession]:
        return self._sessions.get(exam_id)

    def exists(self, exam_id: str) -> bool:
        return exam_id in self._sessions


_session_repository: Optional[SessionRepository] = None


def get_session_repository() -> SessionRepository:
    """One shared SessionRepository per process."""
    global _session_repository
    if _session_repository is None:
        _session_repository = SessionRepository()
    return _session_repository
