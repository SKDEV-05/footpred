"""Raw archive: evidence is written before parsing, addressed by content hash.

The archive is the audit trail that makes a prediction defensible. These tests check
that bytes, metadata, and sensitive-parameter filtering behave as designed.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.core.exceptions import ArchiveError
from app.core.time import utc_now
from app.database.session import session_scope
from app.ingestion.outcomes import ensure_data_provider
from app.ingestion.raw_archive import RawArchive
from app.models.provenance import RawPayload
from app.providers.dto import RawResponse


def _provider_id() -> int:
    with session_scope() as session:
        return ensure_data_provider(
            session, code="football_data_org", name="football-data.org"
        ).id


def _response(
    content: bytes = b'{"competitions": []}',
    *,
    params: dict[str, str] | None = None,
) -> RawResponse:
    return RawResponse(
        url="https://api.example.test/v4/competitions",
        path="/competitions",
        params=params or {"dateFrom": "2026-08-01"},
        status_code=200,
        headers={"content-type": "application/json"},
        content=content,
        fetched_at=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
    )


def test_payload_bytes_and_metadata_are_persisted(database):
    provider_id = _provider_id()
    archive = RawArchive(
        provider_code="football_data_org",
        provider_id=provider_id,
        storage_root=database.raw_dir,
    )
    content = b'{"competitions": []}'
    payload_id = archive.store(_response(content), resource_type="competitions")

    digest = hashlib.sha256(content).hexdigest()
    stored_path = database.raw_dir / "football_data_org" / digest[:2] / f"{digest}.json"
    assert stored_path.read_bytes() == content

    with session_scope() as session:
        row = session.get(RawPayload, payload_id)
        assert row is not None
        assert row.provider_id == provider_id
        assert row.resource_type == "competitions"
        assert row.request_path == "/competitions"
        assert row.http_status == 200
        assert row.content_sha256 == digest
        assert row.byte_size == len(content)
        assert row.content_type == "application/json"
        assert row.storage_path.endswith(f"{digest}.json")
        assert row.fetched_at == datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc)
        assert archive.read(
            storage_path=row.storage_path, content_sha256=row.content_sha256
        ) == content


def test_identical_content_reuses_the_file_but_records_each_observation(database):
    provider_id = _provider_id()
    archive = RawArchive(
        provider_code="football_data_org",
        provider_id=provider_id,
        storage_root=database.raw_dir,
    )
    first = archive.store(_response(), resource_type="competitions")
    second = archive.store(_response(), resource_type="competitions")

    assert first != second
    with session_scope() as session:
        assert len(list(session.execute(select(RawPayload)).scalars().all())) == 2

    files = list((database.raw_dir / "football_data_org").rglob("*.json"))
    assert len(files) == 1


def test_sensitive_request_parameters_are_not_archived(database):
    provider_id = _provider_id()
    archive = RawArchive(
        provider_code="football_data_org",
        provider_id=provider_id,
        storage_root=database.raw_dir,
    )
    payload_id = archive.store(
        _response(params={"token": "super-secret", "dateFrom": "2026-08-01"}),
        resource_type="competitions",
    )

    with session_scope() as session:
        row = session.get(RawPayload, payload_id)
        assert row is not None
        assert row.request_params == {"dateFrom": "2026-08-01"}
        assert "super-secret" not in str(row.request_params)


def test_unwritable_archive_root_raises_archive_error(database):
    provider_id = _provider_id()
    blocked = database.tmp_path / "blocked"
    blocked.write_text("not a directory")

    archive = RawArchive(
        provider_code="football_data_org",
        provider_id=provider_id,
        storage_root=blocked,
    )
    with pytest.raises(ArchiveError):
        archive.store(_response(), resource_type="competitions")


def test_different_content_gets_a_different_path(database):
    provider_id = _provider_id()
    archive = RawArchive(
        provider_code="football_data_org",
        provider_id=provider_id,
        storage_root=database.raw_dir,
    )
    archive.store(_response(b'{"a": 1}'), resource_type="matches")
    archive.store(_response(b'{"a": 2}'), resource_type="matches")

    files = list((database.raw_dir / "football_data_org").rglob("*.json"))
    assert len(files) == 2


def test_equal_size_archive_tampering_is_rejected(database):
    provider_id = _provider_id()
    archive = RawArchive(
        provider_code="football_data_org",
        provider_id=provider_id,
        storage_root=database.raw_dir,
    )
    content = b'{"a": 1}'
    archive.store(_response(content), resource_type="matches")
    digest = hashlib.sha256(content).hexdigest()
    path = database.raw_dir / "football_data_org" / digest[:2] / f"{digest}.json"
    path.write_bytes(b'{"b": 1}')
    with pytest.raises(ArchiveError, match="digest mismatch"):
        archive.store(_response(content), resource_type="matches")
    with pytest.raises(ArchiveError, match="digest mismatch"):
        archive.read(storage_path=str(path.relative_to(database.raw_dir)), content_sha256=digest)


def test_provider_code_is_path_safe(database):
    provider_id = _provider_id()
    with pytest.raises(ValueError):
        RawArchive(
            provider_code="../escape",
            provider_id=provider_id,
            storage_root=database.raw_dir,
        )


def test_failed_response_is_still_archived_with_its_http_status(database):
    provider_id = _provider_id()
    archive = RawArchive(
        provider_code="football_data_org",
        provider_id=provider_id,
        storage_root=database.raw_dir,
    )
    response = RawResponse(
        url="https://api.example.test/v4/competitions",
        path="/competitions",
        params={"dateFrom": "2026-08-01"},
        status_code=403,
        headers={"content-type": "application/json"},
        content=b'{"error":"forbidden"}',
        fetched_at=datetime(2026, 8, 1, 12, 0, tzinfo=timezone.utc),
    )
    payload_id = archive.store(response, resource_type="competitions")

    with session_scope() as session:
        row = session.get(RawPayload, payload_id)
        assert row is not None
        assert row.http_status == 403
        assert row.content_sha256 == hashlib.sha256(b'{"error":"forbidden"}').hexdigest()
        assert row.byte_size == len(b'{"error":"forbidden"}')
