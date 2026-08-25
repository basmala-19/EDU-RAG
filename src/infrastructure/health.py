from src.infrastructure.embeddings import EmbeddingService
from src.infrastructure.vector_store import VectorStore
from src.domain.schemas import HealthResponse

def health() -> HealthResponse:
    emb=EmbeddingService(); store=VectorStore()
    try:
        emb.encode(["health check"])
    except Exception:
        return HealthResponse(status="degraded", embedding_backend=emb.backend, vector_store_backend=store.backend)
    status="ok" if emb.backend=="sentence-transformers" and store.backend=="chromadb" else "degraded"
    return HealthResponse(status=status,embedding_backend=emb.backend,vector_store_backend=store.backend)
