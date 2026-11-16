"""Validated, immutable inputs for point-in-time offline analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
import json
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Sequence


class Venue(StrEnum):
    HOME = "home"
    AWAY = "away"
    NEUTRAL = "neutral"
    OVERALL = "overall"


class DataClassification(StrEnum):
    SYNTHETIC_TEST = "synthetic_test_data"
    VERIFIED_REAL = "verified_real_data"


@dataclass(frozen=True)
class DatasetEvidence:
    """Provenance required for a VERIFIED_REAL dataset (ADR-0010).

    A real dataset is a claim about the world. The evidence block ties that claim to
    archived raw payloads and a bounded observation window so the label cannot be
    asserted bare. SYNTHETIC_TEST datasets require no evidence; VERIFIED_REAL datasets
    are rejected without it.
    """

    provider_code: str
    raw_payload_ids: tuple[int, ...]
    retrieval_from_utc: datetime
    retrieval_to_utc: datetime
    payload_digest: str
    observed_from_utc: datetime
    observed_to_utc: datetime

    def __post_init__(self) -> None:
        if not self.provider_code or not isinstance(self.provider_code, str):
            raise ValueError("provider_code must be a non-empty string")
        if not self.raw_payload_ids:
            raise ValueError("raw_payload_ids must not be empty")
        if any(
            type(item) is not int or item <= 0 for item in self.raw_payload_ids
        ):
            raise ValueError("raw_payload_ids must be positive integers")
        if len(set(self.raw_payload_ids)) != len(self.raw_payload_ids):
            raise ValueError("raw_payload_ids must not contain duplicates")
        for name in ("retrieval_from_utc", "retrieval_to_utc", "observed_from_utc", "observed_to_utc"):
            _require_aware(getattr(self, name), name)
        if self.retrieval_from_utc >= self.retrieval_to_utc:
            raise ValueError("retrieval window must be increasing")
        if self.observed_from_utc >= self.observed_to_utc:
            raise ValueError("observation window must be increasing")
        if (
            len(self.payload_digest) != 64
            or any(character not in "0123456789abcdef" for character in self.payload_digest)
        ):
            raise ValueError("payload_digest must be a lowercase SHA-256 hex digest")


@dataclass(frozen=True)
class ResearchContext:
    classification: DataClassification
    dataset_digest: str
    protocol_version: str
    evidence: DatasetEvidence | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.classification, DataClassification):
            raise ValueError("classification must be a DataClassification")
        if self.classification is DataClassification.VERIFIED_REAL:
            if not isinstance(self.evidence, DatasetEvidence):
                raise ValueError(
                    "VERIFIED_REAL datasets require a DatasetEvidence block"
                )
        elif self.classification is DataClassification.SYNTHETIC_TEST:
            if self.evidence is not None:
                raise ValueError(
                    "SYNTHETIC_TEST datasets must not carry real-data evidence"
                )
        else:  # pragma: no cover - defensive; enum is closed
            raise ValueError("classification must be a DataClassification")
        if len(self.dataset_digest) != 64 or any(
            character not in "0123456789abcdef" for character in self.dataset_digest
        ):
            raise ValueError("dataset_digest must be a lowercase SHA-256 hex digest")
        if not self.protocol_version:
            raise ValueError("protocol_version must not be empty")


def require_context(context: ResearchContext) -> None:
    if not isinstance(context, ResearchContext):
        raise ValueError("a validated ResearchContext is required")


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
    evidence: DatasetEvidence | None = None

    def __post_init__(self) -> None:
        if not self.dataset_id:
            raise ValueError("dataset_id must not be empty")
        if len(self.matches) > 100_000:
            raise ValueError("dataset exceeds the 100000-match safety limit")
        ids = [match.match_id for match in self.matches]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate match ids are not allowed")
        if self.classification is DataClassification.VERIFIED_REAL:
            if not isinstance(self.evidence, DatasetEvidence):
                raise ValueError(
                    "VERIFIED_REAL datasets require a DatasetEvidence block"
                )
        elif self.classification is DataClassification.SYNTHETIC_TEST:
            if self.evidence is not None:
                raise ValueError(
                    "SYNTHETIC_TEST datasets must not carry real-data evidence"
                )

    def _canonical_rows(self) -> list[dict[str, object]]:
        return _canonical_match_rows(self.matches)

    @property
    def content_digest(self) -> str:
        """Digest of the materialised rows, independent of the dataset label.

        ``dataset_id`` is not part of this digest, so the identifier can be derived
        from the content without a circular dependency. Two analyses that read the
        same results receive the same content digest even when they ran at different
        wall-clock times.
        """

        return materialized_content_digest(self.matches, self.classification)

    @property
    def digest(self) -> str:
        canonical = json.dumps(
            {
                "dataset_id": self.dataset_id,
                "classification": self.classification.value,
                "matches": self._canonical_rows(),
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()

    def research_context(self, *, protocol_version: str = "phase4-v1") -> ResearchContext:
        return ResearchContext(
            self.classification, self.digest, protocol_version, evidence=self.evidence
        )


def _canonical_match_rows(matches: Sequence[HistoricalMatch]) -> list[dict[str, object]]:
    return [
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
        for match in sorted(matches, key=lambda item: item.match_id)
    ]


def materialized_content_digest(
    matches: Sequence[HistoricalMatch],
    classification: DataClassification,
) -> str:
    """Digest the rows that determine an analysis, without the dataset identifier."""

    canonical = json.dumps(
        {
            "classification": classification.value,
            "matches": _canonical_match_rows(matches),
        },
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()
