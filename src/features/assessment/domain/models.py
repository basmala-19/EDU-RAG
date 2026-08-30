"""
Core domain models & enums for the adaptive assessment engine.

Vendored from the standalone Diagnostic Assessment Engine project into this
project's feature-based layout. The state machine, grading, and question
selection logic these models support is unchanged; only the surrounding
wiring (where questions and topic order come from) was adapted - see
``infrastructure/question_bank_source.py`` and
``infrastructure/graph_topic_order.py``.

These are plain dataclasses/enums (not Pydantic, not an ORM): sessions are
kept in memory (see infrastructure/session_store.py) and questions are
sourced live from the Question Bank feature, not a database.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from datetime import datetime

if TYPE_CHECKING:
    # Avoids a circular import (exam_question_bank.py imports models.py already).
    # ExamSession only needs this for type hints; at runtime it's just a
    # plain object reference set by the service layer.
    from ..infrastructure.exam_question_bank import ExamQuestionBank


# ---------------------------------------------------------------------------
# Difficulty levels
# ---------------------------------------------------------------------------
class Difficulty(str, Enum):
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"


# ---------------------------------------------------------------------------
# Question types
# ---------------------------------------------------------------------------
class QuestionType(str, Enum):
    MCQ = "MCQ"
    MSQ = "MSQ"
    # TRUE_FALSE = "TRUE_FALSE"      # to be added later
    # SHORT_ANSWER = "SHORT_ANSWER"  # to be added later


# ---------------------------------------------------------------------------
# Confirmed level result for a topic once the exam stops
# ---------------------------------------------------------------------------
class ConfirmedLevel(str, Enum):
    BELOW_L1 = "below_L1"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    NOT_ASSESSED = "not_assessed"  # topic never reached


# ---------------------------------------------------------------------------
# Explicit session state machine (enum instead of a single retry flag)
# ---------------------------------------------------------------------------
class SessionState(str, Enum):
    L1_FIRST_ATTEMPT = "l1_first_attempt"
    L1_RETRY = "l1_retry"                    # wrong here -> ends: BELOW_L1
    L3_FIRST_ATTEMPT = "l3_first_attempt"
    L2_AFTER_L3_FAIL = "l2_after_l3_fail"    # wrong here -> ends: L1 confirmed
    L3_RETRY_AFTER_L2 = "l3_retry_after_l2"  # wrong here -> ends: L2 confirmed
    FINISHED = "finished"


# ---------------------------------------------------------------------------
# Question record
# ---------------------------------------------------------------------------
@dataclass
class Question:
    question_id: str
    node_id: str
    topic_name: str
    question: Dict[str, Any]   # {"text": "...", "options": {"A": "...", ...}}
    # MCQ: one option key (e.g. "B"). MSQ: option keys (e.g. ["A", "C"]).
    answer: str | List[str]
    difficulty_level: Difficulty
    question_type: QuestionType
    justification: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    validation: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Question":
        return Question(
            question_id=d["question_id"],
            node_id=d["node_id"],
            topic_name=d["topic_name"],
            question=d["question"],
            answer=d["answer"],
            difficulty_level=Difficulty(d["difficulty_level"]),
            question_type=QuestionType(d["question_type"]),
            justification=d.get("Justification", ""),
            metadata=d.get("metadata", {}),
            validation=d.get("validation", {}),
        )


# ---------------------------------------------------------------------------
# Per-topic result, accumulated as the exam progresses
# ---------------------------------------------------------------------------
@dataclass
class TopicResult:
    topic_name: str
    confirmed_level: ConfirmedLevel = ConfirmedLevel.NOT_ASSESSED
    answers: List[Dict[str, Any]] = field(default_factory=list)
    # each answer entry: {question_id, difficulty, is_correct, student_answer, correct_answer}


# ---------------------------------------------------------------------------
# Exam session (kept server-side, referenced by exam_id)
# ---------------------------------------------------------------------------
@dataclass
class ExamSession:
    exam_id: str
    student_id: str
    grade: str
    subject: str
    topics_order: List[str]                 # topological order (+ tie-breaker)
    current_topic_index: int = 0
    state: SessionState = SessionState.L1_FIRST_ATTEMPT
    # The engine alternates types where the bank has both, while falling back
    # gracefully when a topic/difficulty has only one available type.
    last_question_type: Optional[QuestionType] = None
    current_question_id: Optional[str] = None
    asked_question_ids_current_topic: List[str] = field(default_factory=list)
    results: Dict[str, TopicResult] = field(default_factory=dict)
    is_finished: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)

    # The exact question set fetched for THIS exam (subject+grade+topics
    # scoped), built once in generate_exam() and reused for every question
    # lookup/grading/report call for the lifetime of this session — see
    # ExamQuestionBank in infrastructure/exam_question_bank.py. Not part of
    # any external schema; purely internal bookkeeping, so it's typed
    # loosely to avoid a circular import.
    bank: Optional["ExamQuestionBank"] = field(default=None, repr=False)

    # Cached LLM-generated report text, filled in the first time
    # get_report() is called for this (finished) session. Re-requesting the
    # report for the same exam_id returns this instead of calling the LLM
    # again.
    report_text: Optional[str] = None

    @property
    def current_topic(self) -> Optional[str]:
        if self.current_topic_index < len(self.topics_order):
            return self.topics_order[self.current_topic_index]
        return None
