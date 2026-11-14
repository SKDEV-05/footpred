"""Deterministic sequential Elo ratings for supplied research configuration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite

from app.intelligence.types import ResearchContext, require_context

MAX_ELO_RESULTS = 100_000
MAX_ABS_RATING = 100_000.0

@dataclass(frozen=True)
class EloConfig:
    initial_rating: float = 1500.0
    k_factor: float = 20.0
    scale: float = 400.0
    home_advantage: float = 0.0

    def __post_init__(self) -> None:
        values = (self.initial_rating, self.k_factor, self.scale, self.home_advantage)
        if not all(isfinite(value) for value in values):
            raise ValueError("Elo configuration must be finite")
        if self.k_factor <= 0 or self.scale <= 0:
            raise ValueError("Elo k_factor and scale must be positive")


@dataclass(frozen=True)
class EloResult:
    match_id: str
    kickoff_utc: datetime
    observed_at: datetime
    home_team_id: str
    away_team_id: str
    home_goals: int
    away_goals: int
    neutral_venue: bool

    def __post_init__(self) -> None:
        if (
            self.kickoff_utc.tzinfo is None
            or self.observed_at.tzinfo is None
            or self.kickoff_utc.utcoffset() is None
            or self.observed_at.utcoffset() is None
        ):
            raise ValueError("Elo timestamps must be timezone-aware")
        if (
            self.kickoff_utc.utcoffset().total_seconds() != 0
            or self.observed_at.utcoffset().total_seconds() != 0
        ):
            raise ValueError("Elo timestamps must be UTC")
        if self.observed_at < self.kickoff_utc:
            raise ValueError("result cannot be observed before kickoff")
        if self.home_team_id == self.away_team_id:
            raise ValueError("teams must differ")
        if type(self.home_goals) is not int or type(self.away_goals) is not int:
            raise ValueError("goals must be non-boolean integers")
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError("goals must be non-negative")


@dataclass(frozen=True)
class EloSnapshot:
    as_of: datetime
    ratings: tuple[tuple[str, float], ...]
    processed_match_ids: tuple[str, ...]
    context: ResearchContext

    def rating_for(self, team_id: str) -> float | None:
        return dict(self.ratings).get(team_id)


class EloState:
    """Small immutable-by-output processor; configuration is not claimed as calibrated."""

    def __init__(self, *, context: ResearchContext, config: EloConfig | None = None) -> None:
        require_context(context)
        self.context = context
        self.config = config or EloConfig()

    def expected_home_score(
        self,
        home_rating: float,
        away_rating: float,
        *,
        neutral_venue: bool,
    ) -> float:
        if (
            not isfinite(home_rating)
            or not isfinite(away_rating)
            or abs(home_rating) > MAX_ABS_RATING
            or abs(away_rating) > MAX_ABS_RATING
        ):
            raise ValueError("ratings must be finite and within the safety bound")
        offset = 0.0 if neutral_venue else self.config.home_advantage
        exponent = -(home_rating - away_rating + offset) / self.config.scale
        if exponent > 300:
            return 0.0
        if exponent < -300:
            return 1.0
        return 1.0 / (1.0 + 10.0**exponent)

    def replay(self, results: tuple[EloResult, ...], *, as_of: datetime) -> EloSnapshot:
        require_context(self.context)
        if as_of.tzinfo is None or as_of.utcoffset() is None:
            raise ValueError("as_of must be timezone-aware")
        if as_of.utcoffset().total_seconds() != 0:
            raise ValueError("as_of must be UTC")
        if len(results) > MAX_ELO_RESULTS:
            raise ValueError("Elo input exceeds the 100000-result safety limit")
        if len({result.match_id for result in results}) != len(results):
            raise ValueError("duplicate Elo match ids are not allowed")
        eligible = [
            result
            for result in results
            if result.kickoff_utc < as_of and result.observed_at < as_of
        ]
        eligible.sort(key=lambda result: (result.kickoff_utc, result.match_id))
        ratings: dict[str, float] = {}
        processed: list[str] = []
        index = 0
        while index < len(eligible):
            kickoff = eligible[index].kickoff_utc
            batch: list[EloResult] = []
            while index < len(eligible) and eligible[index].kickoff_utc == kickoff:
                batch.append(eligible[index])
                index += 1
            teams = [
                team
                for result in batch
                for team in (result.home_team_id, result.away_team_id)
            ]
            if len(teams) != len(set(teams)):
                raise ValueError("a team cannot appear twice at the same kickoff")
            changes: dict[str, float] = {}
            for result in batch:
                home = ratings.get(result.home_team_id, self.config.initial_rating)
                away = ratings.get(result.away_team_id, self.config.initial_rating)
                expected = self.expected_home_score(
                    home,
                    away,
                    neutral_venue=result.neutral_venue,
                )
                actual = (
                    1.0
                    if result.home_goals > result.away_goals
                    else 0.5
                    if result.home_goals == result.away_goals
                    else 0.0
                )
                change = self.config.k_factor * (actual - expected)
                changes[result.home_team_id] = change
                changes[result.away_team_id] = -change
                processed.append(result.match_id)
            for team, change in changes.items():
                ratings[team] = ratings.get(team, self.config.initial_rating) + change
        return EloSnapshot(
            as_of=as_of,
            ratings=tuple(sorted(ratings.items())),
            processed_match_ids=tuple(processed),
            context=self.context,
        )
