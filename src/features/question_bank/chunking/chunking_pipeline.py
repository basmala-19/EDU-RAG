from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from llama_index.core import Document

from .helper_functions.configure_logging import configure_logging
from .helper_functions.entity_counter import count_entities
from .helper_functions.read_document import (
    load_pdf,
    combine_document_text,
)
from .helper_functions.semantic_splitter import (
    create_embedding_model,
    create_semantic_splitter,
)
from .helper_functions.sentence_per_topic import sentences_per_topic
from .helper_functions.sentences_per_topic_normalized import (
    sentences_per_topic_normalized,
)


logger = logging.getLogger(__name__)


# ============================================================
# PIPELINE
# ============================================================

def chunk_document(
    pdf_path: str | Path,
    knowledge_graph: dict[str, Any],

    topic_initial_partitions: int = 20,

    embedding_model_name: str = (
        "jinaai/jina-embeddings-v3"
    ),

    embed_batch_size: int = 10,

    include_metadata: bool = True,

    include_prev_next_rel: bool = True,

) -> list:
    """
    Complete document semantic-chunking pipeline.

    Pipeline:

        PDF
        ↓
        PyMuPDFReader
        ↓
        LlamaIndex Documents
        ↓
        Combine extracted text
        ↓
        Count curriculum concepts/topics
        ↓
        Estimate sentences per topic
        ↓
        Normalize according to desired chunks/topic
        ↓
        HuggingFace embedding model
        ↓
        SemanticSplitterNodeParser
        ↓
        Semantic Nodes

    Args:
        pdf_path:
            Path to the PDF document.

        knowledge_graph:
            Dictionary containing an "entities" list.
            The number of entities is used as the number of
            curriculum topics/concepts.

        topic_initial_partitions:
            Desired approximate number of semantic chunks
            per curriculum topic.

        embedding_model_name:
            HuggingFace embedding model.

        embed_batch_size:
            Number of texts embedded in one batch.

        breakpoint_percentile_threshold:
            Semantic dissimilarity percentile used to determine
            chunk boundaries.

        include_metadata:
            Whether metadata should be included in generated nodes.

        include_prev_next_rel:
            Whether previous/next node relationships should be
            generated.

    Returns:
        List of LlamaIndex semantic Nodes.
    """

    logger.info("=" * 80)
    logger.info("STARTING DOCUMENT CHUNKING PIPELINE")
    logger.info("=" * 80)

    # ========================================================
    # VALIDATION
    # ========================================================

    pdf_path = Path(pdf_path)

    if topic_initial_partitions <= 0:
        raise ValueError(
            "topic_initial_partitions must be greater than 0."
        )




    logger.info(
        "PDF path: %s",
        pdf_path,
    )

    logger.info(
        "Embedding model: %s",
        embedding_model_name,
    )

    logger.info(
        "Chunks per topic: %d",
        topic_initial_partitions,
    )



    # ========================================================
    # STEP 1 — LOAD PDF
    # ========================================================

    logger.info("-" * 80)
    logger.info("STEP 1: Loading PDF")
    logger.info("-" * 80)

    documents: list[Document] = load_pdf(
        pdf_path=pdf_path
    )

    if not documents:
        raise RuntimeError(
            "PDF reader returned no documents."
        )

    logger.info(
        "Loaded %d LlamaIndex documents.",
        len(documents),
    )

    # ========================================================
    # STEP 2 — COMBINE DOCUMENT TEXT
    # ========================================================

    logger.info("-" * 80)
    logger.info("STEP 2: Combining document text")
    logger.info("-" * 80)

    combined_text: str = combine_document_text(
        documents
    )

    if not combined_text.strip():
        raise RuntimeError(
            "No text could be extracted from the PDF."
        )

    logger.info(
        "Extracted document size: %d characters.",
        len(combined_text),
    )

    # ========================================================
    # STEP 3 — COUNT CURRICULUM TOPICS
    # ========================================================

    logger.info("-" * 80)
    logger.info("STEP 3: Counting curriculum topics")
    logger.info("-" * 80)

    num_topics: int = count_entities(
        knowledge_graph
    )

    if num_topics <= 0:
        raise ValueError(
            "Knowledge graph contains no entities/topics."
        )

    logger.info(
        "Number of curriculum topics/entities: %d",
        num_topics,
    )

    # ========================================================
    # STEP 4 — ESTIMATE SENTENCES PER TOPIC
    # ========================================================

    logger.info("-" * 80)
    logger.info("STEP 4: Estimating sentences per topic")
    logger.info("-" * 80)

    estimated_sentences_per_topic: int = (
        sentences_per_topic(
            doc_size=len(combined_text),
            num_topics=num_topics,
        )
    )

    logger.info(
        "Estimated sentences per topic: %d",
        estimated_sentences_per_topic,
    )

    # ========================================================
    # STEP 5 — NORMALIZE BY DESIRED CHUNKS/TOPIC
    # ========================================================

    logger.info("-" * 80)
    logger.info(
        "STEP 5: Calculating target sentences per chunk"
    )
    logger.info("-" * 80)
    target_sentences_per_chunk = sentences_per_topic_normalized(
        sentences_per_topic=estimated_sentences_per_topic,
        number_of_chunks_per_topic=topic_initial_partitions,
    )

    logger.info(
        "Target sentences per chunk: %d",
        target_sentences_per_chunk,
    )

    # ========================================================
    # STEP 6 — CREATE EMBEDDING MODEL
    # ========================================================

    logger.info("-" * 80)
    logger.info("STEP 6: Loading embedding model")
    logger.info("-" * 80)

    embed_model = create_embedding_model(
        model_name=embedding_model_name,
        embed_batch_size=embed_batch_size,
    )

    # ========================================================
    # STEP 7 — CREATE SEMANTIC SPLITTER
    # ========================================================

    logger.info("-" * 80)
    logger.info("STEP 7: Creating semantic splitter")
    logger.info("-" * 80)
   
    breakpoint_percent=((estimated_sentences_per_topic*topic_initial_partitions)//(len(combined_text)/70))*100
    

    sentence_group=target_sentences_per_chunk
    for i in range(5,1):
        test=target_sentences_per_chunk//i
        if test/estimated_sentences_per_topic > 10/100:
            sentence_group=test
            break

    breakpoint_percent= 1-sentence_group/estimated_sentences_per_topic
    logger.info(f"((buffer_size))={sentence_group} || ((breakpoint_percentile_threshold))={breakpoint_percent}")
    
    

    
    splitter = create_semantic_splitter(
        embed_model=embed_model,

        buffer_size=sentence_group,

        breakpoint_percentile_threshold=(
            breakpoint_percent
        ),

        sentence_splitter=None,

        include_metadata=include_metadata,

        include_prev_next_rel=(
            include_prev_next_rel
        ),

        callback_manager=None,

        id_func=None,
    )

    # ========================================================
    # STEP 8 — SEMANTIC CHUNKING
    # ========================================================

    logger.info("-" * 80)
    logger.info("STEP 8: Generating semantic chunks")
    logger.info("-" * 80)

    nodes = splitter.get_nodes_from_documents(
        documents,
        show_progress=True,
    )

    logger.info(
        "Semantic splitting completed."
    )

    logger.info(
        "Generated %d semantic nodes.",
        len(nodes),
    )

    # ========================================================
    # STEP 9 — NODE STATISTICS
    # ========================================================

    logger.info("-" * 80)
    logger.info("STEP 9: Calculating node statistics")
    logger.info("-" * 80)

    if nodes:
        node_lengths = [
            len(node.get_content())
            for node in nodes
        ]

        average_node_length = (
            sum(node_lengths)
            / len(node_lengths)
        )

        min_node_length = min(node_lengths)
        max_node_length = max(node_lengths)

        logger.info(
            "Node count: %d",
            len(nodes),
        )

        logger.info(
            "Minimum node size: %d characters",
            min_node_length,
        )

        logger.info(
            "Maximum node size: %d characters",
            max_node_length,
        )

        logger.info(
            "Average node size: %.2f characters",
            average_node_length,
        )

    else:
        logger.warning(
            "Semantic splitter produced zero nodes."
        )

    # ========================================================
    # FINAL SUMMARY  
    # ========================================================

    logger.info("=" * 80)
    logger.info("PIPELINE COMPLETED")
    logger.info("=" * 80)

    logger.info(
        "PDF: %s",
        pdf_path,
    )

    logger.info(
        "Topics: %d",
        num_topics,
    )

    logger.info(
        "Estimated sentences/topic: %d",
        estimated_sentences_per_topic,
    )

    logger.info(
        "Target sentences/chunk: %d",
        target_sentences_per_chunk,
    )

    logger.info(
        "Generated nodes: %d",
        len(nodes),
    )

    logger.info("=" * 80)

    return nodes

############################################################################################################################################################
# ============================================================
# STANDALONE EXECUTION||||||||||||||||||||||||||||| ===================================================
# ============================================================
############################################################################################################################################################
if __name__ == "__main__":

    configure_logging(
        level=logging.INFO
    )

    # --------------------------------------------------------
    # INPUTS
    # --------------------------------------------------------

    pdf_path = (
        r"F:\pythonProj\question_generator\data\book.pdf"
    )

    # This would normally come from your curriculum
    # knowledge-graph extraction stage.
    knowledge_graph = {
        "entities": [
            {
                "id": "algebra",
                "text": "Algebra",
                "type": "ScientificConcept",
            },
            {
                "id": "linear_algebra",
                "text": "Linear Algebra",
                "type": "ScientificConcept",
            },
            {
                "id": "vectors",
                "text": "Vectors",
                "type": "ScientificConcept",
            },
        ]
    }

    # --------------------------------------------------------
    # RUN PIPELINE
    # --------------------------------------------------------

    nodes = chunk_document(
        pdf_path=pdf_path,

        knowledge_graph=knowledge_graph,

        topic_initial_partitions=2,

        embedding_model_name=(
            "jinaai/jina-embeddings-v3"
        ),

        embed_batch_size=10,
        include_metadata=True,

        include_prev_next_rel=True,
    )

    # --------------------------------------------------------
    # DISPLAY RESULTS
    # --------------------------------------------------------

    print()
    print("=" * 80)
    print("GENERATED SEMANTIC CHUNKS")
    print("=" * 80)

    for index, node in enumerate(
        nodes,
        start=1,
    ):
        print()
        print("-" * 80)
        print(f"CHUNK {index}")
        print("-" * 80)

        print(
            node.get_content()
        )

        print()
        print(
            "Metadata:",
            node.metadata,
        )

        print(
            "Node ID:",
            node.node_id,
        )