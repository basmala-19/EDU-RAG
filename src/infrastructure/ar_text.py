from __future__ import annotations

import re

# Shared Arabic & Multilingual token normalization, OCR repair, and core term extraction.
# Used by:
# 1. Deterministic ranker (ranking.py)
# 2. BM25 lexical index (vector_store.py)
# 3. RAG Quality Evaluator (evaluation.py)
# 4. Scoped query disambiguation (app.py)

# Character repair map for common Arabic PDF font encoding artifacts (Windows-1256 / Type-1 font ligatures)
_OCR_CHAR_MAP = str.maketrans({
    "·": "لا",
    "¡": "في",
    "à": "ت",
    "Ê": "ت",
    "É": "ح",
    "Ü": "ل",
    "ì": "ا",
    "î": "ى",
    "Ö": "ض",
    "¯": "ج",
    "Ì": "ي",
    "ø": "ة",
    "ù": "ت",
    "ð": "ن",
    "þ": "خ",
    "ä": "ش",
    "ß": "ر",
    "û": "ت",
})

# Multi-character prefix combinations (definite article "ال" alone or fused with prepositions)
_PREFIXES = re.compile(r"^(?:وال|فال|بال|كال|لل|ال)(?=.{2,})")

# Safe Arabic suffix stripping applied only when stem >= 3 chars
_SUFFIXES = re.compile(r"(?<=[\u0600-\u06FF]{3})(?:ات|ون|ين|ان|ها|هم|هن|نا|كم|تم|تك|يه|ية|ه|ي)$")

# English inflectional suffixes stripped only when stem >= 3 chars
_EN_SUFFIXES = re.compile(r"(?<=[a-z]{3})(?:'s|s|es|ed|ing)$")

_TASHKEEL = re.compile(r"[\u064B-\u065F\u0670]")

_MULTILINGUAL_STOP = {
    # Arabic stopwords & question boilerplate
    "من", "في", "على", "عن", "إلى", "الى", "مع", "بين", "حتى", "منذ",
    "هو", "هي", "هم", "هن", "هما", "انا", "نحن", "انت", "انتم", "انتن",
    "هذا", "هذه", "هذان", "هاتان", "هؤلاء", "ذلك", "تلك", "اولئك",
    "الذي", "التي", "الذين", "اللاتي", "اللواتي", "اللائي",
    "ما", "ماذا", "هل", "كيف", "لماذا", "أين", "اين", "متى", "كم", "اي", "أية", "اية",
    "اشرح", "وضح", "عرف", "تعريف", "اذكر", "بين", "قارن", "تكلم", "تفصيل", "بالتفصيل",
    "عايز", "اعرف", "اديني", "ايه", "ليه", "ازاي", "فين", "مين", "بتاع", "بتاعة",
    "و", "أو", "او", "ثم", "ف", "بل", "لكن", "أن", "إن", "ان", "انها", "انه", "انهم",
    "كان", "كانت", "يكون", "تكون", "تم", "تمت", "يتم", "تعتبر", "يعتبر", "يعد", "تعد",
    "قد", "لقد", "كل", "جميع", "بعض", "غير", "سوف", "سيتم",
    # English stopwords & question boilerplate
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "from",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "explain", "describe", "define", "definition", "detail", "details", "detailed",
    "tell", "give", "please", "about", "example", "examples", "can", "could", "would", "should",
    "this", "that", "these", "those", "it", "its", "they", "them", "their", "we", "us", "our", "you", "your",
}


def repair_ocr_artifacts(text: str) -> str:
    """Repair common Arabic PDF font ligature and encoding artifacts."""
    if not text:
        return ""
    # Map ligature symbols
    repaired = text.translate(_OCR_CHAR_MAP)
    # Common OCR split/omission repairs: e.g. "اوجـ" -> "موجـ" in wave physics context
    repaired = re.sub(r"\bاوج([ةهة])\b", r"موج\1", repaired)
    repaired = re.sub(r"\bال[تt]دد\b", "التردد", repaired)
    return repaired


def normalize_ar_token(token: str) -> str:
    """Normalize a single token (Arabic, English, or mixed).
    
    1. Repairs OCR artifacts.
    2. Removes diacritics / tashkeel and tatweel.
    3. Collapses Arabic hamza / alef-maqsura / ta-marbuta variants.
    4. Strips attached prefixes (ال, وال, بال, لل...) and suffixes (ات, ون, ين, ها...).
    5. Handles English lowercasing and basic suffix trimming.
    """
    if not token:
        return ""
    t = repair_ocr_artifacts(token.casefold())
    t = _TASHKEEL.sub("", t).replace("ـ", "")
    t = re.sub(r"[إأآٱ]", "ا", t)
    t = t.replace("ى", "ي").replace("ة", "ه")
    
    # Strip prefixes if remainder >= 2 chars
    t = _PREFIXES.sub("", t)
    # Strip Arabic suffixes if stem >= 3 chars
    t = _SUFFIXES.sub("", t)
    # Strip English suffixes if stem >= 3 chars
    t = _EN_SUFFIXES.sub("", t)
    return t


def normalize_token(token: str) -> str:
    """Alias for normalize_ar_token with general multilingual naming."""
    return normalize_ar_token(token)


def extract_core_tokens(text: str) -> set[str]:
    """Extract informative, normalized root/stem tokens from Arabic, English, or mixed text.
    
    Strips noise words, conversational question boilerplate, and short non-informative terms.
    """
    cleaned_text = repair_ocr_artifacts(text or "")
    raw_tokens = re.findall(r"[a-z0-9][a-z0-9_./+\-]*|[\u0600-\u06FF]+", cleaned_text.casefold())
    out: set[str] = set()
    for raw in raw_tokens:
        clean = _TASHKEEL.sub("", raw).replace("ـ", "")
        norm = normalize_token(clean)
        if len(norm) > 1 and norm not in _MULTILINGUAL_STOP and raw not in _MULTILINGUAL_STOP:
            out.add(norm)
    return out
