---
name: rag-retrieval
description: 'Use for retrieval tuning, vector/keyword/hybrid scoring, chunking logic, and PDF indexing upgrades in the regulatory RAG portfolio.'
argument-hint: 'Describe the retrieval bug, ranking issue, or PDF indexing problem.'
user-invocable: true
disable-model-invocation: false
---

# Retrieval Tuning Skill

## When to use

Use this skill when changing:

- document chunking strategy in `app/retrieval.py`
- embedding model selection in `app/config.py`
- vector, keyword, hybrid, or rerank behavior
- index load and rebuild logic from `data/raw/*.pdf`
- retrieval thresholds and scoring expectations in tests

## What is important

The project uses a sentence-aware in-memory index. The retrieval stack is a hybrid system designed for evidence-first regulation search.

Key invariants:

- `ChunkRecord` must retain `doc_title`, `page_start`, and `source_file`
- normalized vectors must remain finite and dimensionally consistent
- ranked retrieval should return copied content with provenance, not only a score
- low-evidence questions must fail gracefully rather than produce speculative answers

## Workflow

1. Confirm the retrieval mode and threshold involved.
2. Inspect the index and scoring code in `app/retrieval.py`.
3. Reproduce with the relevant retrieval tests or a focused regression case.
4. Keep edits minimal; prefer preserving the current architecture over adding a new ranker.
5. Validate scoring behavior and document the effect on top-k results.

## Retrieval playbook

- Use `vector` when the query is semantic and concept-centered.
- Use `keyword` when terms are precise and regulatory phrasing is predictable.
- Use `hybrid` or `hybrid_rerank` when balancing meaning and terminology is important.
- Re-check thresholds after changing embedding models, chunk size, or query normalization.

## References

- [Retrieval architecture notes](./references/retrieval-playbook.md)
- [Project entry point](../../app/main.py)
- [Index implementation](../../app/retrieval.py)
