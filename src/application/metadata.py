from __future__ import annotations

import re
import unicodedata
from typing import Any

# Explicit metadata fields are intentionally generic.  No subject/curriculum-specific values
# are hard-coded here.
EXPLICIT_FIELDS = ("subject", "grade")
HIERARCHY_FIELDS = ("chapter", "lesson", "section", "topic")
STRUCTURE_FIELDS = ("heading", "heading_level", "heading_path")

LABEL_PATTERNS: dict[str, tuple[str, ...]] = {
    "subject": ("subject", "discipline", "course", "المادة", "مادة"),
    "grade": ("grade", "class", "level", "year", "الصف", "صف", "المرحلة", "المستوى"),
    "chapter": ("chapter", "unit", "module", "الفصل", "الوحدة", "الوحدة الدراسية", "المحور"),
    "lesson": ("lesson", "lecture", "lesson title", "الدرس", "المحاضرة"),
    "section": ("section", "part", "subsection", "القسم", "الجزء", "الفرع"),
    "topic": ("topic", "theme", "الموضوع", "المبحث"),
}

EXPLICIT_HEADING_PREFIXES: dict[str, tuple[str, ...]] = {
    "chapter": LABEL_PATTERNS["chapter"],
    "lesson": LABEL_PATTERNS["lesson"],
    "section": LABEL_PATTERNS["section"],
    "topic": LABEL_PATTERNS["topic"],
}

CONTROL_CHARS = "\u0000\u0001\u0002\u0003\u0004\u0005\u0006\u0007\u0008\u000b\u000c\u000e\u000f\u0010\u0011\u0012\u0013\u0014\u0015\u0016\u0017\u0018\u0019\u001a\u001b\u001c\u001d\u001e\u001f"


def clean_optional(value: Any) -> Any:
    """Convert Swagger placeholders and empty values to real None."""
    if value is None:
        return None
    if isinstance(value, str):
        v = value.strip()
        if not v or v.casefold() in {"null", "none", "n/a", "na", "string"}:
            return None
        return v
    return value


def detect_language(text: str) -> str:
    arabic = len(re.findall(r"[\u0600-\u06FF]", text or ""))
    latin = len(re.findall(r"[A-Za-z]", text or ""))
    if arabic and latin:
        # Treat a small number of Latin tokens inside predominantly Arabic text as Arabic.
        if arabic >= 3 * max(latin, 1):
            return "ar"
        return "mixed"
    if arabic:
        return "ar"
    if latin:
        return "en"
    return "unknown"


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    for ch in CONTROL_CHARS:
        text = text.replace(ch, " ")
    for old, new in {
        "\u200f": " ", "\u200e": " ", "\u202a": " ", "\u202b": " ",
        "\u202c": " ", "\u2066": " ", "\u2067": " ", "\u2069": " ", "\ufeff": " ",
    }.items():
        text = text.replace(old, new)
    # Keep content conservative: only repair obvious line-break artifacts and whitespace.
    text = re.sub(r"(?<=[A-Za-z0-9\u0600-\u06FF])\s*\n\s*(?=[A-Za-z0-9\u0600-\u06FF])", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _clean_value(value: Any) -> str | None:
    value = clean_optional(value)
    if value is None:
        return None
    value = str(value).strip(" \t:;-–—|[](){}")
    value = re.sub(r"\s+", " ", value)
    return value or None


def _label_match(line: str) -> tuple[str | None, str | None]:
    stripped = _clean_value(line)
    if not stripped:
        return None, None
    for field, labels in LABEL_PATTERNS.items():
        for label in labels:
            m = re.match(rf"^{re.escape(label)}\s*(?::|=|-|–|—)\s*(.+)$", stripped, flags=re.I)
            if m:
                return field, _clean_value(m.group(1))
    return None, None


def parse_markdown_heading(line: str) -> tuple[int, str] | None:
    s = (line or "").strip()
    m = re.match(r"^(#{1,6})\s+(.+?)\s*$", s)
    if not m:
        return None
    title = _clean_value(m.group(2))
    if not title:
        return None
    return len(m.group(1)), title


def parse_numbered_heading(line: str, *, max_length: int = 180) -> tuple[int, str] | None:
    """Generic numbered heading detection. It records a heading level, not chapter/lesson.

    Accepts both dot-separated ("1.1", "2.3.1") and hyphen-separated ("1-1", "2-1")
    numbering — many Arabic curricula (this one included) number lesson sections with a
    hyphen, not a dot, and the dot-only pattern silently missed every one of them.
    """
    raw_stripped = (line or "").strip()
    # Reject parenthesised enumeration markers like "(1) ..." / "(2) ...". Real headings in
    # this curriculum are written as bare "1-1 ..." / "1.1 ..."; "(N) ..." is the standard
    # convention for a numbered list item *inside* body content (e.g. "(1) تدفق التطور
    # المجتمعي: ..."). _clean_value() strips the leading "(" (it's in its trim set), which
    # otherwise made these look identical to a real level-1 numbered heading and let them
    # stomp on `chapter` via the positional fallback below.
    if raw_stripped.startswith("("):
        return None
    s = _clean_value(line)
    if not s or len(s) > max_length or s.count(" ") > 28:
        return None
    m = re.match(r"^(\d+(?:[.\-]\d+){0,5})[.)\-:]?\s+(.{2,170})$", s)
    if not m:
        return None
    title = _clean_value(m.group(2))
    if not title:
        return None
    # Avoid treating question/list sentences as headings.
    if title.endswith(("?", "؟", "!")) or (title.endswith(".") and len(title) > 50):
        return None
    # A colon inside the "title" is a strong signal this is a definition/enumeration line
    # ("1) تعريف: ...") rather than an actual heading — headings don't carry their own body
    # text on the same line.
    if ":" in title or "：" in title:
        return None
    return len(re.split(r"[.\-]", m.group(1))), title


def parse_bare_number_anchor(line: str, *, max_length: int = 20) -> int | None:
    """Detect a lesson/section number that sits alone on its own line, with the title on
    the following line — e.g. this curriculum's real page-48/49 layout where "1-4" is on
    one line and "الدرس الأول: ..." (or similar) is the next non-empty line.
    parse_numbered_heading() requires the title on the *same* line, so this pattern was
    never registering as a heading at all: the first heading actually captured was
    whatever lettered ('أ.') sub-heading came next, silently promoting a section title to
    stand in for the lesson.

    Deliberately requires a separator ("1-4", "2.3") rather than a bare integer ("48") —
    a lone page number is common and must never be mistaken for a heading anchor.
    """
    s = _clean_value(line)
    if not s or len(s) > max_length:
        return None
    m = re.match(r"^(\d+(?:[.\-]\d+){1,5})$", s)
    if not m:
        return None
    return len(re.split(r"[.\-]", m.group(1)))


_ARABIC_ORDINAL_LETTERS = "أبتثجحخدذرزسشصضطظعغ"


def parse_lettered_heading(line: str, *, max_length: int = 90) -> tuple[int, str] | None:
    """Arabic-letter sub-heading markers ('أ. ', 'ب. ', 'ت. '), a very common second
    heading level under a numbered lesson section in Arabic textbooks (this curriculum
    uses it throughout, e.g. 'أ. البيانات، المعلومات، المعرفة'). detect_heading() had no
    coverage for this convention at all, so every one of these sub-headings was invisible
    to chapter/lesson/heading extraction.

    Kept deliberately strict (short title, no terminal '.', '؟', '!') because the same
    letters are also used for multiple-choice/exercise options ('أ. القاهرة  ب. اإلسكندرية'
    or one option per line) — those are prose answers, not section titles, and must not
    be mistaken for one.
    """
    s = _clean_value(line)
    if not s or len(s) > max_length or s.count(" ") > 12:
        return None
    m = re.match(rf"^([{_ARABIC_ORDINAL_LETTERS}])[.)\-:]\s+(.{{2,80}})$", s)
    if not m:
        return None
    title = _clean_value(m.group(2))
    if not title:
        return None
    if title.endswith(("?", "؟", "!", ".")):
        return None
    return 2, title


def detect_heading(line: str, *, markdown_level: int | None = None, max_length: int = 180) -> tuple[int, str] | None:
    """Detect only structurally explicit headings; ordinary prose is not a heading."""
    parsed = detect_heading_ex(line, markdown_level=markdown_level, max_length=max_length)
    return (parsed[0], parsed[1]) if parsed else None


def detect_heading_ex(
    line: str, *, markdown_level: int | None = None, max_length: int = 180
) -> tuple[int, str, bool] | None:
    """Like detect_heading, but also reports whether the match is "positional-eligible" —
    i.e. whether its level is reliable enough to drive the chapter/lesson/section/topic
    positional fallback in update_structure(). Markdown and numbered headings carry a real,
    consistently-scaled depth (heading level / dot-count), so they are. Lettered headings
    ('أ.', 'ب.') always report level=2 regardless of where they actually sit in the
    document's real hierarchy — that fixed level is fine for cosmetic heading_path display,
    but letting it drive chapter/lesson/section/topic caused a lettered sub-heading (e.g. a
    section under a lesson) to stomp `lesson` itself every time one appeared, since level=2
    happens to also be lesson's positional slot. See update_structure() for how this flag
    is used.
    """
    if markdown_level:
        title = _clean_value(line)
        return (markdown_level, title, True) if title else None
    md = parse_markdown_heading(line)
    if md:
        return (*md, True)
    numbered = parse_numbered_heading(line, max_length=max_length)
    if numbered:
        return (*numbered, True)
    lettered = parse_lettered_heading(line, max_length=max_length)
    if lettered:
        return (*lettered, False)
    return None


def update_structure(state: dict[str, Any], line: str, *, markdown_level: int | None = None, max_length: int = 180) -> bool:
    """Update heading/heading_path and explicit semantic fields only when evidence is clear."""
    changed = False

    # Resolve a bare number anchor left pending by the previous line (see
    # parse_bare_number_anchor): this line is its title. Only consumes the pending anchor
    # if this line isn't itself some other kind of structural marker (label / anchor),
    # so two consecutive bare anchors don't get chained together incorrectly.
    pending_level = state.pop("_pending_anchor_level", None)
    if pending_level is not None:
        stripped = _clean_value(line)
        is_label, _ = _label_match(line)
        if stripped and not is_label and parse_bare_number_anchor(line) is None:
            title = stripped
            prev = state.get("heading")
            path = split_heading_path(state.get("heading_path"))
            path = path[: pending_level - 1] + [title]
            state["heading"] = title
            state["heading_level"] = pending_level
            state["heading_path"] = path
            positional_field = {1: "chapter", 2: "lesson", 3: "section", 4: "topic"}.get(pending_level)
            if positional_field and positional_field not in state.get("_explicit_hierarchy_fields", set()):
                state[positional_field] = title
            return prev != title or state.get("heading_level") != pending_level

    anchor_level = parse_bare_number_anchor(line)
    if anchor_level is not None:
        state["_pending_anchor_level"] = anchor_level
        return False

    field, value = _label_match(line)
    if field and value:
        before = state.get(field)
        state[field] = value
        changed = before != value
        if field in {"chapter", "lesson", "section", "topic"}:
            # Explicit semantic labels are allowed to populate the legacy hierarchy fields,
            # and take priority over the positional fallback below for this field.
            state.setdefault("_explicit_hierarchy_fields", set()).add(field)
            state["heading"] = value
            state["heading_level"] = {"chapter": 1, "lesson": 2, "section": 3, "topic": 4}.get(field, 1)
            path = split_heading_path(state.get("heading_path"))
            level = int(state["heading_level"])
            path = path[: level - 1] + [value]
            state["heading_path"] = path
        return changed

    parsed = detect_heading_ex(line, markdown_level=markdown_level, max_length=max_length)
    if not parsed:
        return False
    level, title, positional_eligible = parsed
    prev = state.get("heading")
    path = split_heading_path(state.get("heading_path"))
    path = path[: level - 1] + [title]
    state["heading"] = title
    state["heading_level"] = level
    state["heading_path"] = path
    # Books that structure content with bare numbered/markdown headings (e.g. "1-1 ...")
    # instead of explicit "Chapter:"/"Lesson:" labels never hit the _label_match branch
    # above, so chapter/lesson/section/topic stayed null even though the hierarchy was
    # captured correctly in heading_path. Fall back to a positional mapping — level 1
    # is the outermost grouping (chapter), level 2 the next (lesson), etc. — so the
    # legacy hierarchy fields stay populated whenever we have depth information at all.
    # An explicit label anywhere in the document still wins for that field, since this
    # only fires when no _label_match was found for the current line.
    if positional_eligible:
        positional_field = {1: "chapter", 2: "lesson", 3: "section", 4: "topic"}.get(level)
        if positional_field and positional_field not in state.get("_explicit_hierarchy_fields", set()):
            state[positional_field] = title
    return prev != title or state.get("heading_level") != level or state.get("heading_path") != path


def strip_private_state(state: dict[str, Any]) -> dict[str, Any]:
    """Drop internal bookkeeping keys (leading underscore, e.g. `_explicit_hierarchy_fields`,
    `_pending_anchor_level`) before a heading-tracking `state` dict is exposed as chunk or
    parent metadata. These keys exist only to make update_structure()'s line-by-line
    decisions correctly; they must never reach storage — `_explicit_hierarchy_fields` in
    particular is a python `set`, which is not JSON-serializable and crashes
    VectorStore.upsert_parents() the moment any explicit "Chapter:"/"Lesson:" label appears
    in the source document.
    """
    return {k: v for k, v in state.items() if not str(k).startswith("_")}


def split_heading_path(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [p.strip() for p in str(value).split(" > ") if p.strip()]


def classify_content_type(text: str, heading: str | None = None) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    if heading and t == heading.strip():
        return "section"
    if re.search(r"(?:اختر|أجب|أكمل|املأ|تمرين|تحدى معلوماتك|جرب بنفسك|exercise|question|fill in|choose|answer)", t, flags=re.I):
        return "exercise"
    if re.search(r"(?:مثال|example)", t, flags=re.I):
        return "example"
    if re.search(r"(?:تعريف|definition|يعرف|تعني|يسمى)", t, flags=re.I):
        return "definition"
    # Markdown/pipe tables and key/value rows are table-like/structured content.
    if "|" in t and t.count("|") >= 2:
        return "table"
    return "paragraph"

def extract_hierarchy(text: str, seed: dict[str, Any] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {k: None for k in (*EXPLICIT_FIELDS, *HIERARCHY_FIELDS)}
    out.update({"heading": None, "heading_level": None, "heading_path": None})
    if seed:
        for key, value in seed.items():
            if key in out and clean_optional(value) is not None:
                out[key] = clean_optional(value)
            elif key in STRUCTURE_FIELDS and clean_optional(value) is not None:
                out[key] = value
    state = dict(out)
    for raw_line in (text or "").splitlines():
        line = re.sub(r"\s+", " ", raw_line.strip())
        if line:
            update_structure(state, line)
    return strip_private_state(state)


def parse_filename_metadata(filename: str) -> dict[str, Any]:
    """Only parse explicit markers; never infer subject/grade from arbitrary filename tokens."""
    name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    stem = re.sub(r"\.[A-Za-z0-9]+$", "", name).strip()
    out: dict[str, Any] = {}
    lang = re.search(r"(?:^|[_\- ])(?:lang|language|lng)[_\- ]?(ar|ara|arabic|en|eng|english)(?:$|[_\- ])", stem, re.I)
    if lang:
        code = lang.group(1).casefold()
        out["language"] = "ar" if code in {"ar", "ara", "arabic"} else "en"
    grade = re.search(r"(?:^|[_\- ])(?:grade|class|level|year)[_\- ]?([^_\-]+?)(?=$|[_\- ])", stem, re.I)
    if grade:
        out["grade"] = _clean_value(grade.group(1))
    return {k: v for k, v in out.items() if clean_optional(v) is not None}


def looks_like_heading(line: str, **_: Any) -> bool:
    return detect_heading(line) is not None
