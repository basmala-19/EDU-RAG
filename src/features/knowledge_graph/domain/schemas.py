"""Shape of a generated knowledge graph, shared by every feature that consumes it.

Produced by ``infrastructure/graph_extractor.py`` (a native LLM pipeline -
see its module docstring). Kept permissive (``extra="allow"``) on
entities/relationships since an LLM-produced entity may carry extra
descriptive fields beyond the ones this project currently reads. Only the
fields other features actually depend on are required: ``id``/``text`` for
entities (``question_bank/questions_service.py`` reads
``entity["text"]`` as the display name - not ``name``), and
``source``/``target``/``type`` for relationships.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GraphEntity(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Stable identifier used to reference this entity elsewhere in the graph.")
    text: str = Field(description="Human-readable entity/topic name.")
    type: str | None = Field(default=None, description="Entity category, e.g. 'concept'.")
    description: str | None = Field(default=None, description="Short description of the entity.")


class GraphRelationship(BaseModel):
    model_config = ConfigDict(extra="allow")

    source: str = Field(description="Entity id this relationship starts from.")
    target: str = Field(description="Entity id this relationship points to.")
    type: str | None = Field(default=None, description="'subsetOf' or 'prerequisiteOf' - see graph_extractor.py.")


class KnowledgeGraph(BaseModel):
    """The parsed graph as returned by ``LLMGraphExtractor.generate``."""

    model_config = ConfigDict(extra="allow")

    entities: list[GraphEntity] = Field(default_factory=list)
    relationships: list[GraphRelationship] = Field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class GenerateGraphResult(BaseModel):
    """Return value of ``KnowledgeGraphService.generate_from_pdf``."""

    model_config = ConfigDict(extra="allow")

    graph: dict[str, Any] = Field(description="The knowledge graph as a plain dict (entities + relationships).")
    source_file_name: str = Field(description="Name of the PDF the graph was built from.")
    content_hash: str = Field(description="SHA-256 of the source PDF, used for cache lookups.")
    cached: bool = Field(description="True if a previously generated graph was reused instead of calling the LLM.")
    entity_count: int = Field(description="Number of entities in the graph, for quick display.")
