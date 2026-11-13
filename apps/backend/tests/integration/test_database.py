"""SQLite operational guarantees and the fail-closed database guard."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.core.exceptions import ConfigurationError
from app.database.session import (
    check_database,
    create_engine_for_settings,
    reset_engine,
)


def test_non_sqlite_url_fails_closed():
    settings = Settings(database_url="postgresql+psycopg://user:pass@localhost/db")
    with pytest.raises(ConfigurationError) as excinfo:
        create_engine_for_settings(settings)
    assert "Only SQLite is supported" in str(excinfo.value)
    assert excinfo.value.details == {"database_url_scheme": "postgresql+psycopg"}


def test_foreign_keys_and_wal_are_enabled(database):
    with database.engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar_one() == 1
        assert connection.execute(text("PRAGMA journal_mode")).scalar_one().lower() == "wal"
        assert connection.execute(text("PRAGMA busy_timeout")).scalar_one() == 5000


def test_foreign_key_violation_is_rejected_by_the_database(session):
    from app.models.core import Team

    session.add(
        Team(
            name="Orphan FC",
            normalized_name="orphan fc",
            country_id=999_999,
        )
    )
    with pytest.raises(IntegrityError):
        session.flush()
    session.rollback()


def test_check_database_reports_health(session):
    assert check_database(session) is True


def test_reset_engine_creates_a_new_engine(database):
    from app.database.session import init_engine

    first = database.engine
    reset_engine()
    second = init_engine()
    assert second is not first
