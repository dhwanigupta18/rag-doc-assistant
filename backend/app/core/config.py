from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str

    # Vector DB
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""
    QDRANT_COLLECTION: str = "document_chunks"

    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440

    # LLM
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "claude-sonnet-4-6"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    JINA_API_KEY: str = ""
    EMBEDDING_MODEL: str = "jina-embeddings-v3"
    RERANKER_MODEL: str = "jina-reranker-v2-base-multilingual"
    
    # File storage
    UPLOAD_DIR: str = "./uploads"

    # CORS
    FRONTEND_ORIGIN: str = "http://localhost:3000"


settings = Settings()
