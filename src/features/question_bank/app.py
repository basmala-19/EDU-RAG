"""Streamlit UI for generating questions with the shared Curriculum RAG service.

Everything the page draws lives inside ``render()``. ``main.py`` calls this
function on every Streamlit rerun. If this code were left at module level
instead, Python's module cache would make ``import ...app`` a no-op after the
first run (Streamlit reruns the whole script on every interaction, but Python
only executes a module's top-level code once per process) - the page would
render once and then go blank on the very next interaction, since none of
the st.* calls below would execute again.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import streamlit as st

from src.features.assessment.application.assessment_service import get_assessment_service
from src.features.knowledge_graph.application.graph_service import KnowledgeGraphService
from src.features.question_bank import book_library, generate_questions_from_knowledge_graph, get_graph_entities, get_questions
from src.features.question_bank.config import (
    get_llm_model,
    get_openrouter_api_key,
    get_question_counts_by_difficulty,
)
from src.features.question_bank.log_handler import configure_app_logging, render_log_panel
from src.features.rag.application.question_bank_integration import QuestionBankRAG


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "question_bank"
UPLOADS_DIR = DATA_DIR / "uploads"
DEFAULT_GRAPH = next((DATA_DIR / "files" / "graph_dictionary_files").glob("*.json"), None)

logger = logging.getLogger(__name__)


def save_uploaded_file(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> Path:
    """Persist an uploaded PDF until the shared RAG service accepts it."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    filename = Path(uploaded_file.name).name
    destination = UPLOADS_DIR / filename
    destination.write_bytes(uploaded_file.getbuffer())
    return destination


@st.cache_resource
def get_rag() -> QuestionBankRAG:
    """One shared in-process RAG service for the Streamlit session."""
    return QuestionBankRAG()


@st.cache_resource
def get_knowledge_graph_service() -> KnowledgeGraphService:
    """One shared in-process Knowledge Graph service for the Streamlit session."""
    return KnowledgeGraphService()


def _reset_exam_state() -> None:
    st.session_state.exam_id = None
    st.session_state.exam_status = None
    st.session_state.exam_current_question = None
    st.session_state.exam_results = None
    st.session_state.exam_report = None


def render() -> None:
    st.set_page_config(page_title="Questions Bank", page_icon=":books:", layout="centered")

    # Re-attach the log handler every run (cheap, idempotent) so log lines
    # from this run's steps are captured and shown in the panel below.
    configure_app_logging()

    if "rag_file_reference_id" not in st.session_state:
        st.session_state.rag_file_reference_id = ""
    if "rag_knowledge_graph" not in st.session_state:
        st.session_state.rag_knowledge_graph = None
    if "rag_knowledge_graph_source_name" not in st.session_state:
        st.session_state.rag_knowledge_graph_source_name = ""
    if "exam_id" not in st.session_state:
        st.session_state.exam_id = None
    if "exam_status" not in st.session_state:
        st.session_state.exam_status = None  # None | "in_progress" | "finished"
    if "exam_current_question" not in st.session_state:
        st.session_state.exam_current_question = None
    if "exam_results" not in st.session_state:
        st.session_state.exam_results = None
    if "exam_report" not in st.session_state:
        st.session_state.exam_report = None

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

    st.header("1. Choose a book")

    library_books = book_library.list_books()
    UPLOAD_NEW_LABEL = "📤 Upload a new book"
    book_options = [UPLOAD_NEW_LABEL] + [
        f"{b['filename']} — {b['grade']} / {b['subject']} "
        f"({b['topics_generated']} topics, {b['entity_count']} entities)"
        for b in library_books
    ]
    selected_book_label = st.selectbox(
        "Use an already-processed book, or upload a new one",
        options=book_options,
    )
    using_existing_book = selected_book_label != UPLOAD_NEW_LABEL

    if using_existing_book:
        selected_book = library_books[book_options.index(selected_book_label) - 1]
        if st.session_state.rag_file_reference_id != selected_book["rag_file_reference_id"]:
            logger.info(
                "Selected existing book from library: '%s' (grade=%s subject=%s)",
                selected_book["filename"], selected_book["grade"], selected_book["subject"],
            )
            st.session_state.rag_file_reference_id = selected_book["rag_file_reference_id"]
            st.session_state.rag_knowledge_graph = selected_book["knowledge_graph"]
            st.session_state.rag_knowledge_graph_source_name = selected_book["filename"]
        grade = selected_book["grade"]
        subject = selected_book["subject"]
        st.success(
            f"Using **{selected_book['filename']}** — {grade} / {subject}. "
            f"Processed {selected_book['processed_at'][:10]}. Ready to run an exam below."
        )
        st.caption(f"file_reference_id: `{selected_book['rag_file_reference_id']}`")
        graph_source: dict | Path | None = st.session_state.rag_knowledge_graph
    else:
        st.subheader("Upload & process book")
        st.caption(
            "Uploading runs the whole pipeline automatically: Knowledge Graph -> RAG indexing "
            "(chunking, embedding, vector store) -> question generation for every topic in the graph. "
            "Once it finishes, the system is ready to run an exam - no extra manual steps."
        )
        uploaded_pdf = st.file_uploader("Book PDF", type=["pdf"])
        grade = st.text_input("Grade", placeholder="Example: Grade 5")
        subject = st.text_input("Subject", placeholder="Example: Mathematics")

        graph_source: dict | Path | None = st.session_state.rag_knowledge_graph
        with st.expander("Advanced: overrides"):
            manual_file_reference_id = st.text_input(
                "Existing RAG file_reference_id (skip re-indexing)",
                value=st.session_state.rag_file_reference_id,
                placeholder="Paste an already indexed file_reference_id",
            )
            if manual_file_reference_id.strip() != st.session_state.rag_file_reference_id:
                st.session_state.rag_file_reference_id = manual_file_reference_id.strip()

            graph_upload = st.file_uploader("Knowledge Graph (JSON) - use instead of auto-generating", type=["json"])
            if graph_upload is not None:
                try:
                    graph_source = json.loads(graph_upload.getvalue().decode("utf-8"))
                    st.caption("Using the uploaded JSON instead of the auto-generated graph for this run.")
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    st.error(f"Invalid Knowledge Graph JSON: {exc}")
            if graph_source is None and DEFAULT_GRAPH is not None:
                graph_source = DEFAULT_GRAPH

        can_process = bool(uploaded_pdf is not None and grade.strip() and subject.strip())
        if st.button("Process book", type="primary", disabled=not can_process):
            try:
                get_openrouter_api_key()
                logger.info("Saving uploaded file '%s' to disk", uploaded_pdf.name)
                pdf_path = save_uploaded_file(uploaded_pdf)
                content_hash = book_library.hash_file(pdf_path)

                # --- Step 1/3: Knowledge Graph -----------------------------
                # Skipped if the Advanced override above already supplied a
                # graph for this run - no need to regenerate one from the PDF.
                if isinstance(graph_source, dict):
                    logger.info("Step 1/3: using the manually supplied Knowledge Graph override (skipping auto-generation)")
                    active_graph = graph_source
                    st.session_state.rag_knowledge_graph = active_graph
                    st.session_state.rag_knowledge_graph_source_name = pdf_path.name
                else:
                    logger.info("Step 1/3: generating Knowledge Graph from '%s'", pdf_path.name)
                    kg_status = st.status("Step 1/3 — Building Knowledge Graph...", expanded=True)
                    kg_result = get_knowledge_graph_service().generate_from_pdf(pdf_path)
                    active_graph = kg_result.graph
                    content_hash = kg_result.content_hash
                    st.session_state.rag_knowledge_graph = active_graph
                    st.session_state.rag_knowledge_graph_source_name = kg_result.source_file_name
                    cache_note = " (reused cached graph)" if kg_result.cached else ""
                    kg_status.update(
                        label=f"Step 1/3 — Knowledge Graph ready: {kg_result.entity_count} entities{cache_note}",
                        state="complete", expanded=False,
                    )

                # --- Step 2/3: RAG indexing --------------------------------
                logger.info("Step 2/3: indexing '%s' into the shared RAG (chunking, embedding, vector upsert)", pdf_path.name)
                rag_status = st.status("Step 2/3 — Indexing book into RAG...", expanded=True)
                index_result = get_rag().index_file(pdf_path)
                file_reference_id = str(index_result.get("file_reference_id") or "").strip()
                if not file_reference_id:
                    raise RuntimeError("RAG indexing completed without returning file_reference_id.")
                st.session_state.rag_file_reference_id = file_reference_id
                indexed_chunks = index_result.get("indexed_chunks", index_result.get("chunks_created", 0))
                rag_status.update(
                    label=f"Step 2/3 — RAG indexed: {indexed_chunks} chunk(s) (file_reference_id={file_reference_id})",
                    state="complete", expanded=False,
                )

                # --- Step 3/3: generate questions for every topic ----------
                logger.info("Step 3/3: generating questions for every topic in the Knowledge Graph")
                qb_status = st.status("Step 3/3 — Generating questions for every topic...", expanded=True)

                def logged_retriever(topic: str):
                    logger.info("Retrieving evidence for topic '%s'", topic)
                    return get_rag().retrieve_topic(topic, file_reference_id)

                saved_paths = generate_questions_from_knowledge_graph(
                    active_graph,
                    grade,
                    subject,
                    rag_file_reference_id=file_reference_id,
                    retriever=logged_retriever,
                    # entity_ids intentionally omitted: process every topic in the graph.
                )
                qb_status.update(
                    label=f"Step 3/3 — Questions saved for {len(saved_paths)} topic(s)",
                    state="complete", expanded=False,
                )

                entity_count = len(active_graph.get("entities", []))
                book_library.register_book(
                    content_hash=content_hash,
                    filename=pdf_path.name,
                    grade=grade,
                    subject=subject,
                    rag_file_reference_id=file_reference_id,
                    indexed_chunks=indexed_chunks,
                    knowledge_graph=active_graph,
                    entity_count=entity_count,
                    topics_generated=len(saved_paths),
                )
                logger.info(
                    "Book processing complete: entities=%d indexed_chunks=%s topics_with_questions=%d "
                    "(added to library, content_hash=%s)",
                    entity_count, indexed_chunks, len(saved_paths), content_hash,
                )
                st.success(
                    f"Book processed end-to-end: Knowledge Graph ({entity_count} entities), "
                    f"RAG indexed ({indexed_chunks} chunks), questions saved for {len(saved_paths)} topic(s). "
                    "Saved to the book library above - ready to run an exam below."
                )
            except Exception as exc:
                logger.error("Book processing failed: %s", exc)
                st.error(f"Book processing failed: {exc}")

    if st.session_state.rag_file_reference_id:
        st.info(f"Active RAG file_reference_id: `{st.session_state.rag_file_reference_id}`")
    if st.session_state.rag_knowledge_graph is not None:
        entity_count = len(st.session_state.rag_knowledge_graph.get("entities", []))
        st.info(
            f"Active Knowledge Graph: built from `{st.session_state.rag_knowledge_graph_source_name}` "
            f"({entity_count} entities)."
        )

    with st.expander("Advanced: regenerate specific topics only"):
        st.caption(
            "Uses the currently active Knowledge Graph and RAG index above - handy for topping up "
            "one topic (e.g. after adding it to the graph) without reprocessing the whole book."
        )
        regen_graph_source = graph_source if graph_source is not None else st.session_state.rag_knowledge_graph
        selected_entity_ids: list[str] = []
        if regen_graph_source is not None:
            try:
                graph_entities = get_graph_entities(regen_graph_source)
                entity_labels = {f"{entity['name']}  [{entity['id']}]": entity["id"] for entity in graph_entities}
                selected_labels = st.multiselect(
                    "Choose entities to regenerate",
                    options=list(entity_labels),
                    placeholder="Select one or more topics",
                )
                selected_entity_ids = [entity_labels[label] for label in selected_labels]
            except (OSError, ValueError, TypeError) as exc:
                st.error(f"Could not read the Knowledge Graph: {exc}")
        else:
            st.warning("No Knowledge Graph active yet - process a book above first.")

        can_regenerate = bool(
            grade.strip()
            and subject.strip()
            and regen_graph_source is not None
            and selected_entity_ids
            and st.session_state.rag_file_reference_id.strip()
        )
        if st.button("Regenerate selected topics", disabled=not can_regenerate):
            try:
                get_openrouter_api_key()
                logger.info(
                    "Regenerating %d selected topic(s): grade=%s subject=%s", len(selected_entity_ids), grade, subject,
                )
                with st.spinner("Retrieving evidence and regenerating questions..."):
                    def logged_retriever(topic: str):
                        logger.info("Retrieving evidence for topic '%s'", topic)
                        return get_rag().retrieve_topic(topic, st.session_state.rag_file_reference_id)

                    paths = generate_questions_from_knowledge_graph(
                        regen_graph_source,
                        grade,
                        subject,
                        entity_ids=selected_entity_ids,
                        rag_file_reference_id=st.session_state.rag_file_reference_id,
                        retriever=logged_retriever,
                        overwrite=True,
                    )
                logger.info("Regeneration complete: %d topic file(s) written", len(paths))
                st.success(f"Saved {len(paths)} topic files inside question_bank.")
                st.code("\n".join(str(path) for path in paths[:10]))
            except Exception as exc:
                logger.error("Regeneration failed: %s", exc)
                st.error(f"Regeneration failed: {exc}")

    st.divider()
    st.header("2. Run exam")
    st.caption(
        "Pulls topics straight from the Knowledge Graph, topic by topic, keeping only the ones that "
        "already have saved questions in step 2 - no manual topic list needed."
    )

    graph_for_exam: dict | None = None
    if isinstance(graph_source, dict):
        graph_for_exam = graph_source
    elif graph_source is not None:
        try:
            graph_for_exam = json.loads(Path(graph_source).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            st.error(f"Could not read the Knowledge Graph for the exam: {exc}")

    if st.session_state.exam_status is None:
        student_id = st.text_input("Student ID", placeholder="Example: S1", key="exam_student_id")
        can_start_exam = bool(grade.strip() and subject.strip() and graph_for_exam is not None)
        if st.button("Start exam", type="primary", disabled=not can_start_exam):
            try:
                logger.info(
                    "Starting exam: student_id=%s grade=%s subject=%s (pulling topics from Knowledge Graph)",
                    student_id or "anonymous", grade, subject,
                )
                result = get_assessment_service().start_exam_from_knowledge_graph(
                    student_id=student_id.strip() or "anonymous",
                    grade=grade,
                    subject=subject,
                    knowledge_graph=graph_for_exam,
                )
                st.session_state.exam_id = result["exam_id"]
                st.session_state.exam_current_question = result["question"]
                st.session_state.exam_status = "in_progress"
                logger.info(
                    "Exam started: exam_id=%s first_topic=%s",
                    result["exam_id"], result["question"]["topic_name"],
                )
                st.rerun()
            except Exception as exc:
                logger.error("Could not start exam: %s", exc)
                st.error(f"Could not start exam: {exc}")
        if not can_start_exam:
            st.info("Fill in Grade, Subject, and make sure a Knowledge Graph is available (step 1 or 2) to start.")

    elif st.session_state.exam_status == "in_progress":
        question = st.session_state.exam_current_question
        st.subheader(question["topic_name"])
        st.caption(f"Difficulty: {question['difficulty_level']}  ·  Type: {question['question_type']}")
        st.write(question["question"]["text"])

        options: dict[str, str] = question["question"]["options"]
        option_keys = list(options)
        widget_key = f"exam_answer_{question['question_id']}"

        if question["question_type"] == "MSQ":
            chosen = st.multiselect(
                "Select all that apply",
                options=option_keys,
                format_func=lambda key: f"{key}. {options[key]}",
                key=widget_key,
            )
        else:
            chosen = st.radio(
                "Choose one",
                options=option_keys,
                format_func=lambda key: f"{key}. {options[key]}",
                index=None,
                key=widget_key,
            )

        answer_given = bool(chosen) if isinstance(chosen, list) else chosen is not None
        if st.button("Submit answer", type="primary", disabled=not answer_given):
            try:
                logger.info(
                    "Submitting answer: exam_id=%s question_id=%s",
                    st.session_state.exam_id, question["question_id"],
                )
                outcome = get_assessment_service().process_answer(
                    st.session_state.exam_id, question["question_id"], chosen,
                )
                if outcome["status"] == "exam_ended":
                    st.session_state.exam_status = "finished"
                    st.session_state.exam_results = outcome["results"]
                    logger.info("Exam finished: exam_id=%s", st.session_state.exam_id)
                else:
                    st.session_state.exam_current_question = outcome["question"]
                    logger.info(
                        "Next question: exam_id=%s status=%s topic=%s",
                        st.session_state.exam_id, outcome["status"], outcome["question"]["topic_name"],
                    )
                st.rerun()
            except Exception as exc:
                logger.error("Could not submit answer: %s", exc)
                st.error(f"Could not submit answer: {exc}")

        if st.button("Abandon exam"):
            logger.info("Exam abandoned by user: exam_id=%s", st.session_state.exam_id)
            _reset_exam_state()
            st.rerun()

    elif st.session_state.exam_status == "finished":
        st.success("Exam finished.")
        for topic_result in st.session_state.exam_results:
            with st.expander(f"{topic_result['topic_name']} — {topic_result['confirmed_level']}"):
                for answer in topic_result["answers"]:
                    verdict = "correct" if answer["is_correct"] else "incorrect"
                    st.write(
                        f"[{answer['difficulty']}] {answer['question_text']}  \n"
                        f"Student answer: `{answer['student_answer']}` — {verdict} "
                        f"(correct: `{answer['correct_answer']}`)"
                    )

        if st.session_state.exam_report is None:
            if st.button("Generate LLM report"):
                try:
                    logger.info("Generating exam report: exam_id=%s", st.session_state.exam_id)
                    st.session_state.exam_report = get_assessment_service().get_report(st.session_state.exam_id)
                    logger.info("Exam report ready: exam_id=%s", st.session_state.exam_id)
                    st.rerun()
                except Exception as exc:
                    logger.error("Report generation failed: %s", exc)
                    st.error(f"Report generation failed: {exc}")
        else:
            st.markdown(st.session_state.exam_report)

        if st.button("Start a new exam"):
            _reset_exam_state()
            st.rerun()

    st.divider()
    st.header("3. Retrieve saved questions")
    topic = st.text_input("Topic name or id", placeholder="Example: algebra")
    if st.button("Retrieve questions", disabled=not (grade.strip() and subject.strip() and topic.strip())):
        logger.info("Retrieving saved questions: grade=%s subject=%s topic=%s", grade, subject, topic)
        questions = get_questions(grade, subject, topic)
        if questions:
            logger.info("Found %d saved question(s)", len(questions))
            st.success(f"Found {len(questions)} questions.")
            st.json(questions)
        else:
            logger.info("No saved questions matched grade=%s subject=%s topic=%s", grade, subject, topic)
            st.info("No saved questions match these values yet.")

    st.divider()
    render_log_panel(expanded=True)