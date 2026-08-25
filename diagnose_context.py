"""
Diagnostic: prints the EXACT context that gets sent to the generation model
for a given query, using the real RetrievalService + build_context from the
project — so you can see with your own eyes whether the fact you're looking
for (e.g. "1906" / "الراديو") survived retrieval + parent-expansion +
truncation intact, or whether it's missing/corrupted/cut off.

Run from the project root (same folder as entrypoint/):

    python diagnose_context.py "اين كان اول بث تجريبي للراديو ؟" \
        --file-reference-id 10dd0fb7c09baef79e088d3a5ba4d425

Add --raw to also print each source's full raw_text (not just the built
context string), so you can tell parent-expansion issues apart from
build_context truncation issues.
"""
from __future__ import annotations

import argparse
import sys

from src.application.generation import build_context
from src.application.retrieval_service import RetrievalService
from src.infrastructure.config import get_settings


def main() -> None:
    p = argparse.ArgumentParser(description="Inspect the exact context sent to the LLM for a query")
    p.add_argument("query")
    p.add_argument("--file-reference-id", required=True)
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--raw", action="store_true", help="also print each source's full raw_text")
    args = p.parse_args()

    settings = get_settings()
    service = RetrievalService()

    filters = {"file_reference_id": args.file_reference_id}
    retrieved = service.retrieve(args.query, filters, args.top_k)
    results = [r.model_dump() for r in retrieved.results]

    if not results:
        print("No results at all — retrieval itself returned nothing for this query/file_reference_id.")
        sys.exit(1)

    print("=" * 100)
    print(f"QUERY: {args.query}")
    print(f"file_reference_id: {args.file_reference_id}")
    print("=" * 100)

    print(f"\n--- {len(results)} retrieved sources (post rerank/dedup) ---\n")
    for i, item in enumerate(results, 1):
        meta = item.get("metadata", {})
        print(
            f"[{i}] page={meta.get('page')} heading={meta.get('heading')!r} "
            f"content_type={meta.get('content_type')} score={item.get('score'):.4f} "
            f"reranker_score={meta.get('reranker_score')} "
            f"retrieval_confidence={meta.get('retrieval_confidence')} "
            f"context_expanded={meta.get('context_expanded')} "
            f"channels={meta.get('retrieval_channels')}"
        )
        if args.raw:
            print("    raw_text:")
            print("    " + item.get("raw_text", "").replace("\n", "\n    "))
            print()

    context = build_context(results, settings.max_context_chars)

    print("\n" + "=" * 100)
    print(f"ACTUAL CONTEXT SENT TO THE LLM ({len(context)} chars, limit={settings.max_context_chars})")
    print("=" * 100)
    print(context)

    print("\n" + "=" * 100)
    print("QUICK CHECKS")
    print("=" * 100)
    truncated = len(context) >= settings.max_context_chars
    print(f"- Context hit the max_context_chars limit and was likely truncated: {truncated}")

    # Add any terms you're specifically hunting for here.
    needles = ["1906", "الراديو", "بث تجريبي"]
    for needle in needles:
        present = needle in context
        print(f"- {needle!r} present in final context: {present}")
        if not present:
            # Check per-source raw_text too, to tell "never retrieved" apart from
            # "retrieved but dropped by build_context's truncation".
            for i, item in enumerate(results, 1):
                if needle in item.get("raw_text", ""):
                    print(f"    -> but IS present in source [{i}]'s raw_text (page {item['metadata'].get('page')}) "
                          f"— build_context or ordering dropped it, not retrieval.")


if __name__ == "__main__":
    main()
