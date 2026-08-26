from src.application.generation import generate_with_ollama
from src.infrastructure.config import get_settings


def test_extractive_fallback_when_model_not_configured():
    settings = get_settings()
    settings.ollama_model = ""
    settings.allow_extractive_fallback = True
    # NOTE: updated 2026-08-25. The old call passed the pre-formatted, multi-block
    # `context` string (with "[Evidence N]/Source:/Page:/..." labels) and expected the
    # fallback to just echo it back. generate_with_ollama's fallback path was
    # deliberately changed to take the actual retrieved chunk dicts (`results`) instead
    # and read `raw_text` from them — dumping the full labelled context string verbatim
    # into a student-facing answer read like raw debug output. `context` here is now
    # just what would be sent to the LLM if it *were* configured; it's irrelevant to
    # the fallback path, so this test must supply `results` to exercise it correctly.
    results = [{"raw_text": "AI is a technology."}]
    result = generate_with_ollama("What is AI?", "[Evidence 1]\nAI is a technology.", [], results=results)
    assert "AI is a technology" in result.answer
    assert result.status == "answered"
    assert result.self_reported is False


def test_extractive_fallback_with_no_results_is_insufficient_evidence():
    settings = get_settings()
    settings.ollama_model = ""
    settings.allow_extractive_fallback = True
    result = generate_with_ollama("What is AI?", "[Evidence 1]\nAI is a technology.", [], results=[])
    assert result.status == "insufficient_evidence"
    assert result.self_reported is False
