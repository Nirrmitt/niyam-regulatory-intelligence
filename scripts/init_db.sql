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
