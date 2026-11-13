"""Shared test fixtures.

Every test runs against an isolated temporary SQLite file and a temporary raw archive.
Synthetic payloads live in ``tests/factories.py`` and ``tests/fixtures/``.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.database.base import Base
from app.database.session import init_engine, reset_engine, session_scope


@pytest.fixture
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database_path}")
    monkeypatch.setenv("RAW_STORAGE_DIR", str(tmp_path / "raw"))
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("API_DOCS_ENABLED", "true")
    monkeypatch.setenv("DATA_STALE_AFTER_MINUTES", "360")
    monkeypatch.setenv("SYNC_COMPETITION_IDS", "")
    monkeypatch.delenv("FOOTBALL_DATA_ORG_TOKEN", raising=False)
    monkeypatch.delenv("SYNC_ENABLED", raising=False)

    get_settings.cache_clear()
    reset_engine()
    engine = init_engine()
    Base.metadata.create_all(engine)

    settings = get_settings()
    yield SimpleNamespace(
        settings=settings,
        engine=engine,
        tmp_path=tmp_path,
        raw_dir=tmp_path / "raw",
    )

    reset_engine()
    get_settings.cache_clear()


@pytest.fixture
def session(database):
    with session_scope() as db:
        yield db


@pytest.fixture
def client(database) -> TestClient:
    from app.main import create_app

    with TestClient(create_app()) as test_client:
        yield test_client
