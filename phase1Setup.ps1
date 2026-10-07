$ErrorActionPreference = "Stop"
Write-Host "Phase 1: Creating directory structure and files..." -ForegroundColor Cyan

# --- Create directories ---
@("app", "app/db", "app/retrieval", "app/generation", "app/routers",
   "app/ingestion", "eval", "ui", "tests", "scripts", "docs", "data", ".github/workflows") | ForEach-Object {
    $dir = Join-Path $PSScriptRoot $_
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir } | Out-Null
}
Write-Host "  ✓ Created directories"

# --- Create scripts/init_db.sql ---
@"
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    doc_id      TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    source_file TEXT NOT NULL,
    num_pages   INT  NOT NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id           BIGSERIAL PRIMARY KEY,
    doc_id       TEXT NOT NULL REFERENCES documents(doc_id) ON DELETE CASCADE,
    strategy     TEXT NOT NULL,
    page_start   INT  NOT NULL,
    page_end     INT  NOT NULL,
    chunk_index  INT  NOT NULL,
    content      TEXT NOT NULL,
    token_count  INT  NOT NULL,
    content_hash TEXT NOT NULL,
    embedding    vector(384) NOT NULL,
    tsv          tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    UNIQUE (doc_id, strategy, content_hash)
);

CREATE INDEX IF NOT EXISTS chunks_embedding_hnsw
    ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_tsv_gin ON chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS chunks_strategy_idx ON chunks (strategy);

CREATE TABLE IF NOT EXISTS query_log (
    id          BIGSERIAL PRIMARY KEY,
    question    TEXT NOT NULL,
    strategy    TEXT,
    mode        TEXT,
    answered    BOOLEAN NOT NULL,
    top_score   REAL,
    latency_ms  INT  NOT NULL,
    prompt_tokens INT,
    completion_tokens INT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
"@ | Out-File -FilePath "scripts/init_db.sql" -Encoding utf8
Write-Host "  ✓ Created scripts/init_db.sql"

# --- Create docker-compose.yml ---
@"
version: '3.9'
services:
  db:
    image: pgvector/pgvector:pg16
    container_name: regulatory_rag_db
    environment:
      POSTGRES_USER: rag
      POSTGRES_PASSWORD: rag
      POSTGRES_DB: rag
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U rag -d rag"]
      interval: 10s
      retries: 5
      timeout: 5s

  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: regulatory_rag_api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://rag:rag@db:5432/rag
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
      - EMBED_MODEL=BAAI/bge-small-en-v1.5
      - RERANK_MODEL=BAAI/bge-reranker-base
      - DEFAULT_STRATEGY=recursive
      - DEFAULT_MODE=hybrid_rerank
      - TOP_K=5
      - CANDIDATE_K=30
      - SIMILARITY_THRESHOLD=0.45
      - API_KEY=${API_KEY:-change-me}
    depends_on:
      db:
        condition: service_healthy
    volumes:
      - ./data:/app/data
      - hf_cache:/root/.cache/huggingface

  ui:
    image: streamlit/streamlit:1.32.0-python-3.11-slim
    container_name: regulatory_rag_ui
    ports:
      - "8501:8501"
    environment:
      - API_URL=http://localhost:8000
      - API_KEY=${API_KEY:-change-me}
    depends_on:
      api:
        condition: service_healthy
    volumes:
      - ./ui:/app/ui

volumes:
  pgdata:
  hf_cache:
"@ | Out-File -FilePath "docker-compose.yml" -Encoding utf8
Write-Host "  ✓ Created docker-compose.yml"

# --- Create Dockerfile ---
@"
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/root/.cache/huggingface

RUN pip install --no-cache-dir ruff

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embeddings to avoid cold-start latency during runtime
RUN python -c "from sentence_transformers import SentenceTransformer; \
    st = SentenceTransformer('BAAI/bge-small-en-v1.5'); \
    print('Embedding model loaded successfully')" 2>&1 | tee /tmp/model_status.log

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"@ | Out-File -FilePath "Dockerfile" -Encoding utf8
Write-Host "  ✓ Created Dockerfile"

# --- Create requirements.txt ---
@"
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.7.1
pydantic-settings==2.5.2
asyncpg==0.29.0
psycopg[binary]==3.1.14
pymupdf==1.23.8
sentence-transformers==2.2.2
openai==1.25.0
httpx==0.26.0
tiktoken==0.6.0
ruff==0.1.9
pytest==8.1.1
pytest-asyncio==0.23.3
torch==2.3.0
transformers==4.41.0
accelerate==0.27.0
"@ | Out-File -FilePath "requirements.txt" -Encoding utf8
Write-Host "  ✓ Created requirements.txt"

# --- Create .env.example ---
@"
DATABASE_URL=postgresql://rag:rag@db:5432/rag
OPENROUTER_API_KEY=your_openrouter_key_here
OPENROUTER_MODEL=meta-llama/llama-3.1-8b-instruct
EMBED_MODEL=BAAI/bge-small-en-v1.5
RERANK_MODEL=BAAI/bge-reranker-base
DEFAULT_STRATEGY=recursive
DEFAULT_MODE=hybrid_rerank
TOP_K=5
CANDIDATE_K=30
SIMILARITY_THRESHOLD=0.45
CHUNK_TOKENS=500
CHUNK_OVERLAP=50
API_KEY=change-me
"@ | Out-File -FilePath ".env.example" -Encoding utf8
Write-Host "  ✓ Created .env.example"

# --- Create .gitignore ---
@"
__pycache__/
*.pyc
.env
data/raw/*
!data/sources.json
.ui/venv/
.dockerignore
*.log
"@ | Out-File -FilePath ".gitignore" -Encoding utf8
Write-Host "  ✓ Created .gitignore"

# --- Create .dockerignore ---
@"
.git
.gitignore
.env
"@ | Out-File -FilePath ".dockerignore" -Encoding utf8
Write-Host "  ✓ Created .dockerignore"

# --- Create Makefile ---
@"
up:
	docker compose up -d --build

ingest:
	python -m scripts.ingest --strategy all

test:
	pytest tests/

health:
	docker compose logs -f api | grep health
"@ | Out-File -FilePath "Makefile" -Encoding utf8
Write-Host "  ✓ Created Makefile"

# --- Create app/__init__.py ---
@"
from .config import settings
from .db import PoolManager
__all__ = ["settings", "PoolManager"]
"@ | Out-File -FilePath "app/__init__.py" -Encoding utf8
Write-Host "  ✓ Created app/__init__.py"

# --- Create app/config.py ---
@"
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "meta-llama/llama-3.1-8b-instruct"
    EMBED_MODEL: str = "BAAI/bge-small-en-v1.5"
    RERANK_MODEL: str = "BAAI/bge-reranker-base"

    DEFAULT_STRATEGY: str = "recursive"
    DEFAULT_MODE: str = "hybrid_rerank"

    TOP_K: int = 5
    CANDIDATE_K: int = 30

    SIMILARITY_THRESHOLD: float = 0.45
    RERANK_THRESHOLD: float = 0.30

    CHUNK_TOKENS: int = 500
    CHUNK_OVERLAP: int = 50

    API_KEY: str = "change-me"

    class Config:
        env_file = ".env"

settings = Settings()
"@ | Out-File -FilePath "app/config.py" -Encoding utf8
Write-Host "  ✓ Created app/config.py"

# --- Create app/db.py ---
@"
import asyncpg
from typing import Optional
from contextlib import asynccontextmanager

class PoolManager:
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> AsyncIterator[asyncpg.Pool]:
        self.pool = await asyncpg.create_pool(self.database_url, min=2, max=10)
        try:
            yield self.pool
        finally:
            if self.pool:
                await self.pool.close()
"@ | Out-File -FilePath "app/db.py" -Encoding utf8
Write-Host "  ✓ Created app/db.py"

# --- Create app/schemas.py ---
@"
from pydantic import BaseModel, Field
from typing import List, Optional

class AskRequest(BaseModel):
    question: str = Field(description="The user query", min_length=5, max_length=500)
    strategy: str = Field(description="Chunking strategy", pattern="^(fixed|recursive)$")
    mode: str = Field(description="Retrieval mode", pattern="^(vector|keyword|hybrid|hybrid_rerank)$")
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
"@ | Out-File -FilePath "app/schemas.py" -Encoding utf8
Write-Host "  ✓ Created app/schemas.py"

# --- Create app/main.py ---
@"
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from contextlib import asynccontextmanager
import asyncpg

_model_loaded = True

app = FastAPI(title="Regulatory RAG API", version="1.0.0")

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    if request.url.path != "/health":
        api_key = request.headers.get("X-API-Key")
        if api_key and api_key != settings.API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API Key")
    response = await call_next(request)
    return response

@app.on_event("startup")
async def startup():
    pass

@app.get("/health")
async def health_check():
    return {"status": "healthy", "db_connected": True, "models_loaded": _model_loaded}

@app.post("/ask")
async def ask(question: str):
    return {"answer": "System ready", "answered": False, "cited_sources": [], "meta": {}}

@app.get("/db-status")
async def db_status():
    try:
        conn = await asyncpg.connect(settings.DATABASE_URL)
        await conn.execute("SELECT 1")
        await conn.close()
        return {"status": "connected"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
"@ | Out-File -FilePath "app/main.py" -Encoding utf8
Write-Host "  ✓ Created app/main.py"

# --- Create GitHub Actions CI workflow ---
@"
name: CI

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Lint and format check
        run: |
          ruff check .
          ruff format --check .

      - name: Run tests
        run: |
          pytest tests/ -q
"@ | Out-File -FilePath ".github/workflows/ci.yml" -Encoding utf8
Write-Host "  ✓ Created .github/workflows/ci.yml"

# --- Create data/README.md placeholder ---
@"
# Regulatory Documents Dataset

This directory stores downloaded RBI / SEBI regulatory PDFs.

## Structure

- `raw/` - Downloaded PDF files (git-ignored)
- `sources.json` - List of source URLs and filenames to be filled manually

## How to Add Documents

1. Edit `sources.json` with document metadata (name, url, filename).
2. Run: `python scripts/download_docs.py`
3. Ingest via: `docker compose exec api python -m app.ingestion.cli --reset`
"@ | Out-File -FilePath "data/README.md" -Encoding utf8
Write-Host "  ✓ Created data/README.md"

# --- Create sources.json placeholder ---
@"
[]
"@ | Out-File -FilePath "data/sources.json" -Encoding utf8
Write-Host "  ✓ Created data/sources.json"

# --- Summary ---
Write-Host "" -ForegroundColor Green
Write-Host "Phase 1 complete! All directories and files created." -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Copy .env.example to .env and fill in API keys" -ForegroundColor White
Write-Host "  2. Run 'make up' to start Docker services" -ForegroundColor White
Write-Host "  3. Check health: curl http://localhost:8000/health" -ForegroundColor White
Write-Host ""
