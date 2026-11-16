"""UTC-first time helpers.

The database stores UTC. SQLite cannot preserve tzinfo, so a custom SQLAlchemy type
attaches UTC on read and rejects naive datetimes on write. Local calendar windows are
computed only at the API edge from an explicit IANA timezone.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.exceptions import RecordValidationError, ValidationIssue


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def ensure_utc(value: datetime, *, field: str = "datetime") -> datetime:
    """Return an aware UTC datetime, rejecting naive input."""

    if value.tzinfo is None or value.utcoffset() is None:
        raise RecordValidationError(
            [
                ValidationIssue(
                    code="naive_datetime",
                    message=f"{field} must include a timezone offset",
                    field=field,
                )
            ]
        )
    return value.astimezone(timezone.utc)


def start_of_utc_day(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def end_of_utc_day_exclusive(value: date) -> datetime:
    return start_of_utc_day(value) + timedelta(days=1)


def get_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise RecordValidationError(
            [
                ValidationIssue(
                    code="invalid_timezone",
                    message="Unknown IANA timezone.",
                    field="timezone",
                )
            ]
        ) from exc


def local_day_window_utc(day: date, timezone_name: str) -> tuple[datetime, datetime]:
    """Return the UTC half-open window covering a local calendar day."""

    zone = get_timezone(timezone_name)
    local_start = datetime.combine(day, time.min, tzinfo=zone)
    local_end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone)
    return (
        local_start.astimezone(timezone.utc),
        local_end.astimezone(timezone.utc),
    )
