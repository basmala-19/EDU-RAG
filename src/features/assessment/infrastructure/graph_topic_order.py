"""Derives an assessment-engine topic plan from a Knowledge Graph.

The standalone engine required the caller to hand it ``kg_edges`` and
``tie_breaker_order`` directly (see its README's curl example). This module
is what removes that manual step: given a Knowledge Graph (from the
``knowledge_graph`` feature) and the set of topic ids that actually have
saved questions (from ``QuestionBankSource``), it derives:

  - the ordered list of ``(topic_id, topic_name)`` pairs to include
  - ``kg_edges``: ``(prerequisite_topic_name, dependent_topic_name)`` pairs,
    read from the graph's ``prerequisiteOf`` relationships (the same
    relation type ``question_bank.questions_service`` already reads for
    generation-time context)
  - ``tie_breaker_order``: each topic's position in the graph's entity
    list, used to order topics that have no dependency relation between
    them (mirrors "book mention order")
"""

from __future__ import annotations

from typing import Any


def build_topic_plan(
    knowledge_graph: dict[str, Any],
    available_topic_ids: set[str] | None = None,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], dict[str, int]]:
    """
    ``available_topic_ids``: restrict the plan to these entity ids (e.g.
    topics that currently have saved questions). ``None`` means include
    every entity in the graph.
    """
    entities = knowledge_graph.get("entities", [])
    if not isinstance(entities, list):
        raise ValueError("Knowledge graph must have an 'entities' list.")

    id_to_name: dict[str, str] = {}
    topic_pairs: list[tuple[str, str]] = []
    tie_breaker_order: dict[str, int] = {}

    for index, entity in enumerate(entities):
        if not isinstance(entity, dict):
            continue
        entity_id = entity.get("id")
        entity_name = entity.get("text", entity_id)
        if not isinstance(entity_id, str) or not isinstance(entity_name, str):
            continue
        id_to_name[entity_id] = entity_name
        if available_topic_ids is None or entity_id in available_topic_ids:
            topic_pairs.append((entity_id, entity_name))
            # First occurrence wins if two entities somehow share a display
            # name; graph entity order is otherwise exactly book/graph
            # mention order.
            tie_breaker_order.setdefault(entity_name, index)

    included_ids = {topic_id for topic_id, _ in topic_pairs}
    kg_edges: list[tuple[str, str]] = []
    for relationship in knowledge_graph.get("relationships", []):
        if not isinstance(relationship, dict) or relationship.get("type") != "prerequisiteOf":
            continue
        source = relationship.get("source")
        target = relationship.get("target")
        if source in included_ids and target in included_ids:
            kg_edges.append((id_to_name[source], id_to_name[target]))

    return topic_pairs, kg_edges, tie_breaker_order
