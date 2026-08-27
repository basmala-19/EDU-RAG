from __future__ import annotations

from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.core.callbacks import CallbackManager
import logging
from typing import Callable, Optional
from llama_index.core import Document
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
# ============================================================
# LOGGING
# ============================================================
logger = logging.getLogger(__name__)
# ============================================================
# SEMANTIC SPLITTER
# ============================================================

def create_semantic_splitter(
    embed_model: HuggingFaceEmbedding,
    buffer_size: int,
    breakpoint_percentile_threshold: int,
    sentence_splitter: Optional[
        Callable[[str], list[str]]
    ] = None,
    include_metadata: bool = True,
    include_prev_next_rel: bool = True,
    callback_manager: Optional[
        CallbackManager
    ] = None,
    id_func: Optional[
        Callable[[int, Document], str]
    ] = None,
) -> SemanticSplitterNodeParser:
    """
    Create a fully configured SemanticSplitterNodeParser.
    """

    logger.info(
        "Creating SemanticSplitterNodeParser."
    )

    logger.info(
        "Semantic splitter configuration: "
        "buffer_size=%d | "
        "breakpoint_percentile_threshold=%d | "
        "include_metadata=%s | "
        "include_prev_next_rel=%s | "
        "custom_sentence_splitter=%s | "
        "custom_id_func=%s",
        buffer_size,
        breakpoint_percentile_threshold,
        include_metadata,
        include_prev_next_rel,
        sentence_splitter is not None,
        id_func is not None,
    )

    splitter = SemanticSplitterNodeParser.from_defaults(
        embed_model=embed_model,

        breakpoint_percentile_threshold=(
            breakpoint_percentile_threshold
        ),

        buffer_size=buffer_size,

        sentence_splitter=sentence_splitter,

        original_text_metadata_key="original_text",

        include_metadata=include_metadata,

        include_prev_next_rel=include_prev_next_rel,

        callback_manager=callback_manager,

        id_func=id_func,
    )

    logger.info(
        "SemanticSplitterNodeParser created."
    )

    return splitter


# ============================================================
# EMBEDDING MODEL
# ============================================================

def create_embedding_model(
    model_name: str = "jinaai/jina-embeddings-v3",
    embed_batch_size: int = 10,
) -> HuggingFaceEmbedding:
    """
    Create the embedding model used by the semantic splitter.
    """

    logger.info(
        "Loading embedding model: %s",
        model_name,
    )

    embed_model = HuggingFaceEmbedding(
        model_name=model_name,
        embed_batch_size=embed_batch_size,
    )

    logger.info(
        "Embedding model initialized: %s",
        model_name,
    )

    return embed_model