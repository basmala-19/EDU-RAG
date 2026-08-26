# Curriculum RAG — Production Multilingual Educational Engine & API

[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![RAGAS Evaluation](https://img.shields.io/badge/RAGAS-Calibrated-teal.svg)](https://github.com/explodinggradients/ragas)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade, domain-isolated Retrieval-Augmented Generation (RAG) system engineered specifically for Arabic, English, and bilingual curriculum textbooks. Built with **Agentic OCR Repair**, **Dense Vector + BM25 Lexical + Question Index Hybrid Search**, **Cross-Encoder Reranking**, **Parent-Child Context Expansion**, **Calibrated RAGAS Metrics**, and an **Interactive Web Console with Embedded PDF Reader & Claim Highlighting**.

---

## 🌟 Key Architecture & Capabilities

* 🌐 **Universal Multilingual Support**: Fully calibrated for Arabic, English, and mixed-language textbooks with native handling of Arabic ligatures, font-encoding fixes, and English inflectional stemming.
* 📄 **High-Fidelity Document Ingestion**: Supports PDF and DOCX curriculum books using LlamaParse Tier 2 (Agentic OCR) for table layout preservation and complex mathematical typography.
* 🔍 **Multi-Channel Hybrid Retrieval**:
  * **Dense Vector Search**: Semantic retrieval powered by `BAAI/bge-m3`.
  * **Sparse Lexical Search**: Stem-aware BM25 keyword matching.
  * **Synthetic Question Index**: Pre-indexed hypothetical student questions per chunk.
  * **Reciprocal Rank Fusion (RRF)**: Rebalanced fusion preserving conceptual matches even with zero literal keyword overlap.
* 🎯 **Cross-Encoder Reranking**: Re-ranks top candidates via `cohere/rerank-v3.5` (OpenRouter) or local `bge-reranker-v2-m3`.
* 🧩 **Parent-Child Context Expansion**: Matches fine-grained child chunks (~650 chars) while providing full parent chunk context (~1600 chars) to the LLM.
* 🧠 **Smart Session Tracking**: Prevents topic pollution across multi-turn queries while preserving conversational follow-ups.
* 🏆 **Real-Time Calibrated RAGAS Evaluation**: Automatically evaluates every response turn for **Faithfulness**, **Answer Relevance**, **Context Precision**, and **Context Recall** with zero-hallucination out-of-scope refusals.
* 💻 **Interactive Testing Console (`/console`)**: Full-featured web playground with book selection, right-panel expander, PDF zoom/page navigation, and **Smart Evidence Claim Highlighting**.

---

## 🏗 System Pipeline

```text
               +-------------------------------------------------------+
               |         Curriculum Document (PDF / DOCX)              |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |     LlamaParse Agentic OCR & Document Structure       |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |       Hierarchy-Aware Parent-Child Chunking           |
               |  (Child: ~650 chars | Parent Context: ~1600 chars)    |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |     Multilingual Embeddings (BGE-M3 / OpenRouter)     |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |   ChromaDB Vector Store + BM25 + QA Question Index    |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |   Hybrid RRF Fusion + Cross-Encoder Reranking (Cohere)|
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |       LLM Generation (Groq / OpenRouter / Ollama)     |
               +-------------------------------------------------------+
                                           |
                                           v
               +-------------------------------------------------------+
               |   RAGAS Evaluation & Evidence Citation Payload        |
               +-------------------------------------------------------+
```

---

## 📋 Prerequisites

* **Operating System**: Windows / Linux / macOS
* **Python**: Python **3.11.x** (Recommended for ChromaDB and NumPy compatibility)
* **API Keys** (Configured in `.env`):
  * **Llama Cloud API Key**: For PDF OCR & layout parsing ([Get Key](https://cloud.llamaindex.ai/))
  * **OpenRouter API Key** or **Groq API Key**: For LLM generation & Cross-Encoder reranking ([OpenRouter](https://openrouter.ai/) / [Groq](https://console.groq.com/))

---

## ⚡ Quick Start & Installation

### 1. Clone & Open Workspace

```powershell
git clone <repository_url>
cd EDU-RAG-main
```

### 2. Set Up Virtual Environment

**Windows (PowerShell):**
```powershell
# Create virtual environment
python -m venv .venv

# Enable execution policy and activate
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1

# Upgrade pip
python -m pip install --upgrade pip
```

**Linux / macOS:**
```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

### 3. Install Dependencies

```powershell
# Install project dependencies in editable mode with test extras
pip install -e ".[test]"
```
*(Or alternatively: `pip install -r requirements.txt`)*

### 4. Configure Environment Variables (`.env`)

Create your `.env` file from the template:

```powershell
cp .env.example .env
```

Open `.env` and configure your API credentials:

```env
APP_ENV=local
LOG_LEVEL=INFO
CORS_ORIGINS=http://127.0.0.1:8000,http://localhost:8000

# Embeddings & Reranker Configuration
EMBEDDING_BACKEND=openrouter
EMBEDDING_MODEL=baai/bge-m3
RERANKER_BACKEND=openrouter
RERANKER_MODEL=cohere/rerank-v3.5
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Generation Backend (Groq / OpenRouter / Ollama)
GENERATION_BACKEND=groq
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-120b

# Document Parsing (LlamaParse OCR)
LLAMA_CLOUD_API_KEY=your_llama_cloud_api_key_here
LLAMA_PARSE_ENABLED=true

# Persistence
VECTOR_STORE=chroma
CHROMA_PATH=data/vector_store/chroma
```

---

## 🚀 Running the API Server

Launch the FastAPI application with live hot-reload:

```powershell
python -m uvicorn src.interfaces.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Once started, access:
* 🖥️ **Interactive Web Console**: [http://127.0.0.1:8000/console](http://127.0.0.1:8000/console)
* 📜 **Swagger OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* 🩺 **Health Check**: [http://127.0.0.1:8000/api/rag/health](http://127.0.0.1:8000/api/rag/health)

---

## 🧪 Running Automated Tests

Run the complete test suite (all 78 unit & integration tests):

```powershell
python -m pytest
```

Run tests with concise output:
```powershell
python -m pytest -q
```

---

## 📡 REST API Specifications

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/rag/health` | Health check & embedding service status. |
| `POST` | `/api/rag/upload` | Upload and ingest a curriculum textbook (PDF/DOCX). |
| `GET` | `/api/rag/ingestion-jobs/{job_id}` | Poll asynchronous ingestion status and metadata. |
| `GET` | `/api/rag/books` | List all previously indexed curriculum documents. |
| `POST` | `/api/rag/response` | Primary RAG endpoint (Retrieval + Rerank + LLM + RAGAS). |
| `POST` | `/api/rag/evaluate` | Standalone RAGAS evaluation endpoint. |
| `GET` | `/api/rag/files/{file_reference_id}` | Stream indexed PDF for embedded page-level viewing. |
| `GET` | `/api/rag/conversations` | List saved learning sessions and turn history. |
| `GET` | `/api/rag/conversations/{session_id}` | Retrieve full conversation turn logs and evidence. |
| `GET` | `/console` | Interactive web testing console. |
| `GET` | `/docs` | Interactive Swagger API documentation. |

---

## 💡 Example Request & Response

### Request:
```bash
curl -X POST "http://127.0.0.1:8000/api/rag/response" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ما العلاقة بين سرعة الموجة وطولها الموجي وترددها؟",
    "file_reference_id": "0567486a32785a3d6e708f40dbf2cff7",
    "top_k": 5
  }'
```

### Response:
```json
{
  "session_id": "sess_a8b9c1d2e3f4",
  "curriculum_id": "cur_physics_sec1",
  "file_reference_id": "0567486a32785a3d6e708f40dbf2cff7",
  "answer": "سرعة الموجة تساوي حاصل ضرب ترددها في طولها الموجي، أي أن v = f λ. ويمكن أيضاً كتابة العلاقة على شكل v = λ / T حيث T هو الزمن الدوري للموجة.",
  "answer_status": "answered",
  "grounded": true,
  "sources": [
    {
      "chunk_id": "chunk_109_1",
      "page": 109,
      "heading": "الموجات الجيبية",
      "score": 0.92,
      "retrieval_confidence": 0.94,
      "reranker_score": 0.91
    }
  ],
  "evaluation": {
    "faithfulness_score": 0.96,
    "context_precision": 0.92,
    "context_recall": 0.94,
    "answer_relevance": 0.95,
    "overall_ragas_score": 0.945,
    "verdict": "PASS"
  }
}
```

---

## 📁 Directory Structure

```text
EDU-RAG-main/
├── data/
│   ├── conversations/        # Per-session JSON conversation logs
│   ├── vector_store/         # ChromaDB persistence & indices
│   └── ingest_registry.json  # Document deduplication registry
├── src/
│   ├── application/          # Chunking, Generation, Session & Evaluation
│   ├── domain/               # Pydantic schemas & entity definitions
│   ├── infrastructure/       # Embeddings, Vector Store, Ranking & AR Text
│   ├── interfaces/api/       # FastAPI application & Web Console UI
│   └── utils/                # Logging & file helpers
├── tests/
│   ├── integration/          # End-to-end pipeline tests
│   └── unit/                 # Unit tests (78 tests)
├── pyproject.toml            # Build configuration & dependencies
├── README.md                 # Project documentation
└── requirements.txt          # Python package requirements
```

---

## 📄 License

This project is licensed under the **MIT License**.
