from src.features.rag.infrastructure.embeddings import get_embedding_service
from src.features.rag.infrastructure.vector_store import VectorStore
from src.features.rag.domain.schemas import HealthResponse

def health() -> HealthResponse:
    emb=get_embedding_service(); store=VectorStore()
    try:
        emb.encode(["health check"])
    except Exception:
        return HealthResponse(status="degraded", embedding_backend=emb.backend, vector_store_backend=store.backend)
    status="ok" if emb.backend=="sentence-transformers" and store.backend=="chromadb" else "degraded"
    return HealthResponse(status=status,embedding_backend=emb.backend,vector_store_backend=store.backend)
