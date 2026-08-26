# Fixes in this session

## 1. `subject` extraction now works for English books too (was Arabic-only)

**Root cause:** `_subject_from_text()` had exactly one content pattern —
`مقدمة في X للصف Y` — plus a strict "Subject:" label match. Any book whose cover doesn't
use that exact Arabic phrasing or an explicit label (i.e. every English book, and any
Arabic book that phrases its cover differently) fell straight to `null`. This wasn't a
parsing bug so much as a coverage gap: the extractor only ever recognized one book's wording.

**Fix** (`src/services/document_metadata.py`):
- Added the English mirror pattern: `"Introduction to X for Grade/Secondary/Class/Level N"`.
- Added a lower-confidence bilingual fallback for covers that name the subject next to a
  grade with no "Introduction to" / "مقدمة في" wording at all (`"X — Grade N"`,
  `"Grade N X"`, and the Arabic `"X الصف Y"` equivalent) — tagged
  `document_pattern_weak` at confidence 0.72 so callers can tell it apart from the
  higher-confidence 0.94 pattern match.
- None of this is tied to any specific book's title/subject text — it's wording-pattern
  matching, so it applies uniformly to any Arabic or English curriculum file.

## 2. Ministry/publisher letterhead no longer leaks into `document_title` or `subject`

**Root cause:** cover pages routinely have a ministry/publisher/copyright line positioned
above or right next to the real title. `_title_from_opening()`'s fallback just took the
first non-generic-looking line in reading order — with no way to distinguish "real title"
from "letterhead sitting above it" — which is what produced
`document_title: "GPS للطبع والنشر والتوزيع MINISTRY OF EDUCATION AND TECHNICAL EDUCATION..."`.

**Fix:** added a generic (not book-specific) boilerplate filter —
`ministry of education / copyright / ISBN / published by / وزارة التربية / جميع الحقوق
محفوظة / للطبع والنشر`, etc. — applied to both the title-line fallback and the subject
patterns, so a letterhead line can never win either field regardless of where it sits on
the page.

## 3. PDF text-order bug in the PyMuPDF (`fitz`) path: multi-column pages were interleaved

This is the one the earlier investigation (pasted into this session) flagged as a
hypothesis but couldn't verify — `fitz` isn't installed in this sandbox either, so it's
still not verified against a real PDF, but the bug is real and reproducible against
synthetic line boxes (see the new tests).

**Root cause:** `_load_pdf_with_pymupdf()` sorted every line on a page by raw `(y, x)`
regardless of layout. For a genuine two-column page, that produces `col1-row1, col2-row1,
col1-row2, col2-row2, ...` instead of reading column 1 fully before column 2 — every
paragraph on a two-column page came out with column 1 and column 2 sentences interleaved
line-by-line. This affects body text generally, not just the cover/title page, and would
degrade chunk quality and metadata-pattern matching anywhere the source PDF uses columns.

**Fix:** new `_order_page_lines()` (pure function, unit-tested without needing `fitz`
installed): clusters lines into left-to-right column bands only when there's a wide,
consistent gap in x-position with enough lines on each side to be a real column — a stray
one-line logo/stamp box doesn't qualify, so it still falls through to the previous flat
sort (unchanged behavior for ordinary cover/single-column pages, so this shouldn't regress
anything that already worked). Genuine two-column pages now read column-by-column.

## 4. New endpoint: `GET /api/rag/structure` — discover subjects/grades/chapters/lessons

Addressed directly: a downstream caller can't send a `chapter`/`lesson` filter to
`/api/rag/response` without already knowing the *exact* stored spelling, and that spelling
varies book to book, language to language. `/api/rag/structure` is the lookup for that,
walked progressively:

- `GET /api/rag/structure` → every indexed subject, with the grades indexed under each.
- `GET /api/rag/structure?subject=X` → every grade indexed under that subject.
- `GET /api/rag/structure?subject=X&grade=Y` → the chapter → lessons tree for that
  subject+grade, in the order the chapters/lessons appear in the book (sorted by page,
  not by whatever order the vector store happens to return).

Implementation:
- `VectorStore.get_all_metadata(filters)` — plain metadata listing (chroma `.get()` /
  local-JSON filter), no embeddings or ranking involved.
- `src/services/curriculum_structure.py` — pure aggregation logic (`subjects_from_rows`,
  `grades_from_rows`, `structure_from_rows`), unit-tested directly with synthetic rows.
- `CurriculumStructureResponse` schema + the endpoint in `app.py`.

This is generic over any indexed book in any language — it only reads whatever
`subject`/`grade`/`chapter`/`lesson`/`page` values ingestion already wrote to chunk
metadata; it doesn't hard-code any curriculum's names.

## 5. Minor cleanup
- `src/services/metadata.py` had `split_heading_path()` and `classify_content_type()` each
  defined twice (the second silently shadowed the first at import time — dead code, not a
  behavior bug, but confusing to read/maintain). Removed the dead first copies.

## What I could and couldn't verify here
- Everything above except item 3 is tested against real extracted text/synthetic data in
  this sandbox and passes (`tests/unit/test_document_metadata.py`,
  `tests/unit/test_document_loader_ordering.py`, `tests/unit/test_curriculum_structure.py`
  — 14/14, plus the pre-existing `test_metadata.py` / `test_content_classification.py`,
  8/8, all still green after the dead-code cleanup).
- I still don't have `fitz`/`pydantic`/`fastapi`/`chromadb` installed here (no network), so
  item 3's column-clustering logic is verified in isolation (pure function, synthetic
  boxes) but not against an actual PDF, and I could not exercise `/api/rag/structure`
  end-to-end through FastAPI. Please run `pytest -q` in your own environment and, ideally,
  re-ingest one known two-column PDF and one English-cover PDF to confirm both fixes hold
  against real extracted text before deploying.
- Re-ingest is still required for anything indexed before this fix (same caveat as last
  session) — this patch doesn't rewrite already-indexed metadata, only what's extracted on
  the next ingest.

## Open question for you (from your message)
You asked whether the chapter/lesson discovery endpoint is worth building — I think yes,
for the reason you gave: an external caller genuinely can't guess your exact stored
chapter/lesson strings, especially across languages. I built it as a progressive
subject → grade → chapter/lesson walk rather than requiring subject+grade up front, so a
caller that doesn't even know your exact subject spelling can still discover it. Let me
know if you'd rather it return something else (e.g. also including `lesson_context`-ready
objects instead of plain strings), and I can adjust.
