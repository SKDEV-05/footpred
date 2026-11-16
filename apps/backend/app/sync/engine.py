"""Synchronisation run lifecycle.

A run is created before any provider work and finalised afterwards. Per-item work is
committed item by item, so one bad record cannot discard a whole batch and a rejected
record is always visible in ``quarantined_records`` plus ``data_sync_errors``.

Counts live in the database, not only in memory: a crashed process leaves an accurate
partial record, and the next startup marks the abandoned run failed.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable, Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.exceptions import AppError, RecordValidationError
from app.core.logging import redact_text, sync_run_id_var
from app.core.time import utc_now
from app.database.session import get_session_factory, session_scope
from app.ingestion.outcomes import IngestionCounts, UpsertResult, jsonable
from app.ingestion.statistics import StatisticsUpsert
from app.models.enums import SyncStatus
from app.models.provenance import (
    DataSyncError,
    DataSyncRun,
    QuarantinedRecord,
    RawPayload,
)

logger = logging.getLogger(__name__)

_MAX_MESSAGE = 2000
_MAX_SUMMARY = 2000


@dataclass(frozen=True)
class SyncRunSummary:
    run_id: int
    job_type: str
    status: SyncStatus
    counts: IngestionCounts
    error_count: int
    started_at: Any
    finished_at: Any
    failure: str | None = None


class SyncContext:
    """Per-run handle used by job functions.

    Every mutation opens one short transaction. Nothing here holds a transaction open
    across provider I/O.
    """

    def __init__(
        self,
        *,
        engine: "SyncEngine",
        run_id: int,
        provider_id: int | None,
        adapter: Any,
        settings: Settings,
        parameters: dict[str, Any],
        session_factory: sessionmaker[Session] | Callable[[], Session],
    ) -> None:
        self.engine = engine
        self.run_id = run_id
        self.provider_id = provider_id
        self.adapter = adapter
        self.settings = settings
        self.parameters = parameters
        self._session_factory = session_factory
        self.raw_payload_ids: set[int] = set()

    def observe_raw_payload(self, payload_id: int | None) -> None:
        if payload_id is not None:
            self.raw_payload_ids.add(payload_id)

    @contextmanager
    def session(self) -> Iterator[Session]:
        token = sync_run_id_var.set(self.run_id)
        try:
            session = self._session_factory()
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
            finally:
                session.close()
        finally:
            sync_run_id_var.reset(token)

    # -- counting ---------------------------------------------------------------

    def count(self, session: Session, result: UpsertResult | StatisticsUpsert) -> None:
        run = self._run(session)
        if isinstance(result, StatisticsUpsert):
            run.records_fetched += 1
            run.records_created += result.created
            run.records_updated += result.updated
            run.records_unchanged += result.unchanged
            return
        run.records_fetched += 1
        if result.created:
            run.records_created += 1
        elif result.updated:
            run.records_updated += 1
        else:
            run.records_unchanged += 1

    def count_many(self, session: Session, results: list[UpsertResult]) -> None:
        for result in results:
            self.count(session, result)

    def count_rejected(self, session: Session) -> None:
        run = self._run(session)
        run.records_fetched += 1
        run.records_rejected += 1
        run.error_count += 1

    # -- failure recording ------------------------------------------------------

    def reject(
        self,
        session: Session,
        *,
        entity_type: str,
        external_id: str | None,
        code: str,
        message: str,
        raw_payload_id: int | None = None,
        payload_excerpt: Any = None,
    ) -> None:
        """Record a rejected record in the transaction of the caller."""

        self.count_rejected(session)
        safe_message = _bounded(redact_text(message))
        if self.provider_id is None:
            raise AppError("Cannot quarantine a record without a provider.")
        if raw_payload_id is not None and session.get(RawPayload, raw_payload_id) is None:
            raw_payload_id = None
        session.add(
            QuarantinedRecord(
                provider_id=self.provider_id,
                sync_run_id=self.run_id,
                raw_payload_id=raw_payload_id,
                entity_type=entity_type[:64],
                external_id=(external_id or None),
                reason_code=code[:64],
                reason_message=safe_message,
                payload_excerpt=jsonable(payload_excerpt) if payload_excerpt else None,
                created_at=utc_now(),
            )
        )
        self._add_error(
            session,
            stage="ingestion",
            code=code,
            message=safe_message,
            entity_type=entity_type,
            external_id=external_id,
            raw_payload_id=raw_payload_id,
        )

    def record_error(
        self,
        session: Session,
        *,
        stage: str,
        code: str,
        message: str,
        entity_type: str | None = None,
        external_id: str | None = None,
        raw_payload_id: int | None = None,
        increments_rejected: bool = False,
    ) -> None:
        run = self._run(session)
        run.error_count += 1
        if increments_rejected:
            run.records_rejected += 1
        self._add_error(
            session,
            stage=stage,
            code=code,
            message=_safe_record_message(code),
            entity_type=entity_type,
            external_id=external_id,
            raw_payload_id=raw_payload_id,
        )

    def _add_error(
        self,
        session: Session,
        *,
        stage: str,
        code: str,
        message: str,
        entity_type: str | None,
        external_id: str | None,
        raw_payload_id: int | None,
    ) -> None:
        session.add(
            DataSyncError(
                sync_run_id=self.run_id,
                stage=stage[:64],
                code=code[:64],
                message=_bounded(message),
                entity_type=entity_type[:64] if entity_type else None,
                external_id=external_id[:128] if external_id else None,
                raw_payload_id=raw_payload_id,
                created_at=utc_now(),
            )
        )

    def _run(self, session: Session) -> DataSyncRun:
        run = session.get(DataSyncRun, self.run_id)
        if run is None:
            raise AppError(f"sync run {self.run_id} disappeared during execution")
        return run


class SyncEngine:
    """Creates, executes, and finalises one bounded synchronisation job."""

    def __init__(
        self,
        *,
        settings: Settings,
        session_factory: sessionmaker[Session] | Callable[[], Session] | None = None,
        provider_id: int | None = None,
        adapter: Any = None,
    ) -> None:
        self._settings = settings
        self._session_factory = session_factory or get_session_factory()
        self._provider_id = provider_id
        self._adapter = adapter

    def run(
        self,
        *,
        job_type: str,
        handler: Callable[[SyncContext], None],
        parameters: dict[str, Any] | None = None,
    ) -> SyncRunSummary:
        started_at = utc_now()
        effective_parameters = self._effective_parameters(job_type, parameters, started_at)
        run_id = self._start_run(job_type, effective_parameters, started_at)
        token = sync_run_id_var.set(run_id)
        context = SyncContext(
            engine=self,
            run_id=run_id,
            provider_id=self._provider_id,
            adapter=self._adapter,
            settings=self._settings,
            parameters=effective_parameters,
            session_factory=self._session_factory,
        )
        failure: str | None = None
        try:
            logger.info(
                "sync run started",
                extra={"event": "sync.started", "component": "sync", "job_type": job_type},
            )
            handler(context)
        except Exception as exc:  # noqa: BLE001 - every failure must be recorded
            failure = _safe_failure_summary(exc)
            logger.exception(
                "sync run failed",
                extra={
                    "event": "sync.failed",
                    "component": "sync",
                    "job_type": job_type,
                    "error_code": exc.code if isinstance(exc, AppError) else type(exc).__name__,
                },
            )
            self._record_job_failure(run_id, exc)
        finally:
            sync_run_id_var.reset(token)

        summary = self._finalise(
            run_id,
            job_type=job_type,
            failure=failure,
            raw_payload_ids=context.raw_payload_ids,
        )
        logger.info(
            "sync run finished",
            extra={
                "event": "sync.finished",
                "component": "sync",
                "job_type": job_type,
                "records_fetched": summary.counts.fetched,
                "records_created": summary.counts.created,
                "records_updated": summary.counts.updated,
                "records_rejected": summary.counts.rejected,
            },
        )
        return summary

    # -- internals --------------------------------------------------------------

    def _effective_parameters(
        self,
        job_type: str,
        parameters: dict[str, Any] | None,
        started_at,
    ) -> dict[str, Any]:
        effective = dict(parameters or {})
        effective["run_started_at"] = started_at.isoformat()
        effective["competition_ids"] = list(self._settings.competition_ids)
        effective["sync_lookback_days"] = self._settings.sync_lookback_days
        effective["sync_lookahead_days"] = self._settings.sync_lookahead_days
        effective["statistics_limit"] = self._settings.sync_statistics_limit_per_run
        run_date = started_at.date()
        if job_type == "fixtures":
            effective["date_from"] = (run_date - timedelta(days=self._settings.sync_lookback_days)).isoformat()
            effective["date_to"] = (run_date + timedelta(days=self._settings.sync_lookahead_days)).isoformat()
        elif job_type == "results":
            effective["date_from"] = (run_date - timedelta(days=self._settings.sync_lookback_days)).isoformat()
            effective["date_to"] = run_date.isoformat()
        return effective

    def _start_run(self, job_type: str, parameters: dict[str, Any], started_at) -> int:
        with self._session_factory() as session:
            run = DataSyncRun(
                provider_id=self._provider_id,
                job_type=job_type[:64],
                status=SyncStatus.RUNNING,
                started_at=started_at,
                parameters=jsonable(parameters),
                records_fetched=0,
                records_created=0,
                records_updated=0,
                records_unchanged=0,
                records_rejected=0,
                error_count=0,
            )
            session.add(run)
            session.commit()
            return run.id

    def _record_job_failure(self, run_id: int, exc: Exception) -> None:
        code = exc.code if isinstance(exc, AppError) else "unexpected_error"
        message = _bounded(_safe_failure_summary(exc))
        try:
            with self._session_factory() as session:
                run = session.get(DataSyncRun, run_id)
                if run is None:
                    return
                run.error_count += 1
                session.add(
                    DataSyncError(
                        sync_run_id=run_id,
                        stage="job",
                        code=code[:64],
                        message=message,
                        created_at=utc_now(),
                    )
                )
                session.commit()
        except Exception:  # noqa: BLE001 - failure recording must not mask the cause
            logger.exception(
                "could not record a sync job failure",
                extra={"event": "sync.failure_not_recorded", "component": "sync"},
            )

    def _finalise(
        self,
        run_id: int,
        *,
        job_type: str,
        failure: str | None,
        raw_payload_ids: set[int] | None = None,
    ) -> SyncRunSummary:
        with self._session_factory() as session:
            run = session.get(DataSyncRun, run_id)
            if run is None:
                raise AppError(f"sync run {run_id} disappeared before finalisation")

            if failure is not None:
                status = SyncStatus.FAILED
            elif run.records_rejected > 0 or run.error_count > 0:
                status = SyncStatus.PARTIAL
            else:
                status = SyncStatus.SUCCESS

            run.status = status
            run.finished_at = utc_now()
            parameters = dict(run.parameters or {})
            parameters["raw_payload_ids"] = sorted(raw_payload_ids or set())
            run.parameters = parameters
            run.error_summary = (
                _bounded(redact_text(failure)) if failure else _summary_for(run)
            )
            session.commit()

            return SyncRunSummary(
                run_id=run.id,
                job_type=job_type,
                status=status,
                counts=IngestionCounts(
                    fetched=run.records_fetched,
                    created=run.records_created,
                    updated=run.records_updated,
                    unchanged=run.records_unchanged,
                    rejected=run.records_rejected,
                ),
                error_count=run.error_count,
                started_at=run.started_at,
                finished_at=run.finished_at,
                failure=failure,
            )


def mark_stale_running_runs(
    *,
    settings: Settings,
    session_factory: sessionmaker[Session] | Callable[[], Session] | None = None,
) -> int:
    """Mark runs abandoned by a crashed worker as failed, with a visible reason."""

    factory = session_factory or get_session_factory()
    threshold = utc_now() - timedelta(minutes=settings.sync_stale_run_after_minutes)
    with factory() as session:
        stale = session.execute(
            select(DataSyncRun).where(
                DataSyncRun.status == SyncStatus.RUNNING,
                DataSyncRun.started_at < threshold,
            )
        ).scalars().all()
        for run in stale:
            run.status = SyncStatus.FAILED
            run.finished_at = utc_now()
            run.error_count += 1
            run.error_summary = (
                "Marked failed: the run did not finish before the worker restarted."
            )
            session.add(
                DataSyncError(
                    sync_run_id=run.id,
                    stage="startup",
                    code="stale_run",
                    message=(
                        "Run was still marked running when the worker started; "
                        "treated as abandoned."
                    ),
                    created_at=utc_now(),
                )
            )
        session.commit()
        return len(stale)


def _safe_failure_summary(exc: Exception) -> str:
    if isinstance(exc, RecordValidationError):
        return f"{exc.code}: validation failed"
    if isinstance(exc, AppError):
        return f"{exc.code}: operation failed"
    return "unexpected_error: operation failed"


def _safe_record_message(code: str) -> str:
    return f"{code}: operation recorded"


def _summary_for(run: DataSyncRun) -> str | None:
    if run.records_rejected == 0 and run.error_count == 0:
        return None
    return (
        f"{run.records_rejected} record(s) rejected, "
        f"{run.error_count} error(s); see data_sync_errors."
    )


def _bounded(message: str) -> str:
    return message if len(message) <= _MAX_MESSAGE else message[: _MAX_MESSAGE - 12] + "…[truncated]"


def _max_summary() -> int:  # pragma: no cover - documentation helper
    return _MAX_SUMMARY
