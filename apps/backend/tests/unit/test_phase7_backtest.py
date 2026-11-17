"""Phase 7 evaluation-engine tests.

The evaluation is the evidence base for every model claim, so these tests pin the
properties that make it trustworthy: chronological ordering, an identical target set
across models, an explicit result horizon, deterministic bootstrap intervals, and
structured per-competition/season/outcome/timeline output.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isclose

import pytest

from app.intelligence.backtest import (
    BACKTEST_EVALUATION_VERSION,
    BACKTEST_PROTOCOL_VERSION,
    MATCH_HORIZON,
    MODEL_KEYS,
    PredictionRow,
    evaluate_rows,
    paired_comparison,
    result_is_available,
    run_multi_competition_backtest,
)
from app.intelligence.types import (
    DataClassification,
    IntelligenceDataset,
)
from tests.phase7_support import build_synthetic_dataset, build_synthetic_matches

KICKOFF = datetime(2026, 1, 10, 15, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module")
def report():
    dataset = build_synthetic_dataset()
    return run_multi_competition_backtest(dataset, bootstrap_resamples=50)


def _row(match_id: str, *, home: float, draw: float, away: float, outcome: int):
    return PredictionRow(
        model_key="test",
        match_id=match_id,
        competition_id="comp",
        season_id="season",
        kickoff_utc=KICKOFF,
        home=home,
        draw=draw,
        away=away,
        outcome=outcome,
    )


# ------------------------------------------------------------------- result horizon


def test_result_becomes_available_after_the_horizon():
    assert result_is_available(KICKOFF, KICKOFF + MATCH_HORIZON)
    assert result_is_available(KICKOFF, KICKOFF + MATCH_HORIZON + timedelta(seconds=1))
    assert not result_is_available(
        KICKOFF, KICKOFF + MATCH_HORIZON - timedelta(seconds=1)
    )


def test_simultaneous_kickoff_is_never_usable_for_itself():
    assert not result_is_available(KICKOFF, KICKOFF)
    assert not result_is_available(KICKOFF, KICKOFF + timedelta(hours=2))


def test_result_horizon_rejects_naive_times_and_negative_horizon():
    with pytest.raises(ValueError):
        result_is_available(datetime(2026, 1, 10, 15, 0), KICKOFF)
    with pytest.raises(ValueError):
        result_is_available(KICKOFF, KICKOFF, horizon=timedelta(hours=-1))


# -------------------------------------------------------------- insufficient data


def test_empty_dataset_evaluates_to_an_explicit_abstention():
    dataset = IntelligenceDataset(
        dataset_id="ds_empty",
        classification=DataClassification.SYNTHETIC_TEST,
        matches=(),
    )
    result = run_multi_competition_backtest(dataset, bootstrap_resamples=10)
    assert result["evaluated"] is False
    assert result["reason"] == "no_historical_matches"
    assert result["models"] == []


def test_competition_below_the_minimum_is_reported_not_scored():
    dataset = build_synthetic_dataset(rounds=4)  # 16 matches, below the 50 minimum
    result = run_multi_competition_backtest(dataset, bootstrap_resamples=10)
    assert result["evaluated"] is False
    assert result["reason"] == "no_competition_has_sufficient_history"
    assert len(result["competitions"]) == 1
    entry = result["competitions"][0]
    assert entry["status"] == "INSUFFICIENT_DATA"
    assert entry["sample_size"] == 16
    assert entry["required"] == 50


def test_evaluate_rows_abstains_without_predictions():
    dataset = build_synthetic_dataset()
    context = dataset.research_context(protocol_version="phase7-test")
    result = evaluate_rows([], context=context)
    assert result["evaluated"] is False
    assert result["sample_size"] == 0
    assert result["reason"] == "no_evaluated_matches"


# --------------------------------------------------------------- evaluation output


def test_all_models_and_baselines_are_scored_on_the_same_matches(report):
    assert report["evaluated"] is True
    assert [model["key"] for model in report["models"]] == list(MODEL_KEYS)
    sizes = {model["sample_size"] for model in report["models"]}
    assert len(sizes) == 1
    assert report["sample_size"] == sizes.pop()
    assert report["sample_size"] > 0


def test_models_carry_their_own_identity(report):
    by_key = {model["key"]: model for model in report["models"]}
    assert by_key["poisson"]["model_version"] == "poisson-v1.1.0"
    assert by_key["dixon_coles"]["model_version"] == "dixon-coles-v1.0.0"
    assert by_key["elo"]["model_version"] == "elo-v1.0.0"
    assert by_key["uniform"]["role"] == "baseline"
    assert by_key["competition_frequency"]["role"] == "baseline"


def test_report_records_protocol_versions_and_the_retrospective_horizon(report):
    assert report["protocol_version"] == BACKTEST_PROTOCOL_VERSION
    assert report["evaluation_version"] == BACKTEST_EVALUATION_VERSION
    settings = report["settings"]
    assert settings["result_horizon_hours"] == 3.0
    assert settings["bootstrap_resamples"] == 50
    assert settings["bootstrap_seed"] == 20_261_116
    assert "random" not in report["settings"]
    assert any("horizon" in note for note in report["notes"])


def test_report_contains_per_competition_season_outcome_and_timeline_blocks(report):
    assert len(report["competitions"]) == 1
    competition = report["competitions"][0]
    assert competition["status"] == "EVALUATED"
    assert competition["sample_size"] == report["sample_size"]
    assert set(competition["models"]) == set(MODEL_KEYS)

    assert len(report["seasons"]) == 1
    season = report["seasons"][0]
    assert set(season["models"]) == set(MODEL_KEYS)

    poisson = next(model for model in report["models"] if model["key"] == "poisson")
    assert set(poisson["per_outcome"]) == {"home", "draw", "away"}
    for block in poisson["per_outcome"].values():
        assert block["sample_size"] == report["sample_size"]
        assert 0.0 <= block["observed_rate"] <= 1.0

    assert len(report["timeline"]) == 1
    timeline = report["timeline"][0]
    assert timeline["sample_size"] == report["sample_size"]
    assert set(timeline["models"]) == set(MODEL_KEYS)


def test_probability_calibration_blocks_are_present(report):
    for model in report["models"]:
        calibration = model["calibration"]
        assert [block["class_label"] for block in calibration] == [
            "home",
            "draw",
            "away",
        ]
        for block in calibration:
            assert block["sample_size"] > 0


def test_bootstrap_intervals_are_ordered_and_seeded(report):
    for model in report["models"]:
        brier_ci = model["bootstrap"]["brier_ci"]
        assert brier_ci is not None
        assert brier_ci["lower"] <= brier_ci["mean"] <= brier_ci["upper"]
        assert isclose(brier_ci["mean"], model["brier_score"], abs_tol=1e-4)


def test_evaluation_is_deterministic():
    dataset = build_synthetic_dataset()
    first = run_multi_competition_backtest(dataset, bootstrap_resamples=40)
    second = run_multi_competition_backtest(dataset, bootstrap_resamples=40)
    # The dataset (including its evidence window) is fixed, so identical input must give the
    # exact same document, including bootstrap intervals.
    assert first == second


def test_dataset_identity_is_reported(report):
    dataset = report["dataset"]
    assert dataset["dataset_id"] == "ds_phase7_synthetic"
    assert dataset["classification"] == DataClassification.SYNTHETIC_TEST.value
    assert dataset["matches"] == len(build_synthetic_matches())
    assert dataset["competitions"] == 1
    assert dataset["provider_code"] is None


# ---------------------------------------------------------------- paired comparison


def test_paired_comparison_requires_the_same_matches():
    reference = [_row("a", home=0.5, draw=0.3, away=0.2, outcome=0)]
    longer = [
        _row("a", home=0.5, draw=0.3, away=0.2, outcome=0),
        _row("b", home=0.4, draw=0.3, away=0.3, outcome=1),
    ]
    assert paired_comparison(reference, longer)["reason"] == "unpaired_or_empty_sample"

    mismatched = [_row("b", home=0.5, draw=0.3, away=0.2, outcome=0)]
    assert paired_comparison(reference, mismatched)["reason"] == "row_mismatch"


def test_paired_comparison_reports_a_signed_difference(report):
    comparisons = {item["candidate"]: item for item in report["comparisons"]}
    assert set(comparisons) == {
        "dixon_coles",
        "elo",
        "uniform",
        "competition_frequency",
    }
    for item in comparisons.values():
        assert item["evaluated"] is True
        assert item["reference"] == "poisson"
        assert item["sample_size"] == report["sample_size"]
        interval = item["brier_difference"]
        assert interval["lower"] <= interval["mean"] <= interval["upper"]
