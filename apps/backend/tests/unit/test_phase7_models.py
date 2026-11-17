"""Phase 7 model tests: Dixon-Coles, Elo + Davidson, and model selection.

These tests pin the properties the Phase 7 report relies on: normalised probabilities,
bounded dependence parameters, chronological training, determinism, and a dispatcher
that refuses unknown models instead of silently substituting one.
"""

from __future__ import annotations

from datetime import timedelta
from math import isclose

import pytest

from app.intelligence.model_selection import (
    MODEL_BY_KEY,
    MODEL_SPECS,
    allowed_model_keys,
    compute_model_prediction,
    replay_elo,
    require_model_spec,
)
from app.intelligence.models.dixon_coles import (
    DC_MODEL_ID,
    DC_MODEL_VERSION,
    RHO_MAX,
    RHO_MIN,
    LowScoreObservation,
    clip_rho,
    dixon_coles_score_matrix,
    fit_rho,
)
from app.intelligence.models.elo_fitted import (
    ELO_MODEL_ID,
    ELO_MODEL_VERSION,
    ChronologicalElo,
    elo_outcome_probabilities,
    fit_davidson,
    outcome_index,
)
from app.intelligence.prediction import (
    PredictionStatus,
    calculate_match_features_from_matches,
)
from app.intelligence.types import (
    DataClassification,
    HistoricalMatch,
    IntelligenceDataset,
)
from tests.phase7_support import (
    COMPETITION_ID,
    TEAMS,
    build_synthetic_dataset,
    build_synthetic_matches,
    target_kickoff,
)

REFERENCE_KICKOFF = target_kickoff(build_synthetic_matches())


def _context(dataset: IntelligenceDataset):
    return dataset.research_context(protocol_version="phase7-test")


def _features(dataset: IntelligenceDataset):
    return calculate_match_features_from_matches(
        dataset.matches,
        home_team_id=TEAMS[0],
        away_team_id=TEAMS[1],
        competition_id=COMPETITION_ID,
    )


def _observations(matches) -> list[LowScoreObservation]:
    return [
        LowScoreObservation(
            home_rate=1.4,
            away_rate=1.1,
            home_goals=match.home_goals,
            away_goals=match.away_goals,
            kickoff_utc=match.kickoff_utc,
        )
        for match in matches
    ]


# --------------------------------------------------------------------------- selection


def test_model_specs_have_distinct_identity():
    keys = [spec.key for spec in MODEL_SPECS]
    assert keys == ["poisson", "dixon_coles", "elo"]
    assert len(set(keys)) == len(keys)
    identities = {(spec.model_id, spec.model_version) for spec in MODEL_SPECS}
    assert len(identities) == len(keys)
    assert MODEL_BY_KEY["dixon_coles"].model_version == DC_MODEL_VERSION
    assert MODEL_BY_KEY["elo"].model_version == ELO_MODEL_VERSION


def test_require_model_spec_rejects_unknown_model():
    with pytest.raises(ValueError) as excinfo:
        require_model_spec("neural_network")
    message = str(excinfo.value)
    assert "neural_network" in message
    for key in allowed_model_keys():
        assert key in message


def test_unknown_model_never_falls_back_to_poisson():
    dataset = build_synthetic_dataset()
    with pytest.raises(ValueError):
        compute_model_prediction(
            dataset,
            _features(dataset),
            model_key="does_not_exist",
            home_team_id=TEAMS[0],
            away_team_id=TEAMS[1],
            competition_id=COMPETITION_ID,
            kickoff_utc=REFERENCE_KICKOFF,
        )


# ------------------------------------------------------------------------ Dixon-Coles


def test_dixon_coles_matrix_is_normalised_and_carries_identity():
    dataset = build_synthetic_dataset()
    matrix = dixon_coles_score_matrix(
        1.4, 1.1, -0.05, context=_context(dataset)
    )
    assert matrix.model_id == DC_MODEL_ID
    assert matrix.model_version == DC_MODEL_VERSION
    total = sum(sum(row) for row in matrix.probabilities)
    assert isclose(total, 1.0, abs_tol=1e-12)
    assert all(
        value >= 0.0 for row in matrix.probabilities for value in row
    )


def test_dixon_coles_matrix_is_deterministic():
    dataset = build_synthetic_dataset()
    context = _context(dataset)
    first = dixon_coles_score_matrix(1.4, 1.1, 0.03, context=context)
    second = dixon_coles_score_matrix(1.4, 1.1, 0.03, context=context)
    assert first.probabilities == second.probabilities


def test_fit_rho_is_bounded_and_deterministic():
    matches = build_synthetic_matches()
    observations = _observations(matches)
    first = fit_rho(observations, reference_kickoff=REFERENCE_KICKOFF)
    second = fit_rho(observations, reference_kickoff=REFERENCE_KICKOFF)

    assert first.status == "FITTED"
    assert first.rho == second.rho
    assert first.log_likelihood == second.log_likelihood
    assert RHO_MIN <= first.rho <= RHO_MAX
    assert first.bound_lower <= first.rho <= first.bound_upper


def test_fit_rho_abstains_below_minimum_sample():
    matches = build_synthetic_matches()[:5]
    fit = fit_rho(_observations(matches), reference_kickoff=REFERENCE_KICKOFF)
    assert fit.status == "IDENTITY_NO_TRAINING_DATA"
    assert fit.matches_used == 0
    assert fit.rho == 0.0


def test_fit_rho_ignores_observations_at_or_after_reference_kickoff():
    matches = build_synthetic_matches()
    observations = _observations(matches)
    cutoff = matches[40].kickoff_utc
    truncated = fit_rho(observations, reference_kickoff=cutoff)
    future = observations[40:]
    with_future = fit_rho(
        [*observations, *future], reference_kickoff=cutoff
    )
    # Future rows are filtered inside the fit, so smuggling later results into the list
    # cannot change the estimate: only the 40 rows before the cutoff are counted.
    assert truncated.matches_used == 40
    assert with_future.matches_used == truncated.matches_used
    assert with_future.rho == truncated.rho


def test_clip_rho_respects_admissible_interval():
    matches = build_synthetic_matches()
    fit = fit_rho(_observations(matches), reference_kickoff=REFERENCE_KICKOFF)
    # A very low scoring rate forces a tighter admissible interval than the fit bound.
    clipped = clip_rho(fit, 0.4, 0.4)
    assert -1.0 / 0.4 <= clipped <= 1.0
    assert clipped <= RHO_MAX
    assert clipped >= RHO_MIN


# -------------------------------------------------------------------------------- Elo


@pytest.mark.parametrize(
    "home_rating, away_rating",
    [
        (1500.0, 1500.0),
        (1800.0, 1500.0),
        (1400.0, 1700.0),
        (2100.0, 1200.0),
    ],
)
def test_elo_probabilities_are_normalised(home_rating, away_rating):
    home, draw, away = elo_outcome_probabilities(
        home_rating, away_rating, home_advantage=60.0, draw_nu=0.8
    )
    assert isclose(home + draw + away, 1.0, abs_tol=1e-12)
    assert 0.0 <= home <= 1.0
    assert 0.0 <= draw <= 1.0
    assert 0.0 <= away <= 1.0


def test_elo_rating_updates_conserve_points():
    elo = ChronologicalElo()
    match = build_synthetic_matches()[0]
    before_home = elo.rating(match.home_team_id) or elo.config.initial_rating
    before_away = elo.rating(match.away_team_id) or elo.config.initial_rating
    elo.apply_batch([match])
    after_home = elo.rating(match.home_team_id)
    after_away = elo.rating(match.away_team_id)
    assert after_home is not None and after_away is not None
    assert isclose(after_home + after_away, before_home + before_away, abs_tol=1e-9)


def test_elo_pre_match_rating_is_captured_before_the_result_is_applied():
    elo = ChronologicalElo()
    match = build_synthetic_matches()[0]
    assert elo.rating(match.home_team_id) is None
    elo.apply_batch([match])
    assert elo.rating(match.home_team_id) is not None
    assert elo.processed_matches == 1


def test_elo_simultaneous_kickoffs_do_not_influence_each_other():
    elo = ChronologicalElo()
    first, second = build_synthetic_matches()[:2]
    assert first.kickoff_utc == second.kickoff_utc
    elo.apply_batch([first, second])
    # Both of the first pair start from the initial rating; neither is updated from the
    # other's result in the same batch.
    for match in (first, second):
        expected_change = elo.config.k_factor * (
            (
                1.0
                if match.home_goals > match.away_goals
                else 0.5
                if match.home_goals == match.away_goals
                else 0.0
            )
            - 0.5
        )
        home_rating = elo.rating(match.home_team_id)
        away_rating = elo.rating(match.away_team_id)
        assert home_rating is not None and away_rating is not None
        assert isclose(home_rating - elo.config.initial_rating, expected_change)
        assert isclose(away_rating - elo.config.initial_rating, -expected_change)


def test_elo_rejects_a_team_appearing_twice_in_one_batch():
    elo = ChronologicalElo()
    matches = build_synthetic_matches()
    first = matches[0]
    duplicate = HistoricalMatch(
        match_id="duplicate",
        competition_id=first.competition_id,
        season_id=first.season_id,
        kickoff_utc=first.kickoff_utc,
        observed_at=first.observed_at,
        home_team_id=first.home_team_id,
        away_team_id=TEAMS[5],
        home_goals=0,
        away_goals=0,
        neutral_venue=False,
    )
    with pytest.raises(ValueError):
        elo.apply_batch([first, duplicate])


def test_fit_davidson_abstains_below_minimum_sample():
    # Use a tiny observation list (5 matches) to trigger the default behavior
    observations = [(1500.0 + index, 1480.0 - index, index % 3) for index in range(5)]
    fit = fit_davidson(observations, minimum_matches=30)
    assert fit.status == "DEFAULT_NO_TRAINING_DATA"
    assert fit.matches_used == 0


def test_fit_davidson_is_deterministic_and_bounded():
    observations = [(1500.0 + index, 1480.0 - index, index % 3) for index in range(40)]
    first = fit_davidson(observations * 2)
    second = fit_davidson(observations * 2)
    assert first == second
    assert first.status == "FITTED"
    assert 0.0 <= first.home_advantage <= 200.0
    assert 0.05 <= first.draw_nu <= 3.0


def test_outcome_index_matches_football_convention():
    assert outcome_index(2, 1) == 0
    assert outcome_index(1, 1) == 1
    assert outcome_index(0, 1) == 2


# ------------------------------------------------------------------ model dispatch


def test_every_model_produces_identical_target_probabilities_shape():
    dataset = build_synthetic_dataset()
    features = _features(dataset)
    results = {}
    for key in allowed_model_keys():
        results[key] = compute_model_prediction(
            dataset,
            features,
            model_key=key,
            home_team_id=TEAMS[0],
            away_team_id=TEAMS[1],
            competition_id=COMPETITION_ID,
            kickoff_utc=REFERENCE_KICKOFF,
        )

    for key, result in results.items():
        assert result["status"] == PredictionStatus.READY
        assert result["model_id"] == MODEL_BY_KEY[key].model_id
        assert result["model_version"] == MODEL_BY_KEY[key].model_version
        assert result["requested_model"] == key
        total = (
            result["home_win_probability"]
            + result["draw_probability"]
            + result["away_win_probability"]
        )
        assert isclose(total, 1.0, abs_tol=1e-6)

    # Models must actually differ: identical output would mean one model is being
    # silently substituted for another.
    signatures = {
        (
            result["home_win_probability"],
            result["draw_probability"],
            result["away_win_probability"],
        )
        for result in results.values()
    }
    assert len(signatures) >= 2
    assert (
        results["poisson"]["home_win_probability"]
        != results["elo"]["home_win_probability"]
    )


def test_model_dispatch_is_deterministic():
    dataset = build_synthetic_dataset()
    features = _features(dataset)
    for key in allowed_model_keys():
        first = compute_model_prediction(
            dataset,
            features,
            model_key=key,
            home_team_id=TEAMS[0],
            away_team_id=TEAMS[1],
            competition_id=COMPETITION_ID,
            kickoff_utc=REFERENCE_KICKOFF,
        )
        second = compute_model_prediction(
            dataset,
            features,
            model_key=key,
            home_team_id=TEAMS[0],
            away_team_id=TEAMS[1],
            competition_id=COMPETITION_ID,
            kickoff_utc=REFERENCE_KICKOFF,
        )
        assert first == second


def test_elo_abstains_without_any_rated_team():
    empty = IntelligenceDataset(
        dataset_id="ds_empty",
        classification=DataClassification.SYNTHETIC_TEST,
        matches=(),
    )
    result = compute_model_prediction(
        empty,
        {},
        model_key="elo",
        home_team_id=TEAMS[0],
        away_team_id=TEAMS[1],
        competition_id=COMPETITION_ID,
        kickoff_utc=REFERENCE_KICKOFF,
    )
    assert result["status"] == PredictionStatus.INSUFFICIENT_DATA
    assert result["model_id"] == ELO_MODEL_ID
    assert "no_historical_ratings" in result["limitations"]


def test_elo_does_not_invent_expected_goals_or_scorelines():
    dataset = build_synthetic_dataset()
    result = compute_model_prediction(
        dataset,
        _features(dataset),
        model_key="elo",
        home_team_id=TEAMS[0],
        away_team_id=TEAMS[1],
        competition_id=COMPETITION_ID,
        kickoff_utc=REFERENCE_KICKOFF,
    )
    assert result["expected_home_goals"] is None
    assert result["expected_away_goals"] is None
    assert result["scoreline_probabilities"] == []
    assert result["btts_probability"] is None


def test_dataset_identity_is_attached_to_every_model_result():
    dataset = build_synthetic_dataset()
    features = _features(dataset)
    for key in allowed_model_keys():
        result = compute_model_prediction(
            dataset,
            features,
            model_key=key,
            home_team_id=TEAMS[0],
            away_team_id=TEAMS[1],
            competition_id=COMPETITION_ID,
            kickoff_utc=REFERENCE_KICKOFF,
        )
        assert result["dataset_id"] == dataset.dataset_id
        assert result["dataset_digest"] == dataset.digest


def test_reference_kickoff_is_after_all_training_matches():
    matches = build_synthetic_matches()
    assert all(match.kickoff_utc < REFERENCE_KICKOFF for match in matches)
    assert REFERENCE_KICKOFF - max(m.kickoff_utc for m in matches) == timedelta(days=7)
