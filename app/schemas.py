from typing import List, Optional

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(description="The user query", min_length=5, max_length=500)
    strategy: str = Field(
        description="Chunking strategy", pattern="^(fixed|recursive)$"
    )
    mode: str = Field(
        description="Retrieval mode", pattern="^(vector|keyword|hybrid|hybrid_rerank)$"
    )
    top_k: int = Field(description="Number of results", ge=1, le=10)


class RetrievedChunk(BaseModel):
    chunk_id: int
    doc_title: str
    page_start: int
    content: str
    vector_score: float
    keyword_score: Optional[float] = None
    rerank_score: Optional[float] = None
    fused_score: Optional[float] = None


class SourceCitation(BaseModel):
    doc_title: str
    page_start: int
    snippet: str


class AskResponse(BaseModel):
    answer: Optional[str]
    answered: bool
    top_score: float
    cited_sources: List[SourceCitation]
    retrieved_sources: List[RetrievedChunk]
    meta: dict
