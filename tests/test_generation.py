import asyncio
from types import SimpleNamespace

import pytest

from app import generation
from app.config import settings
from app.generation import build_generation_messages
from app.retrieval import ChunkRecord


def test_generation_prompt_labels_sources_and_limits_answer_to_evidence():
    chunk = ChunkRecord(
        chunk_id=7,
        doc_title="Disclosure Rules",
        source_file="disclosure.pdf",
        page_start=4,
        content="Banks must disclose material risk exposures.",
    )

    messages = build_generation_messages("What must banks disclose?", [chunk])

    assert "only the supplied source excerpts" in messages[0]["content"]
    assert "[S1] Disclosure Rules, page 4" in messages[1]["content"]
    assert "Banks must disclose material risk exposures." in messages[1]["content"]


def test_generation_calls_configured_openrouter_model(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-key")
    captured = {}

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def create(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(content="  Grounded answer [S1].  ")
                    )
                ]
            )

    monkeypatch.setattr(generation, "AsyncOpenAI", FakeAsyncOpenAI)
    chunk = ChunkRecord(
        chunk_id=1,
        doc_title="Disclosure Rules",
        source_file="disclosure.pdf",
        page_start=4,
        content="Banks must disclose material risk exposures.",
    )

    answer = asyncio.run(
        generation.generate_grounded_answer("What must banks disclose?", [chunk])
    )

    assert answer == "Grounded answer [S1]."
    assert captured["client"]["base_url"] == "https://openrouter.ai/api/v1"
    assert captured["request"]["model"] == settings.OPENROUTER_MODEL
    assert (
        "[S1] Disclosure Rules, page 4" in captured["request"]["messages"][1]["content"]
    )


def test_generation_requires_openrouter_api_key(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")

    with pytest.raises(ValueError, match="OPENROUTER_API_KEY"):
        asyncio.run(generation.generate_grounded_answer("Question", []))
