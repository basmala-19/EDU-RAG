"""Thin OpenRouter/OpenAI-compatible chat-completion wrapper.

Deliberately duplicates the tiny amount of logic in
``question_bank/llm_api/openai_api.py`` instead of importing it: this
feature never imports from ``question_bank`` (see the module docstring on
``infrastructure/config.py`` for why) even though both end up calling the
same OpenRouter endpoint with the same ``.env`` credentials.
"""

from __future__ import annotations

from openai import OpenAI

from .config import get_openrouter_api_key, get_openrouter_base_url


def get_llm_response(model_name: str, prompt: str) -> str:
    """Send a single-turn prompt using credentials from the local ``.env``."""
    client = OpenAI(base_url=get_openrouter_base_url(), api_key=get_openrouter_api_key())
    response = client.chat.completions.create(
        model=model_name,
        messages=[{"role": "user", "content": prompt}],
        extra_body={"reasoning": {"enabled": False}},
    )
    return response.choices[0].message.content
