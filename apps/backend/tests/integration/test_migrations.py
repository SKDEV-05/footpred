"""Migration integrity: the initial revision must build the same schema as the models.

The test runs Alembic in-process against a separate temporary SQLite file.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, inspect

from app.core.config import get_settings
from app.database.base import Base
from app.database.session import reset_engine
import app.models  # noqa: F401  (registers all tables)

REPO_ROOT = Path(__file__).resolve().parents[4]

EXPECTED_TABLES = {
    "alembic_version",
    "countries",
    "competitions",
    "seasons",
    "teams",
    "matches",
    "match_results",
    "team_match_statistics",
    "data_providers",
    "provider_competition_mappings",
    "provider_season_mappings",
    "provider_team_mappings",
    "provider_match_mappings",
    "raw_payloads",
    "data_sync_runs",
    "data_sync_errors",
    "quarantined_records",
    "match_change_log",
}


def _alembic_config() -> Config:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option(
        "script_location", str(REPO_ROOT / "apps" / "backend" / "migrations")
    )
    return config


@pytest.fixture
def migrated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    database_path = tmp_path / "migrated.db"
    url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("RAW_STORAGE_DIR", str(tmp_path / "raw"))
    get_settings.cache_clear()
    reset_engine()

    command.upgrade(_alembic_config(), "head")
    yield url

    reset_engine()
    get_settings.cache_clear()


def test_initial_migration_builds_every_table(migrated):
    engine = create_engine(migrated)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert tables == EXPECTED_TABLES


def test_migrated_schema_has_no_drift_from_the_models(migrated):
    engine = create_engine(migrated)
    try:
        with engine.connect() as connection:
            context = MigrationContext.configure(connection)
            differences = compare_metadata(context, Base.metadata)
    finally:
        engine.dispose()

    assert differences == []


def test_upgrade_is_idempotent(migrated):
    command.upgrade(_alembic_config(), "head")
    engine = create_engine(migrated)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
    assert tables == EXPECTED_TABLES
