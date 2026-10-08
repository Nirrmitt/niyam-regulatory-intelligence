---
name: rag-evaluation
description: 'Use for evaluation, regression testing, and quality checks for the regulatory RAG portfolio, including retrieval metrics and grounded-answer validation.'
argument-hint: 'Describe the evaluation target, test scenario, or quality issue.'
user-invocable: true
disable-model-invocation: false
---

# RAG Evaluation Skill

## When to use

Use this skill when:

- measuring retrieval quality with question sets in `evaluation/`
- testing answer grounding, citation correctness, or abstention behavior
- assessing whether a change affects search quality or generation reliability
- validating new RAG features before release

## Evaluation principles

This portfolio is designed to be citation-first and evidence-aware. Validation should focus on:

- document and page provenance
- relevant passage retrieval for domain questions
- answer grounding to retrieved excerpts
- abstention when evidence is too weak
- citation label correctness `[S1]`, `[S2]`, etc.

## Suggested workflow

1. Start with the smallest relevant test file.
2. Add or update a regression case for the behavior under change.
3. Run the focused suite and inspect failing scores or mismatched citations.
4. Repeat until evidence and citations are correct.

## Repo-specific references

- [Evaluation assets](../../evaluation/)
- [Retrieval script](../../scripts/evaluate_retrieval.py)
- [API tests](../../tests/test_main.py)
- [Grounded generation tests](../../tests/test_generation.py)
- [Retrieval tests](../../tests/test_retrieval.py)

## Quality checklist

- retrieval returns top evidence for regulatory questions
- the API preserves answer metadata and cited sources
- the model does not invent unsupported citations
- low-signal queries abstain instead of hallucinating
- source labels map exactly to the retrieved passage set
