# Educational App

Question Bank and Curriculum RAG run as one application, with two ways to
drive them:

- **Streamlit** (`main.py`) — the internal/admin tool: upload a book, watch
  the Knowledge Graph → RAG → question-generation pipeline run live, and
  run test exams from a browser UI.
- **Mobile API** (`api_main.py`) — an HTTP/JSON surface over the exact same
  pipeline, for a real mobile app: process a book as a background job, list
  processed books, and run the student exam flow (start → answer → report).

Both entrypoints share the same `.env`, the same `data/` directories, and
the same in-process feature code (RAG, Knowledge Graph, Question Bank,
Assessment) — no HTTP boundary between features internally. You can run
either one on its own, or both at once on different ports.

## Setup

From the repository root, create/update the single environment:

```powershell
uv sync
```

Copy `.env.example` to `.env` and set `OPENROUTER_API_KEY` (required for
Knowledge Graph generation, question generation, and exam report
generation — `uv sync` is enough on its own, there is no separate package
to install for Knowledge Graph generation) plus any other values you want
to override.

### How Knowledge Graph generation works

Turning a new PDF into a Knowledge Graph (`POST /books`, or "Process book"
in the Streamlit tool) is a native pipeline over the same OpenRouter LLM
everything else in the app already calls — question generation, exam
reports, etc. — not a separate package or service:

1. Extract the PDF's text page by page.
2. Split it into bounded chunks (`KNOWLEDGE_GRAPH_CHUNK_CHAR_BUDGET`
   characters each, default 12,000) so one very long book is many bounded
   LLM calls instead of one call that overflows the model's context window.
3. One LLM call per chunk extracts the topics/concepts it covers.
4. Topics are merged/deduped by name across all chunks and given stable ids.
5. One further LLM call proposes `subsetOf`/`prerequisiteOf` relationships
   between the merged topics.

See `src/features/knowledge_graph/infrastructure/graph_extractor.py` for
the implementation. An earlier version of this pipeline depended on an
external `semantica_graph` package installed from a local path outside
this repo — that attempt has been dropped in favor of the native pipeline
above, so `uv sync` on a fresh machine no longer depends on anyone else's
local folder existing.

## Running the Streamlit tool

```powershell
uv run streamlit run main.py
```

Or, after activating the same root `.venv`:

```powershell
streamlit run main.py
```

UI available at `http://localhost:8501`.

## Running the Mobile API

```powershell
uv run python api_main.py
```

Or, after activating the same root `.venv`:

```powershell
uvicorn api_main:app --host 0.0.0.0 --port 8000
```

Interactive docs (Swagger UI) at `http://localhost:8000/docs`. Full request/
response reference, with examples for every endpoint, is in
[`docs/mobile-api.md`](docs/mobile-api.md).

### Endpoints

| Method | Path                           | Purpose |
|--------|--------------------------------|---------|
| POST   | `/books`                       | Upload a book → returns a `job_id` immediately (async; see below) |
| GET    | `/books/jobs/{job_id}`         | Poll a book-processing job's status |
| GET    | `/books`                       | List already-processed books (feeds the book picker) |
| GET    | `/books/{content_hash}/topics` | Topics available for one processed book |
| POST   | `/exams`                       | Start an exam: `{student_id, grade, subject, content_hash}` |
| GET    | `/exams/{exam_id}`             | Current exam state (read-only — for resuming/polling, no side effects) |
| POST   | `/exams/{exam_id}/answers`     | Submit an answer → next question or final results |
| GET    | `/exams/{exam_id}/report`      | Final LLM-generated report |

`POST /books` never blocks on the Knowledge Graph + RAG indexing + question
generation pipeline (typically 5-8 minutes) — that's fine for the internal
Streamlit spinner, but not for an HTTP endpoint a mobile app calls. It saves
the file, queues the pipeline on a background thread, and returns a
`job_id` right away. Poll `GET /books/jobs/{job_id}` until `status` is
`"done"` or `"failed"`; status moves through
`queued → generating_kg → indexing → generating_questions → done`.

### Notes / current limitations

- No authentication yet — any caller can hit any endpoint, including
  processing a new book. Add auth before exposing this outside a trusted
  network.
- Book-processing jobs and exam sessions are both kept in memory
  (per-process). They do not survive a process restart, and won't be
  shared across multiple API instances behind a load balancer without
  moving them to shared storage (e.g. Redis/DB).

## Structure

```text
educational_App/
├── main.py                     # Streamlit entrypoint (internal/admin tool)
├── api_main.py                 # Mobile API entrypoint (FastAPI/uvicorn)
├── .env
├── pyproject.toml
├── docs/
│   └── mobile-api.md           # Full mobile API reference (requests/responses/examples)
├── src/
│   ├── features/
│   │   ├── rag/                          # indexing, embeddings, vector storage, retrieval
│   │   ├── knowledge_graph/              # PDF -> Knowledge Graph generation
│   │   ├── assessment/                   # adaptive exam state machine + reports
│   │   └── question_bank/
│   │       ├── app.py                    # Streamlit UI
│   │       ├── book_library.py           # registry of processed books
│   │       ├── questions_service.py      # graph-based question generation
│   │       └── interfaces/api/           # mobile API (books + exams)
│   └── shared/             # future cross-feature contracts/utilities
├── data/
│   ├── rag/
│   └── question_bank/
└── tests/
    └── rag/
```

There is one active `.env` at the repository root.
