"""Central configuration, read from environment variables / .env."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM: openai | anthropic | mock (mock needs no API key; returns retrieved excerpts)
    llm_provider: str = "mock"
    llm_model: str = ""  # empty -> sensible default per provider
    openai_api_key: str = ""
    anthropic_api_key: str = ""

    # Embeddings: openai | fastembed (local, free) | fake (tests only)
    embeddings_provider: str = "fastembed"
    embeddings_model: str = ""

    # Vector store: faiss | pgvector
    vector_store: str = "faiss"
    pgvector_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/docmind"

    data_dir: Path = Path("data")
    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 5
    csv_rows_per_chunk: int = 20
    max_upload_mb: int = 25
    cors_origins: str = "http://localhost:5173"

    @property
    def index_dir(self) -> Path:
        return self.data_dir / "faiss_index"

    @property
    def registry_path(self) -> Path:
        return self.data_dir / "registry.json"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.data_dir.mkdir(parents=True, exist_ok=True)
    return s
