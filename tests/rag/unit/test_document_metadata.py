from src.features.rag.application.document_metadata import extract_document_metadata, resolve_curriculum_identity

def test_extracts_generic_document_metadata_including_term():
    text = "Physics Textbook\nSubject: Physics\nGrade: 12\nTerm: 1\n"
    meta = extract_document_metadata(text, file_name="book.pdf", parser_language="en")
    assert meta["subject"] == "Physics"
    assert meta["grade"] == "12"
    assert meta["term"] == "1"
    assert meta["language"] == "en"
    assert resolve_curriculum_identity(meta).startswith("cur_")

def test_arabic_opening_document_pattern():
    text = "# البرمجة والذكاء الاصطناعي مقدمة في تكنولوجيا المعلومات والاتصالات للصف الأول الثانوي 2025 - 2026 Image"
    meta = extract_document_metadata(text, file_name="ICT_Ar_Sec1_T1.pdf", parser_language="ar")
    assert meta["document_title"] == "البرمجة والذكاء الاصطناعي"
    assert meta["subject"] == "تكنولوجيا المعلومات والاتصالات"
    assert meta["grade"] == "الأول"
    assert "Image" not in meta["document_title"]
    # This cover text never mentions a term/semester explicitly, so it falls back to the
    # filename's own "_T1" marker (a deliberate fallback — see test_document_metadata's
    # filename-fallback tests below).
    assert meta["term"] == "1"


def test_english_opening_document_pattern():
    """English mirror of the Arabic 'مقدمة في X للصف' cover pattern. Previously only the
    Arabic phrasing was recognised, so every English book fell through to subject: null."""
    text = "Programming and Artificial Intelligence\nIntroduction to Information and Communication Technology for Secondary 1\n2024-2025"
    meta = extract_document_metadata(text, file_name="ICT_En_Sec1_T1.pdf", parser_language="en")
    assert meta["subject"] == "Information and Communication Technology"
    assert meta["grade"] == "1"
    assert meta["sources"]["subject"] == "document_pattern"


def test_english_spelled_out_grade():
    text = "Introduction to Chemistry for Secondary First\nUnit 1"
    meta = extract_document_metadata(text, file_name="chem.pdf", parser_language="en")
    assert meta["grade"] == "First"


def test_english_reverse_order_ordinal_year_stage_grade():
    """Real cover wording seen in production: ordinal + 'Year of' + stage, in the
    opposite order from 'Secondary First'. Also checks the subject pattern's lookahead
    stops in the same place, instead of swallowing the grade phrase into the subject."""
    text = "Introduction to Information and Communication Technology For First Year of Secondary School"
    meta = extract_document_metadata(text, file_name="ict.pdf", parser_language="en")
    assert meta["subject"] == "Information and Communication Technology"
    assert meta["grade"] == "First"


def test_weak_subject_fallback_when_no_introduction_phrase():
    text = "Student Book\nComputer Science - Grade 7\nUnit 1"
    meta = extract_document_metadata(text, file_name="cs.pdf", parser_language="en")
    assert meta["subject"] == "Computer Science"
    assert meta["sources"]["subject"] == "document_pattern_weak"
    assert meta["confidence"]["subject"] < 0.94


def test_term_extracted_from_arabic_content_pattern():
    text = "تكنولوجيا المعلومات والاتصالات للصف الأول الثانوي الفصل الدراسي الأول"
    meta = extract_document_metadata(text, file_name="ICT_Ar_Sec1_T1.pdf", parser_language="ar")
    assert meta["term"] == "الأول"


def test_term_bare_chapter_word_is_not_mistaken_for_term():
    """'الفصل' alone means chapter, not term/semester — only 'الفصل الدراسي' (with
    الدراسي) should ever resolve to a term, otherwise every chapter heading would
    falsely produce a term value."""
    text = "الفصل الأول: مقدمة في البرمجة"
    meta = extract_document_metadata(text, file_name="book.pdf", parser_language="ar")
    assert meta["term"] is None


def test_term_extracted_from_english_content_pattern():
    text = "Introduction to Chemistry for Secondary First\nFirst Term\nUnit 1"
    meta = extract_document_metadata(text, file_name="chem.pdf", parser_language="en")
    assert meta["term"] == "First"


def test_term_falls_back_to_filename_only_when_body_says_nothing():
    """A filename like '..._T2.pdf' now IS allowed to fill term, but only once the
    document body itself says nothing about a term/semester at all."""
    text = "Introduction to Mathematics for Grade 10\nUnit 1: Numbers"
    meta = extract_document_metadata(text, file_name="Math_AR_Prim1_T2.pdf", parser_language="en")
    assert meta["term"] == "2"


def test_term_from_body_wins_over_filename():
    text = "Introduction to Mathematics for Grade 10\nTerm: 1"
    meta = extract_document_metadata(text, file_name="Math_AR_Prim1_T2.pdf", parser_language="en")
    assert meta["term"] == "1"


def test_grade_resolves_despite_arabic_font_ligature_corruption():
    """Reproduces the real font bug seen in production (verified letter-by-letter): the
    embedded Arabic font's ToUnicode CMap transposes any 'ل' immediately followed by an
    alef-family letter, so 'الأول' extracts as 'األول'. Grade must still resolve, and the
    text_quality_warning must flag the book for OCR re-upload."""
    text = "مقدمة في تكنولوجيا المعلومات واالتصاالت للصف األول الثانوي"
    meta = extract_document_metadata(text, file_name="ICT_Ar_Sec1_T1.pdf", parser_language="ar")
    assert meta["grade"] == "الأول"
    assert meta["text_quality_warning"] == "arabic_font_ligature_corruption"


def test_no_ligature_warning_on_clean_text():
    text = "مقدمة في تكنولوجيا المعلومات والاتصالات للصف الأول الثانوي"
    meta = extract_document_metadata(text, file_name="ICT_Ar_Sec1_T1.pdf", parser_language="ar")
    assert meta["grade"] == "الأول"
    assert meta["text_quality_warning"] is None


def test_ministry_letterhead_is_not_picked_as_title_or_subject():
    """Ministry/publisher letterhead sitting above the real title on a cover page should
    never leak into document_title or subject, in either language."""
    text = (
        "MINISTRY OF EDUCATION AND TECHNICAL EDUCATION\n"
        "GPS للطبع والنشر والتوزيع\n"
        "Introduction to Mathematics for Grade 10\n"
        "All rights reserved\n"
    )
    meta = extract_document_metadata(text, file_name="math.pdf", parser_language="en")
    assert meta["subject"] == "Mathematics"
    title = meta["document_title"] or ""
    assert "MINISTRY" not in title.upper()
    assert "للطبع" not in title
    assert "rights reserved" not in title.casefold()
