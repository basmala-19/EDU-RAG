from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


# ============================================================
# CONFIGURATION
# ============================================================

# Full retrieval-tree JSON produced by your graph retrieval stage.
FULL_TREE_PATH = Path(
    r"F:\pythonProj\question_generator\graph_topic_retrieval_results\topic_retrieval_tree.json"
)


# Project root.
#
# If this file is:
#
#     project_root/src/retrieval/topic_subtree_retriever.py
#
# then parents[2] = project_root.
PROJECT_ROOT = Path(
    __file__
).resolve().parents[2]


# Output directory at project root.
TOPIC_SUBTREES_DIR = (
    PROJECT_ROOT
    / "topic_subtrees"
)


# Tracking file.
VISITED_NODES_FILE = (
    TOPIC_SUBTREES_DIR
    / "nodes visited.json"
)


# ============================================================
# DIRECTORY MANAGEMENT
# ============================================================

def ensure_output_directory() -> None:
    """
    Ensure the topic_subtrees directory exists.
    """

    TOPIC_SUBTREES_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# LOAD FULL TREE
# ============================================================

def load_full_tree(
    tree_path: str | Path = FULL_TREE_PATH,
) -> dict[str, Any]:
    """
    Load the complete retrieval tree JSON.
    """

    tree_path = Path(tree_path)

    if not tree_path.exists():
        raise FileNotFoundError(
            f"Full tree JSON does not exist: {tree_path}"
        )

    with tree_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            "Full tree JSON root must be a dictionary."
        )

    if not isinstance(
        data.get("top_topics"),
        list,
    ):
        raise ValueError(
            "Full tree JSON must contain a "
            "'top_topics' list."
        )

    return data


# ============================================================
# BUILD NODE INDEX
# ============================================================

def build_node_index(
    tree: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """
    Build an index:

        node_id -> node dictionary

    The full tree can contain the same logical graph node
    in more than one location because prerequisite branches
    can converge with subset branches.

    The first occurrence is retained.
    """

    index: dict[
        str,
        dict[str, Any],
    ] = {}

    def visit(
        node: dict[str, Any],
    ) -> None:

        node_id = node.get("id")

        if not isinstance(
            node_id,
            str,
        ):
            raise ValueError(
                "Every topic node must contain a string 'id'."
            )

        if node_id not in index:
            index[node_id] = node

        # ----------------------------------------------------
        # Subtopics
        # ----------------------------------------------------

        subtopics = node.get(
            "subtopics",
            [],
        )

        if not isinstance(
            subtopics,
            list,
        ):
            raise ValueError(
                f"'subtopics' must be a list for node "
                f"'{node_id}'."
            )

        for child in subtopics:

            if not isinstance(
                child,
                dict,
            ):
                raise ValueError(
                    f"Invalid subtopic under node "
                    f"'{node_id}'."
                )

            visit(child)

        # ----------------------------------------------------
        # Prerequisites
        # ----------------------------------------------------

        prerequisites = node.get(
            "prerequisites",
            [],
        )

        if not isinstance(
            prerequisites,
            list,
        ):
            raise ValueError(
                f"'prerequisites' must be a list for node "
                f"'{node_id}'."
            )

        for prerequisite in prerequisites:

            if not isinstance(
                prerequisite,
                dict,
            ):
                raise ValueError(
                    f"Invalid prerequisite under node "
                    f"'{node_id}'."
                )

            visit(prerequisite)

    # --------------------------------------------------------
    # Traverse all top-level nodes
    # --------------------------------------------------------

    for top_topic in tree["top_topics"]:

        if not isinstance(
            top_topic,
            dict,
        ):
            raise ValueError(
                "Every top_topic must be a dictionary."
            )

        visit(top_topic)

    return index


# ============================================================
# VISITED-NODES FILE
# ============================================================

def load_visited_nodes() -> set[str]:
    """
    Load IDs of nodes whose subtree has already been generated.

    The file contains a JSON list:

        [
            "algebra",
            "numbers",
            "isometries"
        ]
    """

    ensure_output_directory()

    if not VISITED_NODES_FILE.exists():
        return set()

    with VISITED_NODES_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(
        data,
        list,
    ):
        raise ValueError(
            f"{VISITED_NODES_FILE} must contain a JSON list."
        )

    visited = set()

    for node_id in data:

        if isinstance(
            node_id,
            str,
        ):
            visited.add(node_id)

    return visited


def save_visited_nodes(
    visited_nodes: set[str],
) -> None:
    """
    Save all traversed node IDs.
    """

    ensure_output_directory()

    with VISITED_NODES_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            sorted(visited_nodes),
            file,
            indent=4,
            ensure_ascii=False,
        )


# ============================================================
# NODE CACHE PATH
# ============================================================

def get_node_cache_path(
    node_id: str,
) -> Path:
    """
    Return the exact cache path for a node.

    Example:

        node_id = "isometries"

        -> topic_subtrees/isometries.json

    The node ID is intentionally not sanitized because you
    requested the filename to be exactly the node ID.
    """

    return (
        TOPIC_SUBTREES_DIR
        / f"{node_id}.json"
    )


# ============================================================
# LOAD CACHED SUBTREE
# ============================================================

def load_cached_subtree(
    node_id: str,
) -> dict[str, Any]:
    """
    Load an already-generated subtree.
    """

    cache_path = get_node_cache_path(
        node_id
    )

    if not cache_path.exists():
        raise FileNotFoundError(
            f"Node '{node_id}' is marked as visited, "
            f"but its cached subtree does not exist: "
            f"{cache_path}"
        )

    with cache_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        subtree = json.load(file)

    if not isinstance(
        subtree,
        dict,
    ):
        raise ValueError(
            f"Cached subtree for '{node_id}' "
            f"must be a dictionary."
        )

    return subtree


# ============================================================
# SAVE SUBTREE
# ============================================================

def save_subtree(
    node_id: str,
    subtree: dict[str, Any],
) -> None:
    """
    Save a subtree using the exact node ID as filename.
    """

    ensure_output_directory()

    output_path = get_node_cache_path(
        node_id
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            subtree,
            file,
            indent=4,
            ensure_ascii=False,
        )


# ============================================================
# BUILD SUBTREE
# ============================================================

def build_subtree(
    node_id: str,
    node_index: dict[str, dict[str, Any]],
    current_path: set[str] | None = None,
) -> dict[str, Any]:
    """
    Recursively construct a complete subtree for a node.

    Traverses BOTH:

        subtopics
        prerequisites

    Before the subtree is returned, the node's separate:

        chunks
        confidence_scores

    arrays are transformed into paired chunk objects:

        "chunks": [
            {
                "text": "...",
                "confidence_score": 0.95
            },
            ...
        ]

    current_path is used only for cycle protection.
    """

    if node_id not in node_index:
        raise KeyError(
            f"Node ID '{node_id}' was not found in the "
            f"full retrieval tree."
        )

    if current_path is None:
        current_path = set()

    # --------------------------------------------------------
    # Cycle protection
    # --------------------------------------------------------

    if node_id in current_path:
        raise ValueError(
            "Cycle detected while constructing subtree. "
            f"Node '{node_id}' occurs twice in the current "
            f"recursive path: {current_path}"
        )

    new_path = current_path | {node_id}

    # --------------------------------------------------------
    # Deep copy so the original full tree is never modified.
    # --------------------------------------------------------

    node = copy.deepcopy(
        node_index[node_id]
    )

    # --------------------------------------------------------
    # Pair chunks with confidence scores
    # --------------------------------------------------------

    chunks = node.get(
        "chunks",
        [],
    )

    confidence_scores = node.get(
        "confidence_scores",
        [],
    )

    if not isinstance(chunks, list):
        raise ValueError(
            f"'chunks' for node '{node_id}' must be a list."
        )

    if not isinstance(confidence_scores, list):
        raise ValueError(
            f"'confidence_scores' for node '{node_id}' "
            f"must be a list."
        )

    if len(chunks) != len(confidence_scores):
        raise ValueError(
            f"Node '{node_id}' has {len(chunks)} chunks but "
            f"{len(confidence_scores)} confidence scores. "
            "Each chunk must have exactly one corresponding "
            "confidence score."
        )

    paired_chunks = []

    for chunk, confidence_score in zip(
        chunks,
        confidence_scores,
    ):
        if not isinstance(chunk, str):
            raise ValueError(
                f"A chunk for node '{node_id}' must be a string."
            )

        if not isinstance(
            confidence_score,
            (int, float),
        ):
            raise ValueError(
                f"A confidence score for node '{node_id}' "
                "must be a number."
            )

        paired_chunks.append(
            {
                "text": chunk,
                "confidence_score": confidence_score,
            }
        )

    node["chunks"] = paired_chunks

    # --------------------------------------------------------
    # Remove the old separate confidence_scores array
    # --------------------------------------------------------

    node.pop(
        "confidence_scores",
        None,
    )

    # --------------------------------------------------------
    # Subtopics
    # --------------------------------------------------------

    subtopics = node.get(
        "subtopics",
        [],
    )

    if not isinstance(
        subtopics,
        list,
    ):
        raise ValueError(
            f"'subtopics' for node '{node_id}' "
            f"must be a list."
        )

    complete_subtopics = []

    for subtopic in subtopics:

        child_id = subtopic.get(
            "id"
        )

        if not isinstance(
            child_id,
            str,
        ):
            raise ValueError(
                f"Subtopic under '{node_id}' "
                f"does not contain a valid ID."
            )

        complete_subtopics.append(
            build_subtree(
                node_id=child_id,
                node_index=node_index,
                current_path=new_path,
            )
        )

    node["subtopics"] = complete_subtopics

    # --------------------------------------------------------
    # Prerequisites
    # --------------------------------------------------------

    prerequisites = node.get(
        "prerequisites",
        [],
    )

    if not isinstance(
        prerequisites,
        list,
    ):
        raise ValueError(
            f"'prerequisites' for node '{node_id}' "
            f"must be a list."
        )

    complete_prerequisites = []

    for prerequisite in prerequisites:

        prerequisite_id = prerequisite.get(
            "id"
        )

        if not isinstance(
            prerequisite_id,
            str,
        ):
            raise ValueError(
                f"Prerequisite under '{node_id}' "
                f"does not contain a valid ID."
            )

        complete_prerequisites.append(
            build_subtree(
                node_id=prerequisite_id,
                node_index=node_index,
                current_path=new_path,
            )
        )

    node["prerequisites"] = complete_prerequisites

    return node


# ============================================================
# PUBLIC FUNCTION
# ============================================================

def get_topic_subtree(
    node_id: str,
    tree_path: str | Path = FULL_TREE_PATH,
) -> dict[str, Any]:
    """
    Return the complete subtree associated with a node ID.

    Behavior:

    1. Ensure topic_subtrees/ exists.
    2. Check nodes visited.json.
    3. If node has already been processed:
         load <node_id>.json
         and return it.
    4. Otherwise:
         load the complete tree
         find the requested node
         recursively traverse all subtopics and
         prerequisites
         save <node_id>.json
         mark node as visited
         return the subtree.

    Args:
        node_id:
            ID of the node whose subtree should be returned.

        tree_path:
            Full retrieval-tree JSON.

    Returns:
        Complete subtree as a dictionary.
    """

    if not isinstance(
        node_id,
        str,
    ):
        raise TypeError(
            "node_id must be a string."
        )

    node_id = node_id.strip()

    if not node_id:
        raise ValueError(
            "node_id cannot be empty."
        )

    # ========================================================
    # 1. Ensure output directory
    # ========================================================

    ensure_output_directory()

    # ========================================================
    # 2. Load visited nodes
    # ========================================================

    visited_nodes = (
        load_visited_nodes()
    )

    # ========================================================
    # 3. CACHE HIT
    # ========================================================

    if node_id in visited_nodes:

        cache_path = get_node_cache_path(
            node_id
        )

        if cache_path.exists():

            return load_cached_subtree(
                node_id
            )

        # ----------------------------------------------------
        # Inconsistent state:
        #
        # node is marked visited but cache is missing.
        #
        # Remove it from visited state and rebuild.
        # ----------------------------------------------------

        visited_nodes.remove(
            node_id
        )

        save_visited_nodes(
            visited_nodes
        )

    # ========================================================
    # 4. Load full tree
    # ========================================================

    full_tree = load_full_tree(
        tree_path
    )

    # ========================================================
    # 5. Build node index
    # ========================================================

    node_index = build_node_index(
        full_tree
    )

    # ========================================================
    # 6. Verify requested node exists
    # ========================================================

    if node_id not in node_index:
        raise KeyError(
            f"Node ID '{node_id}' does not exist "
            f"in the full retrieval tree."
        )

    # ========================================================
    # 7. Build complete subtree
    # ========================================================

    subtree = build_subtree(
        node_id=node_id,
        node_index=node_index,
    )

    # ========================================================
    # 8. Save subtree
    # ========================================================

    save_subtree(
        node_id=node_id,
        subtree=subtree,
    )

    # ========================================================
    # 9. Mark node as visited
    # ========================================================

    visited_nodes.add(
        node_id
    )

    save_visited_nodes(
        visited_nodes
    )

    # ========================================================
    # 10. Return
    # ========================================================

    return subtree


# ============================================================
# STANDALONE TEST
# ============================================================

if __name__ == "__main__":

    requested_node_id = "isometries"

    subtree = get_topic_subtree(
        node_id=requested_node_id
    )

    print()
    print("=" * 80)
    print("SUBTREE RETRIEVED")
    print("=" * 80)

    print(
        f"Root node: {subtree['id']}"
    )

    print(
        f"Name: {subtree['name']}"
    )

    print()
    print(
        f"Direct subtopics: "
        f"{len(subtree.get('subtopics', []))}"
    )

    print(
        f"Direct prerequisites: "
        f"{len(subtree.get('prerequisites', []))}"
    )

    print()
    print(
        "Saved to:"
    )

    print(
        get_node_cache_path(
            requested_node_id
        )
    )

    print()
    print(
        "Visited nodes file:"
    )

    print(
        VISITED_NODES_FILE
    )