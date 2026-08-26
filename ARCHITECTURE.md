# Architecture

This project follows a clean-architecture-style layering. Dependencies point inward:
`interfaces` → `application` → `domain`, with `infrastructure` implementing technical
concerns (external systems, I/O) that `application` orchestrates. `utils` holds small
cross-cutting helpers with no project-specific dependencies.

```text
src/
├── domain/                 # Pure data contracts — no I/O, no external calls
│   └── schemas.py          # Pydantic request/response/DTO models
│
├── application/             # Use cases / business orchestration
│   ├── ingestion_service.py     # IngestionService — parse → chunk → embed → index a file
│   ├── retrieval_service.py     # RetrievalService — retrieve → rerank → expand context
│   ├── generation.py            # Prompt/context assembly + provider dispatch (Ollama/Groq)
│   ├── chunking.py              # Hierarchy-aware parent/child chunking
│   ├── document_metadata.py     # Curriculum metadata extraction (title/subject/grade/term)
│   ├── curriculum_structure.py  # Subject → grade → chapter/lesson discovery aggregation
│   ├── hypothetical_questions.py# Question-index generation for a chunk
│   ├── metadata.py              # Text/heading/content-type helpers shared across the above
│   └── session.py               # In-memory learning-session state
│
├── infrastructure/          # External systems / technical adapters
│   ├── config.py            # Settings (env + YAML)
│   ├── document_loader.py   # PDF/DOCX/HTML file parsing (PyMuPDF, LlamaParse, ...)
│   ├── embeddings.py        # BGE-M3 embedding model wrapper
│   ├── vector_store.py      # ChromaDB / local-JSON vector store adapter
│   ├── ranking.py           # BGE reranker model wrapper
│   ├── health.py            # Liveness/readiness probes for embeddings + vector store
│   └── ingest_registry.py   # Content-hash dedup registry (skip re-ingesting known files)
│
├── interfaces/
│   └── api/
│       ├── app.py           # FastAPI app, routes, request/response wiring
│       └── static/
│           └── console.html # Self-contained manual-testing chat console (served at /console)
│
└── utils/
    ├── logger.py
    └── validators.py

entrypoint/                  # CLI interface layer (batch ingest / query, outside the API)
config/                      # YAML settings (default.yaml, prod.yaml, local override example)
tests/                       # Mirrors the src/ layout (unit/ + integration/)
```

## Why this shape

- **`domain`** has zero dependencies on the rest of the app — it's the vocabulary every
  other layer shares (`RAGChunk`, `UploadResponse`, `ResponsePayload`, ...).
- **`application`** contains the actual business rules (how a document becomes chunks,
  how retrieval results get reranked and expanded, how curriculum metadata is inferred)
  without caring *how* embeddings are computed or *where* vectors are stored.
- **`infrastructure`** is the replaceable technical layer: swap ChromaDB for another
  vector store, or Ollama for another generation backend, by changing only the matching
  file here — `application` code calling it does not change.
- **`interfaces/api`** is the thinnest layer: HTTP wiring only. It builds the application
  services once at import time and translates HTTP requests/responses into calls against
  them.

## What changed vs. the previous `RAG/` layout

This is a reorganization (renamed/regrouped files, updated imports) merged with the
feature updates from the `New/` drop, not a rewrite of the business logic itself:

| Old path | New path |
|---|---|
| `src/models/schemas.py` | `src/domain/schemas.py` |
| `src/services/config.py` | `src/infrastructure/config.py` |
| `src/services/embeddings.py` | `src/infrastructure/embeddings.py` |
| `src/services/vector_store.py` | `src/infrastructure/vector_store.py` |
| `src/services/ranking.py` | `src/infrastructure/ranking.py` |
| `src/services/health.py` | `src/infrastructure/health.py` |
| `src/pipelines/document_loader.py` | `src/infrastructure/document_loader.py` |
| `src/pipelines/embedding_pipeline.py` | `src/application/ingestion_service.py` |
| `src/pipelines/generation_pipeline.py` | `src/application/generation.py` |
| `src/pipelines/retrieval_pipeline.py` | `src/application/retrieval_service.py` |
| `src/pipelines/chunking.py` | `src/application/chunking.py` |
| `src/services/curriculum_structure.py` | `src/application/curriculum_structure.py` |
| `src/services/document_metadata.py` | `src/application/document_metadata.py` |
| `src/services/hypothetical_questions.py` | `src/application/hypothetical_questions.py` |
| `src/services/metadata.py` | `src/application/metadata.py` |
| `src/services/session.py` | `src/application/session.py` |
| `src/app.py` | `src/interfaces/api/app.py` |
| — (new) | `src/infrastructure/ingest_registry.py` |
| — (new) | `src/interfaces/api/static/console.html` |

`src/utils/*` kept its location — it has no project-specific dependencies either way.

Everything under `docs/` (`PRODUCTION_FIXES.md`, `FIXES_SUMMARY_v2.md`, `FINAL_FIXES_V6.md`,
`VERIFIED_BUILD_NOTES.md`) is the historical fix log carried over unchanged from the
previous build and still references the old file paths — kept as-is for traceability;
the table above is the map from old to new.

## Merged from the `New/` update

- `term` (subject term/semester) extraction restored to the metadata contract, including
  a font-corruption-tolerant matcher for a known Arabic ligature bug (`document_metadata.py`).
- `text_quality_warning` flag surfaced when that font bug is detected, so a caller knows
  to prefer re-OCRing instead of trusting extracted text.
- `raw_text` included in each response source, and a bundled `/console` testing UI that
  displays it (click a `[n]` source chip under an answer to jump to its evidence).
- Content-hash upload deduplication (`ingest_registry.py` + `?force_reingest=true`).
- CORS middleware (permissive by default for local development — tighten before deploying
  publicly) and richer OpenAPI/Swagger UI metadata.
