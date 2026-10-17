"""
Application configuration using Pydantic Settings.
Reads from environment variables / .env file.
"""
from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ─────────────────────────────────────────────────────
    app_name: str = "SplitSmart AI"
    app_version: str = "1.0.0"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False

    # ── Database ─────────────────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://splitsmart:splitsmart@localhost:5432/splitsmart"
    )
    sync_database_url: str = (
        "postgresql://splitsmart:splitsmart@localhost:5432/splitsmart"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ── Redis ────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Auth ─────────────────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production-generate-with-secrets-token-hex-32"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    guest_token_expire_minutes: int = 480

    # ── CORS ─────────────────────────────────────────────────────
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # ── AI ───────────────────────────────────────────────────────
    gemini_api_key: str = ""

    @property
    def use_mock_ocr(self) -> bool:
        """Use mock OCR when no Gemini API key is configured."""
        return not self.gemini_api_key or self.gemini_api_key == "your-google-ai-studio-key-here"

    # ── File Upload ───────────────────────────────────────────────
    max_upload_size_mb: int = 10
    upload_dir: str = "./uploads"

    # ── Rate Limiting ─────────────────────────────────────────────
    rate_limit_ai_per_minute: int = 10
    rate_limit_upload_per_hour: int = 20


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton — call this everywhere."""
    return Settings()
