"""Pagination primitives shared by read repositories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

T = TypeVar("T")


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
