from __future__ import annotations

import re
from typing import Any

from src.infrastructure.config import get_settings


def _clean(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip(" .:-–—#")


def _terms(text: str) -> list[str]:
    terms = []
    for m in re.finditer(r"\*\*([^*]{2,100})\*\*", text or ""):
        t = _clean(m.group(1))
        if t and t not in terms:
            terms.append(t)
    return terms[:4]


def generate_questions(chunks: list[dict[str, Any]]) -> dict[str, list[str]]:
    max_q = max(1, get_settings().max_questions_per_chunk)
    out: dict[str, list[str]] = {}
    for chunk in chunks:
        cid = str(chunk["chunk_id"])
        text = str(chunk.get("text") or "")
        heading = _clean(str(chunk.get("heading") or ""))
        qs: list[str] = []
        for term in _terms(text):
            qs += [f"ما هو {term}؟", f"ما المقصود بـ {term}؟"]
        if heading:
            qs += [f"ما الذي يشرحه {heading}؟"]
        # Lightweight grounded question candidates: no external LLM required.
        m = re.search(r"(.{20,180}?)(?:هو|هي|تعني|يعني|يسمى|:)", text)
        if m:
            qs.append(f"ما المقصود بـ {heading or 'هذا المفهوم'}؟")
        out[cid] = list(dict.fromkeys(qs))[:max_q]
    return out
