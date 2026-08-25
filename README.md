# Curriculum RAG

Local-first educational RAG for Arabic/English/mixed curriculum documents, organized as
a clean-architecture FastAPI service. See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the
full layer breakdown and a map from the previous `src/services` / `src/pipelines` layout
to the current one.

## Public API

- `GET /api/rag/health` — readiness of embeddings + vector store.
- `POST /api/rag/upload` — file only; backend generates `file_reference_id`, `curriculum_id`,
  and `version`. Duplicate content (by hash) is detected and skipped unless
  `?force_reingest=true` is passed.
- `GET /api/rag/structure` — discover indexed subjects → grades → chapters/lessons.
- `POST /api/rag/response` — learning-session context + retrieval + reranking + parent
  expansion + Ollama/Groq generation.
- `GET /console` — a bundled, self-contained testing console (upload a book, chat with it,
  inspect the exact evidence text behind each answer).

There is intentionally no public `/api/rag/ingest`, `/api/rag/retrieve`, Graph `node_id`,
or Graph resolver.

## Architecture

```text
Upload
  ↓
LlamaParse / local loaders  (src/infrastructure/document_loader.py)
  ↓
Document metadata            (src/application/document_metadata.py)
  ↓
Hierarchy-aware Parent/Child Chunking (src/application/chunking.py)
  ├─ child (~650 chars) → embedding + retrieval
  └─ parent (~1600 chars) → context expansion
  ↓
Multilingual embeddings (BGE-M3)     (src/infrastructure/embeddings.py)
  ↓
ChromaDB / local-JSON fallback       (src/infrastructure/vector_store.py)
  ↓
Dense retrieval + Question Index     (src/application/retrieval_service.py)
  ↓
BGE reranking + dedup                (src/infrastructure/ranking.py)
  ↓
Parent context expansion
  ↓
Learning Session context             (src/application/session.py)
  ↓
Ollama / Groq generation             (src/application/generation.py)
  ↓
Grounded response + evidence sources
```

## Run it — VS Code

**Prerequisites:** Python 3.11+, [Ollama](https://ollama.com) installed locally (or a Groq
API key if you'd rather use that as the generation backend).

1. **Open the folder in VS Code**
   `File → Open Folder…` → select `CurriculumRAG/`.
   Install the Microsoft **Python** extension if prompted.

2. **Create and select a virtual environment**
   Open a terminal in VS Code (`` Ctrl+` ``) and run:

   ```bash
   python -m venv .venv
   ```

   Then `Ctrl+Shift+P` → **Python: Select Interpreter** → pick `.venv`. VS Code will use
   this venv for every terminal you open afterward, and for the built-in test runner.

3. **Install dependencies**

   ```bash
   pip install -e ".[test]"
   ```

4. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   Open `.env` and set at least:
   - `OLLAMA_MODEL` — a model you've pulled locally (see step 5), e.g. `llama3.2:3b`.
   - Leave `LLAMA_CLOUD_API_KEY` empty to use the local parsers only, or set it if you
     have a [LlamaParse](https://www.llamaindex.ai/llamaparse) key for higher-fidelity
     PDF parsing.
   - `GROQ_API_KEY` (optional) — set this and `GENERATION_BACKEND=groq` in `.env` instead
     of Ollama if you'd rather use a hosted model.

5. **Start Ollama and pull a model** (skip if using Groq instead)

   ```bash
   ollama pull llama3.2:3b
   ollama serve
   ```

   Check it's running with `ollama ps` in another terminal.

6. **Run the API** — either:
   - Press **F5** (uses the `.vscode/launch.json` config included in this project), or
   - From the terminal:
     ```bash
     uvicorn src.interfaces.api.app:app --reload
     ```

   The API is now at `http://127.0.0.1:8000` — interactive docs at
   `http://127.0.0.1:8000/docs`, and the testing console at `http://127.0.0.1:8000/console`.

7. **Run the tests** — open the **Testing** panel in VS Code's left sidebar (flask icon),
   or from the terminal:

   ```bash
   pytest -q
   ```

### Alternative: Docker

```bash
docker compose up --build
```

Same `.env` file is used; the API is published on `http://localhost:8000`.

## Ollama

This service uses Ollama for generation by default so it can stay fully local and avoid
a paid API during development.

```bash
ollama pull <your-model>
ollama run <your-model>
```

Check where the model is running with:

```bash
ollama ps
```

For CPU-only development, keep the model small and keep the RAG context bounded. The
service does not assume a large local model, and falls back to an extractive answer if
Ollama is unavailable and `ALLOW_EXTRACTIVE_FALLBACK=true`.

## Learning Session

`session_id` is runtime session state, not document/chunk metadata. A session is bound to
one `file_reference_id` and can carry optional `subject`, `grade`, `chapter`, `lesson`,
and `section` context plus a bounded conversation history.

## Metadata

Document metadata contains:

- `document_title`
- `subject`
- `grade`
- `term` — extracted only from the document's own text (never from filename or overrides).
- `language`
- `text_quality_warning` — set to `arabic_font_ligature_corruption` when the source PDF's
  embedded font is known to garble Arabic text extraction, signalling that the document
  should be re-uploaded via OCR rather than trusted as-is.

Chunk metadata contains source/page/heading/heading_path/content_type and backend-owned
`file_reference_id`, `curriculum_id`, and `version`.

## Chunking rationale

Parent/child retrieval is used to address the retrieval/context trade-off: smaller child
chunks are used for precise matching while larger parent sections are returned for
generation context. This avoids choosing a single global chunk size that is either too
broad or too fragmented.

## Upload deduplication

Uploads are hashed by content (not filename). Re-uploading a file that's already indexed
returns the original `curriculum_id`/`file_reference_id` with `duplicate: true` and skips
re-processing. Pass `?force_reingest=true` to index it again anyway.

## Security note

`.env` is git-ignored and **not** included in this project — copy `.env.example` and fill
in your own keys. Never commit a real `LLAMA_CLOUD_API_KEY` or `GROQ_API_KEY`.
