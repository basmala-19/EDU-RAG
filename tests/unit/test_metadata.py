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
    # The body never says "term" explicitly, so it now falls back to the filename's own
    # "_T1" marker — a deliberate fallback, only used once the book's text has nothing.
    assert meta["term"] == "1"


def test_unit_heading_without_separator_is_recognized_as_chapter():
    # "الوحدة الأولى" with no colon/dash — the shape LABEL_PATTERNS/_label_match never
    # covered, since that requires "<label> <separator> <value>".
    h = extract_hierarchy("الوحدة الأولى\nنص عادي في الصفحة")
    assert h["heading"] == "الوحدة الأولى"
    assert h["chapter"] == "Chapter 1"

def test_unit_heading_with_title_after_separator():
    h = extract_hierarchy("الوحدة الثانية: الطاقة والحركة\nنص")
    assert h["heading"] == "الطاقة والحركة"
    assert h["chapter"] == "Chapter 2"

def test_unit_heading_english_word_and_digit_forms():
    assert extract_hierarchy("Unit One: Forces")["chapter"] == "Chapter 1"
    assert extract_hierarchy("Unit 3")["chapter"] == "Chapter 3"

def test_explicit_chapter_label_still_wins_over_later_unit_heading():
    text = "Chapter: Modern Physics\nالوحدة الثانية: شيء آخر"
    h = extract_hierarchy(text)
    assert h["chapter"] == "Modern Physics"
    # heading itself still tracks the latest structural line seen.
    assert h["heading"] == "شيء آخر"


def test_toc_corrects_ambiguous_numbered_heading_level():
    from src.application.toc import TocIndex

    # "Photosynthesis" is a lesson in the TOC, but on its own body page it's only ever
    # printed as a bare "1 Photosynthesis" — numbering depth alone (level 1 by dot-count)
    # would wrongly promote it to chapter. The TOC must correct this to lesson (level 2),
    # while the printed heading text itself stays exactly as written in the body.
    toc = TocIndex.build(["Table of Contents\nUnit 1: Biology Basics .......... 3\nPhotosynthesis .......... 4\n"])
    h = extract_hierarchy("1 Photosynthesis\nsome body text", toc_index=toc)
    assert h["heading"] == "Photosynthesis"
    assert h["lesson"] == "Photosynthesis"
    assert h["chapter"] is None


def test_toc_recognizes_unmarked_heading_with_no_numbering_or_label():
    from src.application.toc import TocIndex

    toc = TocIndex.build(["الفهرس\nالوحدة الأولى .......... 7\n"])
    # No numbering, no colon, no label — just the title standing alone, exactly as a
    # bold/large-font unit title with no printed number would extract. This particular
    # line is also caught earlier by parse_unit_heading() (an existing, independent
    # detector for the bare "الوحدة الأولى" shape) rather than by the new TOC-only path —
    # both agree on the result, and `chapter` is normalized to the language-neutral
    # "Chapter N" form exactly as parse_unit_heading has always done.
    h = extract_hierarchy("الوحدة الأولى\nنص عادي بعدها", toc_index=toc)
    assert h["chapter"] == "Chapter 1"
    assert h["heading"] == "الوحدة الأولى"


def test_toc_recognizes_unmarked_lesson_heading_with_no_numbering_or_label():
    from src.application.toc import TocIndex

    # Unlike the unit case above, a lesson title with no numbering/label at all has no
    # other detector in metadata.py that would catch it — this is the TOC-only path's
    # actual reason for existing.
    toc = TocIndex.build(["الفهرس\nالوحدة الأولى .......... 7\nما هي المعلومات ؟ .......... 7\n"])
    h = extract_hierarchy("الوحدة الأولى\nما هي المعلومات ؟\nنص عادي بعدها", toc_index=toc)
    assert h["lesson"] == "ما هي المعلومات ؟"
    assert h["heading"] == "ما هي المعلومات ؟"


def test_toc_never_overrides_an_explicit_label():
    from src.application.toc import TocIndex

    toc = TocIndex.build(["Table of Contents\nUnit Two .......... 10\n"])
    # Body explicitly labels this "Chapter: Unit One" — that must win even though the
    # TOC only knows "Unit Two", and even though an unrelated TOC entry exists.
    h = extract_hierarchy("Chapter: Unit One", toc_index=toc)
    assert h["chapter"] == "Unit One"


def test_toc_index_none_is_fully_backward_compatible():
    # No toc_index supplied at all — behaviour must be identical to before this
    # parameter existed.
    h = extract_hierarchy("1. Machine Learning\n1.1 Supervised Learning")
    assert h["chapter"] == "Machine Learning"
    assert h["lesson"] == "Supervised Learning"


def test_filename_fills_subject_and_term_gaps_but_never_grade():
    from src.application.document_metadata import extract_document_metadata
    meta = extract_document_metadata("random parser noise", file_name="ICT_Ar_Sec1_T1.pdf", parser_language="ar")
    # Body has nothing at all, so subject/term fall back to the filename's own convention.
    assert meta["subject"] == "ICT"
    assert meta["term"] == "1"
    # Grade is still never guessed from the filename — a stage token like "Sec1" isn't
    # reliable enough on its own to become a grade value.
    assert meta["grade"] is None


def test_filename_fallback_never_overrides_explicit_body_evidence():
    from src.application.document_metadata import extract_document_metadata
    # Body has an explicit "Subject:"/"Term:" label — the filename's own convention
    # (which would suggest "ICT" and term "1") must never override real evidence.
    text = "Subject: Physics\nTerm: 2"
    meta = extract_document_metadata(text, file_name="ICT_Ar_Sec1_T1.pdf", parser_language="en")
    assert meta["subject"] == "Physics"
    assert meta["term"] == "2"


def test_ambiguous_filename_yields_no_subject_guess():
    from src.application.document_metadata import extract_document_metadata
    # Two candidate tokens left after stripping known language/grade/term markers —
    # too ambiguous to guess, so subject must stay null rather than pick one.
    meta = extract_document_metadata("random parser noise", file_name="Math_Extra_Ar_Sec1_T1.pdf", parser_language="ar")
    assert meta["subject"] is None
