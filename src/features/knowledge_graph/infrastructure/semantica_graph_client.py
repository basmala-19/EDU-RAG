"""Adapter over the external ``semantica_graph`` package.

This is the only module in the whole project allowed to import
``semantica_graph`` - every other layer goes through
:class:`SemanticaGraphClient` instead, the same way
``rag/infrastructure/embeddings.py`` is the only place that talks to the
embeddings API directly.

``semantica_graph`` is a separate, external package (source lives outside
this project) and is not declared in this project's pyproject.toml because
it must be installed from its own directory. Install it once into this
project's Python environment with:

    pip install -e /path/to/knowledge_graph-main

The import here is intentionally lazy (inside the method, not at module load
time) so the rest of the app keeps working even if that package has not
been installed yet - only a call into this client fails, with a clear error
telling the caller how to fix it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


class SemanticaGraphUnavailableError(RuntimeError):
    """Raised when the external semantica_graph package is not installed."""


class SemanticaGraphClient:
    def generate(self, *, pdf_path: Path, model_name: str, output_dir: Path) -> dict[str, Any]:
        """Run the external pipeline (PDF -> markdown -> LLM -> graph JSON).

        Returns the parsed graph dict and, as a side effect, writes
        ``*_graph.json`` / ``*_graph.html`` / ``*_tree.html`` /
        ``*_llm_response.txt`` under ``output_dir`` (semantica_graph's own
        behavior - this adapter does not change it).
        """
        try:
            from semantica_graph import get_graph
        except ImportError as exc:
            raise SemanticaGraphUnavailableError(
                "The 'semantica_graph' package is not installed in this environment. "
                "Install it once with: pip install -e /path/to/knowledge_graph-main "
                "(use the same Python environment this app runs in)."
            ) from exc

        return get_graph(
            model_name=model_name,
            input_pdf_file_location=str(pdf_path),
            output_save_location=str(output_dir),
        )

    @staticmethod
    def find_graph_json(output_dir: Path) -> Path | None:
        """Locate the ``*_graph.json`` file semantica_graph wrote, if any."""
        matches = list(output_dir.glob("*_graph.json"))
        return matches[0] if matches else None
