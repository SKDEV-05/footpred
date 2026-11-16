"""Operator CLI and worker startup guards.

These tests exercise process entry points, not just library functions, because a broken
CLI path would make migrations and sync look unavailable in production.
"""

from __future__ import annotations

import json

from sqlalchemy import create_engine, inspect

from app import cli, worker
from app.core.config import get_settings
from app.database.session import reset_engine


def _payload(output: str) -> dict:
    """Extract the CLI's pretty-printed JSON from structured log lines."""

    lines = output.splitlines()
    start = max(
        index for index, line in enumerate(lines) if line.strip() == "{"
    )
    return json.loads("\n".join(lines[start:]))


def _isolated_database(tmp_path, monkeypatch):
    url = f"sqlite+pysqlite:///{tmp_path / 'cli.db'}"
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("RAW_STORAGE_DIR", str(tmp_path / "raw"))
    # An empty token (not a deleted one) is what neutralises a real credential: the
    # Settings validator maps blank to None, and an exported empty variable also stops
    # pydantic-settings from falling back to a token committed to .env on the host.
    monkeypatch.setenv("FOOTBALL_DATA_ORG_TOKEN", "")
    monkeypatch.delenv("SYNC_ENABLED", raising=False)
    get_settings.cache_clear()
    reset_engine()
    return url


def test_migrate_command_finds_and_applies_the_migration(tmp_path, monkeypatch, capsys):
    url = _isolated_database(tmp_path, monkeypatch)

    assert cli.main(["migrate"]) == 0
    payload = _payload(capsys.readouterr().out)
    assert payload["migrated"] == "head"

    engine = create_engine(url)
    try:
        assert "alembic_version" in inspect(engine).get_table_names()
    finally:
        engine.dispose()

    reset_engine()
    get_settings.cache_clear()


def test_status_command_is_json_and_exit_zero(tmp_path, monkeypatch, capsys):
    _isolated_database(tmp_path, monkeypatch)
    cli.main(["migrate"])
    capsys.readouterr()

    assert cli.main(["status"]) == 0
    payload = _payload(capsys.readouterr().out)
    assert payload["provider_configured"] is False
    assert payload["runs"] == []

    reset_engine()
    get_settings.cache_clear()


def test_check_provider_refuses_without_a_token(tmp_path, monkeypatch, capsys):
    _isolated_database(tmp_path, monkeypatch)

    assert cli.main(["check-provider"]) == 2
    payload = _payload(capsys.readouterr().out)
    assert payload["configured"] is False
    assert "not set" in payload["message"]

    reset_engine()
    get_settings.cache_clear()


def test_worker_refuses_to_start_without_configuration(tmp_path, monkeypatch):
    _isolated_database(tmp_path, monkeypatch)
    assert worker.main() == 2

    reset_engine()
    get_settings.cache_clear()
