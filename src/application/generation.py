from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any
import requests

from src.infrastructure.ar_text import extract_core_tokens
from src.infrastructure.config import get_settings

logger = logging.getLogger(__name__)

_STATUS_INSTRUCTION = (
    "\n\nRespond with STRICT JSON only, no markdown fences, no extra text, matching exactly this shape: "
    '{"status": "answered" | "insufficient_evidence", "answer": "..."}. '
    "Set status to \"insufficient_evidence\" and leave answer explaining that briefly whenever the Evidence "
    "does not actually contain what's needed to answer — do not set status to \"answered\" just because you "
    "produced some text."
)

_NO_CITATION_MARKERS_INSTRUCTION = (
    "\n\nWrite the \"answer\" field as plain, clean prose a student can read directly. "
    "Do NOT include citation markers, footnote-style tags, or reference brackets of any kind "
    "(for example 【Evidence 1†L2-L4】, [1], (Evidence 2), or similar) — do not invent or copy any "
    "such notation, even if it appears in training-style text you've seen before. If you want to "
    "point to where something came from, say so in ordinary words (e.g. \"as explained in the "
    "lesson\"), not with bracketed or symbolic markers."
)


@dataclass
class GenerationResult:
    answer: str
    status: str  # "answered" | "insufficient_evidence"
    self_reported: bool  # True if this came from a parsed structured model response


_CITATION_MARKER_PATTERN = re.compile(
    r"【[^】]{0,80}】"          # 【Evidence 1†L2-L4】 style CJK-bracket markers
    r"|\[(?:evidence|source)\s*\d+[^\]]{0,40}\]"  # [Evidence 2], [source 3: ...]
    r"|\((?:evidence|source)\s*\d+[^)]{0,40}\)",  # (Evidence 2), (source 3)
    re.IGNORECASE,
)


def _strip_citation_markers(text: str) -> str:
    cleaned = _CITATION_MARKER_PATTERN.sub("", text)
    cleaned = re.sub(r"[ \t]+([.,؛،])", r"\1", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


def _parse_structured(raw: str) -> GenerationResult | None:
    text = raw.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    if not isinstance(data, dict) or "answer" not in data:
        return None
    status = str(data.get("status", "")).strip().lower()
    if status not in ("answered", "insufficient_evidence"):
        status = "answered" if str(data.get("answer", "")).strip() else "insufficient_evidence"
    answer = _strip_citation_markers(str(data.get("answer", "")).strip())
    return GenerationResult(answer=answer, status=status, self_reported=True)


def build_context(results: list[dict[str, Any]], max_chars: int | None = None) -> str:
    settings = get_settings()
    budget = max_chars or settings.max_context_chars
    blocks: list[str] = []
    used = 0
    for i, item in enumerate(results, 1):
        meta = item.get("metadata", {})
        block = (
            f"[Evidence {i}]\n"
            f"Source: {meta.get('source', 'unknown')}\n"
            f"Page: {meta.get('page', 'unknown')}\n"
            f"Section: {meta.get('heading', 'unknown')}\n"
            f"Text: {item.get('raw_text') or item.get('document', '')}"
        )
        if used + len(block) > budget:
            remaining = budget - used
            if remaining > 250:
                blocks.append(block[:remaining])
            break
        blocks.append(block)
        used += len(block)
    return "\n\n".join(blocks)


def _extractive_fallback(results: list[dict[str, Any]], query: str = "") -> GenerationResult:
    if not results or not str(results[0].get("raw_text") or "").strip():
        return GenerationResult(
            answer="المعلومات المسترجعة من المحتوى غير كافية للإجابة على السؤال بشكل موثوق.",
            status="insufficient_evidence",
            self_reported=False,
        )
    
    # Check concept relevance before dumping raw text
    if query:
        q_tokens = extract_core_tokens(query)
        doc_tokens = extract_core_tokens(str(results[0].get("raw_text") or ""))
        if q_tokens and len(q_tokens.intersection(doc_tokens)) == 0 and float(results[0].get("reranker_score", 0)) < 0.40:
            return GenerationResult(
                answer="لا تتوفر في الأدلة المسترجعة معلومات كافية للإجابة على هذا السؤال بشكل موثوق.",
                status="insufficient_evidence",
                self_reported=False,
            )

    text = "بناءً على الجزء المسترجع من الدرس:\n\n" + str(results[0].get("raw_text") or "").strip()
    return GenerationResult(answer=text, status="answered", self_reported=False)


def _generate_with_openrouter(query: str, context: str, history: list[dict[str, str]], settings: Any) -> GenerationResult:
    if not getattr(settings, "openrouter_api_key", None):
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
        
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert curriculum tutor. Answer the student's question strictly from the provided curriculum Evidence. "
                "If the Evidence does not contain the answer, explicitly state that it is not covered. "
                "Never invent facts or hallucinate formulas outside the Evidence. Always reply in the language of the question."
                + _STATUS_INSTRUCTION
                + _NO_CITATION_MARKERS_INSTRUCTION
            ),
        }
    ]
    for turn in history[-settings.max_session_turns:]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    messages.append({"role": "user", "content": f"Evidence:\n{context}\n\nQuestion:\n{query}"})

    payload = {
        "model": "google/gemini-2.5-flash" if "gemini" in str(getattr(settings, "groq_model", "")) else "meta-llama/llama-3.3-70b-instruct",
        "temperature": 0.0,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    url = f"{str(getattr(settings, 'openrouter_base_url', 'https://openrouter.ai/api/v1')).rstrip('/')}/chat/completions"
    resp = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "curriculum-rag",
        },
        timeout=settings.ollama_timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    raw = str(data["choices"][0]["message"]["content"]).strip()
    parsed = _parse_structured(raw)
    if parsed is not None:
        return parsed
    raw = _strip_citation_markers(raw)
    return GenerationResult(answer=raw, status="answered" if raw else "insufficient_evidence", self_reported=False)


def _generate_with_groq(query: str, context: str, history: list[dict[str, str]], settings: Any) -> GenerationResult:
    if not getattr(settings, "groq_api_key", None):
        raise RuntimeError("GROQ_API_KEY is not configured")
        
    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert curriculum tutor. Answer the student's question strictly from the provided curriculum Evidence. "
                "If the Evidence does not contain the answer, explicitly state that it is not covered. "
                "Never invent facts or hallucinate formulas outside the Evidence. Always reply in the language of the question."
                + _STATUS_INSTRUCTION
                + _NO_CITATION_MARKERS_INSTRUCTION
            ),
        }
    ]
    for turn in history[-settings.max_session_turns:]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    messages.append({"role": "user", "content": f"Evidence:\n{context}\n\nQuestion:\n{query}"})

    payload = {
        "model": settings.groq_model,
        "temperature": 0.0,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }
    resp = requests.post(
        settings.groq_base_url.rstrip("/") + "/chat/completions",
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.groq_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "general-curriculum-rag/1.0 (+https://groq.com)",
        },
        timeout=settings.ollama_timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    raw = str(data["choices"][0]["message"]["content"]).strip()
    parsed = _parse_structured(raw)
    if parsed is not None:
        return parsed
    raw = _strip_citation_markers(raw)
    return GenerationResult(answer=raw, status="answered" if raw else "insufficient_evidence", self_reported=False)


def generate_with_ollama(query: str, context: str, history: list[dict[str, str]], results: list[dict[str, Any]] | None = None) -> GenerationResult:
    settings = get_settings()
    if not settings.ollama_model:
        if settings.allow_extractive_fallback:
            return _extractive_fallback(results or [], query)
        raise RuntimeError("OLLAMA_MODEL is not configured")
    messages = [
        {
            "role": "system",
            "content": (
                "أنت مدرس مساعد داخل منصة تعليمية. أجب اعتمادًا فقط على Evidence الموجود. "
                "لو الإجابة غير موجودة في Evidence، قل بوضوح إن المعلومات غير كافية. "
                "لا تخترع معلومات. أجب بنفس لغة السؤال. لا تعتبر Conversation History دليلًا علميًا؛ استخدمها فقط لفهم المتابعة. "
                "اكتب الإجابة كنص عادي واضح للطالب، من غير أي رموز أو علامات استشهاد أو أرقام مراجع بين قوسين "
                "(زي 【Evidence 1†L2-L4】 أو [1] أو ما شابه). "
                + _STATUS_INSTRUCTION
                + _NO_CITATION_MARKERS_INSTRUCTION
            ),
        }
    ]
    for turn in history[-settings.max_session_turns:]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": turn["assistant"]})
    messages.append({"role": "user", "content": f"Evidence:\n{context}\n\nQuestion:\n{query}"})
    payload = json.dumps({"model": settings.ollama_model, "messages": messages, "stream": False, "keep_alive": "5m", "format": "json"}, ensure_ascii=False).encode("utf-8")
    url = settings.ollama_base_url.rstrip("/") + "/api/chat"
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=settings.ollama_timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        raw = str(data.get("message", {}).get("content") or "").strip()
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        if settings.allow_extractive_fallback:
            return _extractive_fallback(results or [], query)
        raise RuntimeError(f"Ollama generation failed: {exc}") from exc
    parsed = _parse_structured(raw)
    if parsed is not None:
        return parsed
    raw = _strip_citation_markers(raw)
    return GenerationResult(answer=raw, status="answered" if raw else "insufficient_evidence", self_reported=False)


def generate_with_provider(query: str, context: str, history: list[dict[str, str]], results: list[dict[str, Any]] | None = None) -> GenerationResult:
    settings = get_settings()
    backend = str(settings.generation_backend).casefold()

    if backend == "ollama":
        return generate_with_ollama(query, context, history, results)

    # Groq generation
    if backend == "groq" and getattr(settings, "groq_api_key", None):
        try:
            return _generate_with_groq(query, context, history, settings)
        except Exception as exc:
            logger.warning("Groq generation failed, attempting OpenRouter fallback: %s", exc)

    # OpenRouter generation (fallback or primary)
    if getattr(settings, "openrouter_api_key", None):
        try:
            return _generate_with_openrouter(query, context, history, settings)
        except Exception as exc:
            logger.warning("OpenRouter generation failed: %s", exc)

    # Ollama fallback if configured
    if getattr(settings, "ollama_model", None):
        try:
            return generate_with_ollama(query, context, history, results)
        except Exception as exc:
            logger.warning("Ollama generation failed: %s", exc)

    # Extractive fallback if enabled
    if settings.allow_extractive_fallback:
        return _extractive_fallback(results or [], query)

    raise RuntimeError(f"Generation failed: no configured LLM backend available for {settings.generation_backend}")
