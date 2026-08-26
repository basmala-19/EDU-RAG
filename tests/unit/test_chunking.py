import json

from src.application.chunking import HierarchyAwareChunker, HierarchyAwareParentChildChunker

def test_generic_numbered_headings_populate_positional_chapter():
    # NOTE: this assertion was flipped on 2026-08-25. The old assertion
    # (`chapter is None`) matched the pre-positional-fallback design, where only an
    # explicit "Chapter:"/"Lesson:" label could ever populate chapter/lesson. That
    # design left chapter/lesson permanently null for any book that structures itself
    # with bare numbered headings instead of explicit labels (the real-world case this
    # project was fixed for) even though the depth was captured correctly in
    # heading_path. The positional fallback in metadata.update_structure() was added
    # deliberately so a level-1 numbered heading with no explicit label still populates
    # `chapter` positionally; an explicit label anywhere in the doc still takes
    # precedence over it. This test now asserts that intended behavior instead of the
    # superseded one.
    text = """1. Machine Learning - Learning from Mistakes
AI learns from examples and improves with experience.

2. Natural Language Processing - Understanding Languages
It understands written and spoken human language.

3. Computer Vision - Sees the World
AI can analyze images and identify faces."""
    chunks = HierarchyAwareChunker(220, 30, 40).split(text)
    assert len(chunks) >= 3
    assert "Machine Learning" in chunks[0].raw_text
    assert chunks[0].metadata.get("chapter") == "Machine Learning - Learning from Mistakes"
    assert chunks[0].metadata.get("heading") == "Machine Learning - Learning from Mistakes"
    assert chunks[0].metadata.get("heading_path") == ["Machine Learning - Learning from Mistakes"]


def test_parent_child_keeps_retrieval_small_and_context_large():
    text = "1. Lesson\n" + ("Machine learning uses data to identify patterns. " * 40)
    chunks = HierarchyAwareParentChildChunker(parent_size=800, child_size=220, overlap=30, min_size=50).split(text)
    assert len(chunks) > 1
    assert all(c.metadata["parent_chunk_id"] == c.parent_chunk_id for c in chunks)
    assert any(len(c.parent_text) > len(c.raw_text) for c in chunks)


def test_metadata_has_no_leaked_private_keys():
    # Regression test for a real bug found 2026-08-25: update_structure() stores internal
    # bookkeeping (`_explicit_hierarchy_fields`, a python set; `_pending_anchor_level`) on
    # the same state dict that becomes chunk/parent metadata. An explicit "Chapter:"/
    # "Lesson:" label anywhere in the source document used to leave `_explicit_hierarchy_
    # fields` sitting in `parent_metadata`, which crashed VectorStore.upsert_parents() with
    # `TypeError: Object of type set is not JSON serializable`. strip_private_state() must
    # strip every leading-underscore key before metadata leaves chunking.py.
    text = "Chapter: Modern Physics\nLesson: Photoelectric Effect\n\nThreshold frequency is the minimum frequency needed to eject electrons."
    chunks = HierarchyAwareParentChildChunker(parent_size=220, child_size=80, overlap=30, min_size=40).split(text)
    assert chunks
    for c in chunks:
        assert not any(str(k).startswith("_") for k in c.metadata)
        assert not any(str(k).startswith("_") for k in c.parent_metadata)
        json.dumps(c.metadata, ensure_ascii=False)
        json.dumps(c.parent_metadata, ensure_ascii=False)
