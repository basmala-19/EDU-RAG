from src.interfaces.api.app import app


def test_production_api_contract():
    spec = app.openapi()
    paths = spec["paths"]
    assert set(paths) == {
        "/api/rag/health", "/api/rag/upload", "/api/rag/ingestion-jobs/{job_id}",
        "/api/rag/response", "/api/rag/evaluate",
    }
    assert paths["/api/rag/response"]["post"]["operationId"] == "response"
    assert paths["/api/rag/response"]["post"]["requestBody"]["content"]["application/json"]["schema"]
    response_schema = spec["components"]["schemas"]["ResponsePayload"]["properties"]
    for field in ("session_id", "curriculum_id", "version", "file_reference_id", "answer", "sources"):
        assert field in response_schema
    upload_schema = spec["components"]["schemas"]["UploadResponse"]["properties"]
    for field in ("file_reference_id", "curriculum_id", "version", "file_name", "status"):
        assert field in upload_schema
    assert "ErrorResponse" in spec["components"]["schemas"]
