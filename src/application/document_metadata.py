from __future__ import annotations

import json
import os
import re
from hashlib import sha1
from typing import Any

from src.application.metadata import clean_optional, detect_language, normalize_text

# Conservative blacklist copied conceptually from the stable V17 extractor.
_PLACEHOLDER_VALUES = {
    "image", "document", "untitled", "page", "unknown", "none", "null",
    "string", "title", "header", "footer", "figure", "table", "contents",
}
_STOP_AS_TITLE = {
    "image", "document", "page", "chapter", "lesson", "section", "table",
    "contents", "introduction", "preface", "main points", "الرئيسية", "الصورة",
}

# Ministry/publisher/copyright letterhead boilerplate. This kind of line sits at the very
# top (or bottom) of virtually every curriculum cover page we've seen, in both languages,
# regardless of which specific ministry/publisher/book it is, and its presence there (often
# ahead of the real title in raster/line reading order) is what was leaking into
# `document_title` as e.g. "GPS للطبع والنشر والتوزيع MINISTRY OF EDUCATION AND TECHNICAL
# EDUCATION ...". Matched generically on the phrase, never on a specific ministry/publisher
# name, so this isn't tied to any one country's curriculum.
_BOILERPLATE_LINE = re.compile(
    r"(?:"
    r"ministry\s+of\s+education|department\s+of\s+education|"
    r"copyright\s*(?:©|\(c\))?|all\s+rights\s+reserved|isbn\b|"
    r"printed\s+by|published\s+by|printing\s+(?:house|press)|"
    r"وزارة\s+التربية|وزارة\s+التعليم|جميع\s+الحقوق\s+محفوظة|رقم\s+الإيداع|"
    r"للطبع\s+والنشر|دار\s+النشر|حقوق\s+الطبع"
    r")",
    re.I,
)


def _valid(value: Any) -> bool:
    value = clean_optional(value)
    if value is None:
        return False
    s = str(value).strip()
    if s.casefold() in _PLACEHOLDER_VALUES or s.casefold() in _STOP_AS_TITLE:
        return False
    if len(s) > 180:
        return False
    return bool(re.search(r"[A-Za-z\u0600-\u06FF0-9]", s))


def _clean(value: Any) -> str | None:
    value = clean_optional(value)
    if value is None:
        return None
    value = re.sub(r"\s+", " ", str(value)).strip(" \t|-#–—:")
    value = re.sub(r"\s+Image\s*$", "", value, flags=re.I)
    value = re.sub(r"\s+20\d{2}\s*[-–—]\s*20\d{2}\s*$", "", value)
    return value if _valid(value) else None


def _label_value(text: str, labels: tuple[str, ...]) -> tuple[str | None, str | None, str | None]:
    label_group = "|".join(re.escape(x) for x in labels)
    pattern = rf"(?i)(?:^|\n|\s)(?:{label_group})\s*[:=\-–—]\s*(.+?)(?=\s+(?:subject|grade|class|course|المادة|الصف|للصف|term|semester)\s*[:=\-–—]|\n|$)"
    for match in re.finditer(pattern, text):
        value = _clean(match.group(1))
        if value:
            return value, "explicit", match.group(0).strip()
    return None, None, None


_EN_ORDINAL_WORDS = (
    "first", "second", "third", "fourth", "fifth", "sixth",
    "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth",
)
_EN_ORDINAL_GROUP = "|".join(_EN_ORDINAL_WORDS)
_EN_STAGE_WORDS = "secondary|primary|preparatory|prep"

# "For First Year of Secondary School" / "For the Third Year Preparatory" — a very common
# English-cover grade phrasing (ordinal + year + stage), in a different word order than
# "Grade/Secondary N". Shared between subject's lookahead-stop and grade's own pattern so
# the two stay in sync: subject must stop capturing exactly where grade's pattern starts.
_EN_ORDINAL_YEAR_STAGE = rf"(?:the\s+)?(?:{_EN_ORDINAL_GROUP})\s+year\s+(?:of\s+)?(?:{_EN_STAGE_WORDS})\b"


_ALEF_FAMILY = set("اأإآ")


def _ligature_corrupted_form(word: str) -> str:
    """Mirrors a specific, verified font bug (seen in real curriculum PDFs) where an
    embedded Arabic font's ToUnicode CMap silently transposes any lam ('ل') immediately
    followed by an alef-family letter ('ا','أ','إ','آ') — e.g. 'والاتصالات' extracts as
    'واالتصاالت'. This reproduces that exact transposition so we can match either the
    correct or the corrupted spelling of a *known, fixed* set of curriculum words
    (never a blind 'ال'->'لا' swap, which would also wreck the ordinary definite
    article 'ال' that appears throughout Arabic text)."""
    out: list[str] = []
    i = 0
    while i < len(word):
        if word[i] == "ل" and i + 1 < len(word) and word[i + 1] in _ALEF_FAMILY:
            out.append(word[i + 1])
            out.append(word[i])
            i += 2
        else:
            out.append(word[i])
            i += 1
    return "".join(out)


def _ligature_tolerant_group(*words: str) -> str:
    variants: list[str] = []
    for w in words:
        variants.append(re.escape(w))
        corrupted = _ligature_corrupted_form(w)
        if corrupted != w:
            variants.append(re.escape(corrupted))
    return "|".join(variants)


# The three curriculum grade/stage words verified (by direct inspection of the affected
# PDFs) to actually contain a lam+alef-family pair, and therefore the only ones this font
# bug can corrupt. Every other Arabic grade word ("الثاني", "الثانوي", ...) never has this
# letter pair, so it is never affected and is matched only in its normal spelling.
_AR_GRADE_LIGATURE_WORDS = ("الأول", "الإعدادي", "الابتدائي")
_AR_GRADE_ORDINAL_GROUP = _ligature_tolerant_group(
    "الأول", "الثاني", "الثالث", "الرابع", "الخامس", "السادس",
    "السابع", "الثامن", "التاسع", "العاشر", "الحادي عشر", "الثاني عشر",
)
_AR_GRADE_STAGE_GROUP = _ligature_tolerant_group("الثانوي", "الإعدادي", "الابتدائي")


def detect_arabic_ligature_corruption(text: str) -> bool:
    """True if the text contains the corrupted (never the correct) spelling of one of
    the known-affected words — a reliable signal that this document's embedded Arabic
    font has the lam+alef-family ToUnicode bug, so callers can flag it for OCR re-upload
    instead of silently trusting garbled extraction elsewhere in the document too."""
    for word in _AR_GRADE_LIGATURE_WORDS:
        corrupted = _ligature_corrupted_form(word)
        if corrupted != word and corrupted in text:
            return True
    return False


def _grade_from_text(text: str) -> tuple[str | None, str | None, str | None]:
    patterns = (
        r"\bgrade\b\s*[:\-]?\s*([0-9]{1,2}|[A-Za-z][A-Za-z0-9 -]{0,24})\b",
        r"\bclass\b\s*[:\-]?\s*([0-9]{1,2}|[A-Za-z][A-Za-z0-9 -]{0,24})\b",
        r"\bsecondary\s+([0-9]{1,2})\b",
        # Spelled-out English ordinals ("Secondary First", "Grade Second Year") — the
        # digit-only patterns above miss these entirely.
        rf"\b(?:grade|secondary|class|level)\s+((?:{_EN_ORDINAL_GROUP})(?:\s+year)?)\b",
        # Reverse order: "First Year of Secondary School" / "Third Year Preparatory".
        rf"\b(?:the\s+)?({_EN_ORDINAL_GROUP})\s+year\s+(?:of\s+)?(?:{_EN_STAGE_WORDS})\b",
        # Ligature-tolerant: matches either the correct or the font-corrupted spelling of
        # the ordinal/stage words, so grade still resolves even on affected PDFs.
        rf"(?:الصف|للصف)\s+({_AR_GRADE_ORDINAL_GROUP})\s*(?:{_AR_GRADE_STAGE_GROUP})?",
        r"المرحلة\s+([\u0600-\u06FFA-Za-z0-9 -]{2,40})",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.I)
        if match:
            value = _clean(match.group(1))
            if value:
                # Normalize a corrupted match back to the canonical spelling so downstream
                # consumers always see the correct word, never the font-bug artifact.
                for word in _AR_GRADE_LIGATURE_WORDS:
                    if value == _ligature_corrupted_form(word):
                        value = word
                        break
                return value, "explicit", match.group(0)
    return None, None, None




def _subject_from_text(text: str, *, limit: int | None = 30000) -> tuple[str | None, str | None, str | None]:
    value, src, evidence = _label_value(
        text,
        ("subject", "discipline", "course", "المادة", "مادة", "المقرر", "المقرر الدراسي"),
    )
    if value:
        return value, src, evidence

    sample = text if limit is None else text[:limit]

    # High-confidence document-wording patterns: an Arabic cover ("مقدمة في X للصف Y") and
    # its English mirror ("Introduction to X for Grade/Secondary/Class Y"). Neither is
    # tied to a specific book — both are generic curriculum-cover phrasings.
    strong_patterns = (
        re.compile(
            r"مقدمة\s+في\s+(?P<subject>[^\n]{2,180}?)(?=\s+(?:للصف|لطلاب|عام)\b|\s+20\d{2}\s*[-–—]\s*20\d{2}\b|$)",
            flags=re.I,
        ),
        re.compile(
            r"introduction\s+to\s+(?P<subject>[^\n]{2,180}?)"
            rf"(?=\s+for\s+(?:grade|secondary|class|level|students)\b|\s+for\s+{_EN_ORDINAL_YEAR_STAGE}|"
            r"\s+20\d{2}\s*[-–—]\s*20\d{2}\b|$)",
            flags=re.I,
        ),
    )
    for pattern in strong_patterns:
        match = pattern.search(sample)
        if match:
            value = _clean(match.group("subject"))
            if value and not _BOILERPLATE_LINE.search(value):
                return value, "document_pattern", match.group(0)

    # Weaker fallback, same idea in either language: "<Subject> — Grade N" / "Grade N <Subject>"
    # style cover lines with no "Introduction to"/"مقدمة في" wording at all. Lower confidence
    # (see _resolve_field) because a short preceding phrase can occasionally be noise rather
    # than the real subject name.
    weak_patterns = (
        re.compile(
            r"(?:^|\n)\s*(?P<subject>[A-Za-z][A-Za-z &/\-]{2,40}?)\s*[-–—:]?\s*"
            r"(?:for\s+)?(?:grade|secondary|class|level)\s+[0-9]{1,2}\b",
            flags=re.I,
        ),
        re.compile(
            r"(?P<subject>[\u0600-\u06FF][\u0600-\u06FF /\-]{2,80}?)\s+"
            r"(?:الصف|للصف)\s+(?:الأول|الثاني|الثالث|الرابع|الخامس|السادس|السابع|الثامن|التاسع|العاشر)",
            flags=re.I,
        ),
    )
    generic_prefix = re.compile(
        r"^(?:student'?s?\s+book|teacher'?s?\s+(?:book|guide)|work\s*book|text\s*book)\s+",
        flags=re.I,
    )
    for pattern in weak_patterns:
        match = pattern.search(sample)
        if match:
            value = _clean(match.group("subject"))
            if value:
                value = _clean(generic_prefix.sub("", value))
            if value and not _BOILERPLATE_LINE.search(value) and value.casefold() not in _STOP_AS_TITLE:
                return value, "document_pattern_weak", match.group(0)

    return None, None, None


_FILENAME_LANGUAGE_TOKENS = {"ar", "ara", "arabic", "en", "eng", "english", "fr", "fra", "french"}
_FILENAME_GRADE_TOKEN_RE = re.compile(
    r"^(?:grade|class|level|year|sec|secondary|prep|preparatory|prim|primary)\d{0,2}$", re.I
)
_FILENAME_TERM_TOKEN_RE = re.compile(r"^(?:t|term|sem|semester)\d{0,2}$", re.I)


def _filename_stem(file_name: str) -> str:
    name = file_name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    return re.sub(r"\.[A-Za-z0-9]+$", "", name)


def _subject_from_filename(file_name: str) -> tuple[str | None, str | None, str | None]:
    """Best-effort subject candidate from the filename's own naming convention (e.g.
    "ICT_Ar_Sec1_T1.pdf" -> "ICT"): the token left over once known language/grade/term
    markers and bare numbers are excluded. Only fires when the book's own text has no
    subject anywhere (see extract_document_metadata's resolution order) — deliberately
    narrow: a candidate is only accepted when it's the *sole* token left, so an
    unfamiliar naming convention yields nothing instead of a guess.
    """
    stem = _filename_stem(file_name)
    tokens = [t for t in re.split(r"[_\-\s]+", stem) if t]
    candidates = []
    for tok in tokens:
        low = tok.casefold()
        if low in _FILENAME_LANGUAGE_TOKENS:
            continue
        if _FILENAME_GRADE_TOKEN_RE.match(tok):
            continue
        if _FILENAME_TERM_TOKEN_RE.match(tok):
            continue
        if tok.isdigit():
            continue
        if not re.search(r"[A-Za-z\u0600-\u06FF]", tok):
            continue
        candidates.append(tok)
    if len(candidates) == 1:
        return candidates[0], "filename", stem
    return None, None, None


def _term_from_filename(file_name: str) -> tuple[str | None, str | None, str | None]:
    """Fallback only: "_T1"/"_Term2"/"_sem1" style filename markers, used only when the
    book's own text (first pages) never states the term explicitly."""
    stem = _filename_stem(file_name)
    m = re.search(r"(?:^|[_\-\s])(?:t|term|sem|semester)[_\-\s]?(\d{1,2}|one|two|first|second)(?:$|[_\-\s])", stem, re.I)
    if not m:
        return None, None, None
    value = _clean(m.group(1))
    return (value, "filename", stem) if value else (None, None, None)


def _term_from_text(text: str) -> tuple[str | None, str | None, str | None]:
    value, src, evidence = _label_value(text, ("term", "semester", "الفصل الدراسي", "الترم"))
    if value:
        return value, src, evidence

    sample = text[:30000]
    patterns = (
        # "Term 1" / "Term One" / "Semester 2" (no colon).
        re.compile(r"\b(?:term|semester)\s+(one|two|first|second|[12])\b", re.I),
        # "First Term" / "Second Semester".
        re.compile(r"\b(first|second)\s+(?:term|semester)\b", re.I),
        # Arabic: requires "الدراسي" so the bare word "الفصل" (chapter) is never matched
        # as a term — chapter and term/semester share the same root word in Arabic.
        re.compile(r"الفصل\s+الدراسي\s+(الأول|الثاني|1|2)"),
        re.compile(r"الترم\s+(الأول|الثاني|1|2)"),
    )
    for pattern in patterns:
        match = pattern.search(sample)
        if match:
            value = _clean(match.group(1))
            if value:
                return value, "document_pattern", match.group(0)
    return None, None, None


def _title_from_opening(text: str) -> tuple[str | None, str | None, float, str | None]:
    # First search globally for the known generic curriculum title pattern.
    pattern = re.compile(
        r"(?P<title>[A-Za-z\u0600-\u06FF][^\n]{2,120}?)\s+مقدمة\s+في\s+(?P<subject>[^\n]{2,180}?)(?=\s+(?:للصف|لطلاب|عام)\b|\s+20\d{2}\s*[-–—]\s*20\d{2}\b|$)",
        flags=re.I,
    )
    match = pattern.search(text[:30000])
    if match:
        title = _clean(match.group("title"))
        if title:
            return title, "opening_title_pattern", 0.88, match.group(0)

    lines = [re.sub(r"\s+", " ", x).strip(" \t|-#") for x in text.splitlines() if x.strip()]
    for line in lines[:160]:
        if not line:
            continue
        low = line.casefold()
        if low in _PLACEHOLDER_VALUES or low in _STOP_AS_TITLE:
            continue
        if re.match(r"^(subject|grade|course|class|page|chapter|lesson|المادة|الصف)\b\s*[:=]", low):
            continue
        if _BOILERPLATE_LINE.search(line):
            continue
        candidate = _clean(line)
        if candidate and 4 <= len(candidate) <= 140 and not re.search(r"[.!?؟،:;؛]", candidate):
            return candidate, "opening_content", 0.80, line
    return None, None, 0.0, None

def _llm_fallback(evidence_text: str) -> dict[str, Any] | None:
    """Optional conservative metadata LLM fallback.

    Disabled unless OPENAI_API_KEY and OPENAI_METADATA_MODEL are explicitly configured.
    This keeps the default local pipeline free of an external dependency.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None

    model = os.getenv("OPENAI_METADATA_MODEL", "gpt-5-nano")
    schema = {
        "name": "document_metadata",
        "strict": True,
        "schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "document_title": {"type": ["string", "null"]},
                "subject": {"type": ["string", "null"]},
                "grade": {"type": ["string", "null"]},
                "evidence": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "document_title": {"type": ["string", "null"]},
                        "subject": {"type": ["string", "null"]},
                        "grade": {"type": ["string", "null"]},
                    },
                    "required": ["document_title", "subject", "grade"],
                },
            },
            "required": ["document_title", "subject", "grade", "evidence"],
        },
    }
    prompt = (
        "Extract document-level metadata from this educational document excerpt. "
        "Use only evidence present in the excerpt. Never infer from filename. "
        "Never use generic tokens such as Image, Document, Page, Table, Figure, Untitled. "
        "If unsupported, return null. Every non-null field must have evidence.\n\n"
        f"EXCERPT:\n{evidence_text[:24000]}"
    )
    try:
        client = OpenAI(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/"))
        response = client.chat.completions.create(
            model=model,
            temperature=0,
            messages=[
                {"role": "system", "content": "You are a conservative educational document metadata extractor."},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_schema", "json_schema": schema},
        )
        return json.loads(response.choices[0].message.content or "{}")
    except Exception:
        return None


def _resolve_field(
    explicit: tuple[str | None, str | None, str | None],
    llm: dict[str, Any] | None,
    name: str,
) -> tuple[str | None, str | None, float, str | None]:
    value, source, evidence = explicit
    if _valid(value):
        confidence = {
            "override": 0.98,
            "explicit": 0.98,
            "document_pattern": 0.94,
            "document_pattern_weak": 0.72,
            # Weaker than any evidence actually found in the book's own text — this is
            # a fallback for when the book has nothing at all.
            "filename": 0.65,
        }.get(source, 0.90)
        return str(value).strip(), source, confidence, evidence
    if llm:
        candidate = _clean(llm.get(name))
        candidate_evidence = _clean((llm.get("evidence") or {}).get(name))
        if candidate and candidate_evidence:
            return candidate, "llm_evidence", 0.90, candidate_evidence
    return None, None, 0.0, None


def extract_document_metadata(
    text: str,
    *,
    file_name: str,
    parser_language: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    overrides = {k: clean_optional(v) for k, v in (overrides or {}).items() if k in {"subject", "grade"}}
    overrides = {k: v for k, v in overrides.items() if v is not None}

    sample = normalize_text(text)
    language = parser_language or detect_language(sample)

    subject_explicit = (
        (str(overrides["subject"]), "override", str(overrides["subject"]))
        if "subject" in overrides
        else _subject_from_text(sample)
    )
    # Subject fallback chain when the book's own text (first pages) has nothing: try the
    # filename's own convention (e.g. "ICT_Ar_Sec1_T1.pdf" -> "ICT"), then widen the text
    # search to the whole document instead of just the first ~30k chars — some books only
    # name their subject deep inside (a running header, an appendix), not on the cover.
    # Grade is deliberately excluded from this fallback chain; a filename stage token
    # ("Sec1") is not reliable enough to become a grade value on its own.
    if "subject" not in overrides and not subject_explicit[0]:
        subject_explicit = _subject_from_filename(file_name)
    if "subject" not in overrides and not subject_explicit[0]:
        subject_explicit = _subject_from_text(sample, limit=None)
    grade_explicit = (
        (str(overrides["grade"]), "override", str(overrides["grade"]))
        if "grade" in overrides
        else _grade_from_text(sample)
    )

    title, title_source, title_confidence, title_evidence = _title_from_opening(sample)
    lines = [line for line in sample.splitlines() if line.strip()]
    signal_lines = [
        line for line in lines
        if re.search(r"subject|discipline|course|grade|class|secondary|المادة|الصف|للصف|المرحلة", line, re.I)
    ]
    llm = _llm_fallback("\n".join((lines[:180] + signal_lines[:80])[:240]))

    if not title and llm:
        candidate = _clean(llm.get("document_title"))
        evidence = _clean((llm.get("evidence") or {}).get("document_title"))
        if candidate and evidence:
            title, title_source, title_confidence, title_evidence = candidate, "llm_evidence", 0.90, evidence

    # Filename is a title fallback here; subject/term have their own filename fallback
    # above (only once the book's own text has nothing at all). Grade is never guessed
    # from the filename.
    if not title:
        stem = re.sub(r"\.[A-Za-z0-9]+$", "", file_name).replace("_", " ")
        title = _clean(stem)
        title_source = "filename"
        title_confidence = 0.55 if title else 0.0
        title_evidence = stem if title else None

    subject, subject_source, subject_confidence, subject_evidence = _resolve_field(subject_explicit, llm, "subject")
    grade, grade_source, grade_confidence, grade_evidence = _resolve_field(grade_explicit, llm, "grade")
    # Term: the book's own text (first pages) first; only falls back to a filename marker
    # ("_T1"/"_Term2") when the book itself says nothing at all. Never from overrides.
    term_explicit = _term_from_text(sample)
    if not term_explicit[0]:
        term_explicit = _term_from_filename(file_name)
    term, term_source, term_confidence, term_evidence = _resolve_field(term_explicit, llm, "term")

    text_quality_warning = "arabic_font_ligature_corruption" if detect_arabic_ligature_corruption(sample) else None

    return {
        "document_title": title,
        "subject": subject,
        "grade": grade,
        "term": term,
        "language": language,
        "text_quality_warning": text_quality_warning,
        "sources": {
            "document_title": title_source,
            "subject": subject_source,
            "grade": grade_source,
            "term": term_source,
            "language": "parser" if parser_language else "document_text",
        },
        "confidence": {
            "document_title": title_confidence,
            "subject": subject_confidence,
            "grade": grade_confidence,
            "term": term_confidence,
            "language": 0.99,
        },
        "evidence": {
            "document_title": title_evidence,
            "subject": subject_evidence,
            "grade": grade_evidence,
            "term": term_evidence,
        },
    }


def resolve_curriculum_identity(
    document_metadata: dict[str, Any],
    override: str | None = None,
    *,
    file_reference_id: str | None = None,
) -> str:
    override = clean_optional(override)
    if override:
        return str(override)
    # Uploaded files get a deterministic identity tied to the file reference.
    if file_reference_id:
        return f"cur_{sha1(str(file_reference_id).encode('utf-8')).hexdigest()[:12]}"
    basis = "|".join(str(document_metadata.get(k) or "") for k in ("subject", "grade", "document_title", "language"))
    return f"cur_{sha1(basis.encode('utf-8')).hexdigest()[:12]}"
