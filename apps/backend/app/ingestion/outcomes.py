"""Shared ingestion outcomes and change-tracking helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum
from typing import Any, Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.provenance import DataProvider


class UpsertOutcome(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class UpsertResult:
    entity_id: int
    outcome: UpsertOutcome
    changed_fields: tuple[str, ...] = ()

    @property
    def created(self) -> bool:
        return self.outcome is UpsertOutcome.CREATED

    @property
    def updated(self) -> bool:
        return self.outcome is UpsertOutcome.UPDATED

    @property
    def unchanged(self) -> bool:
        return self.outcome is UpsertOutcome.UNCHANGED


@dataclass
class IngestionCounts:
    fetched: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0

    def record(self, result: UpsertResult) -> None:
        if result.outcome is UpsertOutcome.CREATED:
            self.created += 1
        elif result.outcome is UpsertOutcome.UPDATED:
            self.updated += 1
        else:
            self.unchanged += 1

    def merge(self, other: "IngestionCounts") -> None:
        self.fetched += other.fetched
        self.created += other.created
        self.updated += other.updated
        self.unchanged += other.unchanged
        self.rejected += other.rejected


@dataclass
class FieldChange:
    previous: dict[str, Any] = field(default_factory=dict)
    new: dict[str, Any] = field(default_factory=dict)

    @property
    def changed_fields(self) -> tuple[str, ...]:
        return tuple(self.new)

    @property
    def has_changes(self) -> bool:
        return bool(self.new)


def jsonable(value: Any) -> Any:
    """Convert values for JSON columns deterministically."""

    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, StrEnum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [jsonable(item) for item in value]
    return value


def diff_fields(
    current: Mapping[str, Any], incoming: Mapping[str, Any]
) -> FieldChange:
    """Return only the fields whose values actually change.

    ``None`` means "not supplied" for every optional provider field, so a ``None``
    incoming value never erases a stored value. This is essential for slow-updating
    feeds: absence is not a correction.
    """

    change = FieldChange()
    for key, new_value in incoming.items():
        if new_value is None:
            continue
        old_value = current.get(key)
        if old_value != new_value:
            change.previous[key] = jsonable(old_value)
            change.new[key] = jsonable(new_value)
    return change


def ensure_data_provider(
    session: Session,
    *,
    code: str,
    name: str,
    base_url: str | None = None,
) -> DataProvider:
    """Return the provider row, creating it once per database."""

    provider = session.execute(
        select(DataProvider).where(DataProvider.code == code)
    ).scalars().first()
    if provider is None:
        provider = DataProvider(code=code, name=name, base_url=base_url)
        session.add(provider)
        session.flush()
    else:
        if base_url and provider.base_url != base_url:
            provider.base_url = base_url
    return provider
