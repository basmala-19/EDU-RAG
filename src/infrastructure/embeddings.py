from __future__ import annotations

import hashlib
from functools import lru_cache
import numpy as np
import requests

from src.infrastructure.config import get_settings


class EmbeddingService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.model = None
        self.backend = "unavailable"
        self.error: str | None = None

    def _try_load_real_model(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(self.settings.embedding_model, device=self.settings.embedding_device)
            self.backend = "sentence-transformers"
            self.error = None
        except Exception as exc:
            self.model = None
            self.error = f"{type(exc).__name__}: {exc}"

    def _encode_with_openrouter(self, texts: list[str]) -> np.ndarray:
        if not self.settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required when EMBEDDING_BACKEND=openrouter")
        response = requests.post(
            f"{self.settings.openrouter_base_url.rstrip('/')}/embeddings",
            headers={"Authorization": f"Bearer {self.settings.openrouter_api_key}", "Content-Type": "application/json"},
            json={"model": self.settings.embedding_model, "input": texts, "encoding_format": "float"},
            timeout=self.settings.openrouter_timeout,
        )
        response.raise_for_status()
        rows = response.json().get("data") or []
        if len(rows) != len(texts):
            raise RuntimeError(f"OpenRouter returned {len(rows)} embeddings for {len(texts)} inputs")
        try:
            ordered = sorted(rows, key=lambda row: int(row["index"]))
            arr = np.asarray([row["embedding"] for row in ordered], dtype=np.float32)
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError("OpenRouter returned an invalid embeddings response") from exc
        if arr.ndim != 2 or not arr.shape[1]:
            raise RuntimeError("OpenRouter returned empty embeddings")
        return arr / np.maximum(np.linalg.norm(arr, axis=1, keepdims=True), 1e-12)

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0), dtype=np.float32)
        backend = self.settings.embedding_backend.casefold()
        if backend == "openrouter":
            try:
                arr = self._encode_with_openrouter(texts)
                self.backend = "openrouter"
                self.error = None
                return arr
            except Exception as exc:
                self.backend = "unavailable"
                self.error = f"{type(exc).__name__}: {exc}"
                raise RuntimeError(f"Embedding model unavailable: {self.error}") from exc
        if backend != "local":
            raise RuntimeError("EMBEDDING_BACKEND must be 'openrouter' or 'local'")
        if self.model is None:
            self._try_load_real_model()
        if self.model is not None:
            arr = self.model.encode(texts, normalize_embeddings=True)
            return np.asarray(arr, dtype=np.float32)
        if self.settings.embedding_allow_hash_fallback:
            self.backend = "hash-fallback"
            return np.vstack([self._hash_embed(t) for t in texts]).astype(np.float32)
        self.backend = "unavailable"
        raise RuntimeError(f"Embedding model unavailable: {self.error or 'unknown error'}")

    @staticmethod
    def _hash_embed(text: str, dim: int = 384) -> np.ndarray:
        seed = hashlib.sha256(text.encode("utf-8")).digest()
        rng = np.random.default_rng(int.from_bytes(seed[:8], "little"))
        vec = rng.normal(size=dim).astype(np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm else vec


@lru_cache(maxsize=1)
def get_embedding_service() -> EmbeddingService:
    """Return one process-wide embedding client/model for all application services."""
    return EmbeddingService()
