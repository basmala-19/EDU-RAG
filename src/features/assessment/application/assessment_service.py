"""
Business logic for the assessment feature - vendored from the standalone
Diagnostic Assessment Engine (app/assessment/service.py), adapted to run
in-process (no FastAPI ``Depends``, no HTTP boundary - matching how
``question_bank`` calls into ``rag`` and ``knowledge_graph`` elsewhere in
this project) and to source questions from the shared Question Bank feature
instead of a private JSON file.

AssessmentService owns the whole flow:
  1. start_exam_from_knowledge_graph - NEW high-level entry point: given a
     Knowledge Graph and a grade/subject, automatically figures out which
     topics have saved questions, derives the topic order from the graph's
     prerequisiteOf edges, and starts the exam. This is what removes the
     manual kg_edges/tie_breaker_order/topics the standalone engine
     required as request input.
  2. generate_exam       - lower-level entry point (topics/kg_edges/
                            tie_breaker_order already resolved): fetch the
                            question snapshot, validate coverage, issue Q1.
  3. process_answer      - grade the answer and drive the adaptive state
                            machine to decide the next question, or end.
  4. get_report          - once an exam is finished, turn the session into
                            a readable report via an LLM call (cached after
                            the first call).

State machine summary (explicit enum, not a boolean retry flag) -
unchanged from the standalone engine:

    L1_FIRST_ATTEMPT
        correct   -> L3_FIRST_ATTEMPT (ask L3)
        incorrect -> L1_RETRY (ask a *different* L1 question)

    L1_RETRY
        correct   -> L3_FIRST_ATTEMPT (ask L3)
        incorrect -> END: confirmed_level = BELOW_L1

    L3_FIRST_ATTEMPT
        correct   -> topic done, confirmed_level = L3 -> NEXT TOPIC, L1_FIRST_ATTEMPT
        incorrect -> L2_AFTER_L3_FAIL (ask L2)

    L2_AFTER_L3_FAIL
        correct   -> L3_RETRY_AFTER_L2 (ask a *different* L3 question)
        incorrect -> END: confirmed_level = L1

    L3_RETRY_AFTER_L2
        correct   -> topic done, confirmed_level = L3 -> NEXT TOPIC, L1_FIRST_ATTEMPT
        incorrect -> END: confirmed_level = L2

Whenever the assessment ends (BELOW_L1 / L1 / L2), ALL remaining
not-yet-reached topics are marked NOT_ASSESSED and the exam stops entirely.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections import defaultdict, deque
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..domain.models import (
    ConfirmedLevel,
    Difficulty,
    ExamSession,
    Question,
    QuestionType,
    SessionState,
    TopicResult,
)
from ..infrastructure.cooldown_registry import CooldownRegistry, get_cooldown_registry
from ..infrastructure.config import get_question_timeout_seconds
from ..infrastructure.exam_question_bank import ExamQuestionBank
from ..infrastructure.graph_topic_order import build_topic_plan
from ..infrastructure.question_bank_source import QuestionBankSource
from ..infrastructure.session_store import SessionRepository, get_session_repository

logger = logging.getLogger(__name__)

# Which difficulty to request for each state
STATE_DIFFICULTY = {
    SessionState.L1_FIRST_ATTEMPT: Difficulty.L1,
    SessionState.L1_RETRY: Difficulty.L1,
    SessionState.L3_FIRST_ATTEMPT: Difficulty.L3,
    SessionState.L2_AFTER_L3_FAIL: Difficulty.L2,
    SessionState.L3_RETRY_AFTER_L2: Difficulty.L3,
}

ALL_DIFFICULTIES = [Difficulty.L1, Difficulty.L2, Difficulty.L3]


def _opposite_question_type(question_type: Optional[QuestionType]) -> Optional[QuestionType]:
    """Return the type that keeps a mixed exam alternating where possible."""
    if question_type == QuestionType.MCQ:
        return QuestionType.MSQ
    if question_type == QuestionType.MSQ:
        return QuestionType.MCQ
    return None


# ---------------------------------------------------------------------------
# Topic ordering (knowledge-graph topological sort with a tie-breaker)
# ---------------------------------------------------------------------------
def _topological_sort_topics(
    topics: List[str],
    edges: List[Tuple[str, str]],
    tie_breaker_order: Dict[str, int],
) -> List[str]:
    """
    topics: list of topic names (nodes)
    edges: list of (prerequisite_topic, dependent_topic) pairs from the KG
    tie_breaker_order: dict topic_name -> numeric order (e.g. graph mention
           order) used to break ties between topics with no dependency
           relation between them (parallel topics at the same graph level)
    """
    in_degree = {t: 0 for t in topics}
    adjacency = defaultdict(list)

    for prereq, dependent in edges:
        adjacency[prereq].append(dependent)
        in_degree[dependent] += 1

    ready = deque(
        sorted(
            (t for t in topics if in_degree[t] == 0),
            key=lambda t: tie_breaker_order.get(t, 0),
        )
    )

    ordered: List[str] = []
    while ready:
        ready = deque(sorted(ready, key=lambda t: tie_breaker_order.get(t, 0)))
        current = ready.popleft()
        ordered.append(current)

        for nxt in adjacency[current]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                ready.append(nxt)

    if len(ordered) != len(topics):
        missing = set(topics) - set(ordered)
        raise ValueError(f"Cycle detected in topic KG, or disconnected topics found: {missing}")

    return ordered


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------
def _grade_mcq(question: Question, student_answer: Any) -> bool:
    """MCQ grading: student_answer is expected to be the option key (e.g.
    "B"). Case/whitespace normalized to be forgiving of minor formatting."""
    if not isinstance(question.answer, str) or not isinstance(student_answer, str):
        return False
    correct = question.answer.strip().upper()
    given = student_answer.strip().upper()
    return given == correct


def _grade_msq(question: Question, student_answer: Any) -> bool:
    """Grade an MSQ by exact set match, ignoring option-key case and order."""
    if not isinstance(question.answer, list) or not isinstance(student_answer, list):
        return False

    def normalize(answers: List[Any]) -> List[str] | None:
        if not all(isinstance(answer, str) and answer.strip() for answer in answers):
            return None
        normalized = [answer.strip().upper() for answer in answers]
        if len(normalized) != len(set(normalized)):
            return None
        return normalized

    correct = normalize(question.answer)
    given = normalize(student_answer)
    if correct is None or given is None:
        return False

    valid_option_keys = {key.strip().upper() for key in question.question.get("options", {})}
    if not set(correct).issubset(valid_option_keys) or not set(given).issubset(valid_option_keys):
        return False
    return set(given) == set(correct)


QUESTION_TYPE_GRADERS = {
    QuestionType.MCQ: _grade_mcq,
    QuestionType.MSQ: _grade_msq,
}


def _grade_answer(question: Question, student_answer: Any) -> bool:
    """Main grading dispatcher. A `student_answer` of None (timeout case) is
    always graded as incorrect."""
    if student_answer is None:
        return False

    grader = QUESTION_TYPE_GRADERS.get(question.question_type)
    if grader is None:
        raise NotImplementedError(
            f"No grading function registered for question_type={question.question_type}"
        )
    return grader(question, student_answer)


# ---------------------------------------------------------------------------
# Report generation (LLM-backed)
# ---------------------------------------------------------------------------
REPORT_SYSTEM_PROMPT = """You are generating a school assessment report.
Write it so it is understandable both to the student (matching their grade
level) and to a parent. For every topic, state the confirmed level plainly.
For topics marked "not assessed", explain simply that the exam ended before
reaching them. For every question the student answered incorrectly, show
the student's answer, the correct answer, and a short, age-appropriate
explanation of why the student's answer was wrong. Keep the tone
encouraging, not punitive. Respond in the same language as the questions."""


def _topic_results_summary(session: ExamSession, bank: ExamQuestionBank) -> List[Dict[str, Any]]:
    """Topic-by-topic breakdown of every question asked: text/options, what
    the student answered, the correct answer, and whether they got it
    right. Used both as the exam_ended result and as the report's base data.
    """
    summary = []
    for topic in session.topics_order:
        result = session.results[topic]
        answers = []
        for ans in result.answers:
            q = bank.get_by_id(ans["question_id"])
            answers.append(
                {
                    "question_id": ans["question_id"],
                    "difficulty": ans["difficulty"],
                    "question_text": q.question.get("text"),
                    "options": q.question.get("options"),
                    "question_type": q.question_type.value,
                    "student_answer": ans["student_answer"],
                    "correct_answer": ans["correct_answer"],
                    "is_correct": ans["is_correct"],
                }
            )
        summary.append(
            {
                "topic_name": topic,
                "confirmed_level": result.confirmed_level.value,
                "answers": answers,
            }
        )
    return summary


def _build_report_payload(session: ExamSession, bank: ExamQuestionBank) -> Dict[str, Any]:
    topics_payload = _topic_results_summary(session, bank)
    for topic_entry in topics_payload:
        for answer_entry in topic_entry["answers"]:
            q = bank.get_by_id(answer_entry["question_id"])
            answer_entry["justification"] = q.justification

    return {
        "student_id": session.student_id,
        "grade": session.grade,
        "subject": session.subject,
        "topics": topics_payload,
    }


def _generate_report_text(session: ExamSession, bank: ExamQuestionBank) -> str:
    """Calls the project's shared OpenRouter LLM client (question_bank's)
    to turn the structured exam data into a readable report."""
    from src.features.question_bank.config import get_llm_model
    from src.features.question_bank.llm_api.openai_api import get_llm_response

    payload = _build_report_payload(session, bank)
    prompt = (
        f"{REPORT_SYSTEM_PROMPT}\n\n"
        f"Here is the exam data as JSON:\n{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    return get_llm_response(get_llm_model(), prompt)


# ---------------------------------------------------------------------------
# Assessment service
# ---------------------------------------------------------------------------
class AssessmentService:
    def __init__(
        self,
        question_source: QuestionBankSource,
        store: SessionRepository,
        cooldown_registry: CooldownRegistry,
    ):
        self.question_source = question_source
        self.store = store
        self.cooldown_registry = cooldown_registry

    # -------------------------------------------------------------
    # High-level entry point: KG in, running exam out. This is what
    # replaces having to hand the engine kg_edges/tie_breaker_order/topics
    # by hand.
    # -------------------------------------------------------------
    def start_exam_from_knowledge_graph(
        self,
        student_id: str,
        grade: str,
        subject: str,
        knowledge_graph: Dict[str, Any],
        *,
        entity_ids: Optional[Iterable[str]] = None,
    ) -> Dict[str, Any]:
        """
        1. Finds which Knowledge Graph topics currently have saved
           questions in the Question Bank for this grade/subject (or a
           caller-supplied subset of entity ids).
        2. Derives the topic order from the graph's prerequisiteOf edges
           (tie-broken by graph mention order).
        3. Starts the exam (generate_exam) with that plan.
        """
        available_topic_ids = self.question_source.list_available_topic_ids(grade, subject)
        if entity_ids is not None:
            available_topic_ids &= set(entity_ids)

        topic_pairs, kg_edges, tie_breaker_order = build_topic_plan(knowledge_graph, available_topic_ids)
        if not topic_pairs:
            raise ValueError(
                f"No Knowledge Graph topic has saved questions yet for grade={grade}, subject={subject}. "
                "Generate questions for at least one topic in Question Bank first."
            )

        logger.info(
            "Derived exam topic plan from Knowledge Graph: %d topic(s), %d prerequisite edge(s): %s",
            len(topic_pairs), len(kg_edges), [name for _, name in topic_pairs],
        )
        return self.generate_exam(student_id, grade, subject, topic_pairs, kg_edges, tie_breaker_order)

    # -------------------------------------------------------------
    # Lower-level entry point: topics/kg_edges/tie_breaker_order already
    # resolved (either by start_exam_from_knowledge_graph above, or
    # supplied directly for tests / manual overrides).
    # -------------------------------------------------------------
    def generate_exam(
        self,
        student_id: str,
        grade: str,
        subject: str,
        topics: List[Tuple[str, str]],  # (topic_id, topic_name) pairs
        kg_edges: List[Tuple[str, str]],  # (prereq_topic_name, dependent_topic_name) pairs
        tie_breaker_order: Dict[str, int],  # topic_name -> order
    ) -> Dict[str, Any]:
        topic_names = [name for _, name in topics]

        # 1. Fetch this exam's own question snapshot from the Question Bank.
        exam_questions = self.question_source.get_questions_for_exam(subject=subject, grade=grade, topics=topics)
        exam_bank = ExamQuestionBank(questions=exam_questions, cooldown=self.cooldown_registry)

        # 2. Validate THIS snapshot has everything this exam could possibly
        #    need before a student ever sees question 1.
        missing = exam_bank.validate_any_type_coverage(
            topic_names, ALL_DIFFICULTIES, [QuestionType.MCQ, QuestionType.MSQ]
        )
        if missing:
            missing_desc = ", ".join(f"{topic}/{difficulty.value}" for topic, difficulty in missing)
            logger.warning(
                "generate_exam blocked for student_id=%s subject=%s grade=%s: missing coverage for %s",
                student_id, subject, grade, missing_desc,
            )
            raise ValueError(
                f"Question bank is missing coverage for subject={subject}, grade={grade}: {missing_desc}"
            )

        # 3. Build the topic order via the KG.
        topics_order = _topological_sort_topics(topic_names, kg_edges, tie_breaker_order)

        session = ExamSession(
            exam_id=str(uuid.uuid4()),
            student_id=student_id,
            grade=grade,
            subject=subject,
            topics_order=topics_order,
            current_topic_index=0,
            state=SessionState.L1_FIRST_ATTEMPT,
            bank=exam_bank,
        )
        session.results = {t: TopicResult(topic_name=t) for t in topics_order}

        first_topic = session.current_topic
        question = exam_bank.select_question(first_topic, Difficulty.L1, qtype=None)

        session.current_question_id = question.question_id
        session.last_question_type = question.question_type
        session.asked_question_ids_current_topic = [question.question_id]
        self.store.save(session)

        logger.info(
            "Exam generated: exam_id=%s student_id=%s subject=%s grade=%s topics=%s (%d questions in snapshot)",
            session.exam_id, student_id, subject, grade,
            [exam_bank.get_node_id(t) for t in topics_order], len(exam_questions),
        )

        return {
            "exam_id": session.exam_id,
            "question": self._public_question(question),
            "question_timeout_seconds": get_question_timeout_seconds(),
        }

    # -------------------------------------------------------------
    def process_answer(
        self,
        exam_id: str,
        question_id: str,
        student_answer: Optional[str | List[str]],
    ) -> Dict[str, Any]:
        session = self.store.get(exam_id)
        if session is None:
            raise ValueError(f"Unknown exam_id: {exam_id}")
        if session.is_finished:
            return {
                "status": "exam_ended",
                "exam_id": session.exam_id,
                "reason": "already_finished",
                "results": _topic_results_summary(session, session.bank),
            }

        question = session.bank.get_by_id(question_id)
        topic = session.current_topic
        result = session.results[topic]

        is_correct = _grade_answer(question, student_answer)
        result.answers.append(
            {
                "question_id": question.question_id,
                "difficulty": question.difficulty_level.value,
                "is_correct": is_correct,
                "student_answer": student_answer,
                "correct_answer": question.answer,
            }
        )

        logger.info(
            "Answer processed: exam_id=%s topic=%s state=%s question_id=%s correct=%s",
            session.exam_id, session.bank.get_node_id(topic), session.state.value, question_id, is_correct,
        )

        outcome = self._advance_state(session, topic, is_correct)

        self.store.save(session)
        return outcome

    def _advance_state(self, session: ExamSession, topic: str, is_correct: bool) -> Dict[str, Any]:
        state = session.state
        result = session.results[topic]

        if state == SessionState.L1_RETRY and not is_correct:
            result.confirmed_level = ConfirmedLevel.BELOW_L1
            return self._end_exam(session)

        if state == SessionState.L2_AFTER_L3_FAIL and not is_correct:
            result.confirmed_level = ConfirmedLevel.L1
            return self._end_exam(session)

        if state == SessionState.L3_RETRY_AFTER_L2 and not is_correct:
            result.confirmed_level = ConfirmedLevel.L2
            return self._end_exam(session)

        if state in (SessionState.L3_FIRST_ATTEMPT, SessionState.L3_RETRY_AFTER_L2) and is_correct:
            result.confirmed_level = ConfirmedLevel.L3
            return self._advance_to_next_topic(session)

        if state == SessionState.L1_FIRST_ATTEMPT:
            next_state = SessionState.L3_FIRST_ATTEMPT if is_correct else SessionState.L1_RETRY
        elif state == SessionState.L1_RETRY:
            next_state = SessionState.L3_FIRST_ATTEMPT
        elif state == SessionState.L3_FIRST_ATTEMPT:
            next_state = SessionState.L2_AFTER_L3_FAIL
        elif state == SessionState.L2_AFTER_L3_FAIL:
            next_state = SessionState.L3_RETRY_AFTER_L2
        else:
            raise RuntimeError(f"Unhandled state transition from {state}")

        logger.debug("State transition: exam_id=%s %s -> %s", session.exam_id, state.value, next_state.value)
        session.state = next_state
        return self._issue_next_question(session, topic)

    def _issue_next_question(self, session: ExamSession, topic: str) -> Dict[str, Any]:
        difficulty = STATE_DIFFICULTY[session.state]
        question = session.bank.select_question(
            topic, difficulty, qtype=None,
            exclude_ids=session.asked_question_ids_current_topic,
            preferred_qtype=_opposite_question_type(session.last_question_type),
        )
        session.current_question_id = question.question_id
        session.last_question_type = question.question_type
        session.asked_question_ids_current_topic.append(question.question_id)
        return {
            "status": "next_question",
            "exam_id": session.exam_id,
            "question": self._public_question(question),
            "question_timeout_seconds": get_question_timeout_seconds(),
        }

    def _advance_to_next_topic(self, session: ExamSession) -> Dict[str, Any]:
        session.current_topic_index += 1
        session.asked_question_ids_current_topic = []
        next_topic = session.current_topic

        if next_topic is None:
            return self._end_exam(session)

        session.state = SessionState.L1_FIRST_ATTEMPT
        question = session.bank.select_question(
            next_topic, Difficulty.L1, qtype=None,
            preferred_qtype=_opposite_question_type(session.last_question_type),
        )
        session.current_question_id = question.question_id
        session.last_question_type = question.question_type
        session.asked_question_ids_current_topic = [question.question_id]

        logger.info("Exam %s advancing to next topic: %s", session.exam_id, session.bank.get_node_id(next_topic))

        return {
            "status": "next_topic_first_question",
            "exam_id": session.exam_id,
            "topic": next_topic,
            "question": self._public_question(question),
            "question_timeout_seconds": get_question_timeout_seconds(),
        }

    def _end_exam(self, session: ExamSession) -> Dict[str, Any]:
        for idx, topic in enumerate(session.topics_order):
            if idx > session.current_topic_index:
                session.results[topic].confirmed_level = ConfirmedLevel.NOT_ASSESSED

        session.is_finished = True
        session.state = SessionState.FINISHED

        logger.info(
            "Exam ended: exam_id=%s student_id=%s final_levels=%s",
            session.exam_id, session.student_id,
            {session.bank.get_node_id(t): r.confirmed_level.value for t, r in session.results.items()},
        )

        return {
            "status": "exam_ended",
            "exam_id": session.exam_id,
            "results": _topic_results_summary(session, session.bank),
        }

    def handle_timeout(self, exam_id: str, question_id: str) -> Dict[str, Any]:
        return self.process_answer(exam_id, question_id, student_answer=None)

    # -------------------------------------------------------------
    def get_exam_state(self, exam_id: str) -> Dict[str, Any]:
        """Read-only lookup for GET /exams/{exam_id}: lets a client that
        reopened the app (or just wants to poll) find out where an exam
        currently stands without submitting an answer and without mutating
        any state - unlike process_answer, this never advances the session."""
        session = self.store.get(exam_id)
        if session is None:
            raise ValueError(f"Unknown exam_id: {exam_id}")

        if session.is_finished:
            return {
                "status": "exam_ended",
                "exam_id": session.exam_id,
                "results": _topic_results_summary(session, session.bank),
            }

        question = session.bank.get_by_id(session.current_question_id)
        return {
            "status": "in_progress",
            "exam_id": session.exam_id,
            "question": self._public_question(question),
            "question_timeout_seconds": get_question_timeout_seconds(),
        }

    def get_report(self, exam_id: str) -> str:
        session = self.store.get(exam_id)
        if session is None:
            raise ValueError(f"Unknown exam_id: {exam_id}")
        if not session.is_finished:
            raise ValueError("Exam is not finished yet; report unavailable.")

        if session.report_text is not None:
            logger.info("Report cache hit: exam_id=%s", exam_id)
            return session.report_text

        logger.info("Generating report via LLM: exam_id=%s", exam_id)
        report_text = _generate_report_text(session, session.bank)
        session.report_text = report_text
        self.store.save(session)
        return report_text

    @staticmethod
    def _public_question(question: Question) -> Dict[str, Any]:
        """What the student-facing side receives — no `answer` field."""
        return {
            "question_id": question.question_id,
            "topic_name": question.topic_name,
            "difficulty_level": question.difficulty_level.value,
            "question_type": question.question_type.value,
            "question": question.question,
        }


# ---------------------------------------------------------------------------
# Singleton (process-wide) getter, matching the other features' pattern
# (get_rag(), get_knowledge_graph_service()).
# ---------------------------------------------------------------------------
_service: Optional[AssessmentService] = None


def get_assessment_service() -> AssessmentService:
    """One shared in-process AssessmentService per process, so the
    in-memory session store and the global cooldown registry persist
    across calls."""
    global _service
    if _service is None:
        _service = AssessmentService(
            question_source=QuestionBankSource(),
            store=get_session_repository(),
            cooldown_registry=get_cooldown_registry(),
        )
    return _service
