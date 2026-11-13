"""Synchronisation observability endpoints (read-only)."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_session, get_settings_dependency, pagination
from app.api.v1.mappers import sync_run_out
from app.core.config import Settings
from app.core.time import utc_now
from app.models.enums import SyncStatus
from app.repositories import sync as sync_repo
from app.schemas.common import Page
from app.schemas.sync import JobFreshness, SyncRunOut, SyncStatusOut

router = APIRouter(tags=["synchronisation"])


@router.get("/sync/runs", response_model=Page[SyncRunOut])
def list_sync_runs(
    job_type: str | None = None,
    status: SyncStatus | None = None,
    page: Pagination = Depends(pagination),
    session: Session = Depends(get_session),
) -> Page[SyncRunOut]:
    result = sync_repo.list_runs(
        session,
        page=page.page,
        page_size=page.page_size,
        job_type=job_type,
        status=status,
    )
    return Page[SyncRunOut](
        items=[sync_run_out(run) for run in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )


@router.get("/sync/status", response_model=SyncStatusOut)
def sync_status(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_dependency),
) -> SyncStatusOut:
    last_success = sync_repo.last_finished_run(session, status=SyncStatus.SUCCESS)
    last_run = sync_repo.last_run_any_status(session)
    threshold = utc_now() - timedelta(minutes=settings.data_stale_after_minutes)
    stale_running = sync_repo.count_stale_running(
        session,
        older_than=utc_now()
        - timedelta(minutes=settings.sync_stale_run_after_minutes),
    )

    stale = last_success is None or last_success.finished_at is None or (
        last_success.finished_at < threshold
    )

    return SyncStatusOut(
        last_successful_sync_at=last_success.finished_at if last_success else None,
        last_run_at=last_run.started_at if last_run else None,
        last_run_status=last_run.status.value if last_run else None,
        stale_running_count=stale_running,
        per_job_type=[
            JobFreshness(job_type=job_type, last_success_at=finished_at)
            for job_type, finished_at in sync_repo.last_success_per_job_type(session)
        ],
        data_is_stale=stale,
    )
