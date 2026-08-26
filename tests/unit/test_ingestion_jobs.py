from pathlib import Path

from src.application.ingestion_jobs import IngestionJobService
from src.domain.schemas import IngestionResponse


class _Registry:
    def __init__(self):
        self.records = {}

    def register(self, content_hash, record):
        self.records[content_hash] = record


class _Service:
    def ingest(self, *_args, **_kwargs):
        return IngestionResponse(
            curriculum_id="curriculum", version="v1", files_processed=1,
            chunks_created=2, indexed_chunks=2, indexed_question_count=4,
            language_counts={"ar": 2}, metadata_coverage={}, document_metadata=None,
        )


def test_ingestion_job_completes_and_registers_result(tmp_path):
    source = tmp_path / "book.pdf"
    source.write_bytes(b"content")
    registry = _Registry()
    jobs = IngestionJobService(_Service(), registry, workers=1)
    job = jobs.submit(
        source=source, file_reference_id="file-1", file_name="book.pdf",
        size_bytes=7, content_hash="hash-1",
    )

    import time
    for _ in range(20):
        status = jobs.get(job.job_id)
        if status and status["status"] == "completed":
            break
        time.sleep(0.01)

    assert status["status"] == "completed"
    assert status["result"]["indexed_question_count"] == 4
    assert registry.records["hash-1"]["file_reference_id"] == "file-1"
