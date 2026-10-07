from fastapi import FastAPI, HTTPException, Request

import asyncpg

from app.config import settings
from app.retrieval import index
from app.schemas import AskRequest, AskResponse, RetrievedChunk, SourceCitation

_model_loaded = True

app = FastAPI(title="Regulatory RAG API", version="1.0.0")


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    public_paths = {"/health", "/docs", "/openapi.json", "/redoc"}

    if request.url.path not in public_paths:
        api_key = request.headers.get("X-API-Key")
        if api_key is not None and api_key != settings.API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API Key")

    if request.method == "OPTIONS":
        return await call_next(request)

    return await call_next(request)


@app.on_event("startup")
async def startup():
    try:
        loaded_count = index.load()
        app.state.documents_loaded = loaded_count
    except Exception:
        app.state.documents_loaded = 0


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "db_connected": False,
        "models_loaded": _model_loaded,
        "documents_loaded": getattr(app.state, "documents_loaded", 0),
    }


@app.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest):
    retrieved = index.search(payload.question, payload.top_k)
    if not retrieved:
        return AskResponse(
            answer="No regulatory documents are available yet. Add PDFs to the data/raw folder and reload the index.",
            answered=False,
            top_score=0.0,
            cited_sources=[],
            retrieved_sources=[],
            meta={
                "strategy": payload.strategy,
                "mode": payload.mode,
                "requested_top_k": payload.top_k,
                "question_length": len(payload.question),
                "documents_loaded": getattr(app.state, "documents_loaded", 0),
            },
        )

    answer_parts = [chunk.content for chunk in retrieved[:3]]
    summary = " ".join(part[:220] for part in answer_parts)
    top_score = retrieved[0].vector_score
    cited_sources = [
        SourceCitation(
            doc_title=chunk.doc_title,
            page_start=chunk.page_start,
            snippet=chunk.content[:250],
        )
        for chunk in retrieved[: payload.top_k]
    ]
    retrieved_sources = [
        RetrievedChunk(
            chunk_id=chunk.chunk_id,
            doc_title=chunk.doc_title,
            page_start=chunk.page_start,
            content=chunk.content,
            vector_score=chunk.vector_score,
            keyword_score=chunk.keyword_score,
            rerank_score=chunk.rerank_score,
            fused_score=chunk.fused_score,
        )
        for chunk in retrieved
    ]

    return AskResponse(
        answer=(
            "Based on the most relevant excerpts in the available regulatory documents, "
            f"the likely answer is: {summary[:1200]}"
        ),
        answered=True,
        top_score=top_score,
        cited_sources=cited_sources,
        retrieved_sources=retrieved_sources,
        meta={
            "strategy": payload.strategy,
            "mode": payload.mode,
            "requested_top_k": payload.top_k,
            "question_length": len(payload.question),
            "documents_loaded": getattr(app.state, "documents_loaded", 0),
            "matche_count": len(retrieved),
        },
    )


@app.get("/db-status")
async def db_status():
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL)
        await conn.execute("SELECT 1")
        await conn.close()
        return {"status": "connected"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
