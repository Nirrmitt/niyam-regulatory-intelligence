---
name: rag-portfolio
description: 'Use for Retrieval-Augmented Generation work in this regulatory intelligence portfolio project: PDF ingestion, semantic retrieval tuning, grounded answer generation, citations, and evaluation workflows.'
argument-hint: 'Describe the RAG issue, document source, prompt change, or evaluation goal.'
user-invocable: true
disable-model-invocation: false
---

# Regulatory RAG Portfolio Skill

## When to use

Use this skill when working on:

- retrieval or ranking logic in `app/retrieval.py`
- grounded generation or citation validation in `app/generation.py`
- FastAPI request/response behavior in `app/main.py`
- new source PDFs or indexing changes under `data/raw/`
- retrieval evaluation and prompt validation in `scripts/` and `tests/`

## Project overview

This repository implements a citation-first regulatory Q&A workflow:

1. PDF sources are ingested from `data/raw/`.
2. The app chunks page text while preserving page provenance.
3. The in-memory index embeds passages and supports vector, keyword, and hybrid search.
4. Retrieval results feed a grounded OpenRouter prompt that must cite source labels.
5. The API returns the answer, citations, and evidence snippets to the Streamlit UI.

Core files:

- [app/retrieval.py](../../app/retrieval.py)
- [app/generation.py](../../app/generation.py)
- [app/main.py](../../app/main.py)
- [app/config.py](../../app/config.py)
- [ui/streamlit_app.py](../../ui/streamlit_app.py)
- [scripts/evaluate_retrieval.py](../../scripts/evaluate_retrieval.py)

## Operating principles

- Prefer small, evidence-based fixes that preserve the retrieval and citation contract.
- Treat outbound answer generation as a source-grounded step, not free-form summarization.
- Validate PDF indexing behavior with the existing tests before changing search heuristics.
- Keep document provenance (`doc_title`, `page_start`, `source_file`) intact in every retrieval result.

## Workflow

### 1. Diagnose the issue

Check the exact layer involved:

- indexing problem: `app/retrieval.py`
- generation or citation problem: `app/generation.py`
- request validation or HTTP contract: `app/main.py`
- UI issue: `ui/streamlit_app.py`

### 2. Reproduce with a targeted test

Use existing tests or add a focused regression test. Most RAG work is covered by:

- `tests/test_retrieval.py`
- `tests/test_generation.py`
- `tests/test_main.py`

### 3. Apply the fix

Keep changes minimal and aligned with the current architecture:

- retrieval tuning should remain compatible with `ChunkRecord`
- prompt changes should preserve citation labels and abstention logic
- API behavior should continue returning `answered`, `top_score`, `cited_sources`, and `retrieved_sources`

### 4. Verify

Run the smallest relevant suite, then expand only if needed:

```bash
pytest -q
```

## Useful references

- [Project architecture notes](./references/project-architecture.md)
- [Retrieval playbook](../rag-retrieval/SKILL.md)
- [Evaluation checklist](../rag-evaluation/SKILL.md)
- [Project health script](./scripts/check-project-health.py)
