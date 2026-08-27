from __future__ import annotations

import re
from dataclasses import dataclass
from hashlib import sha1
from typing import Any

from src.features.rag.application.metadata import classify_content_type, detect_heading, normalize_text, split_heading_path, strip_private_state, update_structure


@dataclass(frozen=True)
class TextChunk:
    raw_text: str
    normalized_text: str
    metadata: dict[str, Any]
    parent_chunk_id: str
    parent_text: str
    parent_metadata: dict[str, Any]


class HierarchyAwareParentChildChunker:
    """Structure-first parent/child chunking for educational RAG."""

    def __init__(self, parent_size: int = 1600, child_size: int = 650, overlap: int = 80, min_size: int = 220, heading_max_length: int = 180) -> None:
        if overlap >= child_size:
            raise ValueError("overlap must be smaller than child_size")
        self.parent_size = parent_size
        self.child_size = child_size
        self.overlap = overlap
        self.min_size = min_size
        self.heading_max_length = heading_max_length

    def split(self, text: str, base_metadata: dict[str, Any] | None = None) -> list[TextChunk]:
        state = dict(base_metadata or {})
        state.setdefault("heading_path", [])
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text.replace("\r\n", "\n")) if p.strip()]
        parents: list[tuple[str, dict[str, Any], str]] = []
        current_parts: list[str] = []
        current_state = dict(state)

        def flush_parent() -> None:
            nonlocal current_parts
            raw = "\n".join(current_parts).strip()
            if not raw:
                current_parts = []
                return
            pid_basis = "|".join(str(current_state.get(k) or "") for k in ("file_reference_id", "page", "heading", "heading_path")) + "|" + raw
            pid = sha1(pid_basis.encode("utf-8")).hexdigest()[:20]
            parents.append((pid, dict(current_state), raw))
            current_parts = []

        for paragraph in paragraphs:
            body_lines: list[str] = []
            for raw_line in paragraph.splitlines():
                line = raw_line.strip()
                if not line:
                    continue
                before_state = dict(current_state)
                heading_like = detect_heading(line, max_length=self.heading_max_length) is not None
                changed = update_structure(current_state, line, max_length=self.heading_max_length)
                if heading_like and changed:
                    if current_parts:
                        # Flush using the state that belonged to the previous parent.
                        raw = "\n".join(current_parts).strip()
                        if raw:
                            pid_basis = "|".join(str(before_state.get(k) or "") for k in ("file_reference_id", "page", "heading", "heading_path")) + "|" + raw
                            pid = sha1(pid_basis.encode("utf-8")).hexdigest()[:20]
                            parents.append((pid, before_state, raw))
                        current_parts = []
                    current_parts.append(line)
                else:
                    body_lines.append(line)

            if body_lines:
                body = "\n".join(body_lines).strip()
                candidate = "\n".join(current_parts + [body]).strip()
                if len(candidate) <= self.parent_size:
                    current_parts.append(body)
                else:
                    if current_parts:
                        flush_parent()
                    for part in self._split_text(body, self.parent_size, max(40, self.overlap)):
                        pid_basis = "|".join(str(current_state.get(k) or "") for k in ("file_reference_id", "page", "heading", "heading_path")) + "|" + part
                        parents.append((sha1(pid_basis.encode("utf-8")).hexdigest()[:20], dict(current_state), part))
        flush_parent()

        children: list[TextChunk] = []
        for pid, parent_state, parent_text in parents:
            parent_state = strip_private_state(parent_state)
            parent_path = split_heading_path(parent_state.get("heading_path"))
            parent_meta = {
                **parent_state,
                "heading_path": parent_path,
                "content_type": classify_content_type(parent_text, parent_state.get("heading")),
                "parent_chunk_id": pid,
                "chunk_role": "parent",
            }
            for child_text in self._merge_short(self._split_text(parent_text, self.child_size, self.overlap)):
                normalized = normalize_text(child_text)
                context_parts = [str(parent_state[k]).strip() for k in ("subject", "grade") if parent_state.get(k) not in (None, "")]
                if parent_path:
                    context_parts.append(" > ".join(parent_path))
                embed_text = (" > ".join(context_parts) + "\n" + normalized).strip() if context_parts else normalized
                child_meta = {
                    **parent_state,
                    "heading_path": parent_path,
                    "content_type": classify_content_type(child_text, parent_state.get("heading")),
                    "parent_chunk_id": pid,
                    "chunk_role": "child",
                }
                children.append(TextChunk(
                    raw_text=child_text,
                    normalized_text=normalize_text(embed_text),
                    metadata=child_meta,
                    parent_chunk_id=pid,
                    parent_text=parent_text,
                    parent_metadata=parent_meta,
                ))
        return children

    def _merge_short(self, parts: list[str]) -> list[str]:
        merged: list[str] = []
        for part in parts:
            if merged and len(part) < self.min_size:
                merged[-1] = (merged[-1] + "\n" + part).strip()
            else:
                merged.append(part)
        return merged

    @staticmethod
    def _split_text(text: str, limit: int, overlap: int) -> list[str]:
        if len(text) <= limit:
            return [text.strip()]
        sentences = [x.strip() for x in re.split(r"(?<=[.!?؟؛])\s+", text) if x.strip()]
        parts: list[str] = []
        current = ""
        for sentence in sentences:
            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= limit:
                current = candidate
                continue
            if current:
                parts.append(current)
            current = sentence
            while len(current) > limit:
                parts.append(current[:limit].strip())
                current = current[max(1, limit - overlap):]
        if current:
            parts.append(current)
        return parts


# Backward-compatible constructor name for callers/tests that still import the old chunker.
class HierarchyAwareChunker(HierarchyAwareParentChildChunker):
    def __init__(self, target_size: int = 500, overlap: int = 80, min_size: int = 80, heading_max_length: int = 180) -> None:
        # Legacy callers get a parent slightly larger than the child target while retaining the old child target.
        super().__init__(parent_size=max(target_size * 2, 900), child_size=target_size, overlap=overlap, min_size=min_size, heading_max_length=heading_max_length)

