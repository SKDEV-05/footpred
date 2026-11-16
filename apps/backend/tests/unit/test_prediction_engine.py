"""Unit tests for the statistical Poisson prediction engine and feature calculation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import log

import pytest

from app.intelligence.prediction import (
    EVALUATION_VERSION,
    MODEL_ID,
    MODEL_VERSION,
    PredictionStatus,
    calculate_match_features,
    compute_historical_backtest_evaluation,
    run_statistical_prediction,
)
from app.intelligence.types import (
    DataClassification,
    HistoricalMatch,
    IntelligenceDataset,
)

KICKOFF_BASE = datetime(2026, 11, 10, 15, 0, tzinfo=timezone.utc)


def _make_historical_match(
    match_id: str,
    home_team_id: str,
    away_team_id: str,
    home_goals: int,
    away_goals: int,
    kickoff: datetime,
    competition_id: str = "comp_1",
) -> HistoricalMatch:
    return HistoricalMatch(
        match_id=match_id,
        competition_id=competition_id,
        season_id="season_1",
        kickoff_utc=kickoff,
        observed_at=kickoff,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_goals=home_goals,
        away_goals=away_goals,
        neutral_venue=False,
    )


def test_insufficient_sample_size_returns_abstention():
    # Only 2 matches for team A and B (threshold is 5)
    matches = (
        _make_historical_match("1", "team_A", "team_B", 2, 1, KICKOFF_BASE),
        _make_historical_match("2", "team_B", "team_A", 0, 0, KICKOFF_BASE),
    )
    dataset = IntelligenceDataset(
        dataset_id="ds_test",
        classification=DataClassification.SYNTHETIC_TEST,
        matches=matches,
    )

    features = calculate_match_features(
        dataset,
        home_team_id="team_A",
        away_team_id="team_B",
        competition_id="comp_1",
    )
    assert features["home_team"]["sample_size"] == 2
    assert features["away_team"]["sample_size"] == 2
    assert features["statistics_available"] is False
    assert features["statistics_unavailable_on_plan"] is True

    result = run_statistical_prediction(
        dataset,
        features,
        home_team_id="team_A",
        away_team_id="team_B",
        competition_id="comp_1",
    )
    assert result["status"] == PredictionStatus.INSUFFICIENT_DATA
    assert "Insufficient sample size" in result["reason"]


def test_poisson_prediction_probabilities_sum_to_one():
    # Build 10 matches for each team
    matches = []
    for i in range(1, 11):
        dt = datetime(2026, 10, i, 15, 0, tzinfo=timezone.utc)
        matches.append(_make_historical_match(f"h_{i}", "team_A", f"opp_{i}", 2, 1, dt))
        matches.append(_make_historical_match(f"a_{i}", f"opp_{i}", "team_B", 1, 2, dt))

    dataset = IntelligenceDataset(
        dataset_id="ds_test_full",
        classification=DataClassification.SYNTHETIC_TEST,
        matches=tuple(matches),
    )

    features = calculate_match_features(
        dataset,
        home_team_id="team_A",
        away_team_id="team_B",
        competition_id="comp_1",
    )
    assert features["home_team"]["sample_size"] == 10
    assert features["away_team"]["sample_size"] == 10

    result = run_statistical_prediction(
        dataset,
        features,
        home_team_id="team_A",
        away_team_id="team_B",
        competition_id="comp_1",
    )

    assert result["status"] == PredictionStatus.READY
    assert result["model_id"] == MODEL_ID
    assert result["model_version"] == MODEL_VERSION

    # Check that 1X2 probabilities strictly sum to 1.0
    p_home = result["home_win_probability"]
    p_draw = result["draw_probability"]
    p_away = result["away_win_probability"]
    assert 0.0 <= p_home <= 1.0
    assert 0.0 <= p_draw <= 1.0
    assert 0.0 <= p_away <= 1.0
    assert abs((p_home + p_draw + p_away) - 1.0) < 1e-3

    # Check expected goals are positive and realistic
    assert 0.20 <= result["expected_home_goals"] <= 5.0
    assert 0.20 <= result["expected_away_goals"] <= 5.0

    # Check secondary markets
    assert 0.0 <= result["btts_probability"] <= 1.0
    assert 0.0 <= result["over_2_5_probability"] <= 1.0
    assert abs(result["over_2_5_probability"] + result["under_2_5_probability"] - 1.0) < 1e-3

    # Check top scorelines
    scorelines = result["scoreline_probabilities"]
    assert len(scorelines) == 5
    for item in scorelines:
        assert item["home_goals"] >= 0
        assert item["away_goals"] >= 0
        assert 0.0 <= item["probability"] <= 1.0
    # Probabilities should be sorted in descending order
    assert all(
        scorelines[i]["probability"] >= scorelines[i + 1]["probability"]
        for i in range(len(scorelines) - 1)
    )


def _synthetic_competition_dataset(match_count: int = 120) -> IntelligenceDataset:
    """Build a deterministic synthetic league with stable rotation of four teams."""

    teams = ("team_A", "team_B", "team_C", "team_D")
    matches = []
    for index in range(match_count):
        kickoff = datetime(2026, 1, 1, 15, 0, tzinfo=timezone.utc) + timedelta(days=index)
        home = teams[index % 4]
        away = teams[(index + 1) % 4]
        # Vary scores deterministically so all three outcomes occur.
        matches.append(
            _make_historical_match(
                f"m_{index}",
                home,
                away,
                (index * 7) % 4,
                (index * 3) % 4,
                kickoff,
            )
        )
    return IntelligenceDataset(
        dataset_id="ds_backtest_synthetic",
        classification=DataClassification.SYNTHETIC_TEST,
        matches=tuple(matches),
    )


def test_prediction_is_deterministic():
    dataset = _synthetic_competition_dataset(40)
    features = calculate_match_features(
        dataset,
        home_team_id="team_A",
        away_team_id="team_B",
        competition_id="comp_1",
    )

    first = run_statistical_prediction(
        dataset,
        features,
        home_team_id="team_A",
        away_team_id="team_B",
        competition_id="comp_1",
    )
    second = run_statistical_prediction(
        dataset,
        features,
        home_team_id="team_A",
        away_team_id="team_B",
        competition_id="comp_1",
    )

    assert first["status"] == PredictionStatus.READY
    for key in (
        "expected_home_goals",
        "expected_away_goals",
        "home_win_probability",
        "draw_probability",
        "away_win_probability",
        "btts_probability",
        "over_2_5_probability",
        "scoreline_probabilities",
        "model_parameters",
    ):
        assert first[key] == second[key]


def test_probabilities_sum_exactly_to_one():
    dataset = _synthetic_competition_dataset(40)
    features = calculate_match_features(
        dataset,
        home_team_id="team_C",
        away_team_id="team_D",
        competition_id="comp_1",
    )
    result = run_statistical_prediction(
        dataset,
        features,
        home_team_id="team_C",
        away_team_id="team_D",
        competition_id="comp_1",
    )

    total = (
        result["home_win_probability"]
        + result["draw_probability"]
        + result["away_win_probability"]
    )
    # The engine normalises and derives the third probability, so this is exact.
    assert total == 1.0


def test_backtest_reports_calibration_and_uniform_baselines():
    dataset = _synthetic_competition_dataset(120)
    evaluation = compute_historical_backtest_evaluation(
        dataset, competition_id="comp_1"
    )

    assert evaluation["evaluated"] is True
    assert evaluation["sample_size"] >= 10
    assert evaluation["class_labels"] == ["home", "draw", "away"]
    assert 0.0 <= evaluation["brier_score"] <= 2.0
    assert evaluation["log_loss"] >= 0.0
    assert evaluation["uniform_brier_score"] == round(2.0 / 3.0, 4)
    assert evaluation["uniform_log_loss"] == round(log(3.0), 4)
    # Skill is computed from the unrounded Brier, so allow rounding tolerance here.
    expected_skill = 1.0 - evaluation["brier_score"] / evaluation["uniform_brier_score"]
    assert abs(evaluation["brier_skill_score"] - expected_skill) < 1e-3
    assert evaluation["evaluation_version"] == EVALUATION_VERSION

    calibration = evaluation["calibration"]
    assert {item["class_label"] for item in calibration} == {"home", "draw", "away"}
    assert all(item["expected_calibration_error"] is not None for item in calibration)
    assert any(item["bins"] for item in calibration)
    total_bins = sum(len(item["bins"]) for item in calibration)
    # Every bin must carry a real sample, never a placeholder.
    assert all(bin["sample_size"] > 0 for item in calibration for bin in item["bins"])
    assert total_bins >= 3


def test_backtest_abstains_when_competition_history_is_thin():
    dataset = _synthetic_competition_dataset(20)
    evaluation = compute_historical_backtest_evaluation(
        dataset, competition_id="comp_1"
    )

    assert evaluation["evaluated"] is False
    assert evaluation["reason"] == "insufficient_competition_matches_for_backtest"
    assert evaluation["sample_size"] == 20
    assert "brier_score" not in evaluation
    assert "calibration" not in evaluation


def test_rate_estimation_reports_missing_rates_as_none_not_zero():
    dataset = _synthetic_competition_dataset(40)
    features = calculate_match_features(
        dataset,
        home_team_id="team_A",
        away_team_id="team_B",
        competition_id="comp_1",
    )
    # Every synthetic team has played, so rates are observed numbers.
    assert features["home_team"]["overall"]["win_rate"] is not None
    assert features["home_team"]["overall"]["goals_for_avg"] is not None

    # An unseen team must report absence, not a zero rate.
    unseen = calculate_match_features(
        dataset,
        home_team_id="team_UNSEEN",
        away_team_id="team_B",
        competition_id="comp_1",
    )
    assert unseen["home_team"]["overall"]["played"] == 0
    assert unseen["home_team"]["overall"]["win_rate"] is None
    assert unseen["home_team"]["overall"]["goals_for_avg"] is None
    assert unseen["home_team"]["recent_goals_for_avg"] is None
