from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "MaxBridge"
    environment: str = "local"
    database_url: str = "postgresql+asyncpg://maxbridge:maxbridge@postgres:5432/maxbridge"

    public_base_url: str = "https://maxbridge.app"
    telegram_bot_username: str = "MaxBridgeBot"
    telegram_bot_token: str = "000000:dev-token"
    telegram_drop_pending_updates: bool = True

    max_message_length: int = Field(default=4000, ge=1, le=4000)
    rate_limit_window_seconds: float = Field(default=60.0, gt=0)
    rate_limit_max_messages: int = Field(default=20, ge=1)

    @field_validator("public_base_url")
    @classmethod
    def normalize_public_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized:
            raise ValueError("PUBLIC_BASE_URL must not be empty.")
        return normalized

    @field_validator("telegram_bot_username")
    @classmethod
    def normalize_telegram_bot_username(cls, value: str) -> str:
        normalized = value.strip().lstrip("@")
        if not normalized:
            raise ValueError("TELEGRAM_BOT_USERNAME must not be empty.")
        return normalized


@lru_cache
def get_settings() -> Settings:
    return Settings()
