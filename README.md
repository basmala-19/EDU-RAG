# Curriculum RAG — Production RAG Engine & API

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Production-grade Educational Retrieval-Augmented Generation (RAG) system engineered for Arabic, English, and mixed-language curriculum textbooks. Features **LlamaParse Agentic OCR**, **Hybrid Dense/BM25 Search**, **Cross-Encoder Reranking**, **Parent-Child Context Expansion**, **RAGAS Quality Metrics**, and an **Interactive Web Console with Embedded PDF Reader**.

---

## 🌟 Key Features

* **High-Fidelity Document Ingestion**: Native support for complex PDF and DOCX curriculum books using LlamaParse Tier 2 (Agentic OCR) for Arabic font-ligature handling and table layout extraction.
* **Hybrid Retrieval Pipeline**: Combines Vector Similarity (`BAAI/bge-m3`), Lexical BM25 Keyword Search, and Synthetic Question Indexing with Reciprocal Rank Fusion (RRF).
* **Cross-Encoder Reranking**: Re-scores candidate evidence chunks using `bge-reranker-v2-m3` or `cohere/rerank-v3.5`.
* **Parent-Child Context Expansion**: Retains fine-grained child chunk embeddings (~650 chars) while supplying full parent chunk context (~1600 chars) to LLM generation.
* **Built-in RAGAS Evaluation**: Automatic real-time evaluation computing Faithfulness, Answer Relevance, Context Precision, Context Recall, and overall RAGAS score for every query turn.
* **Interactive Testing Console**: Complete web console (`/console`) featuring live chat, RAG hyperparameter sliders, real-time RAGAS evaluation gauges, and an **Embedded PDF Viewer** that jumps straight to cited book pages.

---

## 🏗 System Architecture

```text
               +-------------------------------------------------------+
               |                  Uploaded Document                    |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |    LlamaParse Agentic OCR & Document Loader          |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |       Hierarchy-Aware Parent-Child Chunking          |
               |  (Child: ~650 chars | Parent Context: ~1600 chars)   |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |     Multilingual Embeddings (BGE-M3 / OpenRouter)     |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |   ChromaDB Vector Store + Question Indexing Engine   |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |     Hybrid Search + Cross-Encoder Reranker + RRF      |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |     LLM Generation (Groq / OpenRouter / Ollama)       |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |   RAGAS Evaluation & Evidence Citation Payload       |
               +-------------------------------------------------------+
```

---

## 📋 Prerequisites

* **OS**: Windows / Linux / macOS
* **Python**: Python **3.11.x** (Required for ChromaDB native compatibility)
* **API Keys**:
  * [Llama Cloud Key](https://cloud.llamaindex.ai/) (For high-fidelity LlamaParse PDF OCR)
  * [Groq Key](https://console.groq.com/) or [OpenRouter Key](https://openrouter.ai/) (For LLM generation and cloud retrieval)

---

## ⚡ Quick Start & Setup

### 1. Clone the Repository & Navigate to Workspace

```powershell
# Replace <project_root> with the path to the cloned repository
cd <project_root>
```

### 2. Create & Activate Virtual Environment

**Windows (PowerShell):**

```powershell
python -m venv .venv
.\.venv\Scripts\activate
```

**Linux / macOS:**

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 🔁 Setting up the Virtual Environment (PowerShell)

If you are using the project for the first time, run the following commands **inside `<project_root>`**:

```powershell
# 1. Create a fresh virtual environment
python -m venv .venv

# 2. Activate the new environment (PowerShell)
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install the project in editable mode with test extras
pip install -e "[test]"

# 5. Run the test suite to verify everything works
python -m pytest -q
```

> **Note:** If `Remove-Item` reports that the folder is in use, close the current PowerShell session, open a new one in `<project_root>`, and run the removal command again.

### 4. Configure Environment Variables (`.env`)

Copy `.env.example` to `.env`:
```powershell
cp .env.example .env
```

Open `.env` in any text editor and fill in your API keys:

```env
APP_ENV=local
LOG_LEVEL=INFO
CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000

# Retrieval & Embeddings Configuration
EMBEDDING_BACKEND=openrouter
EMBEDDING_MODEL=baai/bge-m3
RERANKER_BACKEND=openrouter
RERANKER_MODEL=cohere/rerank-v3.5
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Generation Configuration (Groq / OpenRouter / Ollama)
GENERATION_BACKEND=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

# PDF Parsing (LlamaParse OCR)
LLAMA_CLOUD_API_KEY=your_llama_cloud_api_key_here
LLAMA_PARSE_ENABLED=true

# Vector Store Path
VECTOR_STORE=chroma
CHROMA_PATH=data/vector_store/chroma
```

---

## 🚀 Running the API Server

Start the Uvicorn ASGI server with live reload:

```powershell
.venv\Scripts\python -m uvicorn src.interfaces.api.app:app --reload --host 127.0.0.1 --port 8000
```

Once running, access the following endpoints:

* **Interactive Web Console**: [`http://127.0.0.1:8000/console`](http://127.0.0.1:8000/console)
* **OpenAPI / Swagger Documentation**: [`http://127.0.0.1:8000/docs`](http://127.0.0.1:8000/docs)
* **Health Check**: [`http://127.0.0.1:8000/api/rag/health`](http://127.0.0.1:8000/api/rag/health)

---

## 🧪 Running Unit & Integration Tests

Run the full pytest suite:

```powershell
.venv\Scripts\pytest tests/unit
```

---

## 📡 API Endpoint Overview

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/rag/health` | `GET` | Service readiness & embedding backend status. |
| `/api/rag/upload` | `POST` | Upload PDF/DOCX file and trigger background indexing. |
| `/api/rag/ingestion-jobs/{job_id}` | `GET` | Poll status of asynchronous ingestion jobs. |
| `/api/rag/response` | `POST` | Primary RAG endpoint (retrieval + reranking + generation + RAGAS evaluation). |
| `/api/rag/evaluate` | `POST` | Standalone RAG evaluation endpoint for benchmarking. |
| `/api/rag/files/{file_reference_id}` | `GET` | Serves indexed PDF files inline for page-level viewing. |
| `/console` | `GET` | Bundled Web Console playground. |
| `/docs` | `GET` | Interactive Swagger API documentation. |

---

## 📄 License

This project is licensed under the MIT License.
