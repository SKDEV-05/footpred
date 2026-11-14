"""Dixon-Coles low-score adjustment for synthetic supplied parameters."""

from __future__ import annotations

from math import isfinite

from app.intelligence.models.poisson import ScoreMatrix, poisson_score_matrix
from app.intelligence.types import ResearchContext, require_context


def _tau(home: int, away: int, home_rate: float, away_rate: float, rho: float) -> float:
    if home == 0 and away == 0:
        return 1.0 - home_rate * away_rate * rho
    if home == 0 and away == 1:
        return 1.0 + home_rate * rho
    if home == 1 and away == 0:
        return 1.0 + away_rate * rho
    if home == 1 and away == 1:
        return 1.0 - rho
    return 1.0


def _rho_bounds(home_rate: float, away_rate: float) -> tuple[float, float]:
    lower_candidates = [
        -1.0 / rate for rate in (home_rate, away_rate) if rate > 0
    ]
    upper_candidates = [1.0]
    if home_rate * away_rate > 0:
        upper_candidates.append(1.0 / (home_rate * away_rate))
    return (max(lower_candidates, default=float("-inf")), min(upper_candidates))


def dixon_coles_matrix(
    home_rate: float,
    away_rate: float,
    rho: float,
    *,
    context: ResearchContext,
    unresolved_tolerance: float = 1e-10,
    mass_tolerance: float = 1e-12,
) -> ScoreMatrix:
    """Apply the low-score correction without fitting or silent normalization."""

    require_context(context)
    if not isfinite(rho):
        raise ValueError("rho must be finite")
    lower, upper = _rho_bounds(home_rate, away_rate)
    if rho < lower or rho > upper:
        raise ValueError(f"rho must be in the admissible interval [{lower}, {upper}]")
    baseline = poisson_score_matrix(
        home_rate,
        away_rate,
        context=context,
        unresolved_tolerance=unresolved_tolerance,
    )
    adjusted = []
    for home, row in enumerate(baseline.probabilities):
        adjusted_row = []
        for away, probability in enumerate(row):
            factor = _tau(home, away, home_rate, away_rate, rho)
            if factor < 0:
                raise ValueError("rho produces a negative low-score adjustment")
            adjusted_row.append(probability * factor)
        adjusted.append(tuple(adjusted_row))
    probabilities = tuple(adjusted)
    total = sum(sum(row) for row in probabilities)
    if abs(total - 1.0) > mass_tolerance:
        raise ValueError("Dixon-Coles adjustment did not conserve probability mass")
    return ScoreMatrix(
        probabilities=probabilities,
        exact_max_goals=baseline.exact_max_goals,
        home_rate=home_rate,
        away_rate=away_rate,
        model_id="dixon_coles_supplied_parameters",
        model_version="2",
        context=context,
    )
