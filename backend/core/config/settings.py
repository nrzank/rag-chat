from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5434/ragchat"

    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    qdrant_url: str = "http://localhost:6335"
    qdrant_collection: str = "documents"
    embedding_dim: int = 1536

    upload_dir: Path = BASE_DIR / "uploads"

    retrieval_top_k: int = 5

    chunk_size: int = 512
    chunk_overlap: int = 64

    @model_validator(mode="after")
    def check_chunking(self) -> "Settings":
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError(
                f"chunk_overlap must be in [0, chunk_size), got {self.chunk_overlap} with chunk_size={self.chunk_size}"
            )
        return self


settings = Settings()
