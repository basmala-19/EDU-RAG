"""Plain-text extraction from a PDF, for feeding the LLM graph extractor.

Deliberately simple and self-contained - unlike
``rag/infrastructure/document_loader.py`` (headings, columns, multi-format
support, LlamaParse), this only needs one thing: each page's running text,
in reading order, good enough for an LLM to read and identify topics from.
Not imported from ``rag`` on purpose - see the module docstring on
``infrastructure/config.py`` for why knowledge_graph never depends on
other features.
"""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_pages(pdf_path: Path) -> list[str]:
    """Return one plain-text string per page (in page order).

    Tries PyMuPDF (``fitz``) first - it's already a project dependency and
    handles complex/Arabic layouts better - and falls back to ``pypdf`` if
    PyMuPDF isn't importable in this environment. Pages with no extractable
    text (e.g. scanned images with no OCR) come back as an empty string
    rather than being dropped, so page numbers stay meaningful to anyone
    reading logs.
    """
    try:
        import fitz
    except ImportError:
        logger.info("PyMuPDF not available, falling back to pypdf for '%s'", pdf_path.name)
        from pypdf import PdfReader

        reader = PdfReader(str(pdf_path))
        return [(page.extract_text() or "").strip() for page in reader.pages]

    pdf = fitz.open(str(pdf_path))
    try:
        return [(page.get_text("text") or "").strip() for page in pdf]
    finally:
        pdf.close()
