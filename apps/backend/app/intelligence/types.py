"""Validated, immutable inputs for point-in-time offline analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from math import isfinite
from types import MappingProxyType
from typing import Mapping


class Venue(StrEnum):
    HOME = "home"
    AWAY = "away"
    NEUTRAL = "neutral"
    OVERALL = "overall"


class DataClassification(StrEnum):
    SYNTHETIC_TEST = "synthetic_test_data"


@dataclass(frozen=True)
class ResearchContext:
    classification: DataClassification
    dataset_digest: str
    protocol_version: str

    def __post_init__(self) -> None:
        if not isinstance(self.classification, DataClassification):
            raise ValueError("classification must be a DataClassification")
        if self.classification is not DataClassification.SYNTHETIC_TEST:
            raise ValueError("only synthetic test data is permitted in Phase 4")
        if len(self.dataset_digest) != 64 or any(
            character not in "0123456789abcdef" for character in self.dataset_digest
        ):
            raise ValueError("dataset_digest must be a lowercase SHA-256 hex digest")
        if not self.protocol_version:
            raise ValueError("protocol_version must not be empty")


def require_context(context: ResearchContext) -> None:
    if not isinstance(context, ResearchContext):
        raise ValueError("a validated synthetic ResearchContext is required")


@dataclass(frozen=True)
class PointsPolicy:
    policy_id: str
    win_points: int
    draw_points: int
    loss_points: int

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("points policy id must not be empty")
        values = (self.win_points, self.draw_points, self.loss_points)
        if any(type(value) is not int for value in values):
            raise ValueError("points must be non-boolean integers")
        if min(values) < 0:
            raise ValueError("points must be non-negative")


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    if value.utcoffset().total_seconds() != 0:
        raise ValueError(f"{field_name} must be UTC")


@dataclass(frozen=True)
class HistoricalMatch:
    """One known regulation-time result.

    ``observed_at`` is when this exact result became available to the platform. It is not
    interchangeable with kickoff or provider update time. Only regular-duration, completed
    matches belong in this contract; extra time, shootouts and awarded results require richer
    source semantics and are deliberately rejected.
    """

    match_id: str
    competition_id: str
    season_id: str
    kickoff_utc: datetime
    observed_at: datetime
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int
    neutral_venue: bool
    half_time_home_goals: int | None = None
    half_time_away_goals: int | None = None
    metrics: Mapping[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "match_id",
            "competition_id",
            "season_id",
            "home_team_id",
            "away_team_id",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} must not be empty")
        if self.home_team_id == self.away_team_id:
            raise ValueError("home and away teams must differ")
        _require_aware(self.kickoff_utc, "kickoff_utc")
        _require_aware(self.observed_at, "observed_at")
        if self.observed_at < self.kickoff_utc:
            raise ValueError("a result cannot be observed before kickoff")
        if type(self.home_goals) is not int or type(self.away_goals) is not int:
            raise ValueError("goals must be non-boolean integers")
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError("goals must be non-negative")
        half_time = (self.half_time_home_goals, self.half_time_away_goals)
        if (half_time[0] is None) != (half_time[1] is None):
            raise ValueError("both half-time scores must be supplied together")
        if half_time[0] is not None:
            if type(half_time[0]) is not int or type(half_time[1]) is not int:
                raise ValueError("half-time goals must be non-boolean integers")
            if half_time[0] < 0 or half_time[1] < 0:
                raise ValueError("half-time goals must be non-negative")
            if half_time[0] > self.home_goals or half_time[1] > self.away_goals:
                raise ValueError("half-time goals cannot exceed full-time goals")
        clean_metrics: dict[str, float] = {}
        for key, value in self.metrics.items():
            if not key:
                raise ValueError("metric names must not be empty")
            numeric = float(value)
            if not isfinite(numeric) or numeric < 0:
                raise ValueError(f"metric {key!r} must be finite and non-negative")
            clean_metrics[key] = numeric
        object.__setattr__(self, "metrics", MappingProxyType(clean_metrics))

    def involves(self, team_id: str) -> bool:
        return team_id in (self.home_team_id, self.away_team_id)

    def venue_for(self, team_id: str) -> Venue:
        if not self.involves(team_id):
            raise ValueError(f"team {team_id!r} did not play match {self.match_id!r}")
        if self.neutral_venue:
            return Venue.NEUTRAL
        return Venue.HOME if team_id == self.home_team_id else Venue.AWAY

    def goals_for(self, team_id: str) -> int:
        if team_id == self.home_team_id:
            return self.home_goals
        if team_id == self.away_team_id:
            return self.away_goals
        raise ValueError(f"team {team_id!r} did not play match {self.match_id!r}")

    def goals_against(self, team_id: str) -> int:
        if team_id == self.home_team_id:
            return self.away_goals
        if team_id == self.away_team_id:
            return self.home_goals
        raise ValueError(f"team {team_id!r} did not play match {self.match_id!r}")


@dataclass(frozen=True)
class MatchRequest:
    match_id: str
    competition_id: str
    season_id: str
    kickoff_utc: datetime
    home_team_id: str
    away_team_id: str
    neutral_venue: bool
    as_of: datetime

    def __post_init__(self) -> None:
        for name in (
            "match_id",
            "competition_id",
            "season_id",
            "home_team_id",
            "away_team_id",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} must not be empty")
        _require_aware(self.kickoff_utc, "kickoff_utc")
        _require_aware(self.as_of, "as_of")
        if self.as_of >= self.kickoff_utc:
            raise ValueError("analysis as_of must be before kickoff")
        if self.home_team_id == self.away_team_id:
            raise ValueError("home and away teams must differ")


@dataclass(frozen=True)
class IntelligenceDataset:
    dataset_id: str
    classification: DataClassification
    matches: tuple[HistoricalMatch, ...]

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise ValueError("dataset_id must not be empty")
        if len(self.matches) > 100_000:
            raise ValueError("synthetic dataset exceeds the 100000-match safety limit")
        ids = [match.match_id for match in self.matches]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate match ids are not allowed")

    @property
    def digest(self) -> str:
        rows = [
            {
                "match_id": match.match_id,
                "competition_id": match.competition_id,
                "season_id": match.season_id,
                "kickoff_utc": match.kickoff_utc.isoformat(),
                "observed_at": match.observed_at.isoformat(),
                "home_team_id": match.home_team_id,
                "away_team_id": match.away_team_id,
                "home_goals": match.home_goals,
                "away_goals": match.away_goals,
                "neutral_venue": match.neutral_venue,
                "half_time_home_goals": match.half_time_home_goals,
                "half_time_away_goals": match.half_time_away_goals,
                "metrics": sorted(match.metrics.items()),
            }
            for match in sorted(self.matches, key=lambda item: item.match_id)
        ]
        canonical = json.dumps(
            {
                "dataset_id": self.dataset_id,
                "classification": self.classification.value,
                "matches": rows,
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def research_context(self, *, protocol_version: str = "phase4-v1") -> ResearchContext:
        return ResearchContext(self.classification, self.digest, protocol_version)
