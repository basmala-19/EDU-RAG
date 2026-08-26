from src.domain.schemas import ChunkMetadata

def test_heading_path_defaults_to_empty_list():
    m = ChunkMetadata(curriculum_id="demo", version="v1", heading_path=[])
    assert m.heading_path == []
    m2 = ChunkMetadata(curriculum_id="demo", version="v1")
    assert m2.heading_path == []
