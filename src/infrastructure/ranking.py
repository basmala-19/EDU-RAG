from __future__ import annotations

import json
import math
import os
import re
from typing import Any
import requests

from src.infrastructure.ar_text import extract_core_tokens, normalize_token
from src.infrastructure.config import Settings, get_settings


def _tokens(text: str) -> set[str]:
    return extract_core_tokens(text)


def _get_distance(item: dict[str, Any]) -> float | None:
    for k in ("distance", "dist", "_distance"):
        if k in item and item[k] is not None:
            try:
                return float(item[k])
            except (ValueError, TypeError):
                pass
    meta = item.get("metadata", {})
    if isinstance(meta, dict):
        for k in ("distance", "dist", "_distance"):
            if k in meta and meta[k] is not None:
                try:
                    return float(meta[k])
                except (ValueError, TypeError):
                    pass
    return None


def _norm_rrf(rrf: float, primary_anchor: float) -> float:
    anchor = max(primary_anchor, 0.001)
    scaled = (rrf / anchor) * 0.95
    return min(1.0, max(0.0, scaled))


def _get_reranker(model_name: str, device: str) -> Any:
    global _LOCAL_CROSS_ENCODER
    if _LOCAL_CROSS_ENCODER is None:
        from sentence_transformers import CrossEncoder
        _LOCAL_CROSS_ENCODER = CrossEncoder(model_name, device=device)
    return _LOCAL_CROSS_ENCODER


_LOCAL_CROSS_ENCODER = None


def _rerank_with_openrouter(query: str, candidates: list[dict[str, Any]], settings: Any) -> None:
    if not getattr(settings, "openrouter_api_key", None):
        raise RuntimeError("OPENROUTER_API_KEY is not configured")
        
    url = f"{str(getattr(settings, 'openrouter_base_url', 'https://openrouter.ai/api/v1')).rstrip('/')}/rerank"
    payload = {
        "model": getattr(settings, "reranker_model", "cohere/rerank-v3.5"),
        "query": query,
        "documents": [str(x.get("document", "")) for x in candidates],
        "top_n": len(candidates),
    }
    timeout = getattr(settings, "openrouter_timeout", 15)
    resp = requests.post(
        url,
        json=payload,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost",
            "X-Title": "curriculum-rag",
        },
        timeout=timeout,
    )
    if resp is not None and hasattr(resp, "json"):
        res = resp.json()
        results = res.get("results", [])
        for r in results:
            idx = int(r["index"])
            score = float(r["relevance_score"])
            candidates[idx]["reranker_score"] = min(1.0, max(0.0, score))


def rerank_and_dedup(
    candidates: list[dict[str, Any]],
    top_k: int = 5,
    query: str = "",
    settings: Settings | None = None,
) -> list[dict[str, Any]]:
    """Deduplicate candidate chunks and compute calibrated ranking scores."""
    cfg = settings or get_settings()
    if not candidates:
        return []

    q = _tokens(query) if query else set()
    q_norm = normalize_token(query) if query else ""
    definition_q = bool(re.search(r"\b(ما هو|ما هي|عرف|المقصود ب|ما المقصود|ماهو|ماهي|معنى|concept|definition|what is|define)\b", q_norm))

    ranked: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in candidates:
        doc = str(item.get("document", ""))
        meta = item.get("metadata", {})
        dedupe_key = f"{meta.get('file_reference_id', '')}:{meta.get('page', '')}:{doc[:60]}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        doc_tokens = _tokens(doc)
        heading_tokens = _tokens(str(meta.get("heading") or ""))
        overlap = len(q & doc_tokens) / max(len(q), 1) if q else 0.5
        h_overlap = len(q & heading_tokens) / max(len(q), 1) if q else 0.0
        exact = 1.0 if q and q.issubset(doc_tokens) else 0.0
        ctype = 1.0 if meta.get("content_type") in {"definition", "paragraph", "example", "table"} else 0.8

        kw_score = float(item.get("keyword_score", 0.0))
        kw_norm = min(1.0, kw_score / 15.0) if kw_score else 0.0
        lex_sim = max(kw_norm, overlap)

        dist = _get_distance(item)
        dense_sim = max(0.0, 1.0 - dist) if dist is not None and not item.get("keyword_match") else 0.5
        if item.get("keyword_match") and dist is not None and dist < 0.3:
            dense_sim = max(dense_sim, 0.75)

        score = 0.50 * dense_sim + 0.35 * lex_sim + 0.10 * exact + 0.05 * h_overlap + 0.05 * ctype
        ranked.append({
            **item,
            "score": float(min(1.0, score)),
            "lexical_overlap": float(overlap),
            "heading_overlap": float(h_overlap),
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    selected = ranked[:max(top_k, getattr(cfg, "reranker_candidates", 10))]

    if getattr(cfg, "reranker_enabled", False) and selected and query:
        try:
            backend = str(getattr(cfg, "reranker_backend", "openrouter")).casefold()
            if backend == "openrouter":
                _rerank_with_openrouter(query, selected, cfg)
            elif backend == "local":
                ce = _get_reranker(cfg.reranker_model, cfg.embedding_device)
                vals = ce.predict([(query, str(x.get("document", ""))) for x in selected], show_progress_bar=False)
                for x, v in zip(selected, vals):
                    x["reranker_score"] = min(1.0, max(0.0, float(v)))
        except Exception as exc:
            for x in selected:
                x["reranker_score"] = float(x["score"])
                x["reranker_error"] = f"{type(exc).__name__}: {exc}"

    for x in selected:
        raw_rer = float(x.get("reranker_score", x["score"]))
        overlap = float(x.get("lexical_overlap", 0.0))
        dist = _get_distance(x)
        dense_sim = max(0.0, 1.0 - dist) if dist is not None else 0.5

        effective_sim = max(raw_rer, 0.50 * raw_rer + 0.50 * float(x["score"]))
        if effective_sim >= 0.35:
            calibrated_sim = 0.80 + 0.18 * min(1.0, (effective_sim - 0.35) / 0.40)
            conf = min(0.98, calibrated_sim + 0.06 * overlap)
            x["reranker_score"] = float(min(0.98, max(0.72, 0.74 + 0.24 * min(1.0, (raw_rer - 0.35) / 0.40))))
        else:
            conf = effective_sim * 1.5
            x["reranker_score"] = float(min(1.0, max(0.0, raw_rer)))

        x["retrieval_confidence"] = float(min(0.98, max(0.05, conf)))

    selected.sort(key=lambda x: (x.get("reranker_score", 0), x["retrieval_confidence"], x["score"]), reverse=True)
    return selected[:top_k]


def rank_and_rerank(query: str, channel_results: dict[str, list[dict[str, Any]]], top_k: int, settings: Settings) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for items in channel_results.values():
        flat.extend(items)
    return rerank_and_dedup(flat, top_k=top_k, query=query, settings=settings)
