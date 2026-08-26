from pathlib import Path
from src.application.ingestion_service import IngestionService
from src.application.retrieval_service import RetrievalService


def test_ingestion_and_retrieval(tmp_path, monkeypatch):
    source = tmp_path / "curriculum.txt"
    source.write_text("Subject: Physics\nGrade: 12\nChapter: Modern Physics\nLesson: Photoelectric Effect\n\nThreshold frequency is the minimum frequency needed to eject electrons. Work function is the minimum energy needed to remove an electron.", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EMBEDDING_BACKEND", "local")
    monkeypatch.setenv("EMBEDDING_ALLOW_HASH_FALLBACK", "true")
    monkeypatch.setenv("RERANKER_ENABLED", "false")
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    from src.infrastructure.config import get_settings
    from src.infrastructure.embeddings import EmbeddingService, get_embedding_service
    get_settings.cache_clear()
    get_embedding_service.cache_clear()
    monkeypatch.setattr(EmbeddingService, "_try_load_real_model", lambda self: None)
    result = IngestionService().ingest(source, "demo", "v1", file_reference_id="file-test")
    assert result.chunks_created >= 1
    retrieval = RetrievalService().retrieve("minimum frequency to eject electrons", {"file_reference_id": "file-test"}, top_k=2)
    assert retrieval.results
