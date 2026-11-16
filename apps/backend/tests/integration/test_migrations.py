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
from sqlalchemy import create_engine, inspect, text

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
    "match_analyses",
    "model_evaluations",  # Phase 6: evaluation run persistence
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


def test_result_semantics_migration_preserves_populated_rows(tmp_path, monkeypatch):
    database_path = tmp_path / "populated.db"
    url = f"sqlite+pysqlite:///{database_path}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("RAW_STORAGE_DIR", str(tmp_path / "raw"))
    get_settings.cache_clear()
    reset_engine()
    config = _alembic_config()
    command.upgrade(config, "0001")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys = ON")
        connection.execute(text("INSERT INTO countries (id, name, normalized_name, created_at, updated_at) VALUES (1, 'X', 'x', '2026-08-01 12:00:00', '2026-08-01 12:00:00')"))
        connection.execute(text("INSERT INTO competitions (id, name, normalized_name, type, country_id, created_at, updated_at) VALUES (1, 'Cup', 'cup', 'cup', 1, '2026-08-01 12:00:00', '2026-08-01 12:00:00')"))
        connection.execute(text("INSERT INTO seasons (id, competition_id, label, start_date, end_date, is_current, created_at, updated_at) VALUES (1, 1, '2026', '2026-01-01', '2026-12-31', 1, '2026-08-01 12:00:00', '2026-08-01 12:00:00')"))
        connection.execute(text("INSERT INTO teams (id, name, normalized_name, created_at, updated_at) VALUES (1, 'A', 'a', '2026-08-01 12:00:00', '2026-08-01 12:00:00'), (2, 'B', 'b', '2026-08-01 12:00:00', '2026-08-01 12:00:00')"))
        connection.execute(text("INSERT INTO matches (id, competition_id, season_id, home_team_id, away_team_id, kickoff_utc, status, first_seen_at, last_synced_at, created_at, updated_at) VALUES (1, 1, 1, 1, 2, '2026-08-01 12:00:00', 'finished', '2026-08-01 12:00:00', '2026-08-01 12:00:00', '2026-08-01 12:00:00', '2026-08-01 12:00:00')"))
        connection.execute(text("INSERT INTO match_results (match_id, home_score, away_score, status, is_final, resolved_at, created_at, updated_at) VALUES (1, 1, 0, 'finished', 1, '2026-08-01 12:00:00', '2026-08-01 12:00:00', '2026-08-01 12:00:00')"))
    engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys = ON")
        connection.execute(text("INSERT INTO data_providers (id, code, name, created_at, updated_at) VALUES (1, 'p', 'P', '2026-08-01 12:00:00', '2026-08-01 12:00:00')"))
        connection.execute(text("INSERT INTO raw_payloads (id, provider_id, resource_type, request_path, fetched_at, http_status, content_sha256, storage_path, byte_size) VALUES (1, 1, 'matches', '/matches', '2026-08-01 12:00:00', 200, 'a', 'p/a/a.json', 1)"))
        connection.execute(text("UPDATE matches SET raw_payload_id = 1 WHERE id = 1"))
        connection.execute(text("UPDATE match_results SET raw_payload_id = 1 WHERE match_id = 1"))
        assert connection.execute(text("SELECT raw_payload_id FROM matches WHERE id = 1")).scalar_one() == 1
        connection.execute(text("DELETE FROM raw_payloads WHERE id = 1"))
        assert connection.execute(text("SELECT raw_payload_id FROM matches WHERE id = 1")).scalar_one() is None
        assert connection.execute(text("SELECT raw_payload_id FROM match_results WHERE match_id = 1")).scalar_one() is None
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT home_score, away_score, extra_home_score, shootout_home_score FROM match_results WHERE match_id = 1")
        ).one()
    engine.dispose()
    reset_engine()
    get_settings.cache_clear()
    assert tuple(row) == (1, 0, None, None)
