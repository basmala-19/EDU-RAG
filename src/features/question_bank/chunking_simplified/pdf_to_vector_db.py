from pathlib import Path
from typing import Any, Callable
from uuid import uuid5, NAMESPACE_URL

import fitz  # PyMuPDF
import chromadb
from sentence_transformers import SentenceTransformer


# ============================================================
# CONFIGURATION
# ============================================================

PDF_PATH = Path(fr"F:\pythonProj\question_generator\files\pdf_fils\basicMath494pages.pdf")

CHROMA_PATH = "./chroma_db"

COLLECTION_NAME = "book"

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

CHUNK_SIZE = 1000       # characters
CHUNK_OVERLAP = 150     # characters


# ============================================================
# PDF TEXT EXTRACTION
# ============================================================

def extract_pdf_text(pdf_path: Path) -> str:

    document = fitz.open(pdf_path)

    pages = []

    for page in document:
        text = page.get_text("text")

        if text.strip():
            pages.append(text)

    document.close()

    return "\n\n".join(pages)


# ============================================================
# TEXT CHUNKING
# ============================================================

def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:

    if overlap >= chunk_size:
        raise ValueError(
            "overlap must be smaller than chunk_size"
        )

    chunks = []

    start = 0

    while start < len(text):

        end = start + chunk_size

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


# ============================================================
# MAIN PIPELINE
# ============================================================

def index_pdf(
    pdf_path: str | Path,
    *,
    chroma_path: str | Path = CHROMA_PATH,
    collection_name: str = COLLECTION_NAME,
    replace_collection: bool = False,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Extract, embed, and store one PDF in ChromaDB.

    ``replace_collection`` makes the uploaded book the only source in the
    collection. It is useful before generating a bank for that book.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF does not exist: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files can be indexed.")

    def report(message: str) -> None:
        print(message)
        if progress_callback is not None:
            progress_callback(message)

    # --------------------------------------------------------
    # 1. Extract text
    # --------------------------------------------------------

    report("Extracting PDF text...")

    text = extract_pdf_text(pdf_path)

    if not text.strip():
        raise RuntimeError(
            "No text could be extracted from the PDF."
        )

    report(f"Extracted {len(text):,} characters.")


    # --------------------------------------------------------
    # 2. Chunk text
    # --------------------------------------------------------

    report("Creating chunks...")

    chunks = chunk_text(text)

    report(f"Created {len(chunks):,} chunks.")


    # --------------------------------------------------------
    # 3. Load embedding model
    # --------------------------------------------------------

    report("Loading embedding model...")

    model = SentenceTransformer(
        EMBEDDING_MODEL
    )


    # --------------------------------------------------------
    # 4. Generate embeddings
    # --------------------------------------------------------

    report("Generating embeddings...")

    embeddings = model.encode(
        chunks,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )


    # --------------------------------------------------------
    # 5. Create persistent Chroma database
    # --------------------------------------------------------

    report("Opening vector database...")

    client = chromadb.PersistentClient(
        path=str(chroma_path)
    )
    if replace_collection:
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            # The collection may not exist yet.
            pass
    collection = client.get_or_create_collection(
        name=collection_name
    )


    # --------------------------------------------------------
    # 6. Store chunks + vectors
    # --------------------------------------------------------

    source_key = str(pdf_path.resolve()).replace("\\", "/")
    ids = [str(uuid5(NAMESPACE_URL, f"{source_key}:{i}")) for i in range(len(chunks))]

    metadatas = [
        {
            "source": str(pdf_path),
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    collection.upsert(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=metadatas,
    )


    result = {
        "source": str(pdf_path),
        "chunks_stored": len(chunks),
        "database": str(chroma_path),
        "collection": collection_name,
        "collection_count": collection.count(),
    }
    report(f"Completed: {len(chunks):,} chunks stored in '{collection_name}'.")
    return result


def process_pdf():
    """Backward-compatible command-line entry point."""
    return index_pdf(PDF_PATH)


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    process_pdf()
