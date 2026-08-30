"""Sources exam questions from the Question Bank feature, replacing the
standalone engine's private ``questions.json`` file.

This is the ONE place that knows both shapes: the Question Bank's saved
question JSON (produced by
``question_bank.questions_service.generate_questions_from_knowledge_graph``)
and the assessment engine's ``Question`` dataclass. Everything downstream
(``ExamQuestionBank``, ``AssessmentService``) only ever sees ``Question``
objects and has no idea where they came from - the same swap-without-
touching-callers seam the standalone engine's docstrings already called out
for a future "real" question source.

Question Bank's generation prompt does not pin an exact per-field JSON
schema for each question beyond ``task_difficulty`` (see
``question_bank/questions_service.py::_build_prompt``), so field lookup
below is deliberately defensive: a malformed question is skipped with a
warning (logged, so it's visible in the app's log panel) rather than
crashing exam generation for an entire topic over one bad question.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable

from src.features.question_bank.questions_service import DEFAULT_OUTPUT_ROOT, get_questions

from ..domain.models import Difficulty, Question, QuestionType

logger = logging.getLogger(__name__)


def _safe_path_part(value: str) -> str:
    """Must match question_bank.questions_service._safe_path_part exactly -
    both features read/write the same grade/subject/topic folder layout on
    disk, so the sanitizing rule is a real contract between them, not an
    implementation detail. Duplicated here (rather than importing a private
    symbol from question_bank) to avoid depending on the other feature's
    internals."""
    import re

    cleaned = re.sub(r"[^\w.-]+", "_", value.strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("._")
    if not cleaned:
        raise ValueError("grade, subject, and topic cannot be empty.")
    return cleaned[:120]



# Question Bank generates 5 difficulty levels (task_difficulty 1-5); the
# assessment engine's adaptive state machine only distinguishes 3 (L1/L2/L3).
# This is the single place that bucket mapping lives.
TASK_DIFFICULTY_TO_LEVEL: dict[int, Difficulty] = {
    1: Difficulty.L1,
    2: Difficulty.L1,
    3: Difficulty.L2,
    4: Difficulty.L3,
    5: Difficulty.L3,
}


def _first_present(raw: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            return value
    return None


def _normalize_question(
    raw: dict[str, Any], *, topic_id: str, topic_name: str, subject: str, source_file: Path,
) -> Question | None:
    """Best-effort mapping from a Question Bank question dict to Question.

    Returns None (and logs a warning) instead of raising, so one malformed
    question never blocks generating an exam for the rest of a topic.
    """
    question_id = raw.get("id")
    text = _first_present(raw, "text", "question_text", "prompt")
    options = _first_present(raw, "options", "choices")
    answer = _first_present(raw, "answer", "correct_answer")
    task_difficulty = raw.get("task_difficulty")

    if not isinstance(question_id, str) or not question_id.strip():
        logger.warning("Skipping question with no 'id' in %s (topic=%s)", source_file, topic_name)
        return None
    if not isinstance(text, str) or not text.strip():
        logger.warning("Skipping question %s: no usable question text (%s)", question_id, source_file)
        return None
    if not isinstance(options, dict) or not options:
        logger.warning("Skipping question %s: no usable 'options' object (%s)", question_id, source_file)
        return None
    if answer is None:
        logger.warning("Skipping question %s: no usable 'answer' (%s)", question_id, source_file)
        return None
    if task_difficulty not in TASK_DIFFICULTY_TO_LEVEL:
        logger.warning(
            "Skipping question %s: task_difficulty=%r is not an int 1-5 (%s)",
            question_id, task_difficulty, source_file,
        )
        return None

    question_type_raw = str(_first_present(raw, "question_type", "type") or "").strip().upper()
    if question_type_raw not in (QuestionType.MCQ.value, QuestionType.MSQ.value):
        # Infer from the answer shape when the type wasn't stated explicitly.
        question_type_raw = QuestionType.MSQ.value if isinstance(answer, list) else QuestionType.MCQ.value

    justification = _first_present(raw, "justification", "Justification", "explanation") or ""
    validation = raw.get("validation")

    return Question(
        question_id=question_id,
        node_id=topic_id,
        topic_name=topic_name,
        question={"text": text, "options": options},
        answer=answer,
        difficulty_level=TASK_DIFFICULTY_TO_LEVEL[task_difficulty],
        question_type=QuestionType(question_type_raw),
        justification=str(justification),
        metadata={"subject": subject, "topic_id": topic_id, "question_metadata": raw.get("metadata")},
        validation=validation if isinstance(validation, dict) else {},
    )


class QuestionBankSource:
    """Assessment-engine-facing view over the shared Question Bank data.

    Reads live from ``question_bank.questions_service`` (the same saved
    JSON files the Question Bank UI writes to and reads from) instead of a
    private copy, so both features always see the exact same questions.
    """

    def __init__(self, output_root: str | Path = DEFAULT_OUTPUT_ROOT) -> None:
        self.output_root = Path(output_root)

    def list_available_topic_ids(self, grade: str, subject: str) -> set[str]:
        """Topic ids that currently have at least one saved question file
        for this grade+subject - used to intersect against Knowledge Graph
        entities so the exam only ever includes topics that are actually
        ready."""
        subject_dir = self.output_root / _safe_path_part(grade) / _safe_path_part(subject)
        if not subject_dir.is_dir():
            return set()

        topic_ids: set[str] = set()
        for file_path in subject_dir.glob("*.json"):
            import json

            try:
                document = json.loads(file_path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                logger.warning("Could not read question file, skipping: %s", file_path)
                continue
            topic_info = document.get("metadata", {}).get("topic", {})
            topic_id = topic_info.get("id")
            if isinstance(topic_id, str) and topic_id.strip():
                topic_ids.add(topic_id)
        return topic_ids

    def get_questions_for_exam(
        self, *, subject: str, grade: str, topics: Iterable[tuple[str, str]],
    ) -> list[Question]:
        """``topics`` is an iterable of ``(topic_id, topic_name)`` pairs -
        both are needed because Question Bank groups saved files by topic
        id, while the assessment engine's state machine keys everything by
        topic name."""
        topics = list(topics)
        questions: list[Question] = []
        subject_dir = self.output_root / _safe_path_part(grade) / _safe_path_part(subject)
        for topic_id, topic_name in topics:
            raw_questions = get_questions(grade, subject, topic_id, output_root=self.output_root)
            source_file = subject_dir / f"{_safe_path_part(topic_id)}.json"
            for raw in raw_questions:
                normalized = _normalize_question(
                    raw, topic_id=topic_id, topic_name=topic_name, subject=subject, source_file=source_file,
                )
                if normalized is not None:
                    questions.append(normalized)
        logger.info(
            "Question Bank source: loaded %d usable question(s) across %d topic(s) for grade=%s subject=%s",
            len(questions), len(topics), grade, subject,
        )
        return questions
