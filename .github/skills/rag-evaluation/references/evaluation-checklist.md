# Evaluation Checklist

## Retrieval checks

- confirm the relevant passages are ranked above weak distractors
- verify that page and document metadata survive retrieval
- test both semantic and keyword-heavy queries
- ensure hybrid mode behaves predictably when scores are mixed

## Grounded-answer checks

- the answer must only use the supplied excerpt text
- every factual claim should carry a matching `[Sx]` label
- unsupported or weak evidence should trigger abstention
- the model should not cite sources that were not retrieved

## Integration checks

- API response includes `answered`, `top_score`, `cited_sources`, and `retrieved_sources`
- unsuccessful retrieval returns the fallback message instead of a generated answer
- UI can show passage details without breaking the citation contract

## Typical commands

```bash
pytest -q
python scripts/evaluate_retrieval.py
```
