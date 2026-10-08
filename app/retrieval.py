from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any, List

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
        self._embeddings: List[List[float]] = []
        self._embedding_model: Any = None
        self._embedding_lock = Lock()
        self._reranker: Any = None
        self._reranker_lock = Lock()
        self._loaded = False

    def load(self) -> int:
        self.chunks = []
        self._embeddings = []
        self.raw_dir.mkdir(parents=True, exist_ok=True)

        for pdf_path in sorted(self.raw_dir.glob("*.pdf")):
            self._ingest_pdf(pdf_path)

        if self.chunks:
            self._embeddings = self._encode([chunk.content for chunk in self.chunks])
        self._loaded = True
        return len(self.chunks)

    @property
    def embeddings_loaded(self) -> bool:
        return bool(self._embeddings) and len(self._embeddings) == len(self.chunks)

    def _get_embedding_model(self) -> Any:
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            self._embedding_model = SentenceTransformer(settings.EMBED_MODEL)
        return self._embedding_model

    def _encode(self, texts: List[str]) -> List[List[float]]:
        with self._embedding_lock:
            encoded = self._get_embedding_model().encode(
                texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
        vectors = encoded.tolist()
        if len(vectors) != len(texts) or any(
            not vector or not all(math.isfinite(float(value)) for value in vector)
            for vector in vectors
        ):
            raise RuntimeError("The embedding model returned invalid vectors.")
        dimensions = len(vectors[0]) if vectors else 0
        if any(len(vector) != dimensions for vector in vectors):
            raise RuntimeError("The embedding model returned inconsistent dimensions.")
        return vectors

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

    def search(
        self, question: str, top_k: int = 5, mode: str | None = None
    ) -> List[ChunkRecord]:
        if not self.chunks:
            return []

        selected_mode = mode or settings.DEFAULT_MODE
        q_terms = self._term_counts(question)
        query_norm = self._vector_norm(q_terms)
        keyword_scores = [
            self._cosine_similarity(
                q_terms, self._term_counts(chunk.content), query_norm
            )
            for chunk in self.chunks
        ]

        if self.embeddings_loaded:
            query = self._encode(
                [f"Represent this sentence for searching relevant passages: {question}"]
            )[0]
            if len(query) != len(self._embeddings[0]):
                raise RuntimeError("Query and passage embedding dimensions differ.")
            vector_scores = [
                sum(a * b for a, b in zip(query, embedding))
                for embedding in self._embeddings
            ]
        else:
            # Keep directly constructed indexes useful for lightweight lexical tests.
            vector_scores = keyword_scores

        scored = [
            (
                position,
                ChunkRecord(
                    chunk_id=chunk.chunk_id,
                    doc_title=chunk.doc_title,
                    source_file=chunk.source_file,
                    page_start=chunk.page_start,
                    content=chunk.content,
                ),
            )
            for position, chunk in enumerate(self.chunks)
        ]
        for position, chunk in scored:
            chunk.vector_score = vector_scores[position]
            chunk.keyword_score = keyword_scores[position]
            chunk.rerank_score = None
            chunk.fused_score = None

        if selected_mode == "keyword":
            scored.sort(key=lambda item: keyword_scores[item[0]], reverse=True)
        elif selected_mode == "vector":
            scored.sort(key=lambda item: vector_scores[item[0]], reverse=True)
        else:
            for position, chunk in scored:
                chunk.fused_score = (
                    0.7 * vector_scores[position] + 0.3 * keyword_scores[position]
                )
            scored.sort(key=lambda item: item[1].fused_score or 0.0, reverse=True)

        if selected_mode == "hybrid_rerank" and self.embeddings_loaded:
            candidates = scored[: max(settings.CANDIDATE_K, top_k)]
            reranked = self._rerank(question, candidates)
            scored = reranked + scored[len(candidates) :]

        return [chunk for _, chunk in scored[: max(1, min(top_k, len(scored)))]]

    @staticmethod
    def _cosine_similarity(
        left: dict[str, float], right: dict[str, float], left_norm: float
    ) -> float:
        right_norm = InMemoryRegulatoryIndex._vector_norm(right)
        if not left_norm or not right_norm:
            return 0.0
        dot = sum(left.get(term, 0.0) * right.get(term, 0.0) for term in right)
        return dot / (left_norm * right_norm)

    def _rerank(
        self, question: str, candidates: List[tuple[int, ChunkRecord]]
    ) -> List[tuple[int, ChunkRecord]]:
        with self._reranker_lock:
            if self._reranker is None:
                from sentence_transformers import CrossEncoder

                self._reranker = CrossEncoder(settings.RERANK_MODEL)
            pairs = [(question, chunk.content) for _, chunk in candidates]
            raw_scores = self._reranker.predict(pairs)
        if len(raw_scores) != len(candidates):
            raise RuntimeError("The reranker returned an incomplete score list.")
        reranked: List[tuple[int, ChunkRecord]] = []
        for (position, chunk), raw_score in zip(candidates, raw_scores):
            raw_score = float(raw_score)
            if not math.isfinite(raw_score):
                raise RuntimeError("The reranker returned a non-finite score.")
            if raw_score >= 0:
                score = 1.0 / (1.0 + math.exp(-raw_score))
            else:
                exp_score = math.exp(raw_score)
                score = exp_score / (1.0 + exp_score)
            chunk.rerank_score = score
            chunk.fused_score = score
            reranked.append((position, chunk))
        reranked.sort(key=lambda item: item[1].rerank_score or 0.0, reverse=True)
        return reranked

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
