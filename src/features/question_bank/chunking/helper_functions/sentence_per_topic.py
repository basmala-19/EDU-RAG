from __future__ import annotations

import logging


logger = logging.getLogger(__name__)


def sentences_per_topic(
    doc_size: int,
    num_topics: int,
    sentence_size: int = 70,
) -> int:
    """
    Estimate the number of sentences belonging to each topic.

    Args:
        doc_size:
            Number of characters in the document.

        num_topics:
            Number of curriculum-level topics.

        sentence_size:
            Estimated average number of characters per sentence.

    Returns:
        Estimated sentences per topic.
    """

    if doc_size <= 0:
        raise ValueError(
            "doc_size must be greater than zero."
        )

    if num_topics <= 0:
        raise ValueError(
            "num_topics must be greater than zero."
        )

    if sentence_size <= 0:
        raise ValueError(
            "sentence_size must be greater than zero."
        )

    total_sentences = max(
        1,
        doc_size // sentence_size,
    )

    result = max(
        3,
        total_sentences // num_topics,
    )

    logger.info(
        "Sentence/topic estimation: "
        "document_chars=%d | "
        "estimated_total_sentences=%d | "
        "topics=%d | "
        "estimated_sentences_per_topic=%d",
        doc_size,
        total_sentences,
        num_topics,
        result,
    )

    return result