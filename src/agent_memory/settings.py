from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic import SecretStr
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="AGENT_MEMORY_",
        extra="ignore",
    )

    app_name: str = "agent-memory-from-scratch"

    memory_directory: Path = Path(".memory")
    sqlite_database_path: Path = Path(".memory") / "conversations.db"
    semantic_retrieval_enabled: bool = False
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    vector_store_path: Path | None = None
    vector_store_collection: str = "long_term_memory"

    summary_recent_message_limit: int = Field(default=12, ge=1)
    summary_after_message_count: int = Field(default=20, ge=2)
    summary_max_tokens: int = Field(default=512, ge=64)

    model_provider: str = "deepseek"
    model_name: str = "deepseek-chat"
    model_base_url: str | None = "https://api.deepseek.com"
    model_api_key: SecretStr | None = None
    model_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    model_max_output_tokens: int = Field(default=1024, ge=1)
    anthropic_version: str = "2023-06-01"


def get_settings() -> Settings:
    return Settings()
