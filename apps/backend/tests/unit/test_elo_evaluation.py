"""Synthetic-only tests for Elo and evaluation mechanics."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isinf

import pytest

from app.intelligence.evaluation import (
    TemporalObservation,
    binary_brier_score,
    binary_log_loss,
    multiclass_brier_score,
    multiclass_log_loss,
    multiclass_reliability,
    reliability_bins,
    rolling_origin_folds,
    temporal_partition,
)
from app.intelligence.models.elo import EloConfig, EloResult, EloState
from app.intelligence.types import DataClassification, ResearchContext

UTC = timezone.utc
BASE = datetime(2026, 1, 1, tzinfo=UTC)
CONTEXT = ResearchContext(DataClassification.SYNTHETIC_TEST, "2" * 64, "test-v1")


def result(match_id: str, home: str, away: str, home_goals: int, away_goals: int, days: int) -> EloResult:
    kickoff = BASE + timedelta(days=days)
    return EloResult(match_id, kickoff, kickoff + timedelta(hours=3), home, away, home_goals, away_goals, False)


def test_elo_neutral_symmetry_and_home_offset() -> None:
    state = EloState(context=CONTEXT, config=EloConfig(home_advantage=100))
    neutral = state.expected_home_score(1500, 1500, neutral_venue=True)
    home = state.expected_home_score(1500, 1500, neutral_venue=False)
    reverse = state.expected_home_score(1500, 1600, neutral_venue=True)
    assert neutral == pytest.approx(0.5)
    assert home > neutral
    assert reverse == pytest.approx(1 - state.expected_home_score(1600, 1500, neutral_venue=True))


def test_elo_updates_are_zero_sum_and_deterministic() -> None:
    state = EloState(context=CONTEXT, config=EloConfig(k_factor=20, home_advantage=0))
    snapshot = state.replay((result("m1", "A", "B", 1, 0, 0),), as_of=BASE + timedelta(days=2))
    assert snapshot.rating_for("A") == pytest.approx(1510)
    assert snapshot.rating_for("B") == pytest.approx(1490)
    assert snapshot.context is CONTEXT


def test_elo_same_kickoff_uses_one_pre_batch_state() -> None:
    state = EloState(context=CONTEXT, config=EloConfig(k_factor=20))
    snapshot = state.replay(
        (result("m2", "C", "D", 0, 1, 0), result("m1", "A", "B", 1, 0, 0)),
        as_of=BASE + timedelta(days=1),
    )
    assert snapshot.rating_for("A") == pytest.approx(1510)
    assert snapshot.rating_for("C") == pytest.approx(1490)


def test_elo_excludes_result_observed_at_or_after_cutoff() -> None:
    exact = EloResult("m1", BASE, BASE + timedelta(days=2), "A", "B", 1, 0, False)
    state = EloState(context=CONTEXT)
    assert state.replay((exact,), as_of=BASE + timedelta(days=2)).ratings == ()


def test_elo_rejects_duplicate_ids_even_when_ineligible() -> None:
    one = result("same", "A", "B", 1, 0, 0)
    two = result("same", "C", "D", 1, 0, 5)
    with pytest.raises(ValueError, match="duplicate"):
        EloState(context=CONTEXT).replay((one, two), as_of=BASE + timedelta(days=2))


def test_binary_scoring_reference_values_and_boundaries() -> None:
    probabilities = (0.8, 0.3)
    outcomes = (1, 0)
    assert binary_brier_score(probabilities, outcomes, context=CONTEXT).value == pytest.approx(0.065)
    assert binary_log_loss(probabilities, outcomes, context=CONTEXT).value == pytest.approx(0.2899092476264711)
    assert isinf(binary_log_loss((0.0,), (1,), context=CONTEXT).value)


def test_multiclass_scores_use_named_unnormalized_convention() -> None:
    labels = ("home", "draw", "away")
    brier = multiclass_brier_score(((0.7, 0.2, 0.1),), (0,), class_labels=labels, context=CONTEXT)
    loss = multiclass_log_loss(((0.7, 0.2, 0.1),), (0,), class_labels=labels, context=CONTEXT)
    assert brier.value == pytest.approx(0.14)
    assert loss.value == pytest.approx(-__import__("math").log(0.7))
    assert brier.class_labels == labels


def test_reliability_summary_preserves_empty_bins_and_gaps() -> None:
    summary = reliability_bins(
        (0.0, 0.19, 0.2, 1.0),
        (0, 1, 1, 1),
        context=CONTEXT,
        class_label="yes",
        bin_count=5,
    )
    assert summary.bins[0].sample_size == 2
    assert summary.bins[2].mean_probability is None
    assert summary.expected_calibration_error is not None


def test_multiclass_reliability_is_one_vs_rest_for_each_named_class() -> None:
    summaries = multiclass_reliability(
        ((0.7, 0.2, 0.1), (0.1, 0.2, 0.7)),
        (0, 2),
        class_labels=("home", "draw", "away"),
        context=CONTEXT,
        bin_count=2,
    )
    assert tuple(summary.class_label for summary in summaries) == ("home", "draw", "away")


def observations(count: int) -> tuple[TemporalObservation, ...]:
    return tuple(
        TemporalObservation(f"o{i}", BASE + timedelta(days=i), BASE + timedelta(days=i, hours=1))
        for i in range(count)
    )


def test_rolling_origin_folds_are_non_overlapping_and_chronological() -> None:
    folds = rolling_origin_folds(
        observations(7),
        minimum_train_size=3,
        validation_size=2,
        step=2,
        context=CONTEXT,
    )
    assert folds[0].validation_ids == ("o3", "o4")
    assert folds[1].validation_ids == ("o5", "o6")
    assert set(folds[0].validation_ids).isdisjoint(folds[1].validation_ids)


def test_rolling_origin_rejects_overlap_and_delayed_training_label() -> None:
    with pytest.raises(ValueError, match="overlap"):
        rolling_origin_folds(observations(6), minimum_train_size=3, validation_size=2, step=1, context=CONTEXT)
    delayed = (
        TemporalObservation("a", BASE, BASE + timedelta(days=5)),
        TemporalObservation("b", BASE + timedelta(days=1), BASE + timedelta(days=1, hours=1)),
    )
    with pytest.raises(ValueError, match="not available"):
        rolling_origin_folds(delayed, minimum_train_size=1, validation_size=1, context=CONTEXT)


def test_temporal_partition_separates_calibration_test_and_holdout() -> None:
    partition = temporal_partition(
        observations(8),
        train_size=2,
        calibration_size=2,
        test_size=2,
        holdout_size=2,
        context=CONTEXT,
    )
    assert partition.train_ids == ("o0", "o1")
    assert partition.calibration_ids == ("o2", "o3")
    assert partition.test_ids == ("o4", "o5")
    assert partition.final_holdout_ids == ("o6", "o7")
