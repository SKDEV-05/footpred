"""Synchronisation history read queries."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.models.enums import SyncStatus
from app.models.provenance import DataSyncRun
from app.repositories.base import Page, count_of, fetch_page


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
