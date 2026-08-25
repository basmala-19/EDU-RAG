"""Content-hash-based ingest dedup registry.

Purpose: if the admin re-uploads a book they (or someone else) already uploaded before —
even under a different filename — skip re-ingesting it from scratch, unless they explicitly
ask for a re-ingest. Keyed on the file's *content* hash, never on filename, so renaming a
file can't defeat dedup and two different books that happen to share a filename are never
confused with each other.

Deliberately plain filesystem + JSON, matching the rest of this service's storage style
(no new dependency, easy to inspect/edit by hand, safe under low concurrency).
"""
from __future__ import annotations

import json
import threading
from hashlib import sha256
from pathlib import Path
from typing import Any, BinaryIO


class IngestRegistry:
    def __init__(self, path: Path | str = Path("data/ingest_registry.json")) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    # -- hashing -----------------------------------------------------------------
    @staticmethod
    def hash_stream(stream: BinaryIO, chunk_size: int = 1024 * 1024) -> str:
        """Streaming sha256 so we never have to hold the whole upload in memory twice."""
        h = sha256()
        while True:
            chunk = stream.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
        stream.seek(0)
        return h.hexdigest()

    @staticmethod
    def hash_bytes(data: bytes) -> str:
        return sha256(data).hexdigest()

    # -- storage -------------------------------------------------------------------
    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A corrupted registry file should never take ingestion down — treat it as
            # empty and let it get rewritten on the next successful registration.
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    # -- public API ------------------------------------------------------------------
    def lookup(self, content_hash: str) -> dict[str, Any] | None:
        with self._lock:
            return self._read().get(content_hash)

    def register(self, content_hash: str, record: dict[str, Any]) -> None:
        with self._lock:
            data = self._read()
            data[content_hash] = record
            self._write(data)

    def forget(self, content_hash: str) -> None:
        """Used by force_reingest so a fresh ingest overwrites the stale registry entry
        rather than leaving two records (old hash-match + new) pointing at different
        curriculum_ids for what is nominally 'the same' upload attempt."""
        with self._lock:
            data = self._read()
            data.pop(content_hash, None)
            self._write(data)
