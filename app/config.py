from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://rag:rag@localhost:5432/rag"
    OPENROUTER_API_KEY: str = ""
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
