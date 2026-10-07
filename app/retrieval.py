from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

import fitz

from app.config import settings


@dataclass
class ChunkRecord:
    chunk_id: int
    doc_title: str
    source_file: str
    page_start: int
    content: str
    vector_score: float = 0.0
    keyword_score: float | None = None
    rerank_score: float | None = None
    fused_score: float | None = None


class InMemoryRegulatoryIndex:
    def __init__(self, data_dir: str | Path | None = None):
        self.data_dir = Path(data_dir or "data")
        self.raw_dir = self.data_dir / "raw"
        self.chunks: List[ChunkRecord] = []
        self._loaded = False

    def load(self) -> int:
        self.chunks = []
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        for pdf_path in sorted(self.raw_dir.glob("*.pdf")):
            self._ingest_pdf(pdf_path)

        self._loaded = True
        return len(self.chunks)

    def _ingest_pdf(self, pdf_path: Path) -> None:
        doc_title = pdf_path.stem.replace("_", " ").title()
        try:
            pdf_doc = fitz.open(str(pdf_path))
        except Exception:
            return

        for page_index, page in enumerate(pdf_doc, start=1):
            text = page.get_text("text")
            if not text:
                continue
            for chunk_index, chunk in enumerate(
                self._chunk_text(text, settings.CHUNK_TOKENS, settings.CHUNK_OVERLAP),
                start=1,
            ):
                record = ChunkRecord(
                    chunk_id=len(self.chunks) + 1,
                    doc_title=doc_title,
                    source_file=str(pdf_path.name),
                    page_start=page_index,
                    content=chunk.strip(),
                )
                self.chunks.append(record)

        pdf_doc.close()

    def _chunk_text(
        self, text: str, chunk_tokens: int = 500, overlap: int = 50
    ) -> List[str]:
        normalized = re.sub(r"\s+", " ", text).strip()
        if not normalized:
            return []

        sentences = [
            sentence.strip()
            for sentence in re.split(r"(?<=[.!?])\s+", normalized)
            if sentence.strip()
        ]
        if not sentences:
            return [normalized]

        chunks: List[str] = []
        current: List[str] = []
        current_len = 0
        overlap_chars = max(20, int(overlap * 2))

        for sentence in sentences:
            sentence_len = len(sentence)
            if current and current_len + sentence_len > chunk_tokens * 4:
                chunks.append(" ".join(current).strip())
                overlap_tail = current[-max(1, len(current) // 3) :]
                current = list(overlap_tail)
                current_len = sum(len(part) for part in current)
            current.append(sentence)
            current_len += sentence_len

        if current:
            chunks.append(" ".join(current).strip())

        merged: List[str] = []
        for index, chunk in enumerate(chunks):
            if not chunk:
                continue
            if index == 0:
                merged.append(chunk)
                continue
            if len(chunk) < overlap_chars and merged:
                merged[-1] = f"{merged[-1]} {chunk}".strip()
            else:
                merged.append(chunk)

        return merged

    def search(self, question: str, top_k: int = 5) -> List[ChunkRecord]:
        if not self.chunks:
            return []

        q_terms = self._term_counts(question)
        query_norm = self._vector_norm(q_terms)
        if query_norm == 0:
            return []

        scored: List[ChunkRecord] = []
        for index, chunk in enumerate(self.chunks):
            term_counts = self._term_counts(chunk.content)
            dot = sum(
                q_terms.get(term, 0) * term_counts.get(term, 0)
                for term in set(q_terms) | set(term_counts)
            )
            doc_norm = self._vector_norm(term_counts)
            score = dot / (query_norm * doc_norm) if doc_norm and query_norm else 0.0
            chunk.vector_score = score
            chunk.keyword_score = score
            chunk.rerank_score = score
            chunk.fused_score = score
            scored.append(chunk)

        scored.sort(key=lambda item: item.vector_score, reverse=True)
        return scored[: max(1, min(top_k, len(scored)))]

    @staticmethod
    def _term_counts(text: str) -> dict[str, float]:
        matches = re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b", text.lower())
        counts: dict[str, float] = {}
        for token in matches:
            counts[token] = counts.get(token, 0.0) + 1.0
        return counts

    @staticmethod
    def _vector_norm(values: dict[str, float]) -> float:
        return math.sqrt(sum(value * value for value in values.values()))


index = InMemoryRegulatoryIndex("data")
