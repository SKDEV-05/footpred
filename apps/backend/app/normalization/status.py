"""Provider enum translation and deterministic value normalisation.

Every translation is an explicit lookup. An unknown provider value raises
``UnknownProviderValueError`` so the record is quarantined; it is never mapped to a
convenient default such as ``scheduled`` or ``regular``.
"""

from __future__ import annotations

import re
from datetime import date

from app.core.exceptions import RecordValidationError, ValidationIssue
from app.models.enums import CompetitionType, MatchDuration, MatchStatus, MatchWinner

_COMPETITION_TYPE = {
    "LEAGUE": CompetitionType.LEAGUE,
    "LEAGUE_CUP": CompetitionType.LEAGUE_CUP,
    "CUP": CompetitionType.CUP,
    "PLAYOFFS": CompetitionType.PLAYOFFS,
}

_MATCH_STATUS = {
    "SCHEDULED": MatchStatus.SCHEDULED,
    "TIMED": MatchStatus.TIMED,
    "IN_PLAY": MatchStatus.IN_PLAY,
    "PAUSED": MatchStatus.PAUSED,
    "EXTRA_TIME": MatchStatus.EXTRA_TIME,
    "PENALTY_SHOOTOUT": MatchStatus.PENALTY_SHOOTOUT,
    "FINISHED": MatchStatus.FINISHED,
    "SUSPENDED": MatchStatus.SUSPENDED,
    "POSTPONED": MatchStatus.POSTPONED,
    "CANCELLED": MatchStatus.CANCELLED,
    "AWARDED": MatchStatus.AWARDED,
    "ABANDONED": MatchStatus.ABANDONED,
}

_MATCH_WINNER = {
    "HOME_TEAM": MatchWinner.HOME_TEAM,
    "AWAY_TEAM": MatchWinner.AWAY_TEAM,
    "DRAW": MatchWinner.DRAW,
}

_MATCH_DURATION = {
    "REGULAR": MatchDuration.REGULAR,
    "EXTRA_TIME": MatchDuration.EXTRA_TIME,
    "PENALTY_SHOOTOUT": MatchDuration.PENALTY_SHOOTOUT,
}

_NON_WORD = re.compile(r"[^a-z0-9]+")


class UnknownProviderValueError(RecordValidationError):
    """A provider value outside the documented enum."""

    def __init__(self, field: str, value: object, allowed: tuple[str, ...]) -> None:
        super().__init__(
            [
                ValidationIssue(
                    code="unknown_provider_value",
                    message=(
                        f"Unrecognised {field} value {value!r}; "
                        f"expected one of {', '.join(allowed)}"
                    ),
                    field=field,
                )
            ]
        )


def _lookup(mapping: dict[str, object], value: object, field: str):
    if not isinstance(value, str) or not value.strip():
        raise RecordValidationError(
            [
                ValidationIssue(
                    code="missing_provider_value",
                    message=f"{field} is required",
                    field=field,
                )
            ]
        )
    key = value.strip().upper()
    if key not in mapping:
        raise UnknownProviderValueError(field, value, tuple(mapping))
    return mapping[key]


def competition_type(value: object) -> CompetitionType:
    return _lookup(_COMPETITION_TYPE, value, "competition.type")  # type: ignore[return-value]


def match_status(value: object) -> MatchStatus:
    return _lookup(_MATCH_STATUS, value, "match.status")  # type: ignore[return-value]


def match_winner(value: object) -> MatchWinner | None:
    if value is None:
        return None
    return _lookup(_MATCH_WINNER, value, "match.winner")  # type: ignore[return-value]


def match_duration(value: object) -> MatchDuration | None:
    if value is None:
        return None
    return _lookup(_MATCH_DURATION, value, "match.duration")  # type: ignore[return-value]


def snake_case(value: str, *, max_length: int = 64) -> str:
    """Convert a provider metric key to a stable snake_case identifier.

    Examples: ``Ball Possession`` → ``ball_possession``, ``ShotsonGoal`` →
    ``shotson_goal`` is avoided by inserting a boundary only where the provider used a
    separator. The mapping is deterministic, not a semantic guess.
    """

    if not isinstance(value, str) or not value.strip():
        raise ValueError("metric key must be a non-empty string")
    lowered = value.strip().casefold()
    slug = _NON_WORD.sub("_", lowered).strip("_")
    if not slug:
        raise ValueError(f"metric key {value!r} normalises to an empty identifier")
    if slug[0].isdigit():
        slug = f"m_{slug}"
    if len(slug) > max_length:
        raise ValueError(f"metric key {value!r} exceeds {max_length} characters")
    return slug


def stage_name(value: str | None) -> str | None:
    if value is None:
        return None
    return snake_case(value, max_length=48)


def group_name(value: str | None) -> str | None:
    if value is None:
        return None
    slug = snake_case(value, max_length=16)
    return slug


def season_label(start_date: date, end_date: date) -> str:
    """Derive a season label deterministically from its dates.

    A season that starts and ends in the same calendar year is labelled with that year.
    A cross-year season is labelled ``start/end``. No heuristics about which month a
    season begins are applied, because competitions differ.
    """

    if end_date < start_date:
        raise ValueError("season end date precedes start date")
    if start_date.year == end_date.year:
        return str(start_date.year)
    return f"{start_date.year}/{end_date.year}"
