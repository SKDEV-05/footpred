"""Database engine and session management.

SQLite is the only supported engine in Phase 3 (ADR-0003). A non-SQLite URL fails
closed with an explicit message rather than pretending portability has been verified.
The engine is created lazily so importing the application does not require a database.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError

logger = logging.getLogger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _is_sqlite(url: str) -> bool:
    return url.startswith("sqlite")


def _is_memory_sqlite(url: str) -> bool:
    return _is_sqlite(url) and (
        ":memory:" in url or "mode=memory" in url or "cache=shared" in url
    )


def _sqlite_connect_listener(settings: Settings):
    def _configure(dbapi_connection, _connection_record) -> None:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute(f"PRAGMA busy_timeout = {int(settings.sqlite_busy_timeout_ms)}")
            if settings.sqlite_wal_enabled and not _is_memory_sqlite(settings.database_url):
                cursor.execute("PRAGMA journal_mode = WAL")
                cursor.execute("PRAGMA synchronous = NORMAL")
        finally:
            cursor.close()

    return _configure


def create_engine_for_settings(settings: Settings | None = None) -> Engine:
    """Build an engine, validating the engine family explicitly."""

    resolved = settings or get_settings()
    url = resolved.database_url

    if not _is_sqlite(url):
        raise ConfigurationError(
            "Only SQLite is supported in Phase 3 (ADR-0003). "
            "PostgreSQL has not been implemented or verified.",
            details={"database_url_scheme": url.split(":", 1)[0]},
        )

    connect_args: dict[str, object] = {"check_same_thread": False}
    kwargs: dict[str, object] = {
        "connect_args": connect_args,
        "pool_pre_ping": True,
        "future": True,
    }

    if _is_memory_sqlite(url):
        kwargs["poolclass"] = StaticPool
    else:
        _ensure_sqlite_directory(url)

    engine = create_engine(url, **kwargs)
    event.listen(engine, "connect", _sqlite_connect_listener(resolved))
    return engine


def _ensure_sqlite_directory(url: str) -> None:
    """Create the parent directory of a file-backed SQLite database."""

    path_part = url.split("sqlite+pysqlite:///", 1)[-1]
    if path_part.startswith("/"):
        database_path = Path(path_part)
    else:
        database_path = Path(path_part)
    if database_path.name in {"", ":memory:"}:
        return
    database_path.parent.mkdir(parents=True, exist_ok=True)


def init_engine(settings: Settings | None = None) -> Engine:
    global _engine, _session_factory

    if _engine is not None:
        return _engine

    _engine = create_engine_for_settings(settings)
    _session_factory = sessionmaker(
        bind=_engine,
        autoflush=False,
        expire_on_commit=False,
        future=True,
    )
    logger.info(
        "database engine initialised",
        extra={"event": "database.engine_initialised", "component": "database"},
    )
    return _engine


def get_engine() -> Engine:
    return init_engine()


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        init_engine()
    assert _session_factory is not None
    return _session_factory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional unit of work.

    Commits on success, rolls back on any exception, and always closes the session.
    """

    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request, no commit path."""

    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


def check_database(session: Session) -> bool:
    try:
        session.execute(select(1)).scalar_one()
        return True
    except Exception:  # noqa: BLE001 - readiness must not raise
        logger.exception(
            "database readiness check failed",
            extra={"event": "database.readiness_failed"},
        )
        return False


def reset_engine() -> None:
    """Dispose and forget the global engine. Intended for tests and shutdown."""

    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
