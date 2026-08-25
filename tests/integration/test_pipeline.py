from pathlib import Path
from src.application.ingestion_service import IngestionService
from src.application.retrieval_service import RetrievalService


def test_ingestion_and_retrieval(tmp_path, monkeypatch):
    source = tmp_path / "curriculum.txt"
    source.write_text("Subject: Physics\nGrade: 12\nChapter: Modern Physics\nLesson: Photoelectric Effect\n\nThreshold frequency is the minimum frequency needed to eject electrons. Work function is the minimum energy needed to remove an electron.", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    from src.infrastructure.config import Settings, get_settings
    get_settings.cache_clear()
    result = IngestionService().ingest(source, "demo", "v1", file_reference_id="file-test")
    assert result.chunks_created >= 1
    retrieval = RetrievalService().retrieve("minimum frequency to eject electrons", {"file_reference_id": "file-test"}, top_k=2)
    assert retrieval.results
