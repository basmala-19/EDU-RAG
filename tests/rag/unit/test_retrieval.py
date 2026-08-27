from src.features.rag.infrastructure.ranking import rerank_and_dedup

def test_rerank_and_dedup():
    rows = [
        {"id": "1", "document": "threshold frequency definition", "distance": 0.1, "metadata": {}},
        {"id": "2", "document": "threshold frequency definition", "distance": 0.2, "metadata": {}},
        {"id": "3", "document": "work function definition", "distance": 0.3, "metadata": {}},
    ]
    out = rerank_and_dedup(rows, 2)
    assert len(out) == 2
    assert out[0]["id"] == "1"


def test_candidate_k_is_dynamic(monkeypatch):
    from src.features.rag.infrastructure.config import get_settings
    get_settings.cache_clear()
    class DummyEmbedder:
        def encode(self, texts):
            return [[1.0, 0.0]]
    class DummyStore:
        def __init__(self):
            self.requested = None
        def query(self, vector, filters, top_k):
            self.requested = top_k
            return []
    from src.features.rag.application.retrieval_service import RetrievalService
    svc = RetrievalService.__new__(RetrievalService)
    svc.settings = get_settings()
    svc.embedder = DummyEmbedder()
    svc.store = DummyStore()
    out = svc.retrieve("q", {"file_reference_id": "file-test"}, top_k=2)
    assert out.results == []
    # NOTE: updated 2026-08-26. min_candidate_k (floor on the raw dense fetch,
    # independent of top_k/candidate_multiplier) was tuned down from 160 to 100 to trim
    # local candidate-pool compute/IO — it does not touch the reranker_candidates cap
    # that bounds the network-bound OpenRouter rerank request. See config.py's
    # `min_candidate_k` comment for the full rationale, and its original 2026-08-25
    # history: min_candidate_k was introduced there specifically because a low top_k
    # previously narrowed the initial candidate window so much that a correct-but-
    # borderline-scored chunk could be dropped before the reranker ever saw it.
    assert svc.store.requested == 100
