# V6 Fixes

- Chroma is no longer silently replaced by local JSON when a real Chroma initialization error occurs. Only a missing Chroma module permits local-json in dev/test.
- BGE-M3 remains the embedding backend; production hash fallback is disabled by default in `.env.example`.
- BGE reranker logits are converted with sigmoid instead of being misread as already-calibrated probabilities. This prevents valid relevance logits like `0.25` from being treated as a weak 0.25 score.
- Response `retrieval` now reports real semantic, keyword, question, RRF, reranker, and retrieval-confidence values from backend metadata.
- Chroma is pinned to `>=0.6,<0.7` so a fresh install does not silently jump to a newer incompatible major/minor line.
- All retrieval tests pass: 20 passed.
