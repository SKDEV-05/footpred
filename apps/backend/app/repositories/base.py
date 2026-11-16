"""Pagination primitives shared by read repositories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.exceptions import RecordValidationError, ValidationIssue
from app.normalization.names import normalize_name

T = TypeVar("T")


def search_term(query: str) -> str:
    """Normalise a user search string into the comparison key stored on rows.

    Invalid or unsearchable input becomes a structured 422 rather than an empty result,
    so a typo is never indistinguishable from "no matches exist".
    """

    try:
        normalized = normalize_name(query)
    except ValueError as exc:
        raise RecordValidationError(
            [
                ValidationIssue(
                    code="invalid_search",
                    message="search query contains invalid characters",
                    field="q",
                )
            ]
        ) from exc
    if not normalized:
        raise RecordValidationError(
            [
                ValidationIssue(
                    code="empty_search",
                    message="search query has no searchable characters",
                    field="q",
                )
            ]
        )
    return normalized


@dataclass(frozen=True)
class Page(Generic[T]):
    items: Sequence[T]
    page: int
    page_size: int
    total: int

    @property
    def has_next(self) -> bool:
        return self.page * self.page_size < self.total


def fetch_page(
    session: Session,
    *,
    statement: Select,
    count_statement: Select,
    page: int,
    page_size: int,
) -> Page:
    total = int(session.execute(count_statement).scalar_one())
    items = (
        session.execute(
            statement.offset((page - 1) * page_size).limit(page_size)
        )
        .scalars()
        .all()
    )
    return Page(items=list(items), page=page, page_size=page_size, total=total)


def count_of(statement: Select) -> Select:
    """Turn an entity select into a ``count(*)`` select over the same filters."""

    return select(func.count()).select_from(statement.order_by(None).subquery())
