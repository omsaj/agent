from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, HttpUrl
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    """Application configuration loaded from environment variables."""

    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/cyberscope.db",
        description="SQLAlchemy database URL for the dashboard.",
        validation_alias=AliasChoices("CYBERSCOPE_DATABASE_URL", "DATABASE_URL"),
    )
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key",
        validation_alias=AliasChoices("OPENAI_API_KEY"),
    )
    nist_nvd_endpoint: HttpUrl = Field(
        default="https://services.nvd.nist.gov/rest/json/cves/2.0",
        description="Endpoint for the NIST NVD API",
    )
    cisa_kev_endpoint: HttpUrl = Field(
        default="https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        description="Endpoint for the CISA Known Exploited Vulnerabilities feed",
    )
    github_advisory_endpoint: HttpUrl = Field(
        default="https://api.github.com/graphql",
        description="Endpoint for GitHub Security Advisory API (GraphQL)",
    )
    collection_schedule: str = Field(
        default="0 6 * * *",
        description="Cron-formatted schedule for data collection",
    )
    daily_token_budget: int = Field(
        default=50_000,
        description="Maximum number of tokens per day for OpenAI usage.",
    )
    request_rate_limit_per_sec: int = Field(
        default=1,
        description="Maximum number of analysis requests per second.",
    )
    cache_ttl_seconds: int = Field(
        default=21_600, description="TTL for cached API responses in seconds (6 hours)."
    )
    metrics_cache_ttl_seconds: int = Field(
        default=3_600, description="TTL for dashboard metrics cache in seconds."
    )
    frontend_origin: str = Field(
        default="http://localhost:5173",
        description="Allowed CORS origin for the frontend application.",
        validation_alias=AliasChoices("FRONTEND_ORIGIN"),
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Log level for application logging"
    )

    @field_validator("database_url", mode="before")
    @classmethod
    def ensure_async_sqlite(cls, value: str) -> str:
        if value.startswith("sqlite") and "+aiosqlite" not in value:
            if value.startswith("sqlite:///"):
                return value.replace("sqlite:///", "sqlite+aiosqlite:///")
            return value.replace("sqlite://", "sqlite+aiosqlite://")
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""

    return Settings()
