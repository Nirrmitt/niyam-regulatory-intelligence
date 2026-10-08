from fastapi import FastAPI, HTTPException, Request
from openai import OpenAIError
from starlette.concurrency import run_in_threadpool

import asyncpg

from app.config import settings
from app.generation import generate_grounded_answer
from app.retrieval import index
from app.schemas import AskRequest, AskResponse, RetrievedChunk, SourceCitation

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
    app.state.documents_loaded = index.load()


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "db_connected": False,
        "models_loaded": index.embeddings_loaded,
        "generation_configured": bool(settings.OPENROUTER_API_KEY),
        "documents_loaded": getattr(app.state, "documents_loaded", 0),
    }


@app.post("/ask", response_model=AskResponse)
async def ask(payload: AskRequest):
    retrieved = await run_in_threadpool(
        index.search, payload.question, payload.top_k, payload.mode
    )
    if not retrieved:
        return AskResponse(
            answer="No relevant regulatory passages were found. Add PDFs to data/raw and reload the index, or try a more specific question.",
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
                "generation_model": settings.OPENROUTER_MODEL,
            },
        )

    if payload.mode == "keyword":
        top_score = retrieved[0].keyword_score or 0.0
    elif payload.mode == "hybrid_rerank":
        top_score = retrieved[0].rerank_score or 0.0
    else:
        top_score = retrieved[0].vector_score
    threshold = (
        settings.RERANK_THRESHOLD
        if payload.mode == "hybrid_rerank"
        else settings.SIMILARITY_THRESHOLD
    )
    if top_score < threshold:
        return AskResponse(
            answer="The indexed passages did not provide sufficiently strong evidence to answer this question. Try rephrasing it or adding a more relevant source document.",
            answered=False,
            top_score=top_score,
            cited_sources=[],
            retrieved_sources=[
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
            ],
            meta={
                "strategy": payload.strategy,
                "mode": payload.mode,
                "requested_top_k": payload.top_k,
                "question_length": len(payload.question),
                "documents_loaded": getattr(app.state, "documents_loaded", 0),
                "match_count": len(retrieved),
                "generation_model": settings.OPENROUTER_MODEL,
            },
        )

    try:
        answer = await generate_grounded_answer(payload.question, retrieved)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OpenAIError as exc:
        raise HTTPException(
            status_code=502, detail=f"Answer generation failed: {exc}"
        ) from exc

    cited_sources = [
        SourceCitation(
            source_id=f"S{index}",
            doc_title=chunk.doc_title,
            page_start=chunk.page_start,
            snippet=chunk.content[:250],
        )
        for index, chunk in enumerate(retrieved, start=1)
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
        answer=answer,
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
            "match_count": len(retrieved),
            "generation_model": settings.OPENROUTER_MODEL,
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
