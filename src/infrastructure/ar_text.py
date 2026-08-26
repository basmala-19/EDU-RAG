from __future__ import annotations

import re

# Shared Arabic token normalization used by BOTH the deterministic reranker
# (ranking.py::_tokens) and the BM25 lexical index (vector_store.py::_lex_tokens).
#
# Why this exists: the two tokenizers used to be duplicated verbatim and neither
# normalized hamza forms nor stripped attached prepositional/definite-article
# prefixes. That meant a query token like "للراديو" (لـ + الراديو) could never
# exact-match the document token "الراديو", and "اول" (no hamza, how most people
# type/ask) could never match "أول" (with hamza) in the source text — even though
# both refer to the same word. This silently tanked the lexical-overlap component
# of the deterministic score for perfectly relevant chunks, which could push them
# out of the pre-reranker candidate window entirely on certain queries.
# Only strip multi-character prefix combinations (definite article "ال" alone or fused
# with a single-letter preposition: لل/بال/كال/وال/فال). Deliberately excludes bare
# single-letter prefixes (و/ف/ب/ل/ك) — those are too ambiguous to strip safely on any
# general Arabic text: the same letter is just as often the first root letter of an
# ordinary word (لغة "language", كتاب "book", بيت "house", فيديو "video", وقت "time"),
# so blind single-letter stripping mangles common words across every subject/book, not
# just this one. Multi-character prefixes carry much lower false-positive risk.
_PREFIXES = re.compile(r"^(?:وال|فال|بال|كال|لل|ال)(?=.{2,})")


def normalize_ar_token(token: str) -> str:
    """Normalize a single already-segmented token: collapse hamza/alef-maqsura/ta-marbuta
    variants and strip one leading attached Arabic prefix (definite article and/or a
    single-letter preposition), so morphological variants of the same word collide to the
    same token for exact-match/overlap scoring.
    """
    t = re.sub(r"[إأآٱ]", "ا", token)
    t = t.replace("ى", "ي").replace("ة", "ه")
    stripped = _PREFIXES.sub("", t)
    return stripped or t
