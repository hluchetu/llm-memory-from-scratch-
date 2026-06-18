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
        env_prefix="LLM_MEMORY_",
        extra="ignore",
    )

    app_name: str = "llm-memory-from-scratch"

    memory_directory: Path = Path(".memory")
    sqlite_database_path: Path = Path(".memory") / "conversations.db"

    summary_recent_message_limit: int = Field(default=12, ge=1)
    summary_after_message_count: int = Field(default=20, ge=2)
    summary_max_tokens: int = Field(default=512, ge=64)

    model_provider: str = "openai"
    model_name: str = "gpt-5.2"
    model_base_url: str | None = None
    model_api_key: SecretStr | None = None
    model_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    model_max_output_tokens: int = Field(default=1024, ge=1)


def get_settings() -> Settings:
    return Settings()
