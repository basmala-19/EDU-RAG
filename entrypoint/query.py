import argparse
from src.application.retrieval_service import RetrievalService


def main() -> None:
    p = argparse.ArgumentParser(description="Query the curriculum RAG")
    p.add_argument("query")
    p.add_argument("--curriculum-id")
    p.add_argument("--version")
    p.add_argument("--subject")
    p.add_argument("--grade")
    p.add_argument("--chapter")
    p.add_argument("--lesson")
    p.add_argument("--language")
    p.add_argument("--top-k", type=int, default=5)
    args = p.parse_args()

    filters = {k: v for k, v in {
        "curriculum_id": args.curriculum_id,
        "version": args.version,
        "subject": args.subject,
        "grade": args.grade,
        "chapter": args.chapter,
        "lesson": args.lesson,
        "language": args.language,
    }.items() if v is not None}

    results = RetrievalService().retrieve(args.query, filters=filters, top_k=args.top_k)
    for item in results.results:
        print(item.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
