"""Dixon-Coles low-score dependence.

Two layers live here:

* ``dixon_coles_matrix`` — the Phase 4 primitive. It applies a caller-supplied ``rho`` and
  refuses to fit, normalise or guess. Its behaviour is unchanged.
* ``fit_rho`` / ``dixon_coles_score_matrix`` — the Phase 7 fitted model
  (``dixon-coles-v1.0.0``). ``rho`` is estimated by weighted maximum likelihood on training
  matches only, inside an interval where every low-score correction stays positive.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite, log
from typing import Sequence

from app.intelligence.models.poisson import ScoreMatrix, poisson_score_matrix
from app.intelligence.types import ResearchContext, require_context

DC_MODEL_ID = "dixon_coles_baseline"
DC_MODEL_VERSION = "dixon-coles-v1.0.0"
DC_PARAMETER_VERSION = "rho-v1.0"

# Published Dixon-Coles estimates sit near -0.13 for league football. The bound is a
# guard against a degenerate likelihood, not a prior: the data choose inside it.
RHO_MIN = -0.30
RHO_MAX = 0.30
RHO_GRID_STEP = 0.0025
RHO_REFINE_ROUNDS = 4
RHO_HALF_LIFE_DAYS = 180.0
RHO_MIN_MATCHES = 30


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


@dataclass(frozen=True)
class LowScoreObservation:
    """One training result expressed against the rates the model would have used."""

    home_rate: float
    away_rate: float
    home_goals: int
    away_goals: int
    kickoff_utc: datetime

    def __post_init__(self) -> None:
        if not isfinite(self.home_rate) or not isfinite(self.away_rate):
            raise ValueError("training rates must be finite")
        if self.home_rate <= 0 or self.away_rate <= 0:
            raise ValueError("training rates must be positive")
        if type(self.home_goals) is not int or type(self.away_goals) is not int:
            raise ValueError("training goals must be non-boolean integers")
        if self.home_goals < 0 or self.away_goals < 0:
            raise ValueError("training goals must be non-negative")
        if self.kickoff_utc.tzinfo is None or self.kickoff_utc.utcoffset() is None:
            raise ValueError("kickoff_utc must be timezone-aware")


@dataclass(frozen=True)
class RhoFit:
    """A fitted low-score dependence term and the evidence behind it."""

    rho: float
    matches_used: int
    effective_matches: float
    bound_lower: float
    bound_upper: float
    log_likelihood: float
    half_life_days: float
    method: str = "weighted_grid_maximum_likelihood"

    @property
    def status(self) -> str:
        return "FITTED" if self.matches_used else "IDENTITY_NO_TRAINING_DATA"


def _admissible_rho_interval(
    observations: Sequence[LowScoreObservation],
) -> tuple[float, float]:
    """Intersect the per-match positivity constraints into one safe interval."""

    lower, upper = RHO_MIN, RHO_MAX
    for observation in observations:
        match_lower, match_upper = _rho_bounds(
            observation.home_rate, observation.away_rate
        )
        lower = max(lower, match_lower)
        upper = min(upper, match_upper)
    return lower, upper


def fit_rho(
    observations: Sequence[LowScoreObservation],
    *,
    reference_kickoff: datetime,
    half_life_days: float = RHO_HALF_LIFE_DAYS,
    minimum_matches: int = RHO_MIN_MATCHES,
) -> RhoFit:
    """Estimate ``rho`` by time-weighted maximum likelihood.

    Only the four low-score cells depend on ``rho``, so only those contribute to the
    likelihood. Recency weighting is justified because low-score dependence drifts with
    league scoring levels; the half-life is explicit and versioned.
    """

    if half_life_days <= 0 or not isfinite(half_life_days):
        raise ValueError("half_life_days must be finite and positive")
    if reference_kickoff.tzinfo is None or reference_kickoff.utcoffset() is None:
        raise ValueError("reference_kickoff must be timezone-aware")

    if len(observations) < minimum_matches:
        return RhoFit(
            rho=0.0,
            matches_used=0,
            effective_matches=0.0,
            bound_lower=RHO_MIN,
            bound_upper=RHO_MAX,
            log_likelihood=0.0,
            half_life_days=half_life_days,
        )

    lower, upper = _admissible_rho_interval(observations)
    if lower >= upper:
        return RhoFit(
            rho=0.0,
            matches_used=0,
            effective_matches=0.0,
            bound_lower=lower,
            bound_upper=upper,
            log_likelihood=0.0,
            half_life_days=half_life_days,
        )

    weights = [
        0.5 ** (max(0.0, (reference_kickoff - item.kickoff_utc).total_seconds()) / 86400.0 / half_life_days)
        for item in observations
    ]
    effective = sum(weights)

    def evaluate(rho: float) -> float:
        # The score of a training result only involves rho at the four low-score cells.
        total = 0.0
        for observation, weight in zip(observations, weights, strict=True):
            factor = _tau(
                observation.home_goals,
                observation.away_goals,
                observation.home_rate,
                observation.away_rate,
                rho,
            )
            if factor <= 0:
                return float("-inf")
            if (observation.home_goals, observation.away_goals) in {
                (0, 0),
                (0, 1),
                (1, 0),
                (1, 1),
            }:
                total += weight * log(factor)
        return total

    steps = max(2, int(round((upper - lower) / RHO_GRID_STEP)))
    best_rho = lower
    best_value = float("-inf")
    for index in range(steps + 1):
        candidate = lower + (upper - lower) * index / steps
        value = evaluate(candidate)
        if value > best_value:
            best_value, best_rho = value, candidate

    # Deterministic local refinement around the grid optimum.
    span = (upper - lower) / steps
    for _ in range(RHO_REFINE_ROUNDS):
        candidates = (best_rho - span / 2.0, best_rho, best_rho + span / 2.0)
        for candidate in candidates:
            clipped = min(upper, max(lower, candidate))
            value = evaluate(clipped)
            if value > best_value:
                best_value, best_rho = value, clipped
        span /= 2.0

    return RhoFit(
        rho=round(best_rho, 6),
        matches_used=len(observations),
        effective_matches=round(effective, 3),
        bound_lower=round(lower, 6),
        bound_upper=round(upper, 6),
        log_likelihood=round(best_value, 6) if best_value > float("-inf") else 0.0,
        half_life_days=half_life_days,
        method="weighted_grid_maximum_likelihood_low_score_cells",
    )


def clip_rho(fit: RhoFit, home_rate: float, away_rate: float) -> float:
    """Clamp a fitted rho into the interval where this match's corrections stay valid."""

    lower, upper = _rho_bounds(home_rate, away_rate)
    lower = max(lower, RHO_MIN)
    upper = min(upper, RHO_MAX)
    if lower >= upper:
        return 0.0
    return min(upper - 1e-9, max(lower + 1e-9, fit.rho))


def dixon_coles_score_matrix(
    home_rate: float,
    away_rate: float,
    rho: float,
    *,
    context: ResearchContext,
) -> ScoreMatrix:
    """Validated Dixon-Coles matrix carrying the fitted model identity."""

    base = dixon_coles_matrix(home_rate, away_rate, rho, context=context)
    return ScoreMatrix(
        probabilities=base.probabilities,
        exact_max_goals=base.exact_max_goals,
        home_rate=home_rate,
        away_rate=away_rate,
        model_id=DC_MODEL_ID,
        model_version=DC_MODEL_VERSION,
        context=context,
    )
