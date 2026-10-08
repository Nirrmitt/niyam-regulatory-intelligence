from app.retrieval import ChunkRecord
from scripts.evaluate_retrieval import hits_gold_page


def test_page_recall_hit_requires_matching_document_and_page():
    chunk = ChunkRecord(
        chunk_id=1,
        doc_title="KYC",
        source_file="kyc.pdf",
        page_start=22,
        content="Customer identification procedure",
    )
    gold = [{"document": "kyc", "pages": [22, 23]}]

    assert hits_gold_page([chunk], gold, {"kyc": "kyc.pdf"})
    assert not hits_gold_page([chunk], gold, {"kyc": "other.pdf"})


def test_page_recall_rejects_invalid_gold_page():
    gold = [{"document": "kyc", "pages": [0]}]

    try:
        hits_gold_page([], gold, {"kyc": "kyc.pdf"})
    except ValueError as exc:
        assert "Invalid gold page annotation" in str(exc)
    else:
        raise AssertionError("Invalid page annotations must fail.")
