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

## Run it

**Prerequisites:** Python **3.11** (required on Windows for ChromaDB), [Ollama](https://ollama.com) installed locally (or a Groq
API key if you'd rather use that as the generation backend).

1. **Open a terminal in the project folder**

2. **Install `uv`, then create a virtual environment**

   ```bash
   pip install uv
   uv venv --python 3.11
   ```

3. **Install dependencies**

   ```bash
   uv pip install -r requirements.txt
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

6. **Run the API**

   ```bash
   uv run --with-requirements requirements.txt uvicorn src.interfaces.api.app:app --reload
   ```

   The API is now at `http://127.0.0.1:8000` — interactive docs at
   `http://127.0.0.1:8000/docs`, and the testing console at `http://127.0.0.1:8000/console`.

7. **Run the tests** — open the **Testing** panel in VS Code's left sidebar (flask icon),
   or from the terminal:

   ```bash
   uv run --with-requirements requirements.txt pytest -q
   ```

## Generation backend

This service uses **Groq** for generation by default (cloud, OpenAI-compatible, fast).
Set `GROQ_API_KEY` in `.env` — get one from https://console.groq.com/keys. The model used
is controlled by `GROQ_MODEL` (defaults to `openai/gpt-oss-120b`).

If `GROQ_API_KEY` is unset and `ALLOW_EXTRACTIVE_FALLBACK=true`, the service falls back to
an extractive answer (the top retrieved passage) instead of a real generated one.

### Alternative: Ollama (fully local)

Set `GENERATION_BACKEND=ollama` and `OLLAMA_MODEL=<your-model>` in `.env`, then:

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
