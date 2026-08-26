from src.application.curriculum_structure import (
    grades_from_rows,
    structure_from_rows,
    subjects_from_rows,
)

ROWS = [
    {"subject": "Math", "grade": "10", "chapter": "Algebra", "lesson": "Equations", "page": 5},
    {"subject": "Math", "grade": "10", "chapter": "Algebra", "lesson": "Inequalities", "page": 8},
    {"subject": "Math", "grade": "10", "chapter": "Geometry", "lesson": "Angles", "page": 20},
    # Duplicate + out-of-order page: must not create a duplicate lesson, and page order wins.
    {"subject": "Math", "grade": "10", "chapter": "Algebra", "lesson": "Equations", "page": 6},
    {"subject": "Math", "grade": "11", "chapter": "Calculus", "lesson": "Limits", "page": 2},
    {"subject": "تكنولوجيا المعلومات", "grade": "الأول", "chapter": "الوحدة الأولى", "lesson": "مقدمة", "page": 1},
    {"subject": None, "grade": None, "chapter": None, "lesson": None, "page": 1},
]


def test_subjects_from_rows_lists_each_subject_with_its_grades():
    result = subjects_from_rows(ROWS)
    by_subject = {r["subject"]: r["grades"] for r in result}
    assert by_subject["Math"] == ["10", "11"]
    assert by_subject["تكنولوجيا المعلومات"] == ["الأول"]
    assert None not in by_subject


def test_grades_from_rows_filters_to_subject():
    math_rows = [r for r in ROWS if r.get("subject") == "Math"]
    assert grades_from_rows(math_rows) == ["10", "11"]


def test_structure_from_rows_dedupes_and_orders_by_page():
    grade10 = [r for r in ROWS if r.get("subject") == "Math" and r.get("grade") == "10"]
    structure = structure_from_rows(grade10)
    assert structure == [
        {"chapter": "Algebra", "lessons": ["Equations", "Inequalities"]},
        {"chapter": "Geometry", "lessons": ["Angles"]},
    ]


def test_structure_from_rows_empty_when_no_match():
    assert structure_from_rows([]) == []
