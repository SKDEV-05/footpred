"""Independent-Poisson score probabilities for synthetic, caller-supplied rates.

The final row and column are overflow categories, not exact scorelines. No tail mass is
dropped or renormalized.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import exp, isfinite

from app.intelligence.types import ResearchContext, require_context

MAX_PUBLIC_PMF_GOALS = 1_000
MAX_ADAPTIVE_GOALS = 60


@dataclass(frozen=True)
class ScoreMatrix:
    probabilities: tuple[tuple[float, ...], ...]
    exact_max_goals: int
    home_rate: float
    away_rate: float
    model_id: str
    model_version: str
    context: ResearchContext

    def __post_init__(self) -> None:
        require_context(self.context)
        if not self.model_id or not self.model_version:
            raise ValueError("model id and version must not be empty")
        if (
            not isfinite(self.home_rate)
            or not isfinite(self.away_rate)
            or self.home_rate < 0
            or self.away_rate < 0
        ):
            raise ValueError("rates must be finite and non-negative")
        expected_size = self.exact_max_goals + 2
        if self.exact_max_goals < 0 or len(self.probabilities) != expected_size:
            raise ValueError("score matrix size does not match exact_max_goals")
        if any(len(row) != expected_size for row in self.probabilities):
            raise ValueError("score matrix must be square")
        if any(value < 0 or not isfinite(value) for row in self.probabilities for value in row):
            raise ValueError("score probabilities must be finite and non-negative")
        if abs(self.total_probability - 1.0) > 1e-12:
            raise ValueError("score matrix probabilities must sum to one")

    @property
    def overflow_index(self) -> int:
        return self.exact_max_goals + 1

    @property
    def overflow_probability(self) -> float:
        index = self.overflow_index
        return sum(self.probabilities[index]) + sum(
            row[index] for row in self.probabilities[:index]
        )

    @property
    def total_probability(self) -> float:
        return sum(sum(row) for row in self.probabilities)


def poisson_probabilities(
    rate: float,
    maximum: int,
    *,
    context: ResearchContext,
) -> tuple[float, ...]:
    """Return exact probabilities 0..maximum plus one overflow probability."""

    require_context(context)
    if not isfinite(rate) or rate < 0:
        raise ValueError("Poisson rate must be finite and non-negative")
    if type(maximum) is not int or not 0 <= maximum <= MAX_PUBLIC_PMF_GOALS:
        raise ValueError(f"maximum must be an integer in [0, {MAX_PUBLIC_PMF_GOALS}]")
    values = [exp(-rate)]
    for goals in range(1, maximum + 1):
        values.append(values[-1] * rate / goals)
    overflow = max(0.0, 1.0 - sum(values))
    return tuple(values + [overflow])


def _adaptive_maximum(
    home_rate: float,
    away_rate: float,
    tolerance: float,
    context: ResearchContext,
) -> int:
    for maximum in range(6, MAX_ADAPTIVE_GOALS + 1):
        home = poisson_probabilities(home_rate, maximum, context=context)
        away = poisson_probabilities(away_rate, maximum, context=context)
        unresolved = home[-1] * away[-1]
        if unresolved <= tolerance:
            return maximum
    raise ValueError("rates require a goal range above the supported maximum")


def poisson_score_matrix(
    home_rate: float,
    away_rate: float,
    *,
    context: ResearchContext,
    unresolved_tolerance: float = 1e-10,
) -> ScoreMatrix:
    """Build an unconditional matrix with explicit marginal overflow categories."""

    require_context(context)
    if not 0 < unresolved_tolerance < 1:
        raise ValueError("unresolved_tolerance must be between zero and one")
    if not isfinite(home_rate) or not isfinite(away_rate):
        raise ValueError("rates must be finite")
    maximum = _adaptive_maximum(
        home_rate,
        away_rate,
        unresolved_tolerance,
        context,
    )
    home = poisson_probabilities(home_rate, maximum, context=context)
    away = poisson_probabilities(away_rate, maximum, context=context)
    probabilities = tuple(tuple(h * a for a in away) for h in home)
    return ScoreMatrix(
        probabilities=probabilities,
        exact_max_goals=maximum,
        home_rate=home_rate,
        away_rate=away_rate,
        model_id="independent_poisson_supplied_rates",
        model_version="2",
        context=context,
    )
