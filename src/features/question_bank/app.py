"""Streamlit UI for generating questions with the shared Curriculum RAG service."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from src.features.question_bank import generate_questions_from_knowledge_graph, get_graph_entities, get_questions
from src.features.question_bank.config import (
    get_llm_model,
    get_openrouter_api_key,
    get_question_counts_by_difficulty,
)
from src.features.rag.application.question_bank_integration import QuestionBankRAG


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "question_bank"
UPLOADS_DIR = DATA_DIR / "uploads"
DEFAULT_GRAPH = next((DATA_DIR / "files" / "graph_dictionary_files").glob("*.json"), None)


def save_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> Path:
    """Persist an uploaded PDF until the shared RAG service accepts it."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    filename = Path(uploaded_file.name).name
    destination = UPLOADS_DIR / filename
    destination.write_bytes(uploaded_file.getbuffer())
    return destination


st.set_page_config(page_title="Questions Bank", page_icon=":books:", layout="centered")


@st.cache_resource
def get_rag() -> QuestionBankRAG:
    """One shared in-process RAG service for the Streamlit session."""
    return QuestionBankRAG()

if "rag_file_reference_id" not in st.session_state:
    st.session_state.rag_file_reference_id = ""

st.title("Questions Bank")
st.caption("PDF indexing and topic retrieval use the internal Curriculum RAG feature.")

with st.expander("Generation settings from .env"):
    st.write(f"Model: `{get_llm_model()}`")
    st.json({"questions_per_task_difficulty": get_question_counts_by_difficulty()})
    try:
        get_openrouter_api_key()
        st.success("OPENROUTER_API_KEY is configured.")
    except RuntimeError:
        st.warning("OPENROUTER_API_KEY is missing. Copy .env.example to .env and add the key before generation.")

st.header("1. Upload and index book")
uploaded_pdf = st.file_uploader("Book PDF", type=["pdf"])

manual_file_reference_id = st.text_input(
    "Existing RAG file_reference_id (optional)",
    value=st.session_state.rag_file_reference_id,
    placeholder="Paste an already indexed file_reference_id",
)
if manual_file_reference_id.strip() != st.session_state.rag_file_reference_id:
    st.session_state.rag_file_reference_id = manual_file_reference_id.strip()

if st.button("Index book in shared RAG", type="primary", disabled=uploaded_pdf is None):
    try:
        pdf_path = save_uploaded_file(uploaded_pdf)
        status = st.status("Sending the book to Curriculum RAG...", expanded=True)
        result = get_rag().index_file(pdf_path)
        file_reference_id = str(result.get("file_reference_id") or "").strip()
        if not file_reference_id:
            raise RuntimeError("RAG indexing completed without returning file_reference_id.")

        st.session_state.rag_file_reference_id = file_reference_id
        indexed_chunks = result.get("indexed_chunks", result.get("chunks_created", 0))
        status.update(label="Book is indexed in shared RAG", state="complete", expanded=False)
        st.success(f"Book is ready. file_reference_id: `{file_reference_id}`. Indexed chunks: {indexed_chunks}.")
    except Exception as exc:
        st.error(f"Book indexing failed: {exc}")

if st.session_state.rag_file_reference_id:
    st.info(f"Active RAG file_reference_id: `{st.session_state.rag_file_reference_id}`")

st.divider()
st.header("2. Generate questions")
grade = st.text_input("Grade", placeholder="Example: Grade 5")
subject = st.text_input("Subject", placeholder="Example: Mathematics")
graph_upload = st.file_uploader("Knowledge Graph (JSON) - optional", type=["json"])

graph_source: dict | Path | None = None
if graph_upload is not None:
    try:
        graph_source = json.loads(graph_upload.getvalue().decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        st.error(f"Invalid Knowledge Graph JSON: {exc}")
elif DEFAULT_GRAPH is not None:
    graph_source = DEFAULT_GRAPH

selected_entity_ids: list[str] = []
if graph_source is not None:
    try:
        graph_entities = get_graph_entities(graph_source)
        entity_labels = {f"{entity['name']}  [{entity['id']}]": entity["id"] for entity in graph_entities}
        selected_labels = st.multiselect(
            "Choose entities to generate questions for",
            options=list(entity_labels),
            placeholder="Select one or more topics",
        )
        selected_entity_ids = [entity_labels[label] for label in selected_labels]
        st.caption(f"Selected {len(selected_entity_ids)} of {len(graph_entities)} entities.")
    except (OSError, ValueError, TypeError) as exc:
        st.error(f"Could not read the Knowledge Graph: {exc}")
else:
    st.warning("No Knowledge Graph JSON was uploaded and no default graph file was found.")

can_generate = bool(
    grade.strip()
    and subject.strip()
    and graph_source is not None
    and selected_entity_ids
    and st.session_state.rag_file_reference_id.strip()
)

if st.button("Generate and save questions", disabled=not can_generate):
    try:
        get_openrouter_api_key()
        with st.spinner("Retrieving evidence from the internal RAG and generating questions for each topic..."):
            paths = generate_questions_from_knowledge_graph(
                graph_source,
                grade,
                subject,
                entity_ids=selected_entity_ids,
                rag_file_reference_id=st.session_state.rag_file_reference_id,
                retriever=lambda topic: get_rag().retrieve_topic(
                    topic, st.session_state.rag_file_reference_id
                ),
            )
        st.success(f"Saved {len(paths)} topic files inside question_bank.")
        st.code("\n".join(str(path) for path in paths[:10]))
    except Exception as exc:
        st.error(f"Question generation failed: {exc}")

st.divider()
st.header("3. Retrieve saved questions")
topic = st.text_input("Topic name or id", placeholder="Example: algebra")
if st.button("Retrieve questions", disabled=not (grade.strip() and subject.strip() and topic.strip())):
    questions = get_questions(grade, subject, topic)
    if questions:
        st.success(f"Found {len(questions)} questions.")
        st.json(questions)
    else:
        st.info("No saved questions match these values yet.")
