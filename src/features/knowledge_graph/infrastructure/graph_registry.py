"""Content-hash-based graph-generation dedup registry.

Purpose: if the same PDF is (re-)submitted for graph generation - even under
a different filename - reuse the previously generated graph instead of
calling the LLM again, unless the caller explicitly forces regeneration.
Keyed on the file's *content* hash, never on filename.

Deliberately plain filesystem + JSON, matching
``rag/infrastructure/ingest_registry.py``'s storage style (no new
dependency, easy to inspect/edit by hand, safe under low concurrency).
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


class GraphRegistry:
    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = threading.Lock()

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            # A corrupted registry file should never take generation down -
            # treat it as empty and let it get rewritten on the next success.
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def lookup(self, content_hash: str) -> dict[str, Any] | None:
        with self._lock:
            return self._read().get(content_hash)

    def register(self, content_hash: str, record: dict[str, Any]) -> None:
        with self._lock:
            data = self._read()
            data[content_hash] = record
            self._write(data)

    def forget(self, content_hash: str) -> None:
        with self._lock:
            data = self._read()
            data.pop(content_hash, None)
            self._write(data)
