"""Synthetic-only tests for descriptive intelligence contracts."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.intelligence.engine import IntelligenceEngine
from app.intelligence.metrics import calculate_head_to_head, calculate_team_form
from app.intelligence.quality import Coverage, CoveragePolicy, assess_sample
from app.intelligence.types import (
    DataClassification,
    HistoricalMatch,
    IntelligenceDataset,
    MatchRequest,
    PointsPolicy,
    ResearchContext,
    Venue,
)

UTC = timezone.utc
BASE = datetime(2026, 1, 1, 15, tzinfo=UTC)
POINTS = PointsPolicy("synthetic-standard-3-1-0", 3, 1, 0)
CONTEXT = ResearchContext(DataClassification.SYNTHETIC_TEST, "0" * 64, "test-v1")


def match(
    number: int,
    home: str,
    away: str,
    home_goals: int,
    away_goals: int,
    *,
    days: int,
    observed_delay: timedelta = timedelta(hours=3),
    competition: str = "synthetic-league",
    neutral: bool = False,
) -> HistoricalMatch:
    kickoff = BASE + timedelta(days=days)
    return HistoricalMatch(
        match_id=f"synthetic-{number}",
        competition_id=competition,
        season_id="synthetic-season",
        kickoff_utc=kickoff,
        observed_at=kickoff + observed_delay,
        home_team_id=home,
        away_team_id=away,
        home_goals=home_goals,
        away_goals=away_goals,
        neutral_venue=neutral,
    )


def test_team_form_calculates_exact_synthetic_reference_values() -> None:
    history = (
        match(1, "A", "B", 2, 1, days=0),
        match(2, "C", "A", 0, 0, days=1),
        match(3, "A", "D", 1, 3, days=2),
    )
    form = calculate_team_form(
        history,
        team_id="A",
        as_of=BASE + timedelta(days=4),
        window=3,
        venue=Venue.OVERALL,
        points_policy=POINTS,
        context=CONTEXT,
    )
    assert (form.wins, form.draws, form.losses) == (1, 1, 1)
    assert (form.goals_for, form.goals_against, form.goal_difference) == (3, 4, -1)
    assert form.points_per_match == pytest.approx(4 / 3)
    assert form.clean_sheet_rate == pytest.approx(1 / 3)
    assert form.failed_to_score_rate == pytest.approx(1 / 3)


def test_team_form_separates_listed_venue_and_neutral_matches() -> None:
    history = (
        match(1, "A", "B", 1, 0, days=0),
        match(2, "C", "A", 0, 2, days=1),
        match(3, "A", "D", 4, 4, days=2, neutral=True),
    )
    as_of = BASE + timedelta(days=4)
    home = calculate_team_form(
        history, team_id="A", as_of=as_of, window=10, venue=Venue.HOME, points_policy=POINTS, context=CONTEXT
    )
    away = calculate_team_form(
        history, team_id="A", as_of=as_of, window=10, venue=Venue.AWAY, points_policy=POINTS, context=CONTEXT
    )
    neutral = calculate_team_form(
        history, team_id="A", as_of=as_of, window=10, venue=Venue.NEUTRAL, points_policy=POINTS, context=CONTEXT
    )
    assert home.match_ids == ("synthetic-1",)
    assert away.match_ids == ("synthetic-2",)
    assert neutral.match_ids == ("synthetic-3",)


def test_result_not_known_at_cutoff_is_excluded_even_when_match_is_earlier() -> None:
    late = match(
        1,
        "A",
        "B",
        9,
        0,
        days=0,
        observed_delay=timedelta(days=10),
    )
    form = calculate_team_form(
        (late,),
        team_id="A",
        as_of=BASE + timedelta(days=2),
        window=5,
        points_policy=POINTS,
        context=CONTEXT,
    )
    assert form.sample_size == 0
    assert form.goals_for_per_match is None


def test_future_match_cannot_change_point_in_time_form() -> None:
    past = match(1, "A", "B", 1, 0, days=0)
    future = match(2, "A", "C", 20, 0, days=20)
    cutoff = BASE + timedelta(days=2)
    before = calculate_team_form(
        (past,), team_id="A", as_of=cutoff, window=5, points_policy=POINTS, context=CONTEXT
    )
    after = calculate_team_form(
        (past, future), team_id="A", as_of=cutoff, window=5, points_policy=POINTS, context=CONTEXT
    )
    assert before == after


def test_head_to_head_normalizes_historical_orientation() -> None:
    history = (
        match(1, "A", "B", 2, 0, days=0),
        match(2, "B", "A", 3, 1, days=1),
        match(3, "A", "C", 8, 8, days=2),
    )
    result = calculate_head_to_head(
        history,
        home_team_id="A",
        away_team_id="B",
        as_of=BASE + timedelta(days=4),
        window=5,
        context=CONTEXT,
    )
    assert result.sample_size == 2
    assert (result.home_wins, result.draws, result.away_wins) == (1, 0, 1)
    assert (result.home_goals, result.away_goals) == (3, 3)


def test_empty_history_is_missing_not_zero() -> None:
    form = calculate_team_form(
        (),
        team_id="A",
        as_of=BASE,
        window=5,
        points_policy=POINTS,
        context=CONTEXT,
    )
    assert form.sample_size == 0
    assert form.goals_for == 0
    assert form.goals_for_per_match is None
    assert form.scoring_rate is None


def test_quality_thresholds_are_explicit_and_boundary_correct() -> None:
    policy = CoveragePolicy("synthetic-policy", 5, 10, 20)
    assert assess_sample(4, policy, context=CONTEXT).coverage is Coverage.INSUFFICIENT
    assert assess_sample(5, policy, context=CONTEXT).coverage is Coverage.LOW
    assert assess_sample(10, policy, context=CONTEXT).coverage is Coverage.MODERATE
    assert assess_sample(20, policy, context=CONTEXT).coverage is Coverage.HIGH


def test_dataset_digest_is_order_independent_and_changes_with_input() -> None:
    first = match(1, "A", "B", 1, 0, days=0)
    second = match(2, "C", "D", 2, 2, days=1)
    left = IntelligenceDataset("synthetic-set", DataClassification.SYNTHETIC_TEST, (first, second))
    right = IntelligenceDataset("synthetic-set", DataClassification.SYNTHETIC_TEST, (second, first))
    changed = IntelligenceDataset(
        "synthetic-set",
        DataClassification.SYNTHETIC_TEST,
        (first, match(2, "C", "D", 3, 2, days=1)),
    )
    assert left.digest == right.digest
    assert left.digest != changed.digest


def test_engine_produces_reproducible_report_and_abstains_on_thin_sample() -> None:
    dataset = IntelligenceDataset(
        "synthetic-set",
        DataClassification.SYNTHETIC_TEST,
        (
            match(1, "A", "C", 1, 0, days=0),
            match(2, "D", "B", 0, 1, days=1),
        ),
    )
    request = MatchRequest(
        match_id="synthetic-target",
        competition_id="synthetic-league",
        season_id="synthetic-season",
        kickoff_utc=BASE + timedelta(days=10),
        home_team_id="A",
        away_team_id="B",
        neutral_venue=False,
        as_of=BASE + timedelta(days=9),
    )
    engine = IntelligenceEngine(
        coverage_policy=CoveragePolicy("synthetic-policy", 2, 3, 4),
        points_policy=POINTS,
    )
    report = engine.analyze(
        request,
        dataset,
        generated_at=request.as_of,
        form_window=5,
    )
    assert report.input_digest == dataset.digest
    assert not report.eligible_for_research_calculation
    assert "insufficient_venue_specific_history" in report.limitations
    assert engine.analyze(
        request,
        dataset,
        generated_at=request.as_of,
        form_window=5,
    ) == report


def test_historical_match_rejects_ambiguous_or_invalid_values() -> None:
    with pytest.raises(ValueError, match="before kickoff"):
        HistoricalMatch(
            "x", "c", "s", BASE, BASE - timedelta(seconds=1), "A", "B", 0, 0, False
        )
    with pytest.raises(ValueError, match="half-time"):
        HistoricalMatch(
            "x", "c", "s", BASE, BASE, "A", "B", 1, 0, False, 2, 0
        )
    with pytest.raises(ValueError, match="integers"):
        HistoricalMatch("x", "c", "s", BASE, BASE, "A", "B", True, 0, False)
    with pytest.raises(ValueError, match="finite"):
        HistoricalMatch(
            "x", "c", "s", BASE, BASE, "A", "B", 0, 0, False, metrics={"xg": float("nan")}
        )


def test_observation_at_cutoff_is_strictly_excluded() -> None:
    observed_at_cutoff = match(1, "A", "B", 1, 0, days=0, observed_delay=timedelta(days=1))
    form = calculate_team_form(
        (observed_at_cutoff,),
        team_id="A",
        as_of=BASE + timedelta(days=1),
        window=5,
        points_policy=POINTS,
        context=CONTEXT,
    )
    assert form.sample_size == 0


def test_research_context_rejects_unclassified_value() -> None:
    with pytest.raises(ValueError, match="DataClassification"):
        ResearchContext("synthetic_test_data", "0" * 64, "test-v1")  # type: ignore[arg-type]


def test_report_records_request_and_policy_values_for_reproduction() -> None:
    dataset = IntelligenceDataset(
        "synthetic-set",
        DataClassification.SYNTHETIC_TEST,
        (match(1, "A", "C", 1, 0, days=0),),
    )
    request = MatchRequest(
        match_id="synthetic-target",
        competition_id="synthetic-league",
        season_id="synthetic-season",
        kickoff_utc=BASE + timedelta(days=10),
        home_team_id="A",
        away_team_id="B",
        neutral_venue=True,
        as_of=BASE + timedelta(days=9),
    )
    engine = IntelligenceEngine(
        coverage_policy=CoveragePolicy("synthetic-policy", 2, 3, 4),
        points_policy=POINTS,
    )
    report = engine.analyze(
        request,
        dataset,
        generated_at=request.as_of,
        form_window=4,
        h2h_window=2,
    )
    assert report.configuration.kickoff_utc == request.kickoff_utc
    assert report.configuration.season_id == "synthetic-season"
    assert report.configuration.neutral_venue is True
    assert report.configuration.form_window == 4
    assert report.configuration.h2h_window == 2
    assert report.configuration.points_policy == POINTS
    assert report.config_digest == report.configuration.digest
    assert report.data_classification is DataClassification.SYNTHETIC_TEST


def test_config_digest_changes_when_policy_values_change_under_same_id() -> None:
    dataset = IntelligenceDataset(
        "synthetic-set",
        DataClassification.SYNTHETIC_TEST,
        (match(1, "A", "C", 1, 0, days=0),),
    )
    request = MatchRequest(
        match_id="synthetic-target",
        competition_id="synthetic-league",
        season_id="synthetic-season",
        kickoff_utc=BASE + timedelta(days=10),
        home_team_id="A",
        away_team_id="B",
        neutral_venue=False,
        as_of=BASE + timedelta(days=9),
    )
    coverage = CoveragePolicy("synthetic-policy", 2, 3, 4)
    first = IntelligenceEngine(
        coverage_policy=coverage,
        points_policy=PointsPolicy("same-id", 3, 1, 0),
    ).analyze(request, dataset, generated_at=request.as_of)
    second = IntelligenceEngine(
        coverage_policy=coverage,
        points_policy=PointsPolicy("same-id", 2, 1, 0),
    ).analyze(request, dataset, generated_at=request.as_of)
    assert first.input_digest == second.input_digest
    assert first.config_digest != second.config_digest


def test_target_fixture_cannot_contribute_to_its_own_history() -> None:
    target = match(1, "A", "B", 1, 0, days=0)
    dataset = IntelligenceDataset(
        "synthetic-set",
        DataClassification.SYNTHETIC_TEST,
        (target,),
    )
    request = MatchRequest(
        match_id="synthetic-1",
        competition_id="synthetic-league",
        season_id="synthetic-season",
        kickoff_utc=BASE + timedelta(days=10),
        home_team_id="A",
        away_team_id="B",
        neutral_venue=False,
        as_of=BASE + timedelta(days=9),
    )
    with pytest.raises(ValueError, match="target fixture"):
        IntelligenceEngine(
            coverage_policy=CoveragePolicy("synthetic-policy", 1, 2, 3),
            points_policy=POINTS,
        ).analyze(request, dataset, generated_at=request.as_of)


def test_every_feature_source_is_strictly_before_the_cutoff() -> None:
    dataset = IntelligenceDataset(
        "synthetic-set",
        DataClassification.SYNTHETIC_TEST,
        (
            match(1, "A", "C", 1, 0, days=0),
            match(2, "D", "B", 0, 2, days=1),
            match(3, "C", "D", 1, 1, days=2),
        ),
    )
    request = MatchRequest(
        match_id="synthetic-target",
        competition_id="synthetic-league",
        season_id="synthetic-season",
        kickoff_utc=BASE + timedelta(days=10),
        home_team_id="A",
        away_team_id="B",
        neutral_venue=False,
        as_of=BASE + timedelta(days=9),
    )
    report = IntelligenceEngine(
        coverage_policy=CoveragePolicy("synthetic-policy", 1, 2, 3),
        points_policy=POINTS,
    ).analyze(request, dataset, generated_at=request.as_of)
    history = {item.match_id: item for item in dataset.matches}
    for feature in report.features:
        assert feature.window_end_utc == request.as_of
        if feature.available_at_utc is not None:
            assert feature.available_at_utc < request.as_of
        for source_id in feature.source_match_ids:
            source = history[source_id]
            assert source.kickoff_utc < request.as_of
            assert source.observed_at < request.as_of
