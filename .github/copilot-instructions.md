# Project Guidelines

## Architecture

This repository is a regulatory Q&A prototype built around a citation-first retrieval-and-generation flow:

- `app/main.py` exposes the FastAPI API and request validation.
- `app/retrieval.py` builds and searches the in-memory document index from `data/raw/*.pdf`.
- `app/generation.py` composes grounded prompts for OpenRouter and validates citations.
- `app/config.py` holds environment-driven configuration including the embed model, thresholds, and API keys.
- `ui/streamlit_app.py` is the research UI for asking questions and inspecting source passages.
- `scripts/evaluate_retrieval.py` and the tests under `tests/` measure retrieval quality and answer validity.

Keep new work aligned with the retrieval -> grounding -> citation loop. Do not bypass the evidence threshold or generate answers without source-grounding checks.

## RAG workflow conventions

- Prefer the existing in-memory vector index unless the task explicitly requires a database-backed path.
- Preserve chunk/page provenance (`doc_title`, `page_start`, `source_file`) when adding or modifying retrieval logic.
- Keep generation prompts grounded in retrieved excerpts only; cite using `[S1]` style labels and reject ungrounded answers.
- When updating retrieval behavior, validate against `tests/test_retrieval.py`, `tests/test_generation.py`, and relevant API tests.

## Build and validation

Use the project's existing Python tooling:

- `pytest -q`
- `uvicorn app.main:app --reload`

If the work touches API behavior, run the focused test files that cover the path you changed before broad suites.

## Conventions

- Follow the current FastAPI + Pydantic patterns already used in the project.
- Preserve environment-driven configuration via `app/config.py` instead of hardcoding values.
- Keep PDF chunking, embedding, and hybrid retrieval logic consistent with the project's document-centric approach.
- When adding documentation or skill files, keep them concise and tied to actual repo artifacts and workflows.
