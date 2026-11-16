"""FastAPI dependencies: database session, pagination, settings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import RecordValidationError, ValidationIssue
from app.database.session import get_db


@dataclass(frozen=True)
class Pagination:
    page: int
    page_size: int


def get_settings_dependency() -> Settings:
    return get_settings()


def get_session() -> Iterator[Session]:
    yield from get_db()


def pagination(
    page: int = Query(1, ge=1, le=10_000, description="1-based page number."),
    page_size: int | None = Query(
        None, ge=1, description="Items per page; capped by API_PAGE_SIZE_MAX."
    ),
    settings: Settings = Depends(get_settings_dependency),
) -> Pagination:
    resolved = page_size if page_size is not None else settings.api_page_size_default
    if resolved > settings.api_page_size_max:
        raise RecordValidationError(
            [
                ValidationIssue(
                    code="page_size_too_large",
                    message=(
                        f"page_size must not exceed {settings.api_page_size_max}"
                    ),
                    field="page_size",
                )
            ]
        )
    return Pagination(page=page, page_size=resolved)
