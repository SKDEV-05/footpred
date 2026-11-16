"""Fitted Elo baseline (``elo-v1.0.0``).

Ratings remain a pure chronological Elo replay; only the outcome mapping is fitted.
Two parameters are estimated on training matches and frozen for an evaluation window:

* ``home_advantage`` — the rating offset given to the home side, in Elo points.
* ``draw_nu`` — the Davidson (1970) draw parameter.

The mapping is a Bradley-Terry/Davidson model driven by the Elo difference:

    r = 10 ** ((R_home - R_away + H) / 400)
    P(home) = r / (r + 1 + v * sqrt(r))
    P(draw) = v * sqrt(r) / (r + 1 + v * sqrt(r))
    P(away) = 1 / (r + 1 + v * sqrt(r))

The three probabilities sum to one by construction. Elo is a 1X2 baseline, not a
score-distribution model: it produces no expected goals and no scoreline matrix.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite, log
from typing import Sequence

from app.intelligence.models.elo import EloConfig, MAX_ABS_RATING
from app.intelligence.types import HistoricalMatch

ELO_MODEL_ID = "elo_baseline"
ELO_MODEL_VERSION = "elo-v1.0.0"
ELO_PARAMETER_VERSION = "elo-params-v1.0"

DEFAULT_INITIAL_RATING = 1500.0
DEFAULT_K_FACTOR = 20.0
DEFAULT_SCALE = 400.0

# Deliberately coarse grids: with a few hundred training matches a finer grid would
# overfit the noise rather than improve the estimate.
HOME_ADVANTAGE_GRID = tuple(float(value) for value in range(0, 150, 10))
DRAW_NU_GRID = tuple(round(0.30 + 0.05 * index, 2) for index in range(31))
ELO_MIN_TRAINING_MATCHES = 30
ELO_REFINE_ROUNDS = 5


@dataclass(frozen=True)
class DavidsonFit:
    """Fitted home advantage and draw parameter for the Elo outcome mapping."""

    home_advantage: float
    draw_nu: float
    matches_used: int
    log_likelihood: float
    method: str = "grid_maximum_likelihood_davidson"

    @property
    def status(self) -> str:
        return "FITTED" if self.matches_used else "DEFAULT_NO_TRAINING_DATA"


def elo_outcome_probabilities(
    home_rating: float,
    away_rating: float,
    *,
    home_advantage: float,
    draw_nu: float,
) -> tuple[float, float, float]:
    """Return home/draw/away probabilities from two Elo ratings."""

    for value in (home_rating, away_rating, home_advantage, draw_nu):
        if not isfinite(value):
            raise ValueError("Elo probability inputs must be finite")
    if draw_nu <= 0:
        raise ValueError("draw_nu must be positive")
    if abs(home_rating) > MAX_ABS_RATING or abs(away_rating) > MAX_ABS_RATING:
        raise ValueError("ratings exceed the safety bound")

    exponent = (home_rating - away_rating + home_advantage) / DEFAULT_SCALE
    if exponent > 12:
        return (1.0, 0.0, 0.0)
    if exponent < -12:
        return (0.0, 0.0, 1.0)
    ratio = 10.0**exponent
    root = ratio**0.5
    denominator = ratio + 1.0 + draw_nu * root
    home = ratio / denominator
    draw = draw_nu * root / denominator
    away = 1.0 / denominator
    total = home + draw + away
    return (home / total, draw / total, away / total)


def outcome_index(home_goals: int, away_goals: int) -> int:
    if home_goals > away_goals:
        return 0
    if home_goals == away_goals:
        return 1
    return 2


def _log_likelihood(
    observations: Sequence[tuple[float, float, int]],
    home_advantage: float,
    draw_nu: float,
) -> float:
    total = 0.0
    for home_rating, away_rating, outcome in observations:
        probabilities = elo_outcome_probabilities(
            home_rating,
            away_rating,
            home_advantage=home_advantage,
            draw_nu=draw_nu,
        )
        value = probabilities[outcome]
        if value <= 0:
            return float("-inf")
        total += log(value)
    return total


def fit_davidson(
    observations: Sequence[tuple[float, float, int]],
    *,
    minimum_matches: int = ELO_MIN_TRAINING_MATCHES,
) -> DavidsonFit:
    """Fit home advantage and the draw parameter on training ratings only.

    ``observations`` are ``(home_rating, away_rating, outcome_index)`` computed from
    matches that finished before the evaluation window. Test matches are never used.
    """

    if len(observations) < minimum_matches:
        return DavidsonFit(
            home_advantage=0.0,
            draw_nu=0.9,
            matches_used=0,
            log_likelihood=0.0,
        )

    best_value = float("-inf")
    best_home = HOME_ADVANTAGE_GRID[0]
    best_nu = DRAW_NU_GRID[0]
    for home_advantage in HOME_ADVANTAGE_GRID:
        for draw_nu in DRAW_NU_GRID:
            value = _log_likelihood(observations, home_advantage, draw_nu)
            if value > best_value:
                best_value, best_home, best_nu = value, home_advantage, draw_nu

    span_home, span_nu = 10.0, 0.05
    for _ in range(ELO_REFINE_ROUNDS):
        for delta_home in (-span_home, 0.0, span_home):
            for delta_nu in (-span_nu, 0.0, span_nu):
                candidate_home = max(0.0, min(200.0, best_home + delta_home))
                candidate_nu = max(0.05, min(3.0, best_nu + delta_nu))
                value = _log_likelihood(observations, candidate_home, candidate_nu)
                if value > best_value:
                    best_value, best_home, best_nu = (
                        value,
                        candidate_home,
                        candidate_nu,
                    )
        span_home /= 2.0
        span_nu /= 2.0

    return DavidsonFit(
        home_advantage=round(best_home, 3),
        draw_nu=round(best_nu, 4),
        matches_used=len(observations),
        log_likelihood=round(best_value, 4) if best_value > float("-inf") else 0.0,
    )


class ChronologicalElo:
    """Incremental Elo replay.

    ``apply_batch`` must receive matches sharing one kickoff, so that simultaneous
    results cannot influence each other. Ratings are updated only after a match has
    been predicted, which keeps the replay free of future information.
    """

    def __init__(self, *, config: EloConfig | None = None) -> None:
        self.config = config or EloConfig(
            initial_rating=DEFAULT_INITIAL_RATING,
            k_factor=DEFAULT_K_FACTOR,
            scale=DEFAULT_SCALE,
            home_advantage=0.0,
        )
        self._ratings: dict[str, float] = {}
        self.processed_matches = 0

    def rating(self, team_id: str) -> float | None:
        return self._ratings.get(team_id)

    def _rating_or_initial(self, team_id: str) -> float:
        return self._ratings.get(team_id, self.config.initial_rating)

    def expected_home_score(
        self, home_rating: float, away_rating: float, *, neutral_venue: bool
    ) -> float:
        offset = 0.0 if neutral_venue else self.config.home_advantage
        exponent = -(home_rating - away_rating + offset) / self.config.scale
        if exponent > 300:
            return 0.0
        if exponent < -300:
            return 1.0
        return 1.0 / (1.0 + 10.0**exponent)

    def apply_batch(self, batch: Sequence[HistoricalMatch]) -> None:
        changes: dict[str, float] = {}
        seen: set[str] = set()
        for match in batch:
            teams = {match.home_team_id, match.away_team_id}
            if seen & teams:
                raise ValueError("a team cannot appear twice at the same kickoff")
            seen |= teams
            home = self._rating_or_initial(match.home_team_id)
            away = self._rating_or_initial(match.away_team_id)
            expected = self.expected_home_score(
                home, away, neutral_venue=match.neutral_venue
            )
            actual = (
                1.0
                if match.home_goals > match.away_goals
                else 0.5
                if match.home_goals == match.away_goals
                else 0.0
            )
            change = self.config.k_factor * (actual - expected)
            changes[match.home_team_id] = change
            changes[match.away_team_id] = -change
            self.processed_matches += 1
        for team, change in changes.items():
            self._ratings[team] = self._rating_or_initial(team) + change

    def snapshot(self) -> dict[str, float]:
        return dict(self._ratings)
