# Verified Build Notes

This build was produced by extracting `rag-general-rag-v28-production-clean-fixed-v6.zip`,
then actually running (not just reading) the code to verify every claimed fix, and correcting
what didn't hold up. Every item below was reproduced with a concrete before/after test.

## Fixed in this pass

1. **`src/services/ranking.py` — reranker score was non-monotonic**
   The previous formula (`v if 0<=v<=1 else sigmoid(v)`) meant a raw logit of `1.0` scored
   `1.0` but `1.01` scored `0.733` — a worse score for a *more* relevant match. A logit of
   `0.0` (neutral) scored `0.0` (worst possible), while `-0.5` (actually worse) scored `0.38`.
   Fixed to always apply sigmoid, restoring monotonicity. This also fixes `retrieval_confidence`,
   which derives 60% of its value from `reranker_score`.

2. **`src/services/embeddings.py` — real embedding model was never attempted in the default config**
   With `EMBEDDING_ALLOW_HASH_FALLBACK=true` (the default), `_try_load_real_model()` was never
   called at all — every embedding was a random hash vector regardless of whether BGE-M3 was
   installed and working. Fixed so the real model is always attempted first; the fallback flag
   now only controls what happens if that attempt fails (matching what the flag name implies).

3. **`pyproject.toml` — malformed/duplicated version pin**
   `chromadb>=0.6,<0.7,<0.7` cleaned to `chromadb>=0.6,<0.7`.

## Confirmed already correct (verified, not just read)

- `src/app.py` reads `semantic_score` / `keyword_score` / `question_score` / `rrf_score` /
  `reranker_score` / `retrieval_confidence` from `results[0]["metadata"]` — no more dead zeros.
- `src/services/health.py` actually calls `embedder.encode(...)` before reporting status, so
  `/api/rag/health` reflects real state instead of a permanent default.
- Arabic diacritic stripping in both `vector_store.py::_lex_tokens` and `ranking.py::_tokens`
  covers the full tashkeel range (`\u064B-\u065F`, `\u0670`), not just shadda.
- `chromadb` resolves to `0.6.3` (not the unstable `1.5.9` line).

## Known limitation (not fixed, by design trade-off — flagging for visibility)

- `VectorStore` decides Chroma vs. local-JSON per-call based on `self.collection is not None`,
  not on `self.backend`. A genuine Chroma init failure (not a missing package) still results in
  silent local-JSON operation during real requests — only `/health` will show `"degraded"`.
  If you want a hard failure on real Chroma errors instead of a health-check-only signal, add an
  explicit `if store.backend == "unavailable": raise` at the top of the upload/response routes.

## Test result (reproduced from a clean checkout, no stale `data/` state)

```
20 passed
```
