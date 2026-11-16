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

# Freshness only means something for match data. A successful competitions or teams
# run must never make fixture data look current.
REQUIRED_JOB_TYPES = ("fixtures", "results")


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
    completed = {
        job.job_type: job for job in sync_repo.last_completed_per_job_type(session)
    }
    success_at = dict(sync_repo.last_success_per_job_type(session))
    last_run = sync_repo.last_run_any_status(session)
    threshold = utc_now() - timedelta(minutes=settings.data_stale_after_minutes)
    stale_running = sync_repo.count_stale_running(
        session,
        older_than=utc_now()
        - timedelta(minutes=settings.sync_stale_run_after_minutes),
    )

    def is_fresh(job_type: str) -> bool:
        """Stored data counts as fresh when a recent run actually wrote records.

        A partial run qualifies: it stored the records it could and left the rest
        in the error tables. A run that fetched nothing, or stored nothing, does not
        qualify however it was classified.
        """

        job = completed.get(job_type)
        return (
            job is not None
            and job.records_stored > 0
            and job.finished_at >= threshold
        )

    stale = not all(is_fresh(job_type) for job_type in REQUIRED_JOB_TYPES)

    # ``last_successful_sync_at`` stays literal: only unqualified successes of the
    # required datasets count, so a partial run cannot be described as successful.
    required_successes = [
        finished_at
        for job_type, finished_at in success_at.items()
        if job_type in REQUIRED_JOB_TYPES and finished_at is not None
    ]
    last_success_at = max(required_successes) if required_successes else None

    job_types = sorted(set(completed) | set(success_at))
    per_job_type: list[JobFreshness] = []
    for job_type in job_types:
        job = completed.get(job_type)
        per_job_type.append(
            JobFreshness(
                job_type=job_type,
                last_success_at=success_at.get(job_type),
                last_completed_at=job.finished_at if job else None,
                last_completed_status=job.status.value if job else None,
                records_stored=job.records_stored if job else None,
            )
        )

    return SyncStatusOut(
        last_successful_sync_at=last_success_at,
        last_run_at=last_run.started_at if last_run else None,
        last_run_status=last_run.status.value if last_run else None,
        stale_running_count=stale_running,
        per_job_type=per_job_type,
        data_is_stale=stale,
    )
