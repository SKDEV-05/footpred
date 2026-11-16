"""Archive and sync-run retention with safe deletion.

Retention is opt-in: a retention period of 0 days means keep everything. When a
positive period is configured, payloads or runs older than the cutoff become
eligible for cleanup. Deletion is always:

- **Integrity-verified**: a raw payload file is re-hashed before removal; if the
  digest no longer matches the stored SHA-256, the file is left in place and the
  mismatch is reported, not silently corrected.
- **Path-safe**: the archive root and provider-code allowlist already prevent
  traversal; deletion additionally refuses to remove files outside the root.
- **Auditable**: every cleanup run records how many rows and bytes were removed,
  plus any integrity failures, and returns a structured result.
- **Non-destructive by default**: the operator must set a positive retention
  period in configuration before any deletion occurs.

This module does I/O (filesystem + database) and belongs to the Phase 3 data
layer. It never touches the intelligence package.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.time import utc_now
from app.models.provenance import (
    DataSyncError,
    DataSyncRun,
    MatchChangeLog,
    QuarantinedRecord,
    RawPayload,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetentionResult:
    """Structured outcome of one retention cleanup pass."""

    raw_payloads_deleted: int = 0
    raw_bytes_freed: int = 0
    integrity_failures: list[str] = field(default_factory=list)
    sync_runs_deleted: int = 0
    sync_errors_deleted: int = 0
    quarantine_deleted: int = 0
    change_log_deleted: int = 0


def purge_expired_raw_payloads(
    *,
    storage_root: Path,
    session_factory: sessionmaker[Session],
    retention_days: int,
) -> RetentionResult:
    """Delete raw payload files and rows older than ``retention_days``.

    Returns a :class:`RetentionResult` with counts and any integrity failures.
    A ``retention_days`` of 0 or negative is a no-op (keep everything).
    """

    if retention_days <= 0:
        return RetentionResult()

    cutoff = utc_now() - timedelta(days=retention_days)
    root = Path(storage_root).resolve()
    deleted_rows = 0
    freed_bytes = 0
    failures: list[str] = []

    with session_factory() as session:
        candidates = (
            session.execute(
                select(RawPayload).where(RawPayload.fetched_at < cutoff)
            )
            .scalars()
            .all()
        )
        for row in candidates:
            file_path = (root / row.storage_path).resolve()
            if root not in file_path.parents:
                failures.append(
                    f"payload {row.id}: storage_path escapes archive root"
                )
                continue
            if not file_path.exists():
                # File already gone; remove the orphan row.
                session.delete(row)
                deleted_rows += 1
                continue
            try:
                content = file_path.read_bytes()
            except OSError:
                failures.append(f"payload {row.id}: could not read file")
                continue
            actual_digest = hashlib.sha256(content).hexdigest()
            if actual_digest != row.content_sha256:
                failures.append(
                    f"payload {row.id}: digest mismatch, kept file"
                )
                continue
            try:
                file_path.unlink()
            except OSError:
                failures.append(f"payload {row.id}: could not delete file")
                continue
            freed_bytes += row.byte_size
            session.delete(row)
            deleted_rows += 1
        session.commit()

    logger.info(
        "raw payload retention pass complete",
        extra={
            "event": "retention.raw_payloads",
            "component": "ingestion",
            "deleted": deleted_rows,
            "bytes_freed": freed_bytes,
            "failures": len(failures),
        },
    )
    return RetentionResult(
        raw_payloads_deleted=deleted_rows,
        raw_bytes_freed=freed_bytes,
        integrity_failures=failures,
    )


def purge_expired_sync_runs(
    *,
    session_factory: sessionmaker[Session],
    retention_days: int,
) -> RetentionResult:
    """Delete sync runs and their dependent records older than ``retention_days``.

    Dependent records (errors, quarantine, change-log) are deleted first, then
    the run row. A ``retention_days`` of 0 or negative is a no-op.
    """

    if retention_days <= 0:
        return RetentionResult()

    cutoff = utc_now() - timedelta(days=retention_days)
    runs_deleted = 0
    errors_deleted = 0
    quarantine_deleted = 0
    change_log_deleted = 0

    with session_factory() as session:
        old_runs = (
            session.execute(
                select(DataSyncRun.id).where(
                    DataSyncRun.finished_at.is_not(None),
                    DataSyncRun.finished_at < cutoff,
                )
            )
            .scalars()
            .all()
        )
        for run_id in old_runs:
            errors_deleted += session.execute(
                delete(DataSyncError).where(DataSyncError.sync_run_id == run_id)
            ).rowcount
            quarantine_deleted += session.execute(
                delete(QuarantinedRecord).where(
                    QuarantinedRecord.sync_run_id == run_id
                )
            ).rowcount
            change_log_deleted += session.execute(
                delete(MatchChangeLog).where(
                    MatchChangeLog.sync_run_id == run_id
                )
            ).rowcount
            session.execute(
                delete(DataSyncRun).where(DataSyncRun.id == run_id)
            )
            runs_deleted += 1
        session.commit()

    logger.info(
        "sync run retention pass complete",
        extra={
            "event": "retention.sync_runs",
            "component": "ingestion",
            "runs_deleted": runs_deleted,
            "errors_deleted": errors_deleted,
            "quarantine_deleted": quarantine_deleted,
            "change_log_deleted": change_log_deleted,
        },
    )
    return RetentionResult(
        sync_runs_deleted=runs_deleted,
        sync_errors_deleted=errors_deleted,
        quarantine_deleted=quarantine_deleted,
        change_log_deleted=change_log_deleted,
    )
