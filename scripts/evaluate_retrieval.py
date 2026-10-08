from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.retrieval import ChunkRecord, InMemoryRegulatoryIndex

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = PROJECT_ROOT / "evaluation" / "questions.json"
RETRIEVAL_MODES = ("keyword", "vector", "hybrid", "hybrid_rerank")


def hits_gold_page(
    retrieved: list[ChunkRecord],
    gold: list[dict[str, object]],
    filenames: dict[str, str],
) -> bool:
    relevant: set[tuple[str, int]] = set()
    for item in gold:
        document_id = item.get("document")
        pages = item.get("pages")
        if not isinstance(document_id, str) or document_id not in filenames:
            raise ValueError(f"Unknown gold document: {document_id}")
        if not isinstance(pages, list) or not all(
            isinstance(page, int) and page > 0 for page in pages
        ):
            raise ValueError(f"Invalid gold page annotation for {document_id}")
        relevant.update((filenames[document_id], page) for page in pages)
    return any((chunk.source_file, chunk.page_start) in relevant for chunk in retrieved)


def evaluate(
    benchmark: dict[str, list], pdf_directory: Path, ks: tuple[int, ...]
) -> dict[str, dict[int, float]]:
    corpus = benchmark["corpus"]
    questions = benchmark["questions"]
    filenames = {document["id"]: document["filename"] for document in corpus}
    missing = [
        str(pdf_directory / document["filename"])
        for document in corpus
        if not (pdf_directory / document["filename"]).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Evaluation PDFs are missing. Run "
            "scripts\\download_eval_pdfs.ps1 first. Missing files: "
            + ", ".join(missing)
        )
    index = InMemoryRegulatoryIndex(pdf_directory.parent)
    loaded_count = index.load()
    if not loaded_count or not index.embeddings_loaded:
        raise RuntimeError(
            "The evaluation corpus did not produce a complete embedding index."
        )

    results: dict[str, dict[int, float]] = {}
    max_k = max(ks)
    for mode in RETRIEVAL_MODES:
        hits = {k: 0 for k in ks}
        for item in questions:
            ranked = index.search(item["question"], top_k=max_k, mode=mode)
            for k in ks:
                if hits_gold_page(ranked[:k], item["gold"], filenames):
                    hits[k] += 1
        results[mode] = {k: hits[k] / len(questions) for k in ks}
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare regulatory retrieval modes on page-labelled questions."
    )
    parser.add_argument(
        "--pdf-dir",
        type=Path,
        default=PROJECT_ROOT / "evaluation" / "raw",
        help="Directory containing the two source PDFs (default: evaluation/raw).",
    )
    parser.add_argument(
        "--k",
        type=int,
        nargs="+",
        default=[1, 3, 5],
        help="Recall cutoffs to report (default: 1 3 5).",
    )
    args = parser.parse_args()
    if not args.k or any(value < 1 for value in args.k):
        parser.error("All --k values must be positive integers.")

    benchmark = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    ks = tuple(sorted(set(args.k)))
    results = evaluate(benchmark, args.pdf_dir, ks)
    print_results(results, ks, len(benchmark["questions"]))


def print_results(
    results: dict[str, dict[int, float]], ks: tuple[int, ...], question_count: int
) -> None:
    headers = ["Mode", *(f"Recall@{k}" for k in ks)]
    rows = [
        [mode, *(f"{results[mode][k]:.3f}" for k in ks)] for mode in RETRIEVAL_MODES
    ]
    widths = [
        max(len(headers[column]), *(len(row[column]) for row in rows))
        for column in range(len(headers))
    ]
    print(f"Page-level recall on {question_count} labelled questions")
    print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))


if __name__ == "__main__":
    main()
