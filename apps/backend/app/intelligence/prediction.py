"""Transparent statistical prediction engine for real football matches.

The model is a competition-baselined independent Poisson goal model. Attacking and
defensive strengths are estimated only from results that were both played and observed
before the target kickoff; recent form shrinks towards the longer-run rate. The same
estimation function is used by the live analysis and by the rolling-origin backtest, so
reported evaluation metrics describe the model that produced the report.

No probability is hardcoded. Every number below is derived from stored, verified results
or from an explicitly labelled prior used only when the sample is too small to estimate
a baseline.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from math import isfinite, log
from typing import Any, Sequence

from app.intelligence.evaluation import (
    multiclass_brier_score,
    multiclass_log_loss,
    multiclass_reliability,
)
from app.intelligence.models.poisson import ScoreMatrix, poisson_score_matrix
from app.intelligence.probabilities import (
    both_teams_to_score,
    match_outcomes,
    over_probability,
    top_scorelines,
)
from app.intelligence.types import (
    HistoricalMatch,
    IntelligenceDataset,
    ResearchContext,
)

MODEL_ID = "poisson_baseline"
MODEL_VERSION = "poisson-v1.1.0"
FEATURE_VERSION = "features-v1.1.0"
EVALUATION_VERSION = "evaluation-v1.1.0"
PROTOCOL_VERSION = "phase5-v1"

MIN_TEAM_SAMPLE_SIZE = 5
MIN_COMPETITION_SAMPLE_SIZE = 20
MIN_H2H_SAMPLE = 3
FORM_MATCHES = 10
FORM_WEIGHT = 0.20
VENUE_SHRINKAGE = 4.0
EXPECTED_GOALS_MIN = 0.20
EXPECTED_GOALS_MAX = 5.00

# Explicit priors, used only when both the competition and the stored corpus are too
# small to estimate a baseline. They are named in the report as priors, not data.
PRIOR_AVG_HOME_GOALS = 1.50
PRIOR_AVG_AWAY_GOALS = 1.15


class PredictionStatus(StrEnum):
    READY = "READY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"


def _empty_record() -> dict[str, Any]:
    """An absent record. Rates are ``None`` so absence is never encoded as zero."""

    return {
        "played": 0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
        "win_rate": None,
        "goals_for": 0,
        "goals_against": 0,
        "goals_for_avg": None,
        "goals_against_avg": None,
        "clean_sheets": 0,
        "failed_to_score": 0,
    }


def _summarize_team(
    matches: Sequence[HistoricalMatch],
    team_id: str,
) -> dict[str, Any]:
    all_matches = [m for m in matches if m.involves(team_id)]
    home_matches = [m for m in all_matches if m.home_team_id == team_id]
    away_matches = [m for m in all_matches if m.away_team_id == team_id]

    def record(subset: Sequence[HistoricalMatch]) -> dict[str, Any]:
        if not subset:
            return _empty_record()
        wins = draws = losses = goals_for = goals_against = clean_sheets = failed = 0
        for match in subset:
            scored = match.goals_for(team_id)
            conceded = match.goals_against(team_id)
            goals_for += scored
            goals_against += conceded
            if scored > conceded:
                wins += 1
            elif scored == conceded:
                draws += 1
            else:
                losses += 1
            if conceded == 0:
                clean_sheets += 1
            if scored == 0:
                failed += 1
        played = len(subset)
        return {
            "played": played,
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "win_rate": round(wins / played, 3),
            "goals_for": goals_for,
            "goals_against": goals_against,
            "goals_for_avg": round(goals_for / played, 2),
            "goals_against_avg": round(goals_against / played, 2),
            "clean_sheets": clean_sheets,
            "failed_to_score": failed,
        }

    recent = sorted(all_matches, key=lambda m: (m.kickoff_utc, m.match_id))[-FORM_MATCHES:]
    form: list[str] = []
    recent_for = recent_against = 0
    for match in recent:
        scored = match.goals_for(team_id)
        conceded = match.goals_against(team_id)
        recent_for += scored
        recent_against += conceded
        form.append("W" if scored > conceded else "D" if scored == conceded else "L")

    return {
        "overall": record(all_matches),
        "home": record(home_matches),
        "away": record(away_matches),
        "recent_form": "".join(form),
        "recent_matches": len(recent),
        "recent_goals_for_avg": round(recent_for / len(recent), 2) if recent else None,
        "recent_goals_against_avg": (
            round(recent_against / len(recent), 2) if recent else None
        ),
        "sample_size": len(all_matches),
    }


def calculate_match_features_from_matches(
    matches: Sequence[HistoricalMatch],
    *,
    home_team_id: str,
    away_team_id: str,
    competition_id: str,
) -> dict[str, Any]:
    """Calculate point-in-time features from an already filtered match list."""

    competition_matches = [m for m in matches if m.competition_id == competition_id]

    if len(competition_matches) >= MIN_COMPETITION_SAMPLE_SIZE:
        baseline_matches = competition_matches
        baseline_source = "competition"
    elif len(matches) >= MIN_COMPETITION_SAMPLE_SIZE:
        baseline_matches = list(matches)
        baseline_source = "all_competitions"
    else:
        baseline_matches = []
        baseline_source = "explicit_prior"

    if baseline_matches:
        avg_home = sum(m.home_goals for m in baseline_matches) / len(baseline_matches)
        avg_away = sum(m.away_goals for m in baseline_matches) / len(baseline_matches)
        sample_sufficient = True
    else:
        avg_home, avg_away = PRIOR_AVG_HOME_GOALS, PRIOR_AVG_AWAY_GOALS
        sample_sufficient = False

    if avg_home <= 0 or avg_away <= 0:
        avg_home, avg_away = PRIOR_AVG_HOME_GOALS, PRIOR_AVG_AWAY_GOALS
        baseline_source = "explicit_prior"
        sample_sufficient = False

    head_to_head = [
        m
        for m in matches
        if (m.home_team_id == home_team_id and m.away_team_id == away_team_id)
        or (m.home_team_id == away_team_id and m.away_team_id == home_team_id)
    ]
    h2h = {"home_wins": 0, "draws": 0, "away_wins": 0, "home_goals": 0, "away_goals": 0}
    for match in head_to_head:
        home_side = match.home_team_id == home_team_id
        scored = match.home_goals if home_side else match.away_goals
        conceded = match.away_goals if home_side else match.home_goals
        h2h["home_goals"] += scored
        h2h["away_goals"] += conceded
        if scored > conceded:
            h2h["home_wins"] += 1
        elif scored == conceded:
            h2h["draws"] += 1
        else:
            h2h["away_wins"] += 1

    missing = ["in_match_statistics", "lineups", "injuries"]
    if len(head_to_head) < MIN_H2H_SAMPLE:
        missing.append("head_to_head_sample")

    return {
        "feature_version": FEATURE_VERSION,
        "competition": {
            "competition_id": competition_id,
            "matches_analyzed": len(competition_matches),
            "baseline_matches": len(baseline_matches),
            "baseline_source": baseline_source,
            "baseline_sample_sufficient": sample_sufficient,
            "avg_home_goals": round(avg_home, 3),
            "avg_away_goals": round(avg_away, 3),
            "home_advantage_ratio": round(avg_home / avg_away, 3) if avg_away > 0 else None,
        },
        "home_team": _summarize_team(matches, home_team_id),
        "away_team": _summarize_team(matches, away_team_id),
        "head_to_head": {
            "meetings_count": len(head_to_head),
            **h2h,
            "limited_sample": len(head_to_head) < MIN_H2H_SAMPLE,
        },
        "statistics_available": False,
        "statistics_unavailable_on_plan": True,
        "missing_features": missing,
    }


def calculate_match_features(
    dataset: IntelligenceDataset,
    *,
    home_team_id: str,
    away_team_id: str,
    competition_id: str,
) -> dict[str, Any]:
    """Calculate point-in-time statistical features without future data leakage."""

    features = calculate_match_features_from_matches(
        dataset.matches,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        competition_id=competition_id,
    )
    features["dataset"] = {
        "dataset_id": dataset.dataset_id,
        "dataset_digest": dataset.digest,
        "classification": dataset.classification.value,
        "match_count": len(dataset.matches),
    }
    return features


def _shrink(observed: float | None, fallback: float, sample: int) -> float:
    if observed is None:
        return fallback
    weight = sample / (sample + VENUE_SHRINKAGE)
    return weight * observed + (1.0 - weight) * fallback


def estimate_goal_rates(features: dict[str, Any]) -> dict[str, Any]:
    """Estimate expected goals from features. Returns an abstention when too small."""

    home = features["home_team"]
    away = features["away_team"]
    competition = features["competition"]

    home_samples = home["sample_size"]
    away_samples = away["sample_size"]
    if home_samples < MIN_TEAM_SAMPLE_SIZE or away_samples < MIN_TEAM_SAMPLE_SIZE:
        return {
            "status": PredictionStatus.INSUFFICIENT_DATA,
            "reason": (
                f"Insufficient sample size: home team has {home_samples} matches and away "
                f"team has {away_samples} matches; the minimum is {MIN_TEAM_SAMPLE_SIZE}."
            ),
            "home_sample_size": home_samples,
            "away_sample_size": away_samples,
            "limitations": [
                "insufficient_match_history",
                "sample_size_below_threshold",
                "predictions_abstained",
            ],
        }

    avg_home = competition["avg_home_goals"]
    avg_away = competition["avg_away_goals"]
    overall_avg = (avg_home + avg_away) / 2.0

    if overall_avg <= 0:
        return {
            "status": PredictionStatus.INSUFFICIENT_DATA,
            "reason": "The competition baseline has no goal data.",
            "home_sample_size": home_samples,
            "away_sample_size": away_samples,
            "limitations": ["no_goal_baseline", "predictions_abstained"],
        }

    home_overall = home["overall"]
    away_overall = away["overall"]

    home_attack = _shrink(
        (home["home"]["goals_for_avg"] / avg_home) if home["home"]["played"] else None,
        home_overall["goals_for_avg"] / overall_avg,
        home["home"]["played"],
    )
    home_defence = _shrink(
        (home["home"]["goals_against_avg"] / avg_away)
        if home["home"]["played"]
        else None,
        home_overall["goals_against_avg"] / overall_avg,
        home["home"]["played"],
    )
    away_attack = _shrink(
        (away["away"]["goals_for_avg"] / avg_away) if away["away"]["played"] else None,
        away_overall["goals_for_avg"] / overall_avg,
        away["away"]["played"],
    )
    away_defence = _shrink(
        (away["away"]["goals_against_avg"] / avg_home)
        if away["away"]["played"]
        else None,
        away_overall["goals_against_avg"] / overall_avg,
        away["away"]["played"],
    )

    # Form is an observed average, so a genuine zero is used as zero. Only an absent
    # recent sample skips the blend.
    if home["recent_goals_for_avg"] is not None:
        weight = FORM_WEIGHT * min(1.0, home["recent_matches"] / FORM_MATCHES)
        home_attack = (1 - weight) * home_attack + weight * (
            home["recent_goals_for_avg"] / overall_avg
        )
        home_defence = (1 - weight) * home_defence + weight * (
            home["recent_goals_against_avg"] / overall_avg
        )
    if away["recent_goals_for_avg"] is not None:
        weight = FORM_WEIGHT * min(1.0, away["recent_matches"] / FORM_MATCHES)
        away_attack = (1 - weight) * away_attack + weight * (
            away["recent_goals_for_avg"] / overall_avg
        )
        away_defence = (1 - weight) * away_defence + weight * (
            away["recent_goals_against_avg"] / overall_avg
        )

    expected_home = avg_home * home_attack * away_defence
    expected_away = avg_away * away_attack * home_defence

    expected_home = max(EXPECTED_GOALS_MIN, min(EXPECTED_GOALS_MAX, expected_home))
    expected_away = max(EXPECTED_GOALS_MIN, min(EXPECTED_GOALS_MAX, expected_away))

    return {
        "status": PredictionStatus.READY,
        "expected_home_goals": expected_home,
        "expected_away_goals": expected_away,
        "parameters": {
            "baseline_avg_home_goals": round(avg_home, 4),
            "baseline_avg_away_goals": round(avg_away, 4),
            "baseline_source": competition["baseline_source"],
            "home_attack_strength": round(home_attack, 4),
            "home_defence_strength": round(home_defence, 4),
            "away_attack_strength": round(away_attack, 4),
            "away_defence_strength": round(away_defence, 4),
            "home_recent_weight": round(
                FORM_WEIGHT * min(1.0, home["recent_matches"] / FORM_MATCHES), 4
            ),
            "away_recent_weight": round(
                FORM_WEIGHT * min(1.0, away["recent_matches"] / FORM_MATCHES), 4
            ),
            "expected_goals_bounds": [EXPECTED_GOALS_MIN, EXPECTED_GOALS_MAX],
        },
        "home_sample_size": home_samples,
        "away_sample_size": away_samples,
    }


def probability_triplet(matrix: ScoreMatrix) -> tuple[float, float, float]:
    """Return home/draw/away probabilities that sum to one after rounding."""

    outcomes = match_outcomes(matrix)
    raw = (outcomes.home_win.lower, outcomes.draw.lower, outcomes.away_win.lower)
    total = sum(raw)
    if total <= 0 or not isfinite(total):
        raise ValueError("score matrix produced no resolvable outcome probability")
    home = round(raw[0] / total, 4)
    draw = round(raw[1] / total, 4)
    away = round(1.0 - home - draw, 4)
    if min(home, draw, away) < 0 or max(home, draw, away) > 1:
        raise ValueError("normalised 1X2 probability fell outside [0, 1]")
    return home, draw, away


def _validate_prediction(
    *,
    home: float,
    draw: float,
    away: float,
    expected_home: float,
    expected_away: float,
) -> None:
    if abs((home + draw + away) - 1.0) > 1e-9:
        raise ValueError("1X2 probabilities must sum to one")
    if any(not 0.0 <= value <= 1.0 for value in (home, draw, away)):
        raise ValueError("1X2 probabilities must be in [0, 1]")
    for value in (expected_home, expected_away):
        if not EXPECTED_GOALS_MIN <= value <= EXPECTED_GOALS_MAX:
            raise ValueError("expected goals outside the documented bounds")


def predict_from_features(
    features: dict[str, Any],
    *,
    context: ResearchContext,
) -> dict[str, Any]:
    """Run the model from features with an explicit research context."""

    rates = estimate_goal_rates(features)
    if rates["status"] != PredictionStatus.READY:
        return rates

    expected_home = rates["expected_home_goals"]
    expected_away = rates["expected_away_goals"]
    matrix = poisson_score_matrix(
        home_rate=expected_home,
        away_rate=expected_away,
        context=context,
    )
    home, draw, away = probability_triplet(matrix)
    _validate_prediction(
        home=home,
        draw=draw,
        away=away,
        expected_home=expected_home,
        expected_away=expected_away,
    )

    p_over_1_5 = round(over_probability(matrix, 1.5), 4)
    p_over_2_5 = round(over_probability(matrix, 2.5), 4)
    p_over_3_5 = round(over_probability(matrix, 3.5), 4)
    btts = round(both_teams_to_score(matrix).yes, 4)
    scorelines = [
        {"home_goals": h, "away_goals": a, "probability": round(p, 4)}
        for h, a, p in top_scorelines(matrix, limit=5)
    ]

    competition = features["competition"]
    home_stats = features["home_team"]
    away_stats = features["away_team"]
    h2h = features["head_to_head"]
    parameters = rates["parameters"]

    limitations = [
        "independent_poisson_assumption",
        "no_low_score_dependence_adjustment",
        "opponent_strength_estimated_from_historical_averages",
        "in_match_statistics_unavailable_on_free_tier",
        "no_lineup_or_injury_data",
        "probabilities_are_estimates_not_guarantees",
        "no_real_world_performance_claim",
    ]
    if h2h["limited_sample"]:
        limitations.append("limited_head_to_head_sample")
    if not competition["baseline_sample_sufficient"]:
        limitations.append("competition_baseline_below_sample_threshold")

    explanation = {
        "model_rationale": (
            "Expected goals are the competition baseline "
            f"({competition['avg_home_goals']:.3f} home, "
            f"{competition['avg_away_goals']:.3f} away; source: "
            f"{competition['baseline_source']}) multiplied by each side's "
            "attack strength and the opponent's defensive strength, then shrunk "
            "towards observed recent form."
        ),
        "expected_goals_breakdown": {
            "home": (
                f"{expected_home:.2f} expected goals = baseline "
                f"{parameters['baseline_avg_home_goals']:.3f} x home attack "
                f"{parameters['home_attack_strength']:.3f} x away defence "
                f"{parameters['away_defence_strength']:.3f}"
            ),
            "away": (
                f"{expected_away:.2f} expected goals = baseline "
                f"{parameters['baseline_avg_away_goals']:.3f} x away attack "
                f"{parameters['away_attack_strength']:.3f} x home defence "
                f"{parameters['home_defence_strength']:.3f}"
            ),
        },
        "form_impact": (
            f"Home recent form {home_stats['recent_form'] or 'unavailable'} "
            f"({home_stats['recent_goals_for_avg']} goals for, "
            f"{home_stats['recent_goals_against_avg']} against per match; "
            f"weight {parameters['home_recent_weight']:.2f}). "
            f"Away recent form {away_stats['recent_form'] or 'unavailable'} "
            f"({away_stats['recent_goals_for_avg']} goals for, "
            f"{away_stats['recent_goals_against_avg']} against per match; "
            f"weight {parameters['away_recent_weight']:.2f})."
        ),
        "h2h_impact": (
            f"{h2h['meetings_count']} previous meetings in the verified history: "
            f"{h2h['home_wins']} home wins, {h2h['draws']} draws, "
            f"{h2h['away_wins']} away wins. Head-to-head is not used to fit the goal "
            "rates; a sample below three meetings is reported as limited."
        ),
    }

    return {
        "status": PredictionStatus.READY,
        "model_id": MODEL_ID,
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "expected_home_goals": round(expected_home, 2),
        "expected_away_goals": round(expected_away, 2),
        "home_win_probability": home,
        "draw_probability": draw,
        "away_win_probability": away,
        "btts_probability": btts,
        "over_1_5_probability": p_over_1_5,
        "under_1_5_probability": round(1.0 - p_over_1_5, 4),
        "over_2_5_probability": p_over_2_5,
        "under_2_5_probability": round(1.0 - p_over_2_5, 4),
        "over_3_5_probability": p_over_3_5,
        "under_3_5_probability": round(1.0 - p_over_3_5, 4),
        "scoreline_probabilities": scorelines,
        "home_sample_size": rates["home_sample_size"],
        "away_sample_size": rates["away_sample_size"],
        "h2h_sample_size": h2h["meetings_count"],
        "model_parameters": parameters,
        "explanation": explanation,
        "limitations": limitations,
    }


def run_statistical_prediction(
    dataset: IntelligenceDataset,
    features: dict[str, Any],
    *,
    home_team_id: str,
    away_team_id: str,
    competition_id: str,
) -> dict[str, Any]:
    """Calculate expected goals, 1X2 probabilities, markets and scorelines."""

    result = predict_from_features(
        features, context=dataset.research_context(protocol_version=PROTOCOL_VERSION)
    )
    result["dataset_id"] = dataset.dataset_id
    result["dataset_digest"] = dataset.digest
    return result


def compute_historical_backtest_evaluation(
    dataset: IntelligenceDataset,
    *,
    competition_id: str,
    eval_matches_count: int = 50,
    minimum_prior_matches: int = 40,
) -> dict[str, Any]:
    """Rolling-origin evaluation of the production model.

    Each test match is predicted from the same feature and rate functions used by the
    live analysis, using only matches that had finished before that test match kicked
    off. A future result therefore cannot influence an earlier fold.
    """

    competition_matches = sorted(
        [m for m in dataset.matches if m.competition_id == competition_id],
        key=lambda m: (m.kickoff_utc, m.match_id),
    )
    if len(competition_matches) < minimum_prior_matches + 10:
        return {
            "evaluated": False,
            "reason": "insufficient_competition_matches_for_backtest",
            "sample_size": len(competition_matches),
            "model_id": MODEL_ID,
            "model_version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "evaluation_version": EVALUATION_VERSION,
        }

    context = dataset.research_context(protocol_version=PROTOCOL_VERSION)
    test_set = competition_matches[-eval_matches_count:]
    probabilities: list[list[float]] = []
    outcomes: list[int] = []
    first_test: datetime | None = None
    last_test: datetime | None = None

    for test_match in test_set:
        # A retrospective fold may use a result once the match is over. Ingestion time
        # is not the information cutoff here: every backfilled result was archived at
        # roughly the same wall-clock time, which would otherwise make all folds empty.
        # Three hours is a conservative bound on match duration plus stoppage.
        prior = [
            m
            for m in dataset.matches
            if m.kickoff_utc + timedelta(hours=3) <= test_match.kickoff_utc
        ]
        if len(prior) < minimum_prior_matches:
            continue

        features = calculate_match_features_from_matches(
            prior,
            home_team_id=test_match.home_team_id,
            away_team_id=test_match.away_team_id,
            competition_id=competition_id,
        )
        prediction = predict_from_features(features, context=context)
        if prediction["status"] != PredictionStatus.READY:
            continue

        probabilities.append(
            [
                prediction["home_win_probability"],
                prediction["draw_probability"],
                prediction["away_win_probability"],
            ]
        )
        if test_match.home_goals > test_match.away_goals:
            outcomes.append(0)
        elif test_match.home_goals == test_match.away_goals:
            outcomes.append(1)
        else:
            outcomes.append(2)
        first_test = first_test or test_match.kickoff_utc
        last_test = test_match.kickoff_utc

    if len(outcomes) < 10:
        return {
            "evaluated": False,
            "reason": "insufficient_valid_folds",
            "sample_size": len(outcomes),
            "model_id": MODEL_ID,
            "model_version": MODEL_VERSION,
            "feature_version": FEATURE_VERSION,
            "evaluation_version": EVALUATION_VERSION,
        }

    labels = ("home", "draw", "away")
    brier = multiclass_brier_score(
        probabilities, outcomes, class_labels=labels, context=context
    )
    log_loss = multiclass_log_loss(
        probabilities, outcomes, class_labels=labels, context=context
    )
    reliability = multiclass_reliability(
        probabilities, outcomes, class_labels=labels, context=context, bin_count=5
    )

    calibration = []
    for summary in reliability:
        bins = [
            {
                "lower": round(bin.lower, 3),
                "upper": round(bin.upper, 3),
                "sample_size": bin.sample_size,
                "mean_probability": round(bin.mean_probability, 4)
                if bin.mean_probability is not None
                else None,
                "observed_rate": round(bin.observed_rate, 4)
                if bin.observed_rate is not None
                else None,
            }
            for bin in summary.bins
            if bin.sample_size > 0
        ]
        calibration.append(
            {
                "class_label": summary.class_label,
                "sample_size": summary.sample_size,
                "expected_calibration_error": round(
                    summary.expected_calibration_error, 4
                )
                if summary.expected_calibration_error is not None
                else None,
                "maximum_calibration_error": round(
                    summary.maximum_calibration_error, 4
                )
                if summary.maximum_calibration_error is not None
                else None,
                "bins": bins,
            }
        )

    ece_values = [
        item["expected_calibration_error"]
        for item in calibration
        if item["expected_calibration_error"] is not None
    ]
    mce_values = [
        item["maximum_calibration_error"]
        for item in calibration
        if item["maximum_calibration_error"] is not None
    ]
    uniform_brier = 2.0 / 3.0
    uniform_log_loss = log(3.0)

    return {
        "evaluated": True,
        "sample_size": len(outcomes),
        "brier_score": round(brier.value, 4),
        "log_loss": round(log_loss.value, 4),
        "uniform_brier_score": round(uniform_brier, 4),
        "uniform_log_loss": round(uniform_log_loss, 4),
        "brier_skill_score": round(1.0 - brier.value / uniform_brier, 4),
        "expected_calibration_error": round(sum(ece_values) / len(ece_values), 4)
        if ece_values
        else None,
        "maximum_calibration_error": round(max(mce_values), 4) if mce_values else None,
        "calibration": calibration,
        "class_labels": list(labels),
        "model_id": MODEL_ID,
        "model_version": MODEL_VERSION,
        "feature_version": FEATURE_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "dataset_id": dataset.dataset_id,
        "dataset_digest": dataset.digest,
        "evaluation_type": "rolling_origin_out_of_sample",
        "test_period_from": first_test.isoformat() if first_test else None,
        "test_period_to": last_test.isoformat() if last_test else None,
    }
