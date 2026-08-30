"""Native LLM-based Knowledge Graph extraction from a PDF.

Replaces the external ``semantica_graph`` package (an earlier attempt that
has since been dropped - see git history / team discussion) with a
self-contained pipeline that uses the same OpenRouter LLM the rest of the
app already calls (``question_bank`` for question generation,
``assessment`` for reports). No separate package to install, no local
editable path to pin in ``pyproject.toml``.

Pipeline (PDF -> graph JSON), all through :func:`LLMGraphExtractor.generate`:

1. **Extract text** page by page (``pdf_text_extractor.extract_pages``).
2. **Chunk** the pages into windows bounded by
   ``KNOWLEDGE_GRAPH_CHUNK_CHAR_BUDGET`` characters each (default 12,000),
   so a long book is many bounded LLM calls instead of one call that either
   truncates the book or blows the model's context window.
3. **Extract entities per chunk**: one LLM call per chunk asks for the
   distinct educational topics/concepts covered in that chunk, as JSON.
4. **Merge + dedupe** entities across all chunks by normalized name (same
   topic mentioned in two chunks collapses to one entity) and assign each a
   stable id (``entity_1``, ``entity_2``, ...) in first-seen order.
5. **Extract relationships**: one further LLM call, given the full merged
   entity list (id + name + description), asks for ``subsetOf`` /
   ``prerequisiteOf`` edges between them.

The output shape is a plain dict — ``{"entities": [...], "relationships":
[...], "metadata": {...}}`` — matching exactly what
``question_bank/questions_service.py`` already reads (``entity["id"]``,
``entity["text"]``, ``relationship["source"/"target"/"type"]``): that
consumer contract does not change, only how the graph is produced.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .config import get_chunk_char_budget
from .llm_client import get_llm_response
from .pdf_text_extractor import extract_pages

logger = logging.getLogger(__name__)

RELATIONSHIP_TYPES = ("subsetOf", "prerequisiteOf")

Generator = Callable[[str, str], str]


class GraphExtractionError(RuntimeError):
    """Raised when the LLM pipeline could not produce a usable graph
    (e.g. no extractable text in the PDF, or the LLM never returned a
    usable topic list) - always includes a specific reason."""


def _chunk_pages(pages: list[str], *, max_chars: int) -> list[str]:
    """Group consecutive non-empty pages into windows up to ``max_chars``
    each, preserving reading order. A single page longer than the budget on
    its own still becomes its own (oversized) chunk rather than being
    split mid-sentence - simpler, and rare in practice for one PDF page."""
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for page_text in pages:
        page_text = page_text.strip()
        if not page_text:
            continue
        if current and current_len + len(page_text) > max_chars:
            chunks.append("\n\n".join(current))
            current, current_len = [], 0
        current.append(page_text)
        current_len += len(page_text)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _parse_json_object(raw_response: str) -> dict[str, Any]:
    """Same parse strategy as question_bank.questions_service._parse_questions:
    try strict JSON first, then the project's JSON-repair dependency for the
    (common, with LLMs) case of near-valid JSON."""
    try:
        payload = json.loads(raw_response)
    except json.JSONDecodeError:
        from json_repair import loads as repair_json

        payload = repair_json(raw_response)
    return payload if isinstance(payload, dict) else {}


def _entity_extraction_prompt(chunk_text: str) -> str:
    return f"""
You are extracting a knowledge graph of educational topics from one segment
of a school textbook.

Identify the distinct topics/concepts explicitly covered in the text below,
at a granularity useful for organizing exam questions: roughly one entity
per lesson or sub-lesson-sized concept - not one per sentence, and not a
single entity for the whole chapter.

Write each entity's "name" in the SAME language as the source text below
(e.g. if the source is Arabic, write Arabic names).

Return JSON only, no prose before or after, in exactly this shape:
{{
  "entities": [
    {{"name": "<topic name>", "type": "concept", "description": "<one sentence: what this topic covers>"}}
  ]
}}
If this text segment contains no clear educational topic, return
{{"entities": []}}.

Text segment:
<<<
{chunk_text}
>>>
""".strip()


def _relationship_extraction_prompt(entities: list[dict[str, Any]]) -> str:
    topics = [
        {"id": entity["id"], "name": entity["text"], "description": entity.get("description", "")}
        for entity in entities
    ]
    return f"""
You are given a list of educational topics extracted from a textbook, each
with a short description. Identify meaningful relationships between them
for a curriculum knowledge graph.

Only use these two relationship types:
- "subsetOf": the source topic is a specific sub-topic of the broader
  target topic (source is part of target).
- "prerequisiteOf": a student must understand the source topic before the
  target topic (source comes first, chronologically/conceptually).

Only include relationships you are reasonably confident about from the
topic names/descriptions. Returning few or no relationships is fine if the
topics are mostly independent - do not invent relationships to pad the list.

Topics:
{json.dumps(topics, ensure_ascii=False)}

Return JSON only, no prose before or after, in exactly this shape:
{{"relationships": [{{"source": "<id>", "target": "<id>", "type": "subsetOf"}}]}}
""".strip()


def _normalize_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).casefold()


def _merge_entities(per_chunk_entities: list[list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """Dedupe by normalized name across chunks, first-seen description wins,
    and assign stable ids in first-seen order (independent of any id an LLM
    call might have hallucinated - never trusted, same principle as
    question_bank.questions_service._question_id not trusting LLM-supplied ids)."""
    merged: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    counter = 0
    for chunk_entities in per_chunk_entities:
        for raw in chunk_entities:
            if not isinstance(raw, dict):
                continue
            name = str(raw.get("name") or "").strip()
            if not name:
                continue
            key = _normalize_name(name)
            if key in merged:
                continue
            counter += 1
            merged[key] = {
                "id": f"entity_{counter}",
                "text": name,
                "type": str(raw.get("type") or "concept").strip() or "concept",
                "description": str(raw.get("description") or "").strip(),
                "metadata": {"description": str(raw.get("description") or "").strip()},
            }
            order.append(key)
    return [merged[key] for key in order]


def _validate_relationships(raw_relationships: list[Any], *, entity_ids: set[str]) -> list[dict[str, str]]:
    relationships: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for raw in raw_relationships:
        if not isinstance(raw, dict):
            continue
        source, target, rel_type = raw.get("source"), raw.get("target"), raw.get("type")
        if not isinstance(source, str) or not isinstance(target, str) or rel_type not in RELATIONSHIP_TYPES:
            logger.warning("Skipping malformed relationship from LLM: %r", raw)
            continue
        if source not in entity_ids or target not in entity_ids:
            logger.warning("Skipping relationship with unknown entity id: %r", raw)
            continue
        if source == target:
            continue
        key = (source, target, rel_type)
        if key in seen:
            continue
        seen.add(key)
        relationships.append({"source": source, "target": target, "type": rel_type})
    return relationships


class LLMGraphExtractor:
    """Runs the PDF -> Knowledge Graph pipeline described in the module
    docstring. ``generator`` is injectable (same pattern as
    ``question_bank.questions_service.generate_questions_from_knowledge_graph``)
    so tests can exercise the merge/validation logic without calling a real
    LLM."""

    def __init__(self, *, generator: Generator | None = None) -> None:
        self._generate_text = generator or get_llm_response

    def generate(self, *, pdf_path: Path, model_name: str, output_dir: Path) -> dict[str, Any]:
        """Run the full pipeline and write ``<pdf-stem>_graph.json`` under
        ``output_dir`` (mirrors the previous external client's behavior, so
        the caller's on-disk caching/registry logic in
        ``application/graph_service.py`` needs no changes)."""
        pages = extract_pages(pdf_path)
        chunks = _chunk_pages(pages, max_chars=get_chunk_char_budget())
        if not chunks:
            raise GraphExtractionError(
                f"No extractable text found in PDF: {pdf_path.name}. "
                "It may be a scanned/image-only PDF with no text layer."
            )

        per_chunk_entities: list[list[dict[str, Any]]] = []
        for index, chunk in enumerate(chunks, 1):
            logger.info("Extracting entities from chunk %d/%d of '%s'", index, len(chunks), pdf_path.name)
            raw_response = self._generate_text(model_name, _entity_extraction_prompt(chunk))
            parsed = _parse_json_object(raw_response)
            entities = parsed.get("entities")
            per_chunk_entities.append(entities if isinstance(entities, list) else [])

        entities = _merge_entities(per_chunk_entities)
        if not entities:
            raise GraphExtractionError(
                f"The LLM did not extract any topics/entities from '{pdf_path.name}'."
            )
        logger.info("Merged into %d distinct entities for '%s'", len(entities), pdf_path.name)

        logger.info("Extracting relationships between %d entities for '%s'", len(entities), pdf_path.name)
        raw_response = self._generate_text(model_name, _relationship_extraction_prompt(entities))
        parsed = _parse_json_object(raw_response)
        raw_relationships = parsed.get("relationships")
        relationships = _validate_relationships(
            raw_relationships if isinstance(raw_relationships, list) else [],
            entity_ids={entity["id"] for entity in entities},
        )
        logger.info("Kept %d valid relationship(s) for '%s'", len(relationships), pdf_path.name)

        graph: dict[str, Any] = {
            "entities": entities,
            "relationships": relationships,
            "metadata": {
                "source_file_name": pdf_path.name,
                "model": model_name,
                "chunk_count": len(chunks),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        output_dir.mkdir(parents=True, exist_ok=True)
        graph_path = output_dir / f"{pdf_path.stem}_graph.json"
        graph_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return graph

    @staticmethod
    def find_graph_json(output_dir: Path) -> Path | None:
        """Locate the ``*_graph.json`` file :meth:`generate` wrote, if any."""
        matches = list(output_dir.glob("*_graph.json"))
        return matches[0] if matches else None
