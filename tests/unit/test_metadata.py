from src.application.metadata import clean_optional, detect_language, extract_hierarchy, normalize_text, parse_filename_metadata

def test_language():
    assert detect_language("Hello world") == "en"
    assert detect_language("مرحبا بالعالم") == "ar"
    assert detect_language("Hello مرحبا") == "mixed"

def test_explicit_labels_are_semantic_and_numbering_is_generic_heading():
    text = "Subject: Physics\nGrade: 12\nChapter: Modern Physics\nLesson: Photoelectric Effect\nSection: Threshold Frequency"
    h = extract_hierarchy(text)
    assert h["subject"] == "Physics"
    assert h["grade"] == "12"
    assert h["chapter"] == "Modern Physics"
    assert h["lesson"] == "Photoelectric Effect"
    h2 = extract_hierarchy("1. Machine Learning\n1.1 Supervised Learning\n1.1.1 Classification")
    assert h2["heading"] == "Classification"
    assert h2["heading_path"] == ["Machine Learning", "Supervised Learning", "Classification"]

def test_filename_parser_does_not_guess_subject_or_term():
    meta = parse_filename_metadata("ICT_Ar_Sec1_T1.pdf")
    assert "subject" not in meta
    assert "term" not in meta

def test_placeholder_values_are_unknown():
    assert clean_optional("string") is None
    assert clean_optional("null") is None
    assert clean_optional("") is None

def test_normalize_removes_pdf_control_noise_without_changing_content():
    raw = "ICT\u0007   شبكات\n\n LAN"
    out = normalize_text(raw)
    assert "ICT" in out and "شبكات" in out and "LAN" in out
    assert "\u0007" not in out


def test_known_book_opening_is_resilient_to_parser_noise_before_title():
    text = "dsos xenh\n# البرمجة والذكاء الاصطناعي مقدمة في تكنولوجيا المعلومات والاتصالات للصف الأول الثانوي 2025 - 2026 Image"
    from src.application.document_metadata import extract_document_metadata
    meta = extract_document_metadata(text, file_name="ICT_Ar_Sec1_T1.pdf", parser_language="ar")
    assert meta["document_title"] == "البرمجة والذكاء الاصطناعي"
    assert meta["subject"] == "تكنولوجيا المعلومات والاتصالات"
    assert meta["grade"] == "الأول"
    # Filename has "_T1" but the body text never says "term" explicitly, so it must
    # not leak from the filename into term.
    assert meta["term"] is None


def test_filename_never_becomes_subject_or_grade():
    from src.application.document_metadata import extract_document_metadata
    meta = extract_document_metadata("random parser noise", file_name="ICT_Ar_Sec1_T1.pdf", parser_language="ar")
    assert meta["subject"] is None
    assert meta["grade"] is None
