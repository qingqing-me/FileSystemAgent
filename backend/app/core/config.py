"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # LLM
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_model: str = "deepseek-chat"
    llm_temperature: float = 0.3

    # Embedding
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    embedding_device: str = "cpu"

    # Vector Store
    chroma_persist_dir: str = "./chroma_data"

    # Chunking
    chunk_size: int = 800
    chunk_overlap: int = 150

    # Database
    database_url: str = "sqlite+aiosqlite:///./school_rag.db"

    # Ingestion
    ingestion_api_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
