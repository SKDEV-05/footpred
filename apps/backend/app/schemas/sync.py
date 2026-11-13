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
    error_summary: str | None


class JobFreshness(BaseModel):
    job_type: str
    last_success_at: UtcDatetime | None


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
    provider_configured: bool
    last_successful_sync_at: UtcDatetime | None
    data_is_stale: bool
