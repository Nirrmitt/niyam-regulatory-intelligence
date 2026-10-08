# Regulatory RAG Architecture Notes

## Main flow

The project is a single-service RAG stack with an in-memory index and a lightweight grounding prompt pipeline.

- PDF ingestion happens in `app/retrieval.py` at startup via `InMemoryRegulatoryIndex.load()`.
- Each page is normalized, split into sentence-aware chunks, and stored with a `ChunkRecord`.
- Chunk records retain `doc_title`, `page_start`, `source_file`, and chunk text.
- Retrieval computes semantic and lexical similarity and returns the top ranked evidence for the question.
- The generation layer sends only retrieved evidence to OpenRouter and insists on source labels like `[S1]`.

## Retrieval modes

The current project supports these modes:

- `vector` for semantic similarity
- `keyword` for lexical similarity
- `hybrid` for fused vector + keyword scores
- `hybrid_rerank` for reranked hybrid candidates

The request schema in `app/schemas.py` still accepts compatibility fields like `strategy`, but the active runtime behavior is driven by the global configuration in `app/config.py`.

## Grounding requirements

The generation prompt is intentionally constrained:

- answer only from supplied excerpts
- abstain when evidence is weak or insufficient
- cite every factual claim with the matching source label
- never invent citations or overstate support

The API validates citations in `app/main.py` by checking each `[Sx]` label against the retrieved source set. This is a critical part of the portfolio's trust model.

## Evaluation and tests

The repository includes targeted evaluation and API tests:

- `tests/test_retrieval.py` checks retrieval scoring and mode behavior
- `tests/test_generation.py` checks grounded prompts and abstention behavior
- `tests/test_main.py` checks API contract and citation validation
- `scripts/evaluate_retrieval.py` can compare retrieval quality across question sets

Keep any new RAG feature or benchmarking script aligned with these conventions.
