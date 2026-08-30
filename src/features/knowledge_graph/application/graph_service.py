"""Public entry point for the knowledge_graph feature.

Other features depend on this feature by importing ``KnowledgeGraphService``
directly from here - the same pattern used for the RAG feature's
``QuestionBankRAG`` (see ``rag/application/question_bank_integration.py``).
No feature should import from ``knowledge_graph.infrastructure`` or
``knowledge_graph.domain`` directly; this module is the boundary.
"""

from __future__ import annotations

import logging
from hashlib import sha256
from pathlib import Path

from src.features.knowledge_graph.domain.schemas import GenerateGraphResult
from src.features.knowledge_graph.infrastructure.config import get_llm_model, get_storage_dir
from src.features.knowledge_graph.infrastructure.graph_extractor import LLMGraphExtractor
from src.features.knowledge_graph.infrastructure.graph_registry import GraphRegistry

logger = logging.getLogger(__name__)


class KnowledgeGraphService:
    """Generate and cache knowledge graphs from PDFs for any feature to use."""

    def __init__(self, *, storage_dir: str | Path | None = None) -> None:
        self.storage_dir = Path(storage_dir) if storage_dir else get_storage_dir()
        self.registry = GraphRegistry(self.storage_dir / "registry.json")
        self.client = LLMGraphExtractor()

    def generate_from_pdf(
        self,
        pdf_path: str | Path,
        *,
        model_name: str | None = None,
        force: bool = False,
    ) -> GenerateGraphResult:
        """Return the knowledge graph for a PDF, generating it once per unique file.

        Results are cached on disk keyed by the file's content hash (the
        same dedup strategy the RAG feature uses for indexing), so
        re-submitting the same book reuses the previous graph instead of
        paying for another LLM call. Pass ``force=True`` to regenerate
        anyway.
        """
        path = Path(pdf_path)
        if not path.is_file():
            raise FileNotFoundError(f"PDF not found: {path}")
        if path.suffix.casefold() != ".pdf":
            raise ValueError("Knowledge graph generation only supports PDF input.")

        content_hash = self._hash_file(path)

        if not force:
            cached = self._load_cached(content_hash, source_name=path.name)
            if cached is not None:
                return cached

        selected_model = model_name or get_llm_model()
        request_dir = self.storage_dir / content_hash
        logger.info(
            "Generating knowledge graph for '%s' with model=%s (PDF -> markdown -> LLM -> graph JSON)",
            path.name, selected_model,
        )
        graph = self.client.generate(pdf_path=path, model_name=selected_model, output_dir=request_dir)
        entity_count = len(graph.get("entities", [])) if isinstance(graph, dict) else 0
        logger.info("Knowledge graph generated for '%s': %d entities", path.name, entity_count)

        json_path = self.client.find_graph_json(request_dir)
        if json_path is not None:
            self.registry.register(content_hash, {"graph_json_path": str(json_path), "source_file_name": path.name})
        else:
            logger.warning(
                "Graph extraction did not produce a *_graph.json file in %s; "
                "the graph was still returned but will not be cached.",
                request_dir,
            )

        return GenerateGraphResult(
            graph=graph,
            source_file_name=path.name,
            content_hash=content_hash,
            cached=False,
            entity_count=entity_count,
        )

    def _load_cached(self, content_hash: str, *, source_name: str) -> GenerateGraphResult | None:
        record = self.registry.lookup(content_hash)
        if not record:
            return None

        json_path = Path(record.get("graph_json_path", ""))
        if not json_path.is_file():
            logger.warning(
                "Registry pointed to a missing graph file (%s) for '%s' - will regenerate.",
                json_path, source_name,
            )
            self.registry.forget(content_hash)
            return None

        import json
        graph = json.loads(json_path.read_text(encoding="utf-8"))
        entity_count = len(graph.get("entities", [])) if isinstance(graph, dict) else 0
        logger.info("Reusing cached knowledge graph for '%s' (no LLM call): %s", source_name, json_path)
        return GenerateGraphResult(
            graph=graph,
            source_file_name=record.get("source_file_name", source_name),
            content_hash=content_hash,
            cached=True,
            entity_count=entity_count,
        )

    @staticmethod
    def _hash_file(path: Path) -> str:
        digest = sha256()
        with path.open("rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
