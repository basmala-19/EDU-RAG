from src.features.rag.interfaces.api.app import app

def test_public_api_contract():
    paths = app.openapi()["paths"]
    assert "/api/rag/upload" in paths
    assert "/api/rag/response" in paths
    assert "/api/rag/health" in paths
    assert "/api/rag/ingest" not in paths
    assert "/api/rag/retrieve" not in paths
    assert paths["/api/rag/response"]["post"]["operationId"] == "response"
    props = app.openapi()["components"]["schemas"]["ResponsePayload"]["properties"]
    assert all(k in props for k in ("session_id","curriculum_id","version","file_reference_id","answer","sources"))
