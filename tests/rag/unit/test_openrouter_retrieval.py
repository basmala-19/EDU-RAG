from types import SimpleNamespace

import numpy as np

from src.features.rag.infrastructure.embeddings import EmbeddingService
from src.features.rag.infrastructure.ranking import _rerank_with_openrouter


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_openrouter_embeddings_are_normalized_and_ordered(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs["json"]
        return _Response({"data": [
            {"index": 1, "embedding": [0.0, 4.0]},
            {"index": 0, "embedding": [3.0, 0.0]},
        ]})

    monkeypatch.setattr("src.infrastructure.embeddings.requests.post", fake_post)
    service = EmbeddingService.__new__(EmbeddingService)
    service.settings = SimpleNamespace(
        openrouter_api_key="test-key",
        openrouter_base_url="https://openrouter.example/api/v1",
        openrouter_timeout=10,
        embedding_model="baai/bge-m3",
    )
    vectors = service._encode_with_openrouter(["first", "second"])

    assert captured["url"] == "https://openrouter.example/api/v1/embeddings"
    assert captured["json"]["input"] == ["first", "second"]
    assert np.allclose(vectors, [[1.0, 0.0], [0.0, 1.0]])


def test_openrouter_rerank_maps_scores_to_original_candidates(monkeypatch):
    def fake_post(*_args, **_kwargs):
        return _Response({"results": [
            {"index": 1, "relevance_score": 0.9},
            {"index": 0, "relevance_score": 0.2},
        ]})

    monkeypatch.setattr("src.infrastructure.ranking.requests.post", fake_post)
    settings = SimpleNamespace(
        openrouter_api_key="test-key",
        openrouter_base_url="https://openrouter.example/api/v1",
        openrouter_timeout=10,
        reranker_model="cohere/rerank-v3.5",
    )
    candidates = [{"document": "first"}, {"document": "second"}]
    _rerank_with_openrouter("query", candidates, settings)

    assert [item["reranker_score"] for item in candidates] == [0.2, 0.9]
