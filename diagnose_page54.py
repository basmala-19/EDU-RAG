"""
Deeper diagnostic — the first script showed that page 54 (the page that
actually answers the radio question) never even made it into the top-5
retrieved results, and that the 5 chunks that DID get retrieved are full of
garbled/reversed text. This script answers three separate questions so we
know exactly which stage is broken:

  1. Is page 54 indexed at all? (ingestion gap vs retrieval-ranking problem)
  2. If it is indexed, is the STORED text for it clean or corrupted?
     (parsing/ingestion corruption vs something introduced later)
  3. Can a plain lexical/keyword search for "1906" / "الراديو" find it,
     completely bypassing embeddings? (embedding problem vs keyword-index
     problem — if keyword search finds it but semantic search doesn't,
     the embeddings for the corrupted text are the culprit)

Run from the project root:

    python diagnose_page54.py --file-reference-id 10dd0fb7c09baef79e088d3a5ba4d425
"""
from __future__ import annotations

import argparse

from src.infrastructure.vector_store import VectorStore


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--file-reference-id", required=True)
    p.add_argument("--page", type=int, default=54)
    args = p.parse_args()

    store = VectorStore()
    filters = {"file_reference_id": args.file_reference_id}

    print("=" * 100)
    print(f"1) Is page {args.page} indexed at all?")
    print("=" * 100)
    all_meta = store.get_all_metadata(filters)
    print(f"Total chunks indexed for this file_reference_id: {len(all_meta)}")
    page_chunks = [m for m in all_meta if str(m.get("page")) == str(args.page)]
    print(f"Chunks with page == {args.page}: {len(page_chunks)}")
    for m in page_chunks:
        print(f"  - heading={m.get('heading')!r} content_type={m.get('content_type')} "
              f"chunk_role={m.get('chunk_role')} parent_chunk_id={m.get('parent_chunk_id')}")

    if not page_chunks:
        print(f"\n>>> Page {args.page} has ZERO chunks in the index. This is an ingestion gap, "
              f"not a retrieval-ranking problem. Re-check ingestion logs for this page.")
        return

    print("\n" + "=" * 100)
    print(f"2) What does the STORED text for page {args.page} actually look like?")
    print("=" * 100)
    # Pull raw documents directly via chroma's collection.get (bypassing embeddings/ranking).
    if store.collection is not None:
        where = store._chroma_where({**filters, "page": args.page})
        out = store.collection.get(where=where, include=["documents", "metadatas"])
        docs = out.get("documents", [])
        metas = out.get("metadatas", [])
        for doc, meta in zip(docs, metas):
            print(f"\n--- chunk (heading={meta.get('heading')!r}, role={meta.get('chunk_role')}) ---")
            print(doc)
            for needle in ("1906", "الراديو", "بث تجريبي"):
                print(f"    contains {needle!r}: {needle in doc}")
    else:
        print("No chroma collection configured (local JSON store) — inspect the local store file directly.")

    print("\n" + "=" * 100)
    print("3) Does plain lexical/keyword search (BM25-style, no embeddings) find it?")
    print("=" * 100)
    for query in ("اين كان اول بث تجريبي للراديو", "1906", "الراديو", "بث تجريبي"):
        kw_results = store.query_keywords(query, filters, 10) if hasattr(store, "query_keywords") else []
        hit_pages = [r.get("metadata", {}).get("page") for r in kw_results]
        found = str(args.page) in [str(x) for x in hit_pages]
        print(f"query={query!r} -> pages returned={hit_pages} -> page {args.page} in results: {found}")


if __name__ == "__main__":
    main()
