"""Typed, environment-based application configuration.

Secrets are wrapped in ``SecretStr`` so they cannot leak through repr, logs, or
serialisation by accident. Every value has a documented default except the provider
token, which is optional: the API can serve stored data without a provider.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Football Intelligence Platform"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"

    database_url: str = "sqlite+pysqlite:///./data/football.db"
    sqlite_wal_enabled: bool = True
    sqlite_busy_timeout_ms: int = 5000

    raw_storage_dir: Path = Path("./data/raw")

    api_page_size_default: int = 25
    api_page_size_max: int = 100
    api_docs_enabled: bool = True
    data_stale_after_minutes: int = 360

    football_data_org_token: SecretStr | None = None
    football_data_org_base_url: str = "https://api.football-data.org/v4"
    provider_requests_per_minute: int = 10

    http_timeout_seconds: float = 15.0
    http_max_retries: int = 3
    http_backoff_base_seconds: float = 1.0

    sync_enabled: bool = False
    sync_interval_minutes: int = 60
    sync_lookback_days: int = 3
    sync_lookahead_days: int = 14
    sync_competition_ids: str = ""
    sync_statistics_limit_per_run: int = 25
    sync_stale_run_after_minutes: int = 360
    identity_kickoff_window_minutes: int = 180

    @field_validator("football_data_org_token", mode="before")
    @classmethod
    def _blank_token_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("database_url")
    @classmethod
    def _require_database_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DATABASE_URL must not be empty")
        return value.strip()

    @field_validator(
        "provider_requests_per_minute",
        "http_max_retries",
        "api_page_size_default",
        "api_page_size_max",
        "data_stale_after_minutes",
        "sync_interval_minutes",
        "sync_lookback_days",
        "sync_lookahead_days",
        "sync_statistics_limit_per_run",
        "sqlite_busy_timeout_ms",
        "identity_kickoff_window_minutes",
        "sync_stale_run_after_minutes",
    )
    @classmethod
    def _positive_int(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be greater than zero")
        return value

    @field_validator("http_timeout_seconds", "http_backoff_base_seconds")
    @classmethod
    def _positive_float(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("value must be greater than zero")
        return value

    @model_validator(mode="after")
    def _default_within_max(self) -> Settings:
        if self.api_page_size_default > self.api_page_size_max:
            raise ValueError("API_PAGE_SIZE_DEFAULT must not exceed API_PAGE_SIZE_MAX")
        return self

    @property
    def competition_ids(self) -> tuple[str, ...]:
        return tuple(
            item.strip()
            for item in self.sync_competition_ids.split(",")
            if item.strip()
        )

    @property
    def provider_configured(self) -> bool:
        return self.football_data_org_token is not None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
