from src.features.rag.domain.schemas import RAGChunk


def validate_chunk(chunk: RAGChunk) -> RAGChunk:
    raw = " ".join(chunk.raw_text.split())
    normalized = " ".join((chunk.normalized_text or raw).split())
    if len(raw) < 20:
        raise ValueError("Chunk is too short")
    return chunk.model_copy(update={"raw_text": raw, "normalized_text": normalized})
