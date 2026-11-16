"""Synchronisation history read queries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.enums import SyncStatus
from app.models.provenance import DataSyncRun
from app.repositories.base import Page, count_of, fetch_page


@dataclass(frozen=True)
class CompletedJob:
    """The most recent finished run of one job type that did not fail outright."""

    job_type: str
    status: SyncStatus
    finished_at: datetime
    records_stored: int


def list_runs(
    session: Session,
    *,
    page: int,
    page_size: int,
    job_type: str | None = None,
    status: SyncStatus | None = None,
) -> Page[DataSyncRun]:
    statement = select(DataSyncRun)
    if job_type:
        statement = statement.where(DataSyncRun.job_type == job_type)
    if status is not None:
        statement = statement.where(DataSyncRun.status == status)
    statement = statement.order_by(desc(DataSyncRun.started_at), desc(DataSyncRun.id))
    return fetch_page(
        session,
        statement=statement,
        count_statement=count_of(statement),
        page=page,
        page_size=page_size,
    )


def last_finished_run(session: Session, *, status: SyncStatus) -> DataSyncRun | None:
    return session.execute(
        select(DataSyncRun)
        .where(DataSyncRun.status == status)
        .order_by(desc(DataSyncRun.finished_at))
        .limit(1)
    ).scalars().first()


def last_run_any_status(session: Session) -> DataSyncRun | None:
    return session.execute(
        select(DataSyncRun).order_by(desc(DataSyncRun.started_at)).limit(1)
    ).scalars().first()


def count_stale_running(session: Session, *, older_than: datetime) -> int:
    return int(
        session.execute(
            select(func.count(DataSyncRun.id)).where(
                DataSyncRun.status == SyncStatus.RUNNING,
                DataSyncRun.started_at < older_than,
            )
        ).scalar_one()
    )


def last_success_per_job_type(session: Session) -> list[tuple[str, datetime | None]]:
    rows = session.execute(
        select(DataSyncRun.job_type, func.max(DataSyncRun.finished_at))
        .where(DataSyncRun.status == SyncStatus.SUCCESS)
        .group_by(DataSyncRun.job_type)
    ).all()
    return [(row[0], row[1]) for row in rows]


def last_completed_per_job_type(session: Session) -> list[CompletedJob]:
    """Most recent finished run per job type, success or partial.

    A partial run still counts as work done: valid records were stored and only the
    remainder was quarantined or skipped. Freshness asks whether stored data was
    refreshed, so the caller decides from ``records_stored`` and the age of the run.
    Failed and still-running runs are excluded: they prove nothing about the data.
    """

    ranked = (
        select(
            DataSyncRun.job_type.label("job_type"),
            DataSyncRun.status.label("status"),
            DataSyncRun.finished_at.label("finished_at"),
            (
                DataSyncRun.records_created
                + DataSyncRun.records_updated
                + DataSyncRun.records_unchanged
            ).label("records_stored"),
            func.row_number()
            .over(
                partition_by=DataSyncRun.job_type,
                order_by=(desc(DataSyncRun.finished_at), desc(DataSyncRun.id)),
            )
            .label("position"),
        )
        .where(
            DataSyncRun.status.in_((SyncStatus.SUCCESS, SyncStatus.PARTIAL)),
            DataSyncRun.finished_at.is_not(None),
        )
        .subquery()
    )
    rows = session.execute(
        select(
            ranked.c.job_type,
            ranked.c.status,
            ranked.c.finished_at,
            ranked.c.records_stored,
        )
        .where(ranked.c.position == 1)
        .order_by(ranked.c.job_type)
    ).all()
    return [
        CompletedJob(
            job_type=row.job_type,
            status=SyncStatus(row.status),
            finished_at=row.finished_at,
            records_stored=int(row.records_stored),
        )
        for row in rows
    ]
