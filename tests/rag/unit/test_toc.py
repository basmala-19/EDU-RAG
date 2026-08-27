from src.features.rag.application.toc import (
    TocIndex,
    find_toc_section,
    is_toc_heading_line,
    parse_toc_entries,
    parse_toc_entry_line,
    similarity,
)

# A minimal, realistic slice of this curriculum's actual TOC shape (ICT_Ar_Sec1_T1),
# in correct logical reading order (as the production pipeline's text is expected to be —
# see toc.py's module docstring/comments), one book unit + a couple of lessons under it.
AR_TOC_PAGE = """الفهرس
الوحدة الأولى .......................................................................................... 7
ما هي المعلومات ؟ ...................................................................................... 7
المعلومات والوسائط .................................................................................... 8
الوحدة الثانية .......................................................................................... 16
القوانين والحقوق في مجتمع المعلومات ................................................................ 16
"""

EN_TOC_PAGE = """Table of Contents
Unit One .......................................................................... 7
What is Information? ............................................................. 7
Information and Media ............................................................ 8
Unit Two .......................................................................... 16
"""


def test_is_toc_heading_line_recognises_both_languages():
    assert is_toc_heading_line("الفهرس")
    assert is_toc_heading_line("Table of Contents")
    assert is_toc_heading_line("Contents")
    assert not is_toc_heading_line("الوحدة الأولى")


def test_parse_toc_entry_line_handles_leader_dots_and_trailing_page():
    parsed = parse_toc_entry_line("الوحدة الأولى .......................................................................................... 7")
    assert parsed == ("الوحدة الأولى", 7)


def test_parse_toc_entry_line_handles_leading_page_number():
    parsed = parse_toc_entry_line("7    الوحدة الأولى")
    assert parsed == ("الوحدة الأولى", 7)


def test_parse_toc_entry_line_returns_none_without_a_page_number():
    assert parse_toc_entry_line("نص عادي بدون رقم صفحة في آخره") is None
    assert parse_toc_entry_line("") is None


def test_parse_toc_entries_classifies_unit_and_lesson_level():
    entries = parse_toc_entries(AR_TOC_PAGE)
    by_title = {e.title: e for e in entries}
    assert by_title["الوحدة الأولى"].level == 1
    assert by_title["الوحدة الأولى"].page == 7
    # "ما هي المعلومات ؟" carries no "lesson"/"الدرس" keyword of its own — real curricula
    # routinely leave lesson titles unlabeled like this — but it appears right after a
    # recognised unit entry, so it's correctly inferred as a lesson under it (level 2).
    assert by_title["ما هي المعلومات ؟"].level == 2


def test_parse_toc_entries_leaves_front_matter_before_first_unit_unclassified():
    text = "الفهرس\nمقدمة .......... 3\nالوحدة الأولى .......... 7\n"
    entries = parse_toc_entries(text)
    by_title = {e.title: e for e in entries}
    # "مقدمة" (preface/introduction) appears before any unit is seen at all — nothing in
    # its wording or position says whether it's chapter- or lesson-level, so it must stay
    # unclassified rather than being guessed either way.
    assert by_title["مقدمة"].level is None
    assert by_title["الوحدة الأولى"].level == 1


def test_find_toc_section_locates_ar_and_en_toc_pages():
    pages = ["غلاف الكتاب", AR_TOC_PAGE, "محتوى الوحدة الأولى الفعلي هنا"]
    section = find_toc_section(pages)
    assert section is not None
    assert "الوحدة الأولى" in section

    pages_en = ["Cover page", EN_TOC_PAGE, "Actual unit one body content here"]
    section_en = find_toc_section(pages_en)
    assert section_en is not None
    assert "Unit One" in section_en


def test_find_toc_section_returns_none_when_no_toc_page_exists():
    pages = ["غلاف الكتاب", "محتوى عادي بدون فهرس", "محتوى آخر"]
    assert find_toc_section(pages) is None


def test_similarity_is_tolerant_of_wording_differences_not_exact_match():
    # Same meaning, different wording/whitespace/diacritics — must still score high.
    assert similarity("الوحدة الأولى", "الوحدة  الاولى") > 0.85
    assert similarity("Unit One: Information", "Information - Unit One") > 0.7
    # Genuinely different titles must not be confused for one another.
    assert similarity("الوحدة الأولى", "الوحدة الثانية") < 0.85


def test_toc_index_match_does_not_require_exact_string_match():
    index = TocIndex.build([AR_TOC_PAGE])
    found = index.match("الوحدة الاولى")  # missing hamza — a very common OCR/typing drift
    assert found is not None
    entry, score = found
    assert entry.title == "الوحدة الأولى"
    assert score >= 0.72


def test_toc_index_classify_level_prefers_toc_over_ambiguous_numbering():
    index = TocIndex.build([AR_TOC_PAGE])
    assert index.classify_level("الوحدة الأولى") == 1
    assert index.classify_level("عنوان غير موجود في الفهرس إطلاقًا") is None


def test_toc_index_build_returns_none_without_a_toc_page():
    assert TocIndex.build(["صفحة عادية", "صفحة أخرى بدون فهرس"]) is None
