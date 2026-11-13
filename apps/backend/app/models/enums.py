"""Canonical enumerations and the portable enum column factory.

Values are lowercase snake case in the database. Provider values are translated in the
adapter/normalisation layer; an unknown provider value is a validation failure, never a
default.
"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Enum as SAEnum


class CompetitionType(StrEnum):
    LEAGUE = "league"
    LEAGUE_CUP = "league_cup"
    CUP = "cup"
    PLAYOFFS = "playoffs"


class MatchStatus(StrEnum):
    SCHEDULED = "scheduled"
    TIMED = "timed"
    IN_PLAY = "in_play"
    PAUSED = "paused"
    EXTRA_TIME = "extra_time"
    PENALTY_SHOOTOUT = "penalty_shootout"
    FINISHED = "finished"
    SUSPENDED = "suspended"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    AWARDED = "awarded"


FINAL_STATUSES = frozenset({MatchStatus.FINISHED, MatchStatus.AWARDED})


class MatchWinner(StrEnum):
    HOME_TEAM = "home_team"
    AWAY_TEAM = "away_team"
    DRAW = "draw"


class MatchDuration(StrEnum):
    REGULAR = "regular"
    EXTRA_TIME = "extra_time"
    PENALTY_SHOOTOUT = "penalty_shootout"


class SyncStatus(StrEnum):
    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


def enum_column(enum_cls: type[StrEnum], *, name: str, length: int = 32) -> SAEnum:
    """A portable VARCHAR + CHECK enum column (no native database enum)."""

    return SAEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length,
        values_callable=lambda members: [member.value for member in members],
        validate_strings=True,
    )
