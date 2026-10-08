# Retrieval Playbook

## Search modes

The in-memory retrieval layer compares query text to chunk text using two signals:

- semantic similarity with an embedding model
- lexical similarity with token frequency matching

These are combined into hybrid retrieval, with optional reranking over the leading candidates.

## Chunking and indexing

The current chunking strategy is page-aware and sentence-first. It works as follows:

- read each PDF page from `data/raw/`
- normalize whitespace and split by sentence boundaries
- accumulate sentences into bounded chunks with a heuristic overlap
- store each chunk with source metadata

Avoid changing the chunking contract without also updating any tests that assert the resulting provenance or number of passages.

## Thresholds

Threshold logic sits in `app/main.py` and is selected by mode. A weak top result prevents generation to keep the answer grounded. This is essential for regulatory language, where false certainty is worse than abstention.

## Maintenance checklist

- confirm PDF text extraction still succeeds for source docs
- ensure scoring remains finite and in range
- check that hybrid and rerank results still return expected source labels
- keep tests and evaluation prompts aligned with retrieval changes
