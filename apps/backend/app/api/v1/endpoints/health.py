"""Health and readiness endpoints."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_session, get_settings_dependency
from app.core.config import Settings
from app.core.exceptions import AppError
from app.core.time import utc_now
from app.database.session import check_database
from app.models.enums import SyncStatus
from app.repositories.sync import last_finished_run
from app.schemas.sync import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def readiness(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings_dependency),
) -> HealthOut:
    if not check_database(session):
        raise AppError(
            "The database is not reachable.",
            code="not_ready",
            http_status=503,
        )

    last_success = last_finished_run(session, status=SyncStatus.SUCCESS)
    threshold = utc_now() - timedelta(minutes=settings.data_stale_after_minutes)
    stale = last_success is None or last_success.finished_at is None or (
        last_success.finished_at < threshold
    )

    return HealthOut(
        status="ok",
        database="ok",
        provider_configured=settings.provider_configured,
        last_successful_sync_at=last_success.finished_at if last_success else None,
        data_is_stale=stale,
    )
