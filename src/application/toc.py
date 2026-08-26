from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

# Generic, language-neutral: detects a page/section that IS a table of contents, never a
# specific book's actual heading text. Works for any subject/language — this whole module
# never hard-codes a curriculum-specific word beyond these structural marker vocabularies.
_TOC_TITLE_RE = re.compile(
    r"^(?:table\s+of\s+contents|contents|(?:ال)?فهرس(?:\s+المحتويات)?|(?:ال)?محتويات)\s*$",
    re.I,
)

_UNIT_WORD_RE = re.compile(r"\b(?:unit|module|chapter)\b|الوحدة|الفصل(?!\s+الدراسي)|المحور", re.I)
_LESSON_WORD_RE = re.compile(r"\b(?:lesson|lecture)\b|الدرس|المحاضرة", re.I)

# Dot/underscore/middle-dot "leader" runs connecting a TOC title to its page number
# ("Introduction .......... 7" / "المقدمة ...... 7"), in any of the glyphs commonly used
# for this by different PDF producers.
_LEADER_RUN_RE = re.compile(r"[.\u2026_\-·•]{2,}")
_DIACRITICS_RE = re.compile(r"[\u064B-\u0652\u0670\u0640]")
_NON_WORD_RE = re.compile(r"[^\w\u0600-\u06FF ]+", re.U)


@dataclass(frozen=True)
class TocEntry:
    """One parsed line from the book's own table of contents.

    `level` is 1 for a chapter/unit-style entry, 2 for a lesson/lecture-style entry, and
    None when the wording gives no structural clue either way (still useful for fuzzy
    matching, just not for level classification).
    """

    title: str
    normalized: str
    level: int | None
    page: int | None


def _normalize_for_match(text: str) -> str:
    """Normalize a heading/TOC title for tolerant comparison: NFKC, diacritics and tatweel
    stripped, alef/ya variants unified, punctuation dropped, case-folded, whitespace
    collapsed. Two titles that only differ in spelling variant, diacritics, or a trailing
    subtitle are meant to normalize close enough for `similarity()` to recognise them."""
    if not text:
        return ""
    value = unicodedata.normalize("NFKC", text)
    value = _DIACRITICS_RE.sub("", value)
    for src, dst in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ى", "ي"), ("ة", "ه")):
        value = value.replace(src, dst)
    value = _NON_WORD_RE.sub(" ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value.casefold()


def _token_sort(value: str) -> str:
    return " ".join(sorted(value.split()))


def similarity(a: str, b: str) -> float:
    """Fuzzy-match score in [0, 1] between two raw titles, tolerant of word order, minor
    spelling drift, and one title being a superset of the other (e.g. a TOC entry that
    carries a subtitle the in-book heading itself doesn't repeat). This never requires an
    exact string match — different wording with the same meaning is expected to still
    score highly, per how this curriculum's TOC entries and in-book headings actually
    relate to each other."""
    na, nb = _normalize_for_match(a), _normalize_for_match(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if len(na) >= 4 and len(nb) >= 4 and (na in nb or nb in na):
        return 0.92
    return SequenceMatcher(None, _token_sort(na), _token_sort(nb)).ratio()


def is_toc_heading_line(line: str) -> bool:
    """True if `line` is itself the TOC's own section heading (e.g. "Contents" /
    "الفهرس"), the generic signal used to locate where a TOC section starts."""
    stripped = (line or "").strip(" \t|-#:")
    return bool(_TOC_TITLE_RE.match(stripped))


def parse_toc_entry_line(line: str) -> tuple[str, int | None] | None:
    """Parse a single TOC line into (title, page_number).

    Handles either page-number placement ("Title .... 12" or "12 .... Title") and any of
    the common leader-dot styles, or no leader at all (just whitespace). Returns None for
    lines that don't carry a trailing/leading page number at all — those are either a
    continuation of the previous entry's title or not a TOC line, and dropping them is
    safer than guessing an entry that has nothing to anchor it to a page.
    """
    stripped = (line or "").strip()
    if not stripped:
        return None
    collapsed = _LEADER_RUN_RE.sub(" ", stripped)
    collapsed = re.sub(r"\s+", " ", collapsed).strip(" .")
    if not collapsed:
        return None
    trailing = re.match(r"^(?P<title>.+?)\s+(?P<page>\d{1,4})$", collapsed)
    if trailing:
        title = trailing.group("title").strip(" .-")
        if title:
            return title, int(trailing.group("page"))
    leading = re.match(r"^(?P<page>\d{1,4})\s+(?P<title>.+)$", collapsed)
    if leading:
        title = leading.group("title").strip(" .-")
        if title:
            return title, int(leading.group("page"))
    return None


def _keyword_level(title: str) -> int | None:
    if _UNIT_WORD_RE.search(title):
        return 1
    if _LESSON_WORD_RE.search(title):
        return 2
    return None


def parse_toc_entries(text: str, *, max_lines: int = 400) -> list[TocEntry]:
    """Parse every TOC-shaped line out of `text` (normally just the TOC page(s)' own
    text) into `TocEntry` rows, in the order they appear.

    Level classification is two-stage, because most curricula's TOC only spells out the
    word "Unit"/"الوحدة" on the chapter-level entry — a lesson is typically just its own
    plain title with no "Lesson"/"الدرس" keyword at all (verified against this book's real
    TOC: "ما هي المعلومات ؟" carries no keyword, yet it is unambiguously a lesson entry
    under "الوحدة الأولى" right above it). So: (1) a keyword match is trusted outright;
    (2) failing that, any entry that appears *after* the first recognised unit/chapter
    entry is inferred to be a lesson under it, since that's the only structural position
    that wording alone leaves it in; (3) entries before any unit is seen (front matter —
    preface, introduction) are left unclassified rather than guessed.
    """
    entries: list[TocEntry] = []
    seen_unit = False
    for raw_line in (text or "").splitlines()[:max_lines]:
        parsed = parse_toc_entry_line(raw_line)
        if not parsed:
            continue
        title, page = parsed
        level = _keyword_level(title)
        if level == 1:
            seen_unit = True
        elif level is None and seen_unit:
            level = 2
        entries.append(
            TocEntry(
                title=title,
                normalized=_normalize_for_match(title),
                level=level,
                page=page,
            )
        )
    return entries


def find_toc_section(pages: list[str]) -> str | None:
    """Given the document's pages of text (in order), return the concatenated text of the
    page(s) that make up the table of contents, or None if no TOC page is recognisable.

    A TOC page is identified generically: one of its own first few lines is a bare
    "Contents"/"الفهرس"-style heading. Curricula routinely spread the TOC across two or
    three consecutive pages with no repeated heading on the later ones, so once the start
    page is found, following pages are included as long as they keep looking like TOC
    lines (a majority of their non-empty lines parse as a title+page-number entry).
    """
    start = None
    for idx, page_text in enumerate(pages):
        lines = [ln for ln in (page_text or "").splitlines() if ln.strip()]
        if any(is_toc_heading_line(ln) for ln in lines[:5]):
            start = idx
            break
    if start is None:
        return None

    collected = [pages[start]]
    for page_text in pages[start + 1 :]:
        lines = [ln for ln in (page_text or "").splitlines() if ln.strip()]
        if not lines:
            break
        hits = sum(1 for ln in lines if parse_toc_entry_line(ln) is not None)
        if hits < max(2, len(lines) // 2):
            break
        collected.append(page_text)
    return "\n".join(collected)


class TocIndex:
    """A book's own table of contents, held for fuzzy matching against headings found
    while walking the document. Matching is assistive, never authoritative: it never
    overwrites the in-book wording of a heading, and any explicit label ("Chapter: ...")
    or unambiguous structural marker ("الوحدة الأولى") found in the body still wins over
    whatever the TOC says. It only helps in the cases the body text alone leaves genuinely
    ambiguous — classifying a numbered heading's chapter/lesson level, and recognising a
    heading that carries no numbering or label at all.
    """

    def __init__(self, entries: list[TocEntry]) -> None:
        self.entries = entries

    @classmethod
    def build(cls, pages: list[str]) -> "TocIndex | None":
        section_text = find_toc_section(pages)
        if not section_text:
            return None
        entries = parse_toc_entries(section_text)
        return cls(entries) if entries else None

    @classmethod
    def build_from_text(cls, text: str) -> "TocIndex | None":
        """Convenience for callers that only have one flat text blob rather than a
        page list — splits on blank-line-delimited pages as a best effort."""
        pages = re.split(r"\n\s*\n(?=\S)", text or "")
        return cls.build(pages) if len(pages) > 1 else cls.build([text or ""])

    def match(self, title: str, *, min_ratio: float = 0.72) -> tuple[TocEntry, float] | None:
        """Best-scoring TOC entry for `title`, or None if nothing clears `min_ratio`."""
        if not title or not self.entries:
            return None
        best: tuple[TocEntry, float] | None = None
        for entry in self.entries:
            score = similarity(title, entry.title)
            if score >= min_ratio and (best is None or score > best[1]):
                best = (entry, score)
        return best

    def classify_level(self, title: str, *, min_ratio: float = 0.72) -> int | None:
        """Like `match`, but only returns a level when the matched entry's wording
        actually gives one (see `_classify_level`) — used to correct chapter-vs-lesson
        classification for a heading whose own numbering depth is ambiguous."""
        found = self.match(title, min_ratio=min_ratio)
        return found[0].level if found else None

    def to_debug_list(self) -> list[dict[str, Any]]:
        return [
            {"title": e.title, "level": e.level, "page": e.page}
            for e in self.entries
        ]
