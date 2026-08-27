# Educational App

Question Bank and Curriculum RAG run as one Streamlit application. The two
feature folders remain separate, but Question Bank calls the RAG feature
directly in-process (no local HTTP service is started).

From the repository root, create/update the single environment and run:

```powershell
uv sync
uv run streamlit run main.py
```

Or, after activating the same root `.venv`:

```powershell
streamlit run main.py
```

The only UI is available at `http://localhost:8501`.

## Structure

```text
educational_App/
├── main.py
├── .env
├── pyproject.toml
├── src/
│   ├── features/
│   │   ├── rag/            # indexing, embeddings, vector storage, retrieval
│   │   └── question_bank/  # Streamlit UI and graph-based question generation
│   └── shared/             # future cross-feature contracts/utilities
├── data/
│   ├── rag/
│   └── question_bank/
└── tests/
    └── rag/
```

There is one active `.env` at the repository root.
