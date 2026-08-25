from __future__ import annotations

import hashlib
import numpy as np

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

    def encode(self, texts: list[str]) -> np.ndarray:
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
