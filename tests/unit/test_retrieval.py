from src.infrastructure.ranking import rerank_and_dedup

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
    from src.infrastructure.config import get_settings
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
    from src.application.retrieval_service import RetrievalService
    svc = RetrievalService.__new__(RetrievalService)
    svc.settings = get_settings()
    svc.embedder = DummyEmbedder()
    svc.store = DummyStore()
    out = svc.retrieve("q", {"file_reference_id": "file-test"}, top_k=2)
    assert out.results == []
    # NOTE: updated 2026-08-25. top_k=2 * candidate_multiplier=8 = 16 was the pre-fix
    # value; this test asserted it before `min_candidate_k` (a floor of 160 on the raw
    # dense fetch, independent of top_k/candidate_multiplier) existed. That floor is a
    # deliberate fix, not a regression: a low top_k previously narrowed the initial
    # candidate window so much that a correct-but-borderline-scored chunk could be
    # dropped before the reranker ever saw it. See config.py's `min_candidate_k` comment.
    assert svc.store.requested == 160
