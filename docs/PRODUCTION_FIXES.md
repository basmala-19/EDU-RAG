# Production Clean V5

- Fixed Chroma metadata serialization: list/tuple/set metadata is converted to a scalar string before upsert.
- Fixed dynamic retrieval candidate expansion: `candidate_k = top_k * max(candidate_multiplier, 8)`.
- Fixed direct-question query handling: chapter/lesson context is not appended to a new question before retrieval; it remains request/session context.
- Fixed Arabic lexical normalization for full tashkeel and tatweel.
- Fixed multi-channel ranking so semantic, question, and keyword contributions can coexist on one candidate.
- Keyword retrieval includes heading text to improve exact curriculum-term retrieval.
- Added BGE reranking and multi-signal retrieval confidence while keeping a deterministic fallback if reranker loading fails.
- Added Groq generation provider while retaining Ollama for local development.
- Added health embedding probe.
- Production embedding mode can disable hash fallback with `EMBEDDING_ALLOW_HASH_FALLBACK=false`.
- Pinned ChromaDB to `<0.7` for reproducibility.

Verification: `pytest -q` => 20 passed.
