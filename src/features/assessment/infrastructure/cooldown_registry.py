"""Global, in-memory question cooldown - vendored unchanged from the
standalone Diagnostic Assessment Engine (app/assessment/repository.py).

Deliberately NOT owned by any per-exam question snapshot: it's shared
across every student, every exam, every subject, and must outlive any
single exam's ExamQuestionBank.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .config import get_cooldown_duration


@dataclass
class CooldownRegistry:
    # question_id -> last_used_at
    last_used: Dict[str, datetime] = field(default_factory=dict)
    cooldown_duration: timedelta = field(default_factory=get_cooldown_duration)

    def mark_used(self, question_id: str, when: Optional[datetime] = None) -> None:
        self.last_used[question_id] = when or datetime.utcnow()

    def is_under_cooldown(self, question_id: str, now: Optional[datetime] = None) -> bool:
        now = now or datetime.utcnow()
        last = self.last_used.get(question_id)
        if last is None:
            return False
        return (now - last) < self.cooldown_duration

    def reset(self, question_ids: List[str]) -> None:
        for qid in question_ids:
            self.last_used.pop(qid, None)


_cooldown_registry: Optional[CooldownRegistry] = None


def get_cooldown_registry() -> CooldownRegistry:
    """One shared, GLOBAL CooldownRegistry per process."""
    global _cooldown_registry
    if _cooldown_registry is None:
        _cooldown_registry = CooldownRegistry()
    return _cooldown_registry
