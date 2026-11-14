"""Synthetic mathematical reference tests; these are not football validation."""

from __future__ import annotations

from math import exp

import pytest

from app.intelligence.models.dixon_coles import dixon_coles_matrix
from app.intelligence.models.poisson import poisson_probabilities, poisson_score_matrix
from app.intelligence.probabilities import (
    both_teams_to_score,
    double_chance,
    match_outcomes,
    over_probability,
    top_scorelines,
)
from app.intelligence.types import DataClassification, ResearchContext

CONTEXT = ResearchContext(DataClassification.SYNTHETIC_TEST, "1" * 64, "test-v1")


def test_poisson_reference_values_zero_rate_and_overflow() -> None:
    values = poisson_probabilities(2.0, 3, context=CONTEXT)
    exact = (exp(-2), 2 * exp(-2), 2 * exp(-2), 4 * exp(-2) / 3)
    assert values[:4] == pytest.approx(exact)
    assert values[4] == pytest.approx(1 - sum(exact))
    assert poisson_probabilities(0.0, 3, context=CONTEXT) == (1.0, 0.0, 0.0, 0.0, 0.0)


@pytest.mark.parametrize("invalid", [-1.0, float("nan"), float("inf")])
def test_poisson_rejects_invalid_rates(invalid: float) -> None:
    with pytest.raises(ValueError):
        poisson_score_matrix(invalid, 1.0, context=CONTEXT)


def test_poisson_matrix_keeps_explicit_overflow_and_full_mass() -> None:
    matrix = poisson_score_matrix(1.4, 1.1, context=CONTEXT, unresolved_tolerance=1e-12)
    assert matrix.total_probability == pytest.approx(1.0, abs=1e-12)
    assert matrix.probabilities[matrix.overflow_index][matrix.overflow_index] <= 1e-12
    assert matrix.overflow_probability > 0
    assert matrix.context is CONTEXT


def test_market_probability_bounds_are_coherent() -> None:
    matrix = poisson_score_matrix(1.4, 1.1, context=CONTEXT)
    outcomes = match_outcomes(matrix)
    unresolved = outcomes.unresolved_probability
    lower_total = outcomes.home_win.lower + outcomes.draw.lower + outcomes.away_win.lower
    assert lower_total + unresolved == pytest.approx(1.0)
    assert outcomes.home_win.upper - outcomes.home_win.lower == pytest.approx(unresolved)
    chances = double_chance(outcomes)
    assert chances.home_or_draw.lower == pytest.approx(
        outcomes.home_win.lower + outcomes.draw.lower
    )
    assert over_probability(matrix, 0.5) >= over_probability(matrix, 1.5)
    assert over_probability(matrix, 1.5) >= over_probability(matrix, 2.5)
    btts = both_teams_to_score(matrix)
    assert btts.yes + btts.no == pytest.approx(1.0)
    assert btts.yes == pytest.approx((1 - exp(-1.4)) * (1 - exp(-1.1)), abs=1e-12)


def test_top_scorelines_exclude_overflow_and_are_sorted() -> None:
    matrix = poisson_score_matrix(1.2, 0.8, context=CONTEXT)
    scores = top_scorelines(matrix, limit=4)
    assert len(scores) == 4
    assert all(home <= matrix.exact_max_goals and away <= matrix.exact_max_goals for home, away, _ in scores)
    assert [item[2] for item in scores] == sorted((item[2] for item in scores), reverse=True)


def test_dixon_coles_rho_zero_is_poisson() -> None:
    poisson = poisson_score_matrix(1.3, 0.9, context=CONTEXT)
    adjusted = dixon_coles_matrix(1.3, 0.9, 0.0, context=CONTEXT)
    assert adjusted.probabilities == poisson.probabilities


def test_dixon_coles_changes_only_low_scores_and_conserves_mass() -> None:
    poisson = poisson_score_matrix(1.3, 0.9, context=CONTEXT)
    adjusted = dixon_coles_matrix(1.3, 0.9, -0.1, context=CONTEXT)
    assert adjusted.total_probability == pytest.approx(1.0)
    changed = {
        (home, away)
        for home, row in enumerate(poisson.probabilities)
        for away, value in enumerate(row)
        if adjusted.probabilities[home][away] != value
    }
    assert changed == {(0, 0), (0, 1), (1, 0), (1, 1)}


def test_dixon_coles_rejects_rho_outside_admissible_interval() -> None:
    with pytest.raises(ValueError, match="admissible"):
        dixon_coles_matrix(1.0, 1.0, 2.0, context=CONTEXT)


def test_dixon_coles_handles_zero_rates_at_boundary() -> None:
    matrix = dixon_coles_matrix(0.0, 0.0, 1.0, context=CONTEXT)
    assert matrix.total_probability == pytest.approx(1.0)


def test_model_entry_points_require_validated_context() -> None:
    with pytest.raises((TypeError, ValueError)):
        poisson_score_matrix(1.0, 1.0, context=None)  # type: ignore[arg-type]


SUPPORTED_RATES = (0.0, 0.2, 0.8, 1.4, 2.5, 3.8)


@pytest.mark.parametrize("home_rate", SUPPORTED_RATES)
@pytest.mark.parametrize("away_rate", SUPPORTED_RATES)
def test_matrix_and_market_invariants_hold_across_rate_grid(
    home_rate: float,
    away_rate: float,
) -> None:
    matrix = poisson_score_matrix(home_rate, away_rate, context=CONTEXT)
    cells = [value for row in matrix.probabilities for value in row]
    assert all(0.0 <= value <= 1.0 for value in cells)
    assert matrix.total_probability == pytest.approx(1.0, abs=1e-12)

    outcomes = match_outcomes(matrix)
    lower_total = outcomes.home_win.lower + outcomes.draw.lower + outcomes.away_win.lower
    assert lower_total + outcomes.unresolved_probability == pytest.approx(1.0, abs=1e-12)
    for bound in (outcomes.home_win, outcomes.draw, outcomes.away_win):
        assert 0.0 <= bound.lower <= bound.upper <= 1.0

    chances = double_chance(outcomes)
    assert chances.home_or_draw.lower == pytest.approx(
        outcomes.home_win.lower + outcomes.draw.lower
    )
    assert chances.draw_or_away.lower == pytest.approx(
        outcomes.draw.lower + outcomes.away_win.lower
    )
    assert chances.home_or_away.lower == pytest.approx(
        outcomes.home_win.lower + outcomes.away_win.lower
    )
    for bound in (chances.home_or_draw, chances.draw_or_away, chances.home_or_away):
        assert 0.0 <= bound.lower <= bound.upper <= 1.0

    over = [over_probability(matrix, line) for line in (0.5, 1.5, 2.5, 3.5)]
    assert over == sorted(over, reverse=True)
    assert 0.0 <= over[-1] <= over[0] <= 1.0

    btts = both_teams_to_score(matrix)
    assert btts.yes + btts.no == pytest.approx(1.0)
    assert 0.0 <= btts.yes <= over[1]


@pytest.mark.parametrize("rho", (-0.05, 0.0, 0.05))
def test_dixon_coles_grid_conserves_mass_and_non_negative_cells(rho: float) -> None:
    matrix = dixon_coles_matrix(1.3, 1.1, rho, context=CONTEXT)
    cells = [value for row in matrix.probabilities for value in row]
    assert all(value >= 0 for value in cells)
    assert matrix.total_probability == pytest.approx(1.0, abs=1e-12)


def test_extra_zero_rate_low_score_cell_keeps_valid_tau() -> None:
    matrix = dixon_coles_matrix(0.0, 0.0, 1.0, context=CONTEXT)
    assert matrix.probabilities[0][0] == pytest.approx(1.0)
