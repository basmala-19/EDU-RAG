"""Public API for generating and retrieving bank questions.

The service deliberately keeps one JSON document per topic.  A document is
both the storage unit and the retrieval unit, so no database scan/index is
required to retrieve questions for a grade, subject, and topic.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .config import get_llm_model, get_question_counts_by_difficulty

logger = logging.getLogger(__name__)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_ROOT = PROJECT_ROOT / "data" / "question_bank"

Retriever = Callable[[str], dict[str, Any]]
Generator = Callable[[str, str], str]


def _safe_path_part(value: str) -> str:
    """Return a readable, filesystem-safe path component."""
    cleaned = re.sub(r"[^\w.-]+", "_", value.strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("._")
    if not cleaned:
        raise ValueError("grade, subject, and topic cannot be empty.")
    return cleaned[:120]


def _load_graph(knowledge_graph: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(knowledge_graph, dict):
        graph = knowledge_graph
    else:
        path = Path(knowledge_graph)
        if not path.is_file():
            raise FileNotFoundError(f"Knowledge graph does not exist: {path}")
        graph = json.loads(path.read_text(encoding="utf-8"))

    # Some graph-generation APIs wrap the actual graph as
    # {"success": true, "graph": {"entities": [...]}}.  Accept that response
    # directly so it can be uploaded to the UI without manual editing.
    if isinstance(graph, dict) and isinstance(graph.get("graph"), dict) and "entities" not in graph:
        graph = graph["graph"]

    graph = _repair_mojibake(graph)

    if not isinstance(graph, dict) or not isinstance(graph.get("entities"), list):
        raise ValueError("Knowledge graph must be an object with an 'entities' list.")
    return graph


def _repair_mojibake(value: Any) -> Any:
    """Repair common UTF-8-as-Latin-1 corruption in API-produced Arabic text.

    Correct UTF-8 Arabic text is left untouched. If a value cannot safely be
    repaired, it is preserved exactly as supplied.
    """
    if isinstance(value, dict):
        return {key: _repair_mojibake(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_repair_mojibake(item) for item in value]
    if not isinstance(value, str) or not any(marker in value for marker in ("Ø", "Ù", "Ã")):
        return value

    for encoding in ("latin-1", "cp1252"):
        try:
            repaired = value.encode(encoding).decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if repaired != value:
            return repaired
    return value


def get_graph_entities(knowledge_graph: dict[str, Any] | str | Path) -> list[dict[str, str]]:
    """Return normalized entities for a user to select before generation."""
    graph = _load_graph(knowledge_graph)
    entities: list[dict[str, str]] = []
    for entity in graph["entities"]:
        if not isinstance(entity, dict):
            continue
        entity_id = entity.get("id")
        entity_name = entity.get("text", entity_id)
        if isinstance(entity_id, str) and isinstance(entity_name, str):
            entities.append({"id": entity_id, "name": entity_name})
    return entities


def _default_retriever(topic: str) -> dict[str, Any]:
    raise RuntimeError("A RAG file reference is required. Use the shared RAG client retriever.")


def _default_generator(model: str, prompt: str) -> str:
    from .llm_api.openai_api import get_llm_response

    return get_llm_response(model, prompt)


def _parse_questions(raw_response: str) -> list[dict[str, Any]]:
    """Parse normal JSON first, then use the project's JSON repair dependency."""
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError:
        from json_repair import loads as repair_json

        payload = repair_json(raw_response)

    if not isinstance(payload, dict) or not isinstance(payload.get("questions"), list):
        raise ValueError("LLM response must be a JSON object containing a 'questions' list.")
    if not all(isinstance(question, dict) for question in payload["questions"]):
        raise ValueError("Every generated question must be a JSON object.")
    return payload["questions"]


def _question_id(question: dict[str, Any]) -> str:
    """Generate a stable ID without trusting an ID returned by the LLM."""
    identity = {key: value for key, value in question.items() if key not in {"id", "metadata"}}
    canonical = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "q_" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def _direct_graph_context(graph: dict[str, Any], topic_id: str) -> dict[str, list[dict[str, str]]]:
    """Return the direct prerequisite/subtopic context for one graph entity."""
    entity_names = {
        entity["id"]: entity.get("text", entity["id"])
        for entity in graph["entities"]
        if isinstance(entity, dict) and isinstance(entity.get("id"), str)
    }
    context: dict[str, list[dict[str, str]]] = {
        "subtopics": [],
        "prerequisites": [],
        "parent_topics": [],
        "dependent_topics": [],
    }
    for relationship in graph.get("relationships", []):
        if not isinstance(relationship, dict):
            continue
        source = relationship.get("source")
        target = relationship.get("target")
        relation_type = relationship.get("type")
        if not isinstance(source, str) or not isinstance(target, str):
            continue
        if relation_type == "subsetOf":
            if target == topic_id:
                context["subtopics"].append({"id": source, "name": entity_names.get(source, source)})
            elif source == topic_id:
                context["parent_topics"].append({"id": target, "name": entity_names.get(target, target)})
        elif relation_type == "prerequisiteOf":
            if target == topic_id:
                context["prerequisites"].append({"id": source, "name": entity_names.get(source, source)})
            elif source == topic_id:
                context["dependent_topics"].append({"id": target, "name": entity_names.get(target, target)})
    return context


def _build_prompt(
    *,
    grade: str,
    subject: str,
    topic: str,
    subtree: dict[str, Any],
    graph_context: dict[str, list[dict[str, str]]],
    question_counts: dict[int, int],
) -> str:
    # Keep the grade near the top of the prompt: it is a generation constraint,
    # not merely metadata added after generation.
    return f"""
Generate questions for the following school level and subject.

Grade: {grade}
Subject: {subject}
Topic: {topic}

The grade is mandatory: use vocabulary, prerequisite knowledge, calculations,
and cognitive demand appropriate for students in this grade. Do not generate
questions that require knowledge beyond this grade.

Generate exactly the following number of questions for each `task_difficulty`:
{json.dumps({str(level): count for level, count in question_counts.items()})}
Do not produce questions for a difficulty whose requested count is 0. Every
question must include its `task_difficulty` as an integer from 1 to 5.

Direct knowledge-graph context (use it only as background; generate questions
about the stated Topic, not a different related topic):
{json.dumps(graph_context, ensure_ascii=False)}

Use only the retrieved material below as the knowledge source. Generate
questions only about the stated Topic; prerequisite and subtopic material is
context, not a separate target. Return JSON only, in this exact shape:
{{"questions": [{{...}}]}}

Retrieved topic material:
{json.dumps(subtree, ensure_ascii=False)}
""".strip()


def generate_questions_from_knowledge_graph(
    knowledge_graph: dict[str, Any] | str | Path,
    grade: str,
    subject: str,
    *,
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    retriever: Retriever | None = None,
    generator: Generator | None = None,
    model: str | None = None,
    overwrite: bool = False,
    entity_ids: Iterable[str] | None = None,
    rag_file_reference_id: str | None = None,
) -> list[Path]:
    """Retrieve each graph entity, generate its questions, and store one file/topic.

    Files are written as ``<output_root>/<grade>/<subject>/<topic-id>.json``.
    When ``entity_ids`` is supplied, only those topic IDs are processed.
    ``retriever`` and ``generator`` are injectable to make batch jobs and tests
    independent of the local vector database and LLM provider.
    """
    if not all(isinstance(value, str) and value.strip() for value in (grade, subject)):
        raise ValueError("grade and subject must be non-empty strings.")

    graph = _load_graph(knowledge_graph)
    if retriever is not None:
        retrieve = retriever
    else:
        if not isinstance(rag_file_reference_id, str) or not rag_file_reference_id.strip():
            raise ValueError("rag_file_reference_id is required when no custom retriever is supplied.")
        # Question Bank and RAG are features of the same application. Keep the
        # integration in-process instead of calling a second local HTTP service.
        from src.features.rag.application.question_bank_integration import QuestionBankRAG

        rag = QuestionBankRAG()
        retrieve = lambda topic: rag.retrieve_topic(topic, rag_file_reference_id)
    generate = generator or _default_generator
    selected_model = model or get_llm_model()
    question_counts = get_question_counts_by_difficulty()
    subject_dir = Path(output_root) / _safe_path_part(grade) / _safe_path_part(subject)
    saved_paths: list[Path] = []
    seen_ids: set[str] = set()
    requested_entity_ids = set(entity_ids) if entity_ids is not None else None
    all_entity_ids = {
        entity.get("id")
        for entity in graph["entities"]
        if isinstance(entity, dict) and isinstance(entity.get("id"), str)
    }
    if requested_entity_ids is not None:
        unknown_entity_ids = requested_entity_ids - all_entity_ids
        if unknown_entity_ids:
            raise ValueError(f"Unknown entity IDs: {', '.join(sorted(unknown_entity_ids))}")

    for entity in graph["entities"]:
        if not isinstance(entity, dict):
            raise ValueError("Every knowledge-graph entity must be an object.")
        topic_id = entity.get("id")
        topic_name = entity.get("text", topic_id)
        if not isinstance(topic_id, str) or not topic_id.strip():
            raise ValueError("Every entity must have a non-empty string 'id'.")
        if not isinstance(topic_name, str) or not topic_name.strip():
            raise ValueError(f"Entity '{topic_id}' must have a non-empty 'text'.")
        if topic_id in seen_ids:
            raise ValueError(f"Duplicate entity ID in knowledge graph: {topic_id}")
        seen_ids.add(topic_id)

        if requested_entity_ids is not None and topic_id not in requested_entity_ids:
            continue

        destination = subject_dir / f"{_safe_path_part(topic_id)}.json"
        if destination.exists() and not overwrite:
            logger.info(
                "Topic '%s' (id=%s) already has a saved file at %s - skipping generation, reusing it as-is. "
                "Pass overwrite=True to regenerate.",
                topic_name, topic_id, destination,
            )
            saved_paths.append(destination)
            continue

        logger.info("Retrieving RAG evidence for topic '%s' (id=%s)", topic_name, topic_id)
        retrieved = retrieve(topic_name)
        if not isinstance(retrieved, dict):
            raise TypeError(f"Retriever must return an object for topic '{topic_name}'.")
        prompt = _build_prompt(
            grade=grade,
            subject=subject,
            topic=topic_name,
            subtree=retrieved,
            graph_context=_direct_graph_context(graph, topic_id),
            question_counts=question_counts,
        )
        logger.info("Calling LLM (%s) to generate questions for topic '%s'", selected_model, topic_name)
        raw_response = generate(selected_model, prompt)
        if not isinstance(raw_response, str):
            raise TypeError(f"Generator must return text for topic '{topic_name}'.")
        generated_questions = _parse_questions(raw_response)
        logger.info("LLM returned %d question(s) for topic '%s'", len(generated_questions), topic_name)

        topic_metadata = {
            "grade": grade.strip(),
            "subject": subject.strip(),
            "topic": {
                "id": topic_id,
                "name": topic_name,
                "type": entity.get("type"),
                "metadata": entity.get("metadata", {}),
            },
            "graph_metadata": graph.get("metadata", {}),
            "graph_context": _direct_graph_context(graph, topic_id),
            "retrieval": retrieved,
            "generation": {
                "model": selected_model,
                "question_counts_by_difficulty": question_counts,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }
        questions: list[dict[str, Any]] = []
        used_question_ids: set[str] = set()
        for question in generated_questions:
            question_copy = dict(question)
            question_id = _question_id(question_copy)
            if question_id in used_question_ids:
                continue
            used_question_ids.add(question_id)
            original_metadata = question_copy.pop("metadata", None)
            question_copy["id"] = question_id
            question_copy["metadata"] = {
                **topic_metadata,
                "question_metadata": original_metadata,
            }
            questions.append(question_copy)

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps({"metadata": topic_metadata, "questions": questions}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        saved_paths.append(destination)

    return saved_paths


def get_questions(grade: str, subject: str, topic: str, *, output_root: str | Path = DEFAULT_OUTPUT_ROOT) -> list[dict[str, Any]]:
    """Return all questions for an exact grade, subject, and topic with full metadata."""
    if not all(isinstance(value, str) and value.strip() for value in (grade, subject, topic)):
        raise ValueError("grade, subject, and topic must be non-empty strings.")

    subject_dir = Path(output_root) / _safe_path_part(grade) / _safe_path_part(subject)
    if not subject_dir.is_dir():
        logger.info("No saved question directory yet for grade=%s subject=%s (%s)", grade, subject, subject_dir)
        return []

    matches: list[dict[str, Any]] = []
    wanted = topic.strip().casefold()
    available: list[str] = []
    for file_path in subject_dir.glob("*.json"):
        document = json.loads(file_path.read_text(encoding="utf-8"))
        metadata = document.get("metadata", {})
        topic_info = metadata.get("topic", {}) if isinstance(metadata, dict) else {}
        topic_id = str(topic_info.get("id", ""))
        topic_display_name = str(topic_info.get("name", ""))
        available.append(f"{topic_id!r}/{topic_display_name!r}")
        candidates = {topic_id.casefold(), topic_display_name.casefold()}
        if wanted not in candidates:
            continue
        questions = document.get("questions", [])
        if not isinstance(questions, list):
            raise ValueError(f"Invalid question document: {file_path}")
        matches.extend(questions)
    if not matches:
        logger.info(
            "No file matched topic=%r under %s. Saved topic id/name pairs found: %s",
            topic, subject_dir, available or "(none)",
        )
    return matches