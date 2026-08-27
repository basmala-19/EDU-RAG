from __future__ import annotations

from typing import Any

from src.features.rag.application.metadata import clean_optional


def _norm(value: Any) -> str | None:
    value = clean_optional(value)
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def _sort_key(row: dict[str, Any]) -> tuple[int, float]:
    """Order chunks the way they appear in the source file, not however the store returns
    them (chromadb's `.get()` order is not guaranteed to follow document order)."""
    page = row.get("page")
    if isinstance(page, (int, float)):
        return (0, float(page))
    return (1, 0.0)


def subjects_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Distinct subjects actually indexed, each with the grades indexed under it."""
    by_subject: dict[str, set[str]] = {}
    for row in rows:
        subject = _norm(row.get("subject"))
        if not subject:
            continue
        grade = _norm(row.get("grade"))
        bucket = by_subject.setdefault(subject, set())
        if grade:
            bucket.add(grade)
    return [{"subject": s, "grades": sorted(grades)} for s, grades in sorted(by_subject.items())]


def grades_from_rows(rows: list[dict[str, Any]]) -> list[str]:
    grades = {g for g in (_norm(r.get("grade")) for r in rows) if g}
    return sorted(grades)


def structure_from_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chapter -> lessons tree for rows already filtered to one subject+grade.

    Rows are sorted by page first so chapter/lesson order follows the book, not whatever
    order the underlying store happens to return.
    """
    ordered = sorted(rows, key=_sort_key)
    chapters: dict[str, list[str]] = {}
    chapter_order: list[str] = []
    for row in ordered:
        chapter = _norm(row.get("chapter"))
        if not chapter:
            continue
        lesson = _norm(row.get("lesson"))
        if chapter not in chapters:
            chapters[chapter] = []
            chapter_order.append(chapter)
        if lesson and lesson not in chapters[chapter]:
            chapters[chapter].append(lesson)
    return [{"chapter": c, "lessons": chapters[c]} for c in chapter_order]


class CurriculumStructureService:
    """Discovery for /api/rag/structure: subjects -> grades -> chapters -> lessons,
    driven entirely by what's actually indexed. Works for any book, any language —
    it never hard-codes a subject/grade/chapter name."""

    def __init__(self, store: Any) -> None:
        self.store = store

    def list_subjects(self) -> list[dict[str, Any]]:
        return subjects_from_rows(self.store.get_all_metadata({}))

    def list_grades(self, subject: str) -> list[str]:
        return grades_from_rows(self.store.get_all_metadata({"subject": subject}))

    def list_structure(self, subject: str, grade: str) -> list[dict[str, Any]]:
        return structure_from_rows(self.store.get_all_metadata({"subject": subject, "grade": grade}))
