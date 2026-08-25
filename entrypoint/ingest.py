from pathlib import Path
import argparse

from src.application.ingestion_service import IngestionService


def main() -> None:
    p = argparse.ArgumentParser(description="Ingest curriculum documents into the RAG store")
    p.add_argument("source", help="File or directory containing curriculum files")
    p.add_argument("--curriculum-id", required=True)
    p.add_argument("--version", default="v1")
    args = p.parse_args()

    service = IngestionService()
    result = service.ingest(Path(args.source), args.curriculum_id, args.version)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
