import asyncio

from app import main
from app.retrieval import ChunkRecord
from app.schemas import AskRequest


def test_ask_returns_grounded_answer_with_matching_source_label(monkeypatch):
    chunk = ChunkRecord(
        chunk_id=1,
        doc_title="Disclosure Rules",
        source_file="disclosure.pdf",
        page_start=4,
        content="Banks must disclose material risk exposures.",
        vector_score=0.82,
        keyword_score=0.75,
        rerank_score=0.91,
        fused_score=0.91,
    )
    monkeypatch.setattr(main.index, "search", lambda question, top_k, mode: [chunk])

    async def fake_generate(question, chunks):
        assert question == "What must banks disclose?"
        assert chunks == [chunk]
        return "Banks must disclose material risk exposures [S1]."

    monkeypatch.setattr(main, "generate_grounded_answer", fake_generate)
    payload = AskRequest(
        question="What must banks disclose?",
        strategy="recursive",
        mode="vector",
        top_k=1,
    )

    response = asyncio.run(main.ask(payload))

    assert response.answered is True
    assert response.answer.endswith("[S1].")
    assert response.cited_sources[0].source_id == "S1"
    assert response.cited_sources[0].page_start == 4


def test_ask_abstains_when_retrieved_evidence_is_below_threshold(monkeypatch):
    chunk = ChunkRecord(
        chunk_id=1,
        doc_title="Unrelated Rules",
        source_file="unrelated.pdf",
        page_start=2,
        content="The board reviews committee membership annually.",
        vector_score=0.1,
        keyword_score=0.1,
    )
    monkeypatch.setattr(main.index, "search", lambda question, top_k, mode: [chunk])

    async def unexpected_generation(question, chunks):
        raise AssertionError("Generation must not run for weak evidence.")

    monkeypatch.setattr(main, "generate_grounded_answer", unexpected_generation)
    payload = AskRequest(
        question="What must banks disclose?",
        strategy="recursive",
        mode="vector",
        top_k=1,
    )

    response = asyncio.run(main.ask(payload))

    assert response.answered is False
    assert response.cited_sources == []
    assert response.retrieved_sources[0].chunk_id == chunk.chunk_id
