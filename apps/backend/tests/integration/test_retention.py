"""Retention and deletion policy: safe cleanup with integrity verification.

Tests that the retention module deletes only expired payloads, re-hashes
before removal, refuses tampered files, and is a no-op when retention is 0.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.time import utc_now
from app.database.session import get_session_factory, session_scope
from app.ingestion.outcomes import ensure_data_provider
from app.ingestion.raw_archive import RawArchive
from app.ingestion.retention import (
    purge_expired_raw_payloads,
    purge_expired_sync_runs,
)
from app.models.enums import SyncStatus
from app.models.provenance import DataSyncError, DataSyncRun, RawPayload
from app.providers.dto import RawResponse


def _provider_id() -> int:
    with session_scope() as session:
        return ensure_data_provider(
            session, code="football_data_org", name="football-data.org"
        ).id


def _archive_response(
    archive: RawArchive, content: bytes, *, fetched_at: datetime
) -> int:
    response = RawResponse(
        url="https://api.example.test/v4/competitions",
        path="/competitions",
        params={"dateFrom": "2026-08-01"},
        status_code=200,
        headers={"content-type": "application/json"},
        content=content,
        fetched_at=fetched_at,
    )
    return archive.store(response, resource_type="competitions")


def test_zero_retention_is_a_noop(database):
    provider_id = _provider_id()
    archive = RawArchive(
        provider_code="football_data_org",
        provider_id=provider_id,
        storage_root=database.raw_dir,
    )
    _archive_response(archive, b'{"a":1}', fetched_at=utc_now())

    result = purge_expired_raw_payloads(
        storage_root=database.raw_dir,
        session_factory=get_session_factory(),
        retention_days=0,
    )
    assert result.raw_payloads_deleted == 0
    with session_scope() as session:
        assert session.execute(select(RawPayload)).scalars().first() is not None


def test_expired_payload_is_deleted(database):
    provider_id = _provider_id()
    archive = RawArchive(
        provider_code="football_data_org",
        provider_id=provider_id,
        storage_root=database.raw_dir,
    )
    old_content = b'{"old":true}'
    old_id = _archive_response(
        archive, old_content, fetched_at=utc_now() - timedelta(days=90)
    )
    new_content = b'{"new":true}'
    _archive_response(archive, new_content, fetched_at=utc_now())

    result = purge_expired_raw_payloads(
        storage_root=database.raw_dir,
        session_factory=get_session_factory(),
        retention_days=30,
    )
    assert result.raw_payloads_deleted == 1
    assert result.raw_bytes_freed == len(old_content)
    assert result.integrity_failures == []

    with session_scope() as session:
        remaining = session.execute(select(RawPayload)).scalars().all()
        assert len(remaining) == 1
        assert remaining[0].id != old_id


def test_tampered_payload_is_not_deleted(database):
    provider_id = _provider_id()
    archive = RawArchive(
        provider_code="football_data_org",
        provider_id=provider_id,
        storage_root=database.raw_dir,
    )
    content = b'{"original":true}'
    payload_id = _archive_response(
        archive, content, fetched_at=utc_now() - timedelta(days=90)
    )

    # Tamper with the archived file after it was written.
    with session_scope() as session:
        row = session.get(RawPayload, payload_id)
        assert row is not None
        path = database.raw_dir / row.storage_path
    path.write_bytes(b'{"tampered":true}')

    result = purge_expired_raw_payloads(
        storage_root=database.raw_dir,
        session_factory=get_session_factory(),
        retention_days=30,
    )
    assert result.raw_payloads_deleted == 0
    assert len(result.integrity_failures) == 1
    assert "digest mismatch" in result.integrity_failures[0]
    assert path.exists(), "tampered file must be kept, not deleted"


def test_sync_run_retention_deletes_old_runs(database):
    provider_id = _provider_id()
    old_time = utc_now() - timedelta(days=90)
    recent_time = utc_now() - timedelta(days=1)

    with session_scope() as session:
        old_run = DataSyncRun(
            provider_id=provider_id,
            job_type="fixtures",
            status=SyncStatus.SUCCESS,
            started_at=old_time,
            finished_at=old_time + timedelta(minutes=5),
            parameters={},
            records_fetched=1,
            records_created=1,
            records_updated=0,
            records_unchanged=0,
            records_rejected=0,
            error_count=0,
        )
        session.add(old_run)
        session.flush()
        session.add(
            DataSyncError(
                sync_run_id=old_run.id,
                stage="ingestion",
                code="test_error",
                message="synthetic",
                created_at=old_time,
            )
        )
        recent_run = DataSyncRun(
            provider_id=provider_id,
            job_type="fixtures",
            status=SyncStatus.SUCCESS,
            started_at=recent_time,
            finished_at=recent_time + timedelta(minutes=5),
            parameters={},
            records_fetched=1,
            records_created=1,
            records_updated=0,
            records_unchanged=0,
            records_rejected=0,
            error_count=0,
        )
        session.add(recent_run)
        session.commit()

    result = purge_expired_sync_runs(
        session_factory=get_session_factory(),
        retention_days=30,
    )
    assert result.sync_runs_deleted == 1
    assert result.sync_errors_deleted == 1

    with session_scope() as session:
        remaining = session.execute(select(DataSyncRun)).scalars().all()
        assert len(remaining) == 1
