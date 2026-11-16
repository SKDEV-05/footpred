"""Synchronisation and health response schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import UtcDatetime


class SyncRunOut(BaseModel):
    id: int
    job_type: str
    status: str
    started_at: UtcDatetime
    finished_at: UtcDatetime | None
    records_fetched: int
    records_created: int
    records_updated: int
    records_unchanged: int
    records_rejected: int
    error_count: int


class JobFreshness(BaseModel):
    job_type: str
    last_success_at: UtcDatetime | None
    last_completed_at: UtcDatetime | None
    last_completed_status: str | None
    records_stored: int | None


class SyncStatusOut(BaseModel):
    last_successful_sync_at: UtcDatetime | None
    last_run_at: UtcDatetime | None
    last_run_status: str | None
    stale_running_count: int
    per_job_type: list[JobFreshness]
    data_is_stale: bool


class HealthOut(BaseModel):
    status: str
    database: str
