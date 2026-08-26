from pathlib import Path

from src.infrastructure.ingest_registry import IngestRegistry


def test_lookup_miss_then_register_then_hit(tmp_path):
    reg = IngestRegistry(tmp_path / "registry.json")
    content_hash = IngestRegistry.hash_bytes(b"same book bytes")
    assert reg.lookup(content_hash) is None
    reg.register(content_hash, {"file_reference_id": "ref1", "curriculum_id": "cur_1", "version": "v1"})
    found = reg.lookup(content_hash)
    assert found["file_reference_id"] == "ref1"
    assert found["curriculum_id"] == "cur_1"


def test_different_content_never_collides():
    a = IngestRegistry.hash_bytes(b"book A content")
    b = IngestRegistry.hash_bytes(b"book B content")
    assert a != b


def test_same_content_different_filenames_hashes_identically(tmp_path):
    """Renaming a file must not defeat dedup — the hash is content-only."""
    reg = IngestRegistry(tmp_path / "registry.json")
    content = b"identical pdf bytes"
    h1 = IngestRegistry.hash_bytes(content)
    reg.register(h1, {"file_reference_id": "ref1", "curriculum_id": "cur_1", "version": "v1"})
    # A different upload, different original filename, but identical bytes.
    h2 = IngestRegistry.hash_bytes(content)
    assert h1 == h2
    assert reg.lookup(h2)["file_reference_id"] == "ref1"


def test_forget_clears_entry_for_force_reingest(tmp_path):
    reg = IngestRegistry(tmp_path / "registry.json")
    content_hash = IngestRegistry.hash_bytes(b"book bytes")
    reg.register(content_hash, {"file_reference_id": "ref1", "curriculum_id": "cur_1", "version": "v1"})
    reg.forget(content_hash)
    assert reg.lookup(content_hash) is None


def test_corrupted_registry_file_does_not_crash(tmp_path):
    path = tmp_path / "registry.json"
    path.write_text("{not valid json", encoding="utf-8")
    reg = IngestRegistry(path)
    assert reg.lookup("anything") is None
    # And it should self-heal: registering after a corrupt read still works.
    reg.register("h1", {"file_reference_id": "ref1"})
    assert reg.lookup("h1")["file_reference_id"] == "ref1"


def test_hash_stream_matches_hash_bytes():
    import io
    data = b"streamed pdf content" * 500
    assert IngestRegistry.hash_stream(io.BytesIO(data)) == IngestRegistry.hash_bytes(data)
