from src.application.metadata import classify_content_type


def test_classification_is_generic_and_clean():
    assert classify_content_type("اختر المصطلح الأنسب الذي يملأ الفراغ") == "exercise"
    assert classify_content_type("مثال: 2 + 2 = 4") == "example"
    assert classify_content_type("تعريف الشبكة: نظام يربط الأجهزة") == "definition"
    assert classify_content_type("شرح عام للمفهوم") == "paragraph"
