from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chromadb
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURATION
# ============================================================

CHROMA_PATH = "./chroma_db"

COLLECTION_NAME = "book"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Number of candidates retrieved from Chroma
CANDIDATE_COUNT = 100

# Minimum cosine similarity required for a chunk
# to be considered relevant.
#
# For all-MiniLM-L6-v2, you should experiment with this.
# 0.01 is much too low for meaningful filtering.
SIMILARITY_THRESHOLD = 0.40

# Number of candidates to print for diagnostics
DEBUG_PRINT_COUNT = 100

# Number of final chunks to display
FINAL_DISPLAY_COUNT = 10


# ============================================================
# LOAD EMBEDDING MODEL ONCE
# ============================================================

print("=" * 80)
print("LOADING EMBEDDING MODEL")
print("=" * 80)

MODEL = SentenceTransformer(
    EMBEDDING_MODEL
)

print(f"Embedding model: {EMBEDDING_MODEL}")


# ============================================================
# OPEN CHROMA ONCE
# ============================================================

print()
print("=" * 80)
print("OPENING CHROMA DATABASE")
print("=" * 80)

CLIENT = chromadb.PersistentClient(
    path=CHROMA_PATH
)

COLLECTION = CLIENT.get_collection(
    name=COLLECTION_NAME
)

print(f"Chroma path: {CHROMA_PATH}")
print(f"Collection: {COLLECTION_NAME}")
print(f"Collection count: {COLLECTION.count()}")


# ============================================================
# DETERMINE DISTANCE METRIC
# ============================================================

collection_metadata = COLLECTION.metadata or {}

# Chroma normally stores the metric here when explicitly configured.
# If it is absent, Chroma's default is l2.
DISTANCE_METRIC = collection_metadata.get(
    "hnsw:space",
    "l2",
).lower()

print(f"Distance metric: {DISTANCE_METRIC}")

if DISTANCE_METRIC not in {
    "l2",
    "cosine",
    "ip",
}:
    raise ValueError(
        f"Unsupported Chroma distance metric: {DISTANCE_METRIC}"
    )


# ============================================================
# DISTANCE -> COSINE SIMILARITY
# ============================================================

def distance_to_cosine_similarity(
    distance: float,
    metric: str,
) -> float:
    """
    Convert Chroma's distance into cosine similarity.

    Supported metrics:

    cosine:
        Chroma distance = 1 - cosine_similarity

        cosine_similarity = 1 - distance

    l2:
        For normalized vectors, Chroma's L2 distance is
        squared Euclidean distance:

            d² = 2 - 2*cos(theta)

        Therefore:

            cosine_similarity = 1 - d² / 2

    ip:
        Chroma's inner-product distance is:

            distance = 1 - dot_product

        For normalized vectors:

            dot_product = cosine_similarity

        Therefore:

            cosine_similarity = 1 - distance
    """

    if metric == "cosine":
        return 1.0 - distance

    if metric == "l2":
        return 1.0 - (distance / 2.0)

    if metric == "ip":
        return 1.0 - distance

    raise ValueError(
        f"Unsupported distance metric: {metric}"
    )


# ============================================================
# TOPIC RETRIEVER
# ============================================================

def retrieve_topic_chunks(
    topic: str,
) -> dict[str, Any]:
    """
    Retrieve chunks relevant to a single topic.

    Args:
        topic:
            Topic name, for example:
            "isometries"

    Returns:
        Dictionary containing:

        {
            "topic": str,
            "chunks": list[str],
            "confidence_scores": list[float],
            "distances": list[float],
            "candidates": list[dict]
        }
    """

    # --------------------------------------------------------
    # 1. Validate topic
    # --------------------------------------------------------

    if not isinstance(topic, str):
        raise TypeError(
            "topic must be a string."
        )

    topic = topic.strip()

    if not topic:
        raise ValueError(
            "topic cannot be empty."
        )

    # --------------------------------------------------------
    # 2. Generate topic embedding
    # --------------------------------------------------------

    topic_embedding = MODEL.encode(
        topic,
        normalize_embeddings=True,
    )

    # --------------------------------------------------------
    # 3. Retrieve candidate chunks
    # --------------------------------------------------------

    results = COLLECTION.query(
        query_embeddings=[
            topic_embedding.tolist()
        ],
        n_results=CANDIDATE_COUNT,
        include=[
            "documents",
            "distances",
        ],
    )

    documents = results["documents"][0]
    distances = results["distances"][0]

    # --------------------------------------------------------
    # 4. Convert distances to cosine similarities
    # --------------------------------------------------------

    candidates = []

    for rank, (
        document,
        distance,
    ) in enumerate(
        zip(
            documents,
            distances,
        ),
        start=1,
    ):

        similarity = distance_to_cosine_similarity(
            float(distance),
            DISTANCE_METRIC,
        )

        candidates.append(
            {
                "rank": rank,
                "distance": float(distance),
                "similarity": float(similarity),
                "document": document,
            }
        )

    # --------------------------------------------------------
    # 5. Explicitly sort by similarity
    # --------------------------------------------------------

    candidates.sort(
        key=lambda candidate: candidate["similarity"],
        reverse=True,
    )

    # --------------------------------------------------------
    # 6. Diagnostic output
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("RETRIEVAL SUMMARY")
    print("=" * 80)

    print(f"Topic: {topic}")
    print(f"Distance metric: {DISTANCE_METRIC}")
    print(f"Candidates retrieved: {len(candidates)}")
    print(
        f"Similarity threshold: "
        f"{SIMILARITY_THRESHOLD:.3f}"
    )

    if candidates:
        print(
            f"Best distance: "
            f"{candidates[0]['distance']:.6f}"
        )

        print(
            f"Best similarity: "
            f"{candidates[0]['similarity']:.6f}"
        )

    # --------------------------------------------------------
    # 7. Print candidates for inspection
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("CANDIDATES")
    print("=" * 80)

    for candidate in candidates[
        :DEBUG_PRINT_COUNT
    ]:

        print()
        print("-" * 80)

        print(
            f"CANDIDATE {candidate['rank']}"
        )

        print(
            f"Distance:   "
            f"{candidate['distance']:.6f}"
        )

        print(
            f"Similarity: "
            f"{candidate['similarity']:.6f}"
        )

        print("-" * 80)

        print(
            candidate["document"][:1000]
        )

    # --------------------------------------------------------
    # 8. Apply similarity threshold
    # --------------------------------------------------------

    relevant_candidates = [
        candidate
        for candidate in candidates
        if candidate["similarity"]
        >= SIMILARITY_THRESHOLD
    ]

    # --------------------------------------------------------
    # 9. Extract final results
    # --------------------------------------------------------

    relevant_chunks = [
        candidate["document"]
        for candidate in relevant_candidates
    ]

    confidence_scores = [
        candidate["similarity"]
        for candidate in relevant_candidates
    ]

    relevant_distances = [
        candidate["distance"]
        for candidate in relevant_candidates
    ]

    # --------------------------------------------------------
    # 10. Return result
    # --------------------------------------------------------

    return {
        "topic": topic,
        "distance_metric": DISTANCE_METRIC,
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "candidate_count": len(candidates),
        "relevant_count": len(relevant_candidates),
        "chunks": relevant_chunks,
        "confidence_scores": confidence_scores,
        "distances": relevant_distances,
        "candidates": candidates,
    }


# ============================================================
# TEST ------------------------ ------------------------ ------------------------ ------------------------ ------------------------
# ============================================================

if __name__ == "__main__":

    topic_name = "isometries"

    result = retrieve_topic_chunks(
        topic_name
    )

    # ========================================================
    # DISPLAY FINAL RESULTS
    # ========================================================

    print()
    print("=" * 80)
    print("FINAL RESULTS")
    print("=" * 80)

    print(
        f"TOPIC: {result['topic']}"
    )

    print(
        f"DISTANCE METRIC: "
        f"{result['distance_metric']}"
    )

    print(
        f"NUMBER OF CANDIDATES: "
        f"{result['candidate_count']}"
    )

    print(
        f"NUMBER OF RELEVANT CHUNKS: "
        f"{result['relevant_count']}"
    )

    print(
        f"SIMILARITY THRESHOLD: "
        f"{result['similarity_threshold']}"
    )

    # ========================================================
    # DISPLAY TOP FINAL RESULTS
    # ========================================================

    for index, (
        chunk,
        score,
        distance,
    ) in enumerate(
        zip(
            result["chunks"][:FINAL_DISPLAY_COUNT],
            result["confidence_scores"][
                :FINAL_DISPLAY_COUNT
            ],
            result["distances"][
                :FINAL_DISPLAY_COUNT
            ],
        ),
        start=1,
    ):

        print()
        print("-" * 80)

        print(
            f"CHUNK {index}"
        )

        print(
            f"CONFIDENCE: {score:.6f}"
        )

        print(
            f"CHROMA DISTANCE: {distance:.6f}"
        )

        print("-" * 80)

        print(chunk)

    # ========================================================
    # SAVE RESULT
    # ========================================================

    output_dir = Path(
        "retrieval_results"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    # --------------------------------------------------------
    # Safe filename
    # --------------------------------------------------------

    safe_topic_name = "".join(
        character
        if character.isalnum()
        or character in " _-"
        else "_"
        for character in topic_name
    ).strip()

    safe_topic_name = (
        safe_topic_name[:30]
    )

    output_path = (
        output_dir
        / f"{safe_topic_name}.json"
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print()
    print("=" * 80)
    print("RESULT SAVED")
    print("=" * 80)

    print(
        f"File: {output_path}"
    )