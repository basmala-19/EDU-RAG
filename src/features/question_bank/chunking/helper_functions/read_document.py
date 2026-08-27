from __future__ import annotations
import logging
from pathlib import Path
from llama_index.core import Document
from llama_index.readers.file import PyMuPDFReader

# ============================================================
# LOGGING
# ============================================================

logger = logging.getLogger(__name__)


# ============================================================
# LOAD PDF
# ============================================================

def load_pdf(
    pdf_path: str | Path,
) -> list[Document]:
    """
    Load a PDF using LlamaIndex's PyMuPDFReader.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(
            f"PDF does not exist: {pdf_path}"
        )

    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Expected a PDF file, got: {pdf_path.suffix}"
        )

    logger.info(
        "Loading PDF: %s",
        pdf_path,
    )

    reader = PyMuPDFReader()

    documents = reader.load_data(
        file_path=str(pdf_path)
    )

    logger.info(
        "PDF loaded successfully: %d LlamaIndex documents",
        len(documents),
    )

    for index, document in enumerate(documents):
        logger.debug(
            "Loaded document %d: characters=%d | metadata=%s",
            index,
            len(document.text),
            document.metadata,
        )

    return documents


# ============================================================
# COMBINE DOCUMENT TEXT
# ============================================================

def combine_document_text(
    documents: list[Document],
) -> str:
    """
    Combine loaded LlamaIndex documents into one text string.

    This is used for estimating global semantic-chunking
    parameters.
    """

    text_parts = [
        document.text
        for document in documents
        if document.text
    ]

    combined_text = "\n\n".join(text_parts)

    logger.info(
        "Combined document text: %d characters",
        len(combined_text),
    )

    return combined_text






