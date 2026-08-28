"""Route the app's Python logging into the Streamlit session so users can see
pipeline steps (upload, indexing, retrieval, generation) as they happen,
instead of only in the terminal.
"""

from __future__ import annotations

import logging

import streamlit as st

LOG_STATE_KEY = "_app_log_records"
MAX_LOG_RECORDS = 500

_FORMATTER = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%H:%M:%S")


class StreamlitLogHandler(logging.Handler):
    """Append formatted log lines to a bounded list in ``st.session_state``.

    Streamlit re-executes the script on every interaction, so the handler
    itself is re-created each run; the backing list lives in session_state
    so history survives across reruns.
    """

    def __init__(self, session_state: dict) -> None:
        super().__init__()
        self._session_state = session_state
        if LOG_STATE_KEY not in self._session_state:
            self._session_state[LOG_STATE_KEY] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            line = self.format(record)
        except Exception:  # pragma: no cover - formatting must never crash a run
            return
        records = self._session_state.setdefault(LOG_STATE_KEY, [])
        records.append(line)
        del records[: max(0, len(records) - MAX_LOG_RECORDS)]


def configure_app_logging(level: int = logging.INFO) -> None:
    """Attach one Streamlit-backed handler to the root logger for this run.

    Safe to call on every script rerun: it removes any handler this function
    previously added before attaching a fresh one, so log lines are never
    duplicated across reruns.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for existing in list(root_logger.handlers):
        if isinstance(existing, StreamlitLogHandler):
            root_logger.removeHandler(existing)

    handler = StreamlitLogHandler(st.session_state)
    handler.setFormatter(_FORMATTER)
    handler.setLevel(level)
    root_logger.addHandler(handler)


def render_log_panel(*, expanded: bool = False) -> None:
    """Render the accumulated log lines for this session."""
    records: list[str] = st.session_state.get(LOG_STATE_KEY, [])
    with st.expander(f"Logs ({len(records)})", expanded=expanded):
        if not records:
            st.caption("No log activity yet. Steps will appear here as they run.")
        else:
            st.code("\n".join(records), language="log")
            if st.button("Clear logs"):
                st.session_state[LOG_STATE_KEY] = []
                st.rerun()
