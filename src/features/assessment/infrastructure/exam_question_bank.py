"""Per-exam question snapshot - vendored unchanged from the standalone
Diagnostic Assessment Engine (app/assessment/repository.py).

This class operates purely on already-built ``Question`` objects; it has no
idea (and doesn't need one) that those objects now come from the shared
Question Bank feature instead of a private JSON file. That swap happens
entirely in ``question_bank_source.py``.

Why a per-exam snapshot instead of one shared bank?
----------------------------------------------------
The Question Bank data for one topic can keep changing (new questions
generated later, a topic regenerated). Freezing the exact set an exam was
generated against, and reusing that same set for grading + the final
report, means:
  - a student's answers are always graded against the question they were
    actually shown, even if the source bank changes mid-exam elsewhere
  - `validate_coverage()` runs against this exact snapshot inside
    generate_exam() before any question is sent to the student; a gap
    surfaces as an immediate, clear error instead of breaking mid-exam
"""

from __future__ import annotations

import logging
import random
from typing import Dict, List, Optional, Tuple

from ..domain.models import Difficulty, Question, QuestionType
from .cooldown_registry import CooldownRegistry

logger = logging.getLogger(__name__)


def _match_questions(
    questions: List[Question], topic: str, difficulty: Difficulty, qtype: QuestionType
) -> List[Question]:
    return [
        q
        for q in questions
        if q.topic_name == topic and q.difficulty_level == difficulty and q.question_type == qtype
    ]


def find_missing_coverage(
    questions: List[Question],
    topics: List[str],
    difficulties: List[Difficulty],
    question_types: List[QuestionType],
) -> List[Tuple[str, Difficulty, QuestionType]]:
    """Every (topic, difficulty, type) combination with ZERO matching questions.
    Empty list = fully covered."""
    missing = []
    for topic in topics:
        for diff in difficulties:
            for qtype in question_types:
                if not _match_questions(questions, topic, diff, qtype):
                    missing.append((topic, diff, qtype))
    return missing


class ExamQuestionBank:
    """
    The exact, frozen set of questions available to ONE exam session, plus
    the selection rules (cooldown-aware, retry-aware) for picking the next
    question from it. Built once by ``QuestionBankSource.get_questions_for_exam()``
    at generate_exam time and then reused for every subsequent question
    pick, grading lookup, and report lookup for that same exam.
    """

    def __init__(self, questions: List[Question], cooldown: CooldownRegistry):
        self.questions = questions
        self.cooldown = cooldown

    def validate_coverage(
        self, topics: List[str], difficulties: List[Difficulty], question_types: List[QuestionType]
    ) -> List[Tuple[str, Difficulty, QuestionType]]:
        return find_missing_coverage(self.questions, topics, difficulties, question_types)

    def _match(self, topic: str, difficulty: Difficulty, qtype: Optional[QuestionType]) -> List[Question]:
        if qtype is None:
            return [q for q in self.questions if q.topic_name == topic and q.difficulty_level == difficulty]
        return _match_questions(self.questions, topic, difficulty, qtype)

    def validate_any_type_coverage(
        self, topics: List[str], difficulties: List[Difficulty], question_types: List[QuestionType]
    ) -> List[Tuple[str, Difficulty]]:
        """Return topic/difficulty pairs with no question of any allowed type."""
        missing = []
        for topic in topics:
            for difficulty in difficulties:
                if not any(self._match(topic, difficulty, qtype) for qtype in question_types):
                    missing.append((topic, difficulty))
        return missing

    def select_question(
        self,
        topic: str,
        difficulty: Difficulty,
        qtype: Optional[QuestionType],
        exclude_ids: Optional[List[str]] = None,
        preferred_qtype: Optional[QuestionType] = None,
    ) -> Question:
        """
        Semi-random pick among questions matching (topic, difficulty, type),
        excluding:
          - questions currently under GLOBAL cooldown
          - `exclude_ids` (questions already asked in this session/topic,
            so a retry never repeats the same question)

        If ALL matching questions (before exclude_ids) are under cooldown,
        reset cooldown for that whole matching set and re-pick.
        """
        exclude_ids = exclude_ids or []
        matches = self._match(topic, difficulty, qtype)

        # In a mixed exam, prefer the opposite type of the preceding
        # question when it is available. This prevents random selection from
        # producing a long run of MCQs despite MSQs being in the bank.
        if qtype is None and preferred_qtype is not None:
            preferred_matches = [q for q in matches if q.question_type == preferred_qtype]
            if preferred_matches:
                matches = preferred_matches

        if not matches:
            # Should never happen: generate_exam() runs validate_coverage()
            # against this exact snapshot before the exam starts.
            raise ValueError(
                f"No questions available for topic={topic}, "
                f"difficulty={difficulty}, type={qtype.value if qtype else 'any'}. "
                f"This exam's snapshot should have been validated at generate_exam time."
            )

        available = [q for q in matches if not self.cooldown.is_under_cooldown(q.question_id)]

        if not available:
            # all matching questions are cooling down -> reset them all
            logger.info(
                "All %d question(s) for topic=%s difficulty=%s type=%s are under cooldown; resetting.",
                len(matches),
                topic,
                difficulty.value,
                qtype.value if qtype else "any",
            )
            self.cooldown.reset([q.question_id for q in matches])
            available = matches[:]

        # exclude questions already asked in this session (must differ on retry)
        candidates = [q for q in available if q.question_id not in exclude_ids]
        if not candidates:
            # every available question was already asked in this session;
            # fall back to the full available set (can't guarantee novelty
            # forever if the bank is very small for this combination)
            candidates = available

        chosen = random.choice(candidates)
        self.cooldown.mark_used(chosen.question_id)
        return chosen

    def get_by_id(self, question_id: str) -> Question:
        for q in self.questions:
            if q.question_id == question_id:
                return q
        raise ValueError(f"Question {question_id} not found in this exam's question bank")

    def get_node_id(self, topic_name: str) -> str:
        """
        Stable identifier for a topic — used in log lines instead of the
        raw topic_name (topic names are arbitrary bank content, often
        Arabic). Falls back to topic_name itself if no question for that
        topic is in this snapshot (shouldn't happen after
        validate_coverage()).
        """
        for q in self.questions:
            if q.topic_name == topic_name:
                return q.node_id
        return topic_name
