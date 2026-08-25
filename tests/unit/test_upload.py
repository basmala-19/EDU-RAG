from fastapi.testclient import TestClient
from src.interfaces.api.app import app

def test_upload_accepts_file_only_and_backend_generates_ids(monkeypatch):
    class DummyResult:
        def model_dump(self):
            return {
                "curriculum_id": "cur_demo", "version": "v1", "files_processed": 1,
                "chunks_created": 1, "indexed_chunks": 1, "indexed_question_count": 2,
                "language_counts": {"en": 1},
                "metadata_coverage": {"subject": 100.0, "grade": 100.0, "heading": 100.0, "heading_path": 100.0},
                "document_metadata": {"document_title":"Demo","subject":"Physics","grade":"12","language":"en","sources":{},"confidence":{},"evidence":{}},
            }
    def fake_ingest(*args, **kwargs):
        assert kwargs.get("file_reference_id")
        return DummyResult()
    monkeypatch.setattr("src.interfaces.api.app.ingestion_service.ingest", fake_ingest)
    response = TestClient(app).post("/api/rag/upload", files={"file": ("sample.txt", b"Machine Learning", "text/plain")})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["file_name"] == "sample.txt"
    assert len(data["file_reference_id"]) == 32
    assert data["curriculum_id"] == "cur_demo"
    assert data["document_metadata"]["term"] is None
