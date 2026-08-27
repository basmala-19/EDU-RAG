from __future__ import annotations
import json
from pathlib import Path
from typing import Any

from ..question_attributes.prompts import MSQ_PROMPT
from ..config import get_llm_model
from .topic_subtree_retriever import get_topic_subtree
from ..llm_api.openai_api import get_llm_response

# ============================================================
# CONFIGURATION
# ============================================================

GRAPH_PATH = Path(
    r"F:\pythonProj\question_generator\files\graph_dictionary_files\deepseek_deepseek_v4_flash_0731_basicMath494pages_13_15_graph.json"
)

LLM_GENERATIONS_DIR = (
    Path(__file__).resolve().parents[2]
    / "llm_response_generations\info_track"
)

VISITED_NODES_FILE = (
    LLM_GENERATIONS_DIR
    / "visited_nodes"
)
# ============================================================
# CONFIGURATION
# ============================================================

LLM_RESPONSE_GENERATIONS_DIR = (
    Path(__file__).resolve().parents[2]
    / "llm_response_generations"
)


# ============================================================
# DIRECTORY MANAGEMENT
# ============================================================

def ensure_llm_generations_directory() -> None:
    """
    Ensure the llm_generations_answers directory exists.
    """

    LLM_GENERATIONS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# LOAD GRAPH
# ============================================================

def load_graph(
    graph_path: str | Path = GRAPH_PATH,
) -> dict[str, Any]:
    """
    Load the graph JSON.

    Expected top-level structure:

        {
            "entities": [...],
            "relationships": [...],
            "metadata": {...}
        }
    """

    graph_path = Path(graph_path)

    if not graph_path.exists():
        raise FileNotFoundError(
            f"Graph JSON does not exist: {graph_path}"
        )

    with graph_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        graph = json.load(file)

    if not isinstance(graph, dict):
        raise ValueError(
            "Graph JSON root must be a dictionary."
        )

    entities = graph.get("entities")

    if not isinstance(
        entities,
        list,
    ):
        raise ValueError(
            "Graph JSON must contain an 'entities' list."
        )

    return graph


# ============================================================
# LOAD VISITED NODES
# ============================================================

def load_visited_nodes() -> set[str]:
    """
    Load previously successfully processed node IDs.

    The file contains a JSON array:

        [
            "algebra",
            "numbers",
            "isometries"
        ]

    This function is intended to be called exactly once
    at the beginning of the traversal.
    """

    ensure_llm_generations_directory()

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
            f"{VISITED_NODES_FILE} must contain a JSON array."
        )

    visited_nodes: set[str] = set()

    for node_id in data:

        if not isinstance(
            node_id,
            str,
        ):
            raise ValueError(
                "Every item in visited_nodes must be a string."
            )

        visited_nodes.add(node_id)

    return visited_nodes


# ============================================================
# SAVE VISITED NODES
# ============================================================

def save_visited_nodes(
    visited_nodes: set[str],
) -> None:
    """
    Save all successfully processed node IDs.

    This should only be called after the traversal has
    successfully completed.
    """

    ensure_llm_generations_directory()

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
# TRAVERSE GRAPH
# ============================================================





# ============================================================
# DIRECTORY MANAGEMENT
# ============================================================

def ensure_llm_response_directory() -> None:
    """
    Ensure the llm_response_generations directory exists.
    """

    LLM_RESPONSE_GENERATIONS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


# ============================================================
# SAVE LLM RESPONSE
# ============================================================

def save_llm_response(
    node_id: str,
    llm_response: str,
) -> Path:
    """
    Save an LLM response using the node ID as the filename.

    Example:

        node_id = "isometries"

        -> llm_response_generations/isometries.txt

    Returns:
        Path to the saved response.
    """

    ensure_llm_response_directory()

    output_path = (
        LLM_RESPONSE_GENERATIONS_DIR
        / f"{node_id}.txt"
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        file.write(llm_response)

    return output_path


# ============================================================
# TRAVERSE GRAPH AND GENERATE LLM RESPONSES
# ============================================================

def traverse_graph_and_retrieve_subtrees(
    graph_path: str | Path = GRAPH_PATH,
) -> list[str]:
    """
    Traverse every entity in the graph, retrieve its topic
    subtree, generate an LLM response, save that response,
    and mark the node as visited.

    Processing logic:

    1. Load the graph.
    2. Load visited_nodes exactly once.
    3. Iterate through every entity.
    4. Extract the entity ID.
    5. Skip IDs already visited.
    6. Pass the ID to get_topic_subtree().
    7. Generate the LLM response.
    8. Save the LLM response to:
           llm_response_generations/<node_id>.txt
    9. Add the node ID to the in-memory visited set.
    10. Immediately save the updated visited_nodes file.
    11. Continue to the next entity.

    A node is therefore considered successfully processed
    only when the LLM response has been successfully generated
    and saved.

    Returns:
        A list of LLM responses successfully generated during
        this invocation.
    """

    # ========================================================
    # 1. Load graph
    # ========================================================

    graph = load_graph(
        graph_path
    )

    entities = graph["entities"]

    # ========================================================
    # 2. Load visited nodes ONCE
    # ========================================================

    visited_nodes = load_visited_nodes()

    # ========================================================
    # 3. Store LLM responses generated during this run
    # ========================================================

    llm_responses: list[str] = []

    # ========================================================
    # 4. Traverse every graph entity
    # ========================================================

    for entity in entities:

        if not isinstance(
            entity,
            dict,
        ):
            raise ValueError(
                "Every item in 'entities' must be a dictionary."
            )

        # ----------------------------------------------------
        # Retrieve node ID
        # ----------------------------------------------------

        node_id = entity.get(
            "id"
        )

        if not isinstance(
            node_id,
            str,
        ):
            raise ValueError(
                "Every entity must contain a string 'id'."
            )

        node_id = node_id.strip()

        if not node_id:
            raise ValueError(
                "Entity ID cannot be empty."
            )

        # ----------------------------------------------------
        # Skip already processed nodes
        # ----------------------------------------------------

        if node_id in visited_nodes:
            continue

        # ----------------------------------------------------
        # Retrieve subtree
        # ----------------------------------------------------

        try:

            subtree = get_topic_subtree(
                node_id=node_id
            )

        except Exception as exc:

            print(
                f"Failed to retrieve subtree for "
                f"'{node_id}': {exc}"
            )

            continue

        # ----------------------------------------------------
        # Build prompt
        # ----------------------------------------------------

        prompt = f"""
given the following topic tree in JSON, you will get a topic at the top of the following id: {node_id} which is the topic you ask questions about, not the pre-requisites and not the subsets. 
the pre-requisite & subset topics are for reference how this top topic is understood and teached. 
And in that sense, you create questions ONLY according to the data given in the chunks, and the questions should only be about the topic {node_id}. 
each `chunk` in the JSON will have a `text` which is the text data that acts as your reference and a `confidence_score` which shows how much we are confident this chunk belongs to that said topic.
The lower the confidence, the more you should analyze whether the chunk is about out topic {node_id} and see if questions should be based on that chunk or not. 
The chunks gives you the general idea of what material is available to the student. You understand the information available to the student, but you don't literally ask about the chunks themselves.
In better words, the chunks here provide what the student knows(or should know). Your questions should be about that knowledge, not the exact chunks in literal sense. 
The pre-requisites and subset topics are provided, so if this topic can be understood from many different dimensions, those subsets/pre-requisite topics should provide which ways this top topic is understood. (the background of the student).

------>>>>>here's the subtree I was talking about that acts as your reference:
{subtree}

------>>>>> here are the rules you MUST follow strictly to know what type, difficulty of question and quantity and know your STRICTLY output structure:
{MSQ_PROMPT}
"""

        # ----------------------------------------------------
        # Generate LLM response
        # ----------------------------------------------------

        try:

            llm_output = get_llm_response(
                get_llm_model(),
                prompt,
            )

        except Exception as exc:

            print(
                f"Failed to generate LLM response for "
                f"'{node_id}': {exc}"
            )

            # IMPORTANT:
            # Do not mark the node as visited because
            # generation failed.

            continue

        # ----------------------------------------------------
        # Validate response
        # ----------------------------------------------------

        if not isinstance(
            llm_output,
            str,
        ):
            raise TypeError(
                f"LLM response for '{node_id}' "
                "must be a string."
            )

        # ----------------------------------------------------
        # Save LLM response
        # ----------------------------------------------------

        try:

            response_path = save_llm_response(
                node_id=node_id,
                llm_response=llm_output,
            )

        except Exception as exc:

            print(
                f"Failed to save LLM response for "
                f"'{node_id}': {exc}"
            )

            # Do not mark as visited if the response
            # could not be persisted.

            continue

        # ----------------------------------------------------
        # Store response in return list
        # ----------------------------------------------------

        llm_responses.append(
            llm_output
        )

        # ----------------------------------------------------
        # Mark node as visited IN MEMORY
        # ----------------------------------------------------

        visited_nodes.add(
            node_id
        )

        # ----------------------------------------------------
        # IMMEDIATELY persist visited state
        # ----------------------------------------------------

        save_visited_nodes(
            visited_nodes
        )

        print(
            f"Successfully generated and saved response "
            f"for '{node_id}'"
        )

        print(
            f"Response saved to: {response_path}"
        )

    # ========================================================
    # 5. Return LLM responses
    # ========================================================

    return llm_responses




































# ----->>>>>>>>>>>>>>>>>>> (THIS ONE IS FOR TESTING only a single node!!!)
def generate_single_node_response(
    node_id: str,
) -> str:
    """
    Test the complete generation pipeline for a single node.

    Processing:

    1. Validate node_id.
    2. Load visited_nodes exactly once.
    3. Check whether node_id has already been processed.
    4. Retrieve the node subtree.
    5. Build the LLM prompt.
    6. Generate the LLM response.
    7. Save the LLM response to:
           llm_response_generations/<node_id>.txt
    8. Mark the node as visited.
    9. Immediately save the updated visited_nodes file.
    10. Return the LLM response.

    A node is considered successfully processed only after
    the LLM response has been successfully generated and saved.
    """

    # ========================================================
    # 1. Validate node ID
    # ========================================================

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
    # 2. Load visited nodes ONCE
    # ========================================================

    visited_nodes = load_visited_nodes()

    # ========================================================
    # 3. Check whether node was already processed
    # ========================================================

    if node_id in visited_nodes:
        raise ValueError(
            f"Node '{node_id}' has already been processed."
        )

    # ========================================================
    # 4. Retrieve subtree
    # ========================================================

    try:

        subtree = get_topic_subtree(
            node_id=node_id
        )

    except Exception as exc:

        raise RuntimeError(
            f"Failed to retrieve subtree for "
            f"'{node_id}': {exc}"
        ) from exc

    # ========================================================
    # 5. Build prompt
    # ========================================================

    prompt = f"""
given the following topic tree in JSON, you will get a topic at the top of the following id: {node_id} which is the topic you ask questions about, not the pre-requisites and not the subsets. 
the pre-requisite & subset topics are for reference how this top topic is understood and teached. 
And in that sense, you create questions ONLY according to the data given in the chunks, and the questions should only be about the topic {node_id}. 
each `chunk` in the JSON will have a `text` which is the text data that acts as your reference and a `confidence_score` which shows how much we are confident this chunk belongs to that said topic.
The lower the confidence, the more you should analyze whether the chunk is about out topic {node_id} and see if questions should be based on that chunk or not. 
The chunks gives you the general idea of what material is available to the student. You understand the information available to the student, but you don't literally ask about the chunks themselves.
In better words, the chunks here provide what the student knows(or should know). Your questions should be about that knowledge, not the exact chunks in literal sense. 
The pre-requisites and subset topics are provided, so if this topic can be understood from many different dimensions, those subsets/pre-requisite topics should provide which ways this top topic is understood. (the background of the student).

------>>>>>here's the subtree I was talking about that acts as your reference:
{subtree}

------>>>>> here are the rules you MUST follow strictly to know what type, difficulty of question and quantity and know your STRICTLY output structure:
{MSQ_PROMPT}
""".strip()
    # Save prompt to a .txt file
    print(prompt[:10000])
    with open(r'F:\pythonProj\question_generator\llm_response_generations\prompt_output.txt', 'w', encoding='utf-8') as f:
        f.write(prompt)


    # ========================================================
    # 6. Generate LLM response
    # ========================================================

    try:

        llm_output = get_llm_response(
            get_llm_model(),
            prompt,
        )

    except Exception as exc:

        raise RuntimeError(
            f"Failed to generate LLM response for "
            f"'{node_id}': {exc}"
        ) from exc

    # ========================================================
    # 7. Validate response
    # ========================================================

    if not isinstance(
        llm_output,
        str,
    ):
        raise TypeError(
            f"LLM response for '{node_id}' "
            "must be a string."
        )

    # ========================================================
    # 8. Save LLM response
    # ========================================================

    try:

        response_path = save_llm_response(
            node_id=node_id,
            llm_response=llm_output,
        )

    except Exception as exc:

        raise RuntimeError(
            f"Failed to save LLM response for "
            f"'{node_id}': {exc}"
        ) from exc

    # ========================================================
    # 9. Mark node as visited IN MEMORY
    # ========================================================

    visited_nodes.add(
        node_id
    )

    # ========================================================
    # 10. Immediately persist visited state
    # ========================================================

    save_visited_nodes(
        visited_nodes
    )

    # ========================================================
    # 11. Report success
    # ========================================================

    print(
        f"Successfully generated and saved response "
        f"for '{node_id}'"
    )

    print(
        f"Response saved to: {response_path}"
    )

    # ========================================================
    # 12. Return LLM response
    # ========================================================

    return llm_output

if __name__ == "__main__":
    response = generate_single_node_response(
        node_id="isometries"
    )

    print(response)
