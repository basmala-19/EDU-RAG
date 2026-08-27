import random

from src.features.rag.infrastructure.document_loader import _order_page_lines


def test_two_column_body_reads_column_by_column_not_interleaved():
    """A flat (y, x) sort interleaves parallel columns row-by-row: col1-row1, col2-row1,
    col1-row2, ... This asserts the fix reads column 1 fully, then column 2."""
    page_width = 600.0
    lines = [(f"col1-{i}", 10.0, False, float(i * 15), 20.0) for i in range(6)]
    lines += [(f"col2-{i}", 10.0, False, float(i * 15), 320.0) for i in range(6)]
    random.shuffle(lines)

    ordered = [t[0] for t in _order_page_lines(lines, page_width)]

    assert ordered == [f"col1-{i}" for i in range(6)] + [f"col2-{i}" for i in range(6)]


def test_single_column_page_keeps_top_to_bottom_order():
    lines = [
        ("Title", 30.0, True, 50.0, 100.0),
        ("Subtitle", 14.0, False, 90.0, 100.0),
        ("Body one", 10.0, False, 130.0, 50.0),
        ("Body two", 10.0, False, 150.0, 50.0),
    ]
    random.shuffle(lines)
    ordered = [t[0] for t in _order_page_lines(lines, 600.0)]
    assert ordered == ["Title", "Subtitle", "Body one", "Body two"]


def test_stray_small_box_does_not_get_treated_as_a_real_column():
    """A single small logo/stamp box off to the side has too few lines to count as a
    column, so it must not fragment reading order the way a real 2-column body would."""
    lines = [
        ("Real Title Line 1", 30.0, True, 50.0, 100.0),
        ("Real Title Line 2", 30.0, True, 90.0, 100.0),
        ("Subtitle", 14.0, False, 130.0, 100.0),
        ("Body para 1", 10.0, False, 170.0, 50.0),
        ("Body para 2", 10.0, False, 190.0, 50.0),
        ("LOGO", 8.0, False, 40.0, 500.0),
    ]
    ordered = [t[0] for t in _order_page_lines(lines, 600.0)]
    # Falls back to the flat (y, x) sort: LOGO happens to sit above the title (y=40 < 50),
    # so it's still first — but it isn't interleaved mid-paragraph. Filtering boilerplate
    # like this out of *title selection* is handled separately in document_metadata.py.
    assert ordered.index("Real Title Line 1") < ordered.index("Real Title Line 2") < ordered.index("Subtitle")
    assert ordered.index("Body para 1") < ordered.index("Body para 2")


def test_empty_input():
    assert _order_page_lines([], 600.0) == []


def test_pymupdf_cover_text_returns_none_without_fitz_instead_of_raising():
    """fitz isn't installed in every environment (LlamaParse-only deployments, some CI
    images) — this must degrade to 'no override' rather than blow up the whole ingest."""
    from pathlib import Path

    from src.features.rag.infrastructure.document_loader import _pymupdf_cover_text

    assert _pymupdf_cover_text(Path("/nonexistent/does-not-matter.pdf")) is None
