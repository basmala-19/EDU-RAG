from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


def sentences_per_topic_normalized(
    sentences_per_topic: int,
    number_of_chunks_per_topic: int,
) -> int:
    """
    Estimate the desired number of sentences per semantic chunk.

    Args:
        sentences_per_topic:
            Estimated sentences belonging to one curriculum topic.

        number_of_chunks_per_topic:
            Desired number of semantic chunks per topic.

    Returns:
        Estimated sentences per chunk.
    """

    if sentences_per_topic <= 0:
        raise ValueError(
            "sentences_per_topic must be greater than zero."
        )

    if number_of_chunks_per_topic <= 0:
        raise ValueError(
            "number_of_chunks_per_topic must be greater than zero."
        )

    result = max(
        1,
        sentences_per_topic // number_of_chunks_per_topic,
    )

    logger.info(
        "Normalized sentence/chunk estimation: "
        "sentences_per_topic=%d | "
        "chunks_per_topic=%d | "
        "sentences_per_chunk=%d",
        sentences_per_topic,
        number_of_chunks_per_topic,
        result,
    )

    return result