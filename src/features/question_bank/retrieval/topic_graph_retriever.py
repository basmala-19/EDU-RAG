from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from topic_retriever import retrieve_topic_chunks


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

GRAPH_PATH = Path(
    r"files\graph_dictionary_files\deepseek_deepseek_v4_flash_0731_basicMath494pages_13_15_graph.json"
)

RETRIEVAL_RESULTS_DIR = Path(
    "retrieval_results"
)

FINAL_RESULTS_DIR = Path(
    "graph_topic_retrieval_results"
)

FINAL_RESULTS_FILE = (
    FINAL_RESULTS_DIR
    / "topic_retrieval_tree.json"
)


# ============================================================
# GRAPH LOADING
# ============================================================

def load_graph(
    graph_path: str | Path,
) -> dict[str, Any]:

    graph_path = Path(graph_path)

    if not graph_path.exists():
        raise FileNotFoundError(
            f"Graph file does not exist: {graph_path}"
        )

    with graph_path.open(
        "r",
        encoding="utf-8",
    ) as file:

        graph = json.load(file)

    if not isinstance(graph, dict):
        raise ValueError(
            "Graph root must be a dictionary."
        )

    if not isinstance(
        graph.get("entities"),
        list,
    ):
        raise ValueError(
            "Graph must contain an 'entities' list."
        )

    if not isinstance(
        graph.get("relationships"),
        list,
    ):
        raise ValueError(
            "Graph must contain a 'relationships' list."
        )

    logger.info(
        "Loaded graph: %d entities | %d relationships",
        len(graph["entities"]),
        len(graph["relationships"]),
    )

    return graph


# ============================================================
# ENTITY INDEX
# ============================================================

def build_entity_index(
    graph: dict[str, Any],
) -> dict[str, dict[str, Any]]:

    entity_index: dict[str, dict[str, Any]] = {}

    for entity in graph["entities"]:

        entity_id = entity.get("id")

        if not isinstance(
            entity_id,
            str,
        ):
            continue

        if entity_id in entity_index:
            raise ValueError(
                f"Duplicate entity ID: {entity_id}"
            )

        entity_index[entity_id] = entity

    return entity_index


# ============================================================
# RELATIONSHIP INDEXES
# ============================================================

def build_relationship_indexes(
    graph: dict[str, Any],
) -> tuple[
    dict[str, list[str]],
    dict[str, list[str]],
]:

    subsets_by_parent: dict[str, list[str]] = {}

    prerequisites_by_topic: dict[str, list[str]] = {}

    for relationship in graph["relationships"]:

        source = relationship.get("source")
        target = relationship.get("target")
        relation_type = relationship.get("type")

        if not isinstance(source, str):
            continue

        if not isinstance(target, str):
            continue

        # source subsetOf target
        #
        # Therefore target -> source
        # when traversing downward through the hierarchy.
        if relation_type == "subsetOf":

            subsets_by_parent.setdefault(
                target,
                [],
            ).append(source)

        # source prerequisiteOf target
        #
        # Therefore target -> source
        # when looking for prerequisites.
        elif relation_type == "prerequisiteOf":

            prerequisites_by_topic.setdefault(
                target,
                [],
            ).append(source)

    return (
        subsets_by_parent,
        prerequisites_by_topic,
    )


# ============================================================
# TOP TOPICS
# ============================================================

def find_top_topics(
    graph: dict[str, Any],
    entity_index: dict[str, dict[str, Any]],
) -> list[str]:

    subset_sources: set[str] = set()

    for relationship in graph["relationships"]:

        if relationship.get("type") != "subsetOf":
            continue

        source = relationship.get("source")

        if isinstance(source, str):
            subset_sources.add(source)

    return [
        entity_id
        for entity_id in entity_index
        if entity_id not in subset_sources
    ]


# ============================================================
# DUPLICATE TOPIC NAMES
# ============================================================

def find_duplicate_topic_names(
    entity_index: dict[str, dict[str, Any]],
) -> set[str]:

    name_to_ids: dict[str, list[str]] = {}

    for entity_id, entity in entity_index.items():

        name = entity.get(
            "text",
            entity_id,
        )

        name_to_ids.setdefault(
            name,
            [],
        ).append(entity_id)

    return {
        name
        for name, ids in name_to_ids.items()
        if len(ids) > 1
    }


# ============================================================
# FILENAME
# ============================================================

def sanitize_filename(
    text: str,
    maximum_length: int = 60,
) -> str:

    safe = "".join(
        character
        if character.isalnum()
        or character in " _-"
        else "_"
        for character in text
    ).strip()

    return safe[:maximum_length] or "topic"


def topic_cache_path(
    topic_id: str,
    topic_name: str,
    duplicate_topic_names: set[str],
) -> Path:

    safe_name = sanitize_filename(
        topic_name
    )

    if topic_name in duplicate_topic_names:

        safe_id = sanitize_filename(
            topic_id
        )

        filename = (
            f"{safe_name}__{safe_id}.json"
        )

    else:

        filename = (
            f"{safe_name}.json"
        )

    return (
        RETRIEVAL_RESULTS_DIR
        / filename
    )


# ============================================================
# RETRIEVAL CACHE
# ============================================================

def retrieve_or_load_topic(
    topic_id: str,
    topic_name: str,
    duplicate_topic_names: set[str],
) -> dict[str, Any]:

    RETRIEVAL_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cache_path = topic_cache_path(
        topic_id=topic_id,
        topic_name=topic_name,
        duplicate_topic_names=duplicate_topic_names,
    )

    # --------------------------------------------------------
    # Existing result
    # --------------------------------------------------------

    if cache_path.exists():

        logger.info(
            "CACHE HIT: %s",
            topic_name,
        )

        with cache_path.open(
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    # --------------------------------------------------------
    # Run retrieval
    # --------------------------------------------------------

    logger.info(
        "CACHE MISS: retrieving '%s'",
        topic_name,
    )

    result = retrieve_topic_chunks(
        topic_name
    )

    with cache_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False,
        )

    return result


# ============================================================
# DEPTH CHECK
# ============================================================

def depth_allowed(
    current_depth: int,
    maximum_depth: int | None,
) -> bool:
    """
    None means unlimited depth.
    """

    if maximum_depth is None:
        return True

    return current_depth < maximum_depth


# ============================================================
# CREATE TOPIC NODE
# ============================================================

def create_topic_node(
    topic_id: str,
    entity_index: dict[str, dict[str, Any]],
    duplicate_topic_names: set[str],
    traversal_state: dict[str, Any],
    subsets_by_parent: dict[str, list[str]],
    prerequisites_by_topic: dict[str, list[str]],
    subset_depth: int | None,
    prerequisite_depth: int | None,
    current_subset_depth: int,
    current_prerequisite_depth: int,
    subset_path: set[str],
    prerequisite_path: set[str],
) -> dict[str, Any]:

    entity = entity_index[topic_id]

    topic_name = entity.get(
        "text",
        topic_id,
    )

    # ========================================================
    # GLOBAL PER-TOP-TOPIC VISITED CHECK
    # ========================================================

    already_traversed = (
        topic_id
        in traversal_state["visited"]
    )

    if already_traversed:

        logger.debug(
            "Already traversed for this top topic: %s",
            topic_id,
        )

        return {
            "id": topic_id,
            "name": topic_name,
            "metadata": entity.get(
                "metadata",
                {},
            ),
            "chunks": [],
            "confidence_scores": [],
            "subtopics": [],
            "prerequisites": [],
            "already_traversed": True,
        }

    # ========================================================
    # CYCLE PROTECTION
    # ========================================================

    if topic_id in subset_path:

        logger.warning(
            "Subset cycle detected at: %s",
            topic_id,
        )

        return {
            "id": topic_id,
            "name": topic_name,
            "metadata": entity.get(
                "metadata",
                {},
            ),
            "chunks": [],
            "confidence_scores": [],
            "subtopics": [],
            "prerequisites": [],
            "cycle_detected": True,
        }

    if topic_id in prerequisite_path:

        logger.warning(
            "Prerequisite cycle detected at: %s",
            topic_id,
        )

        return {
            "id": topic_id,
            "name": topic_name,
            "metadata": entity.get(
                "metadata",
                {},
            ),
            "chunks": [],
            "confidence_scores": [],
            "subtopics": [],
            "prerequisites": [],
            "cycle_detected": True,
        }

    # ========================================================
    # MARK AS TRAVERSED
    # ========================================================

    traversal_state["visited"].add(
        topic_id
    )

    traversal_state["traversal_order"].append(
        topic_id
    )

    logger.info(
        "TRAVERSE [%d]: %s (%s)",
        len(
            traversal_state["traversal_order"]
        ),
        topic_name,
        topic_id,
    )

    # ========================================================
    # RETRIEVE CHUNKS
    # ========================================================

    retrieval_result = retrieve_or_load_topic(
        topic_id=topic_id,
        topic_name=topic_name,
        duplicate_topic_names=duplicate_topic_names,
    )

    node: dict[str, Any] = {
        "id": topic_id,
        "name": topic_name,

        "metadata": entity.get(
            "metadata",
            {},
        ),

        "chunks": retrieval_result.get(
            "chunks",
            [],
        ),

        "confidence_scores": retrieval_result.get(
            "confidence_scores",
            [],
        ),

        "subtopics": [],
        "prerequisites": [],
    }

    # ========================================================
    # SUBTOPICS
    # ========================================================

    if depth_allowed(
        current_subset_depth,
        subset_depth,
    ):

        children = subsets_by_parent.get(
            topic_id,
            [],
        )

        for child_id in children:

            child_node = create_topic_node(
                topic_id=child_id,
                entity_index=entity_index,
                duplicate_topic_names=(
                    duplicate_topic_names
                ),
                traversal_state=(
                    traversal_state
                ),
                subsets_by_parent=(
                    subsets_by_parent
                ),
                prerequisites_by_topic=(
                    prerequisites_by_topic
                ),
                subset_depth=subset_depth,
                prerequisite_depth=(
                    prerequisite_depth
                ),
                current_subset_depth=(
                    current_subset_depth + 1
                ),
                current_prerequisite_depth=(
                    current_prerequisite_depth
                ),
                subset_path=(
                    subset_path | {topic_id}
                ),
                prerequisite_path=(
                    prerequisite_path
                ),
            )

            # Only include actual newly-built nodes.
            if not child_node.get(
                "already_traversed",
                False,
            ):

                node["subtopics"].append(
                    child_node
                )

    # ========================================================
    # PREREQUISITES
    # ========================================================

    if depth_allowed(
        current_prerequisite_depth,
        prerequisite_depth,
    ):

        prerequisites = (
            prerequisites_by_topic.get(
                topic_id,
                [],
            )
        )

        for prerequisite_id in prerequisites:

            prerequisite_node = create_topic_node(
                topic_id=prerequisite_id,
                entity_index=entity_index,
                duplicate_topic_names=(
                    duplicate_topic_names
                ),
                traversal_state=(
                    traversal_state
                ),
                subsets_by_parent=(
                    subsets_by_parent
                ),
                prerequisites_by_topic=(
                    prerequisites_by_topic
                ),
                subset_depth=subset_depth,
                prerequisite_depth=(
                    prerequisite_depth
                ),
                current_subset_depth=(
                    current_subset_depth
                ),
                current_prerequisite_depth=(
                    current_prerequisite_depth + 1
                ),
                subset_path=(
                    subset_path
                ),
                prerequisite_path=(
                    prerequisite_path | {topic_id}
                ),
            )

            if not prerequisite_node.get(
                "already_traversed",
                False,
            ):

                node["prerequisites"].append(
                    prerequisite_node
                )

    return node


# ============================================================
# MAIN
# ============================================================

def retrieve_graph_topics(
    graph_path: str | Path = GRAPH_PATH,

    # None means unlimited.
    subset_depth: int | None = None,

    # None means unlimited.
    prerequisite_depth: int | None = None,
) -> dict[str, Any]:

    graph = load_graph(
        graph_path
    )

    entity_index = build_entity_index(
        graph
    )

    (
        subsets_by_parent,
        prerequisites_by_topic,
    ) = build_relationship_indexes(
        graph
    )

    duplicate_topic_names = (
        find_duplicate_topic_names(
            entity_index
        )
    )

    top_topic_ids = find_top_topics(
        graph=graph,
        entity_index=entity_index,
    )

    logger.info(
        "Top topics: %d",
        len(top_topic_ids),
    )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    result: dict[str, Any] = {
        "metadata": {
            "graph_path": str(
                graph_path
            ),

            "subset_depth": (
                subset_depth
            ),

            "prerequisite_depth": (
                prerequisite_depth
            ),

            "number_of_entities": len(
                entity_index
            ),

            "number_of_top_topics": len(
                top_topic_ids
            ),
        },

        "top_topics": [],
    }

    # ========================================================
    # PROCESS EACH TOP TOPIC
    # ========================================================

    for index, top_topic_id in enumerate(
        top_topic_ids,
        start=1,
    ):

        top_entity = entity_index[
            top_topic_id
        ]

        top_name = top_entity.get(
            "text",
            top_topic_id,
        )

        logger.info(
            "=" * 80
        )

        logger.info(
            "TOP TOPIC %d/%d: %s [%s]",
            index,
            len(top_topic_ids),
            top_name,
            top_topic_id,
        )

        logger.info(
            "=" * 80
        )

        # ----------------------------------------------------
        # Per-top-topic traversal state
        # ----------------------------------------------------

        traversal_state = {
            "visited": set(),
            "traversal_order": [],
        }

        # ----------------------------------------------------
        # Traverse
        # ----------------------------------------------------

        tree = create_topic_node(
            topic_id=top_topic_id,

            entity_index=entity_index,

            duplicate_topic_names=(
                duplicate_topic_names
            ),

            traversal_state=(
                traversal_state
            ),

            subsets_by_parent=(
                subsets_by_parent
            ),

            prerequisites_by_topic=(
                prerequisites_by_topic
            ),

            subset_depth=subset_depth,

            prerequisite_depth=(
                prerequisite_depth
            ),

            current_subset_depth=0,

            current_prerequisite_depth=0,

            subset_path=set(),

            prerequisite_path=set(),
        )

        # ----------------------------------------------------
        # Attach traversal information
        # ----------------------------------------------------

        tree["traversal"] = {
            "node_count": len(
                traversal_state[
                    "traversal_order"
                ]
            ),

            "node_ids": (
                traversal_state[
                    "traversal_order"
                ]
            ),
        }

        result["top_topics"].append(
            tree
        )

        logger.info(
            "Top topic '%s' traversed %d nodes.",
            top_name,
            len(
                traversal_state[
                    "traversal_order"
                ]
            ),
        )

        logger.info(
            "Total graph nodes: %d | "
            "reachable/traversed from this top topic: %d",
            len(entity_index),
            len(
                traversal_state[
                    "traversal_order"
                ]
            ),
        )

    # ========================================================
    # SAVE FINAL RESULT
    # ========================================================

    FINAL_RESULTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with FINAL_RESULTS_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False,
        )

    logger.info(
        "Saved final result: %s",
        FINAL_RESULTS_FILE,
    )

    return result


# ============================================================
# STANDALONE EXECUTION   #  -----------------------------------------> (((((((((THE RUN OF THE CODE STARTS FROM HERE))))))))) ++++++
# ============================================================

if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
    )

    result = retrieve_graph_topics(
        graph_path=GRAPH_PATH,

        # None = unlimited.
        #
        # 0 = top topic only
        # 1 = direct subsets
        # 2 = subsets + grandchildren
        subset_depth=None,

        # None = unlimited.
        #
        # 0 = no prerequisites
        # 1 = direct prerequisites
        # 2 = prerequisites recursively
        prerequisite_depth=None,
    )

    print()
    print("=" * 80)
    print("GRAPH RETRIEVAL COMPLETED")
    print("=" * 80)

    print(
        "Top topics:",
        len(
            result["top_topics"]
        ),
    )

    for top_topic in result[
        "top_topics"
    ]:

        print()
        print(
            f"TOPIC: {top_topic['name']}"
        )

        print(
            "Traversed nodes:",
            top_topic[
                "traversal"
            ][
                "node_count"
            ],
        )

    print()
    print(
        "Saved:",
        FINAL_RESULTS_FILE,
    )