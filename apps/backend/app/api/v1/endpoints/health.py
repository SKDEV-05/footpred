"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.exceptions import AppError
from app.database.session import check_database
from app.schemas.sync import HealthOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def readiness(
    session: Session = Depends(get_session),
) -> HealthOut:
    if not check_database(session):
        raise AppError(
            "The database is not reachable.",
            code="not_ready",
            http_status=503,
        )

    return HealthOut(
        status="ok",
        database="ok",
    )
