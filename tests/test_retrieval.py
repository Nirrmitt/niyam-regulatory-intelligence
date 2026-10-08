import pytest
from pydantic import ValidationError

from app.retrieval import ChunkRecord, InMemoryRegulatoryIndex
from app.schemas import AskRequest


def test_search_ranks_matching_passage_first():
    index = InMemoryRegulatoryIndex()
    matching = ChunkRecord(
        chunk_id=1,
        doc_title="Disclosure Rules",
        source_file="disclosure.pdf",
        page_start=4,
        content="Banks must disclose material risk exposures.",
    )
    unrelated = ChunkRecord(
        chunk_id=2,
        doc_title="Governance Rules",
        source_file="governance.pdf",
        page_start=2,
        content="The board reviews committee membership annually.",
    )
    index.chunks = [unrelated, matching]

    results = index.search("disclose risk exposures", top_k=2)

    assert [chunk.chunk_id for chunk in results] == [1, 2]
    assert results[0].vector_score > results[1].vector_score


def test_search_returns_at_most_requested_number_of_passages():
    index = InMemoryRegulatoryIndex()
    index.chunks = [
        ChunkRecord(
            chunk_id=chunk_id,
            doc_title="Rules",
            source_file="rules.pdf",
            page_start=chunk_id,
            content=f"Disclosure requirements for institution {chunk_id}.",
        )
        for chunk_id in range(1, 4)
    ]

    assert len(index.search("disclosure requirements", top_k=2)) == 2


def test_search_returns_no_results_for_empty_index():
    assert InMemoryRegulatoryIndex().search("disclosure requirements") == []


def test_search_modes_use_semantic_and_keyword_scores(monkeypatch):
    index = InMemoryRegulatoryIndex()
    semantic_match = ChunkRecord(
        chunk_id=1,
        doc_title="Capital Rules",
        source_file="capital.pdf",
        page_start=1,
        content="Institutions shall maintain adequate own funds.",
    )
    keyword_match = ChunkRecord(
        chunk_id=2,
        doc_title="Disclosure Rules",
        source_file="disclosure.pdf",
        page_start=2,
        content="Banks must disclose material risk exposures.",
    )
    index.chunks = [semantic_match, keyword_match]
    index._embeddings = [[1.0, 0.0], [0.0, 1.0]]
    monkeypatch.setattr(index, "_encode", lambda texts: [[1.0, 0.0]])

    assert index.search("disclose risk exposures", 1, "vector")[0].chunk_id == 1
    assert index.search("disclose risk exposures", 1, "keyword")[0].chunk_id == 2


def test_hybrid_rerank_orders_candidates_by_cross_encoder_score(monkeypatch):
    index = InMemoryRegulatoryIndex()
    index.chunks = [
        ChunkRecord(
            chunk_id=1,
            doc_title="First",
            source_file="first.pdf",
            page_start=1,
            content="First matching passage.",
        ),
        ChunkRecord(
            chunk_id=2,
            doc_title="Second",
            source_file="second.pdf",
            page_start=2,
            content="Second matching passage.",
        ),
    ]
    index._embeddings = [[1.0, 0.0], [0.0, 1.0]]
    monkeypatch.setattr(index, "_encode", lambda texts: [[1.0, 0.0]])

    class FakeReranker:
        def predict(self, pairs):
            return [0.0, 2.0]

    index._reranker = FakeReranker()

    results = index.search("matching passage", 1, "hybrid_rerank")

    assert results[0].chunk_id == 2
    assert results[0].rerank_score > results[0].vector_score


def test_ask_request_accepts_supported_parameters():
    request = AskRequest.model_validate(
        {
            "question": "What must a bank disclose?",
            "strategy": "recursive",
            "mode": "hybrid_rerank",
            "top_k": 5,
        }
    )

    assert request.top_k == 5


def test_ask_request_rejects_unsupported_retrieval_mode():
    with pytest.raises(ValidationError):
        AskRequest.model_validate(
            {
                "question": "What must a bank disclose?",
                "strategy": "recursive",
                "mode": "not-a-mode",
                "top_k": 5,
            }
        )
