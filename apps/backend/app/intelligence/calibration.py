"""Probability calibration subsystem for Phase 8.

Implements calibration analysis and correction methods:
- Reliability diagrams with proper visualization data
- Expected Calibration Error (ECE) and Maximum Calibration Error (MCE)
- Per-competition, per-season, per-probability-range calibration
- Draw probability bias analysis
- Calibration correction methods (temperature scaling, isotonic regression)
- Calibration data/train/test split

All calibration is performed on strictly held-out chronological data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from math import exp, isfinite, log
from typing import Sequence

from app.intelligence.baselines import (
    FREQUENCY_MODEL_ID,
    FREQUENCY_MODEL_VERSION,
    UNIFORM_MODEL_ID,
    UNIFORM_MODEL_VERSION,
    competition_frequency_probabilities,
    uniform_probabilities,
)
from app.intelligence.evaluation import (
    ReliabilitySummary,
    multiclass_brier_score,
    multiclass_log_loss,
    multiclass_reliability,
)
from app.intelligence.models.dixon_coles import (
    DC_MODEL_ID,
    DC_MODEL_VERSION,
    LowScoreObservation,
    clip_rho,
    dixon_coles_score_matrix,
    fit_rho,
)
from app.intelligence.models.elo_fitted import (
    ELO_MODEL_ID,
    ELO_MODEL_VERSION,
    ChronologicalElo,
    DavidsonFit,
    elo_outcome_probabilities,
    fit_davidson,
    outcome_index,
)
from app.intelligence.prediction import (
    MODEL_ID,
    MODEL_VERSION,
    PredictionStatus,
    calculate_match_features_from_matches,
    estimate_goal_rates,
    predict_from_features,
    probability_triplet,
)
from app.intelligence.types import (
    HistoricalMatch,
    IntelligenceDataset,
)
from app.intelligence.validation import (
    ValidationProtocol,
    _bootstrap_ci,
    _evaluate_rows,
    _outcome,
    _baseline_rates,
    _group_by_kickoff,
    _select_targets,
    MATCH_HORIZON,
    MIN_PRIOR_MATCHES,
    MAX_TEST_PER_COMPETITION,
    BOOTSTRAP_RESAMPLES,
    BOOTSTRAP_SEED,
    TIMELINE_BUCKET_SIZE,
    CALIBRATION_BINS,
    MIN_COMPETITION_MATCHES,
    MIN_ELO_TRAINING,
    MODEL_KEYS,
    MODEL_SPECS,
)

CALIBRATION_PROTOCOL_VERSION = "phase8-calibration-v1"
CALIBRATION_EVALUATION_VERSION = "evaluation-v1.2.0"


@dataclass(frozen=True)
class CalibrationPoint:
    """One calibrated prediction point."""
    match_id: str
    competition_id: str
    season_id: str
    kickoff_utc: datetime
    home: float
    draw: float
    away: float
    outcome: int


@dataclass(frozen=True)
class CalibrationResult:
    """Calibration analysis output."""
    protocol_version: str
    evaluation_version: str
    evaluated: bool
    reason: str | None = None
    sample_size: int = 0
    overall_ece: float | None = None
    overall_mce: float | None = None
    per_class_calibration: list[dict] = field(default_factory=list)
    per_competition_calibration: list[dict] = field(default_factory=list)
    per_season_calibration: list[dict] = field(default_factory=list)
    probability_range_calibration: list[dict] = field(default_factory=list)
    draw_bias_analysis: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CalibrationParameters:
    """Fitted calibration parameters."""
    method: str
    temperature: float | None = None
    isotonic_bins: list[tuple[float, float]] | None = None
    fitted_on: str = "calibration_set"
    calibration_sample_size: int = 0
    training_sample_size: int = 0


def _softmax(logits: Sequence[float]) -> list[float]:
    """Stable softmax."""
    max_logit = max(logits)
    exps = [exp(x - max_logit) for x in logits]
    total = sum(exps)
    return [x / total for x in exps]


def _log_softmax(logits: Sequence[float]) -> list[float]:
    """Log softmax for numerical stability."""
    max_logit = max(logits)
    exp_sum = sum(exp(x - max_logit) for x in logits)
    return [x - max_logit - log(exp_sum) for x in logits]


def fit_temperature_scaling(
    calibration_logits: Sequence[Sequence[float]],
    calibration_outcomes: Sequence[int],
    *,
    initial_temperature: float = 1.0,
    learning_rate: float = 0.01,
    max_iterations: int = 1000,
    tolerance: float = 1e-6,
) -> tuple[float, float]:
    """Fit temperature scaling parameter using gradient descent.

    Minimizes negative log likelihood on calibration set.
    """
    if not calibration_logits or len(calibration_logits) != len(calibration_outcomes):
        raise ValueError("logits and outcomes must have equal non-zero length")

    T = initial_temperature
    n = len(calibration_logits)
    classes = len(calibration_logits[0])

    for iteration in range(max_iterations):
        grad = 0.0
        loss = 0.0

        for logits, outcome in zip(calibration_logits, calibration_outcomes, strict=True):
            scaled = [x / T for x in logits]
            probs = _softmax(scaled)
            true_prob = probs[outcome]
            loss -= log(true_prob) if true_prob > 0 else 100.0

            # Gradient w.r.t T
            for k, p in enumerate(probs):
                indicator = 1.0 if k == outcome else 0.0
                grad += (p - indicator) * logits[k] / (T * T)

        grad /= n
        loss /= n

        if abs(grad) < tolerance:
            break

        T -= learning_rate * grad
        T = max(0.01, T)  # Prevent negative/zero temperature

    return T, loss


def fit_isotonic_regression(
    calibration_probs: Sequence[float],
    calibration_outcomes: Sequence[int],
) -> list[tuple[float, float]]:
    """Fit isotonic regression using Pool Adjacent Violators Algorithm (PAVA).

    Returns list of (probability_bin, calibrated_probability) pairs.
    """
    if len(calibration_probs) != len(calibration_outcomes):
        raise ValueError("probs and outcomes must have equal length")

    # Sort by predicted probability
    pairs = sorted(zip(calibration_probs, calibration_outcomes))
    n = len(pairs)

    # Initialize blocks: each point is its own block
    blocks = [{"probs": [p], "outcomes": [o], "mean_prob": p, "mean_obs": o} for p, o in pairs]

    # Pool Adjacent Violators
    merged = True
    while merged:
        merged = False
        i = 0
        while i < len(blocks) - 1:
            if blocks[i]["mean_obs"] > blocks[i + 1]["mean_obs"]:
                # Merge blocks i and i+1
                blocks[i] = {
                    "probs": blocks[i]["probs"] + blocks[i + 1]["probs"],
                    "outcomes": blocks[i]["outcomes"] + blocks[i + 1]["outcomes"],
                    "mean_prob": sum(blocks[i]["probs"] + blocks[i + 1]["probs"]) / (len(blocks[i]["probs"]) + len(blocks[i + 1]["probs"])),
                    "mean_obs": sum(blocks[i]["outcomes"] + blocks[i + 1]["outcomes"]) / (len(blocks[i]["outcomes"]) + len(blocks[i + 1]["outcomes"])),
                }
                blocks.pop(i + 1)
                merged = True
                break
            i += 1

    # Build calibration mapping
    result = []
    for block in blocks:
        # Use mean predicted probability as bin center
        bin_center = block["mean_prob"]
        calibrated = block["mean_obs"]
        result.append((bin_center, calibrated))

    return result


def apply_temperature_scaling(
    probabilities: Sequence[Sequence[float]],
    temperature: float,
) -> list[list[float]]:
    """Apply temperature scaling to probability vectors."""
    calibrated = []
    for probs in probabilities:
        # Convert probabilities back to logits, scale, then softmax
        logits = [log(max(1e-12, p)) for p in probs]
        scaled = [x / temperature for x in logits]
        calibrated.append(_softmax(scaled))
    return calibrated


def apply_isotonic_calibration(
    probabilities: Sequence[Sequence[float]],
    isotonic_mapping: list[tuple[float, float]],
) -> list[list[float]]:
    """Apply isotonic calibration to probability vectors.

    Each class is calibrated independently using its own isotonic mapping.
    """
    if len(probabilities) == 0:
        return []

    classes = len(probabilities[0])
    calibrated = []

    for probs in probabilities:
        calibrated_probs = []
        for class_idx in range(classes):
            p = probs[class_idx]
            # Find nearest bin and interpolate
            if not isotonic_mapping:
                calibrated_probs.append(p)
                continue

            # Simple nearest neighbor interpolation
            # In production, use linear interpolation between bins
            nearest = min(isotonic_mapping, key=lambda x: abs(x[0] - p))
            calibrated_probs.append(nearest[1])

        # Renormalize to sum to 1
        total = sum(calibrated_probs)
        if total > 0:
            calibrated_probs = [c / total for c in calibrated_probs]
        calibrated.append(calibrated_probs)

    return calibrated


def _collect_calibration_data(
    dataset: IntelligenceDataset,
    *,
    protocol: ValidationProtocol,
    calibration_fraction: float = 0.3,
) -> tuple[list[CalibrationPoint], list[CalibrationPoint]]:
    """Collect calibration and test data using strict chronological split.

    Returns (calibration_set, test_set) where calibration_set is chronologically
    earlier than test_set.
    """
    matches = sorted(dataset.matches, key=lambda item: (item.kickoff_utc, item.match_id))
    by_competition: dict[str, list[HistoricalMatch]] = {}
    for match in matches:
        by_competition.setdefault(match.competition_id, []).append(match)

    targets, window_start, insufficient = _select_targets(
        by_competition,
        min_prior_matches=protocol.min_prior_matches,
        max_test_per_competition=protocol.max_test_per_competition,
        min_competition_matches=protocol.min_competition_matches,
    )

    if not targets:
        return [], []

    context = dataset.research_context(protocol_version=protocol.protocol_version)
    elo = ChronologicalElo()
    available: list[HistoricalMatch] = []
    cursor = 0
    elo_training: dict[str, list[tuple[float, float, int]]] = {}
    fits: dict[str, any] = {}
    all_rows: list[CalibrationPoint] = []
    diagnostics: dict[str, any] = {
        competition_id: {"evaluated": 0, "skipped_model": 0, "skipped_history": 0}
        for competition_id in by_competition
    }

    for group in _group_by_kickoff(matches):
        kickoff = group[0].kickoff_utc

        while cursor < len(matches):
            head_kickoff = matches[cursor].kickoff_utc
            if head_kickoff + MATCH_HORIZON > kickoff:
                break
            batch: list[HistoricalMatch] = []
            while cursor < len(matches) and matches[cursor].kickoff_utc == head_kickoff:
                batch.append(matches[cursor])
                cursor += 1
            for match in batch:
                home_rating = elo.rating(match.home_team_id)
                away_rating = elo.rating(match.away_team_id)
                if home_rating is None or away_rating is None:
                    continue
                start = window_start.get(match.competition_id)
                if start is not None and match.kickoff_utc < start:
                    elo_training.setdefault(match.competition_id, []).append(
                        (home_rating, away_rating, _outcome(match.home_goals, match.away_goals))
                    )
            available.extend(batch)
            elo.apply_batch(batch)

        for match in group:
            if match.match_id not in targets:
                continue
            competition_id = match.competition_id
            entry = diagnostics[competition_id]
            if len(available) < protocol.min_prior_matches:
                entry["skipped_history"] += 1
                continue

            if competition_id not in fits:
                competition_prior = [item for item in available if item.competition_id == competition_id]
                rate_pair = _baseline_rates(competition_prior)
                observations = (
                    [
                        LowScoreObservation(
                            home_rate=rate_pair[0],
                            away_rate=rate_pair[1],
                            home_goals=item.home_goals,
                            away_goals=item.away_goals,
                            kickoff_utc=item.kickoff_utc,
                        )
                        for item in competition_prior
                    ]
                    if rate_pair
                    else []
                )
                fits[competition_id] = {
                    "rho": fit_rho(observations, reference_kickoff=kickoff) if observations else None,
                    "davidson": fit_davidson(elo_training.get(competition_id, ()), minimum_matches=protocol.min_elo_training),
                    "baseline_home": rate_pair[0] if rate_pair else None,
                    "baseline_away": rate_pair[1] if rate_pair else None,
                    "training_matches": len(competition_prior),
                }

            fit = fits[competition_id]
            features = calculate_match_features_from_matches(
                available,
                home_team_id=match.home_team_id,
                away_team_id=match.away_team_id,
                competition_id=competition_id,
            )
            poisson = predict_from_features(features, context=context)
            if poisson["status"] != PredictionStatus.READY:
                entry["skipped_model"] += 1
                continue

            rates = estimate_goal_rates(features)
            if rates["status"] != PredictionStatus.READY:
                entry["skipped_model"] += 1
                continue

            home_rating = elo.rating(match.home_team_id)
            away_rating = elo.rating(match.away_team_id)
            if home_rating is None or away_rating is None or fit["davidson"] is None:
                entry["skipped_model"] += 1
                continue

            expected_home = rates["expected_home_goals"]
            expected_away = rates["expected_away_goals"]
            rho = clip_rho(fit["rho"], expected_home, expected_away) if fit["rho"] is not None else 0.0
            try:
                matrix = dixon_coles_score_matrix(expected_home, expected_away, rho, context=context)
            except ValueError:
                entry["skipped_model"] += 1
                continue
            dc_home, dc_draw, dc_away = probability_triplet(matrix)

            elo_probabilities = elo_outcome_probabilities(
                home_rating, away_rating,
                home_advantage=fit["davidson"].home_advantage,
                draw_nu=fit["davidson"].draw_nu,
            )
            frequency, _source = competition_frequency_probabilities(available, competition_id=competition_id)

            outcome = _outcome(match.home_goals, match.away_goals)
            all_rows.append(CalibrationPoint(
                match_id=match.match_id,
                competition_id=competition_id,
                season_id=match.season_id,
                kickoff_utc=match.kickoff_utc,
                home=poisson["home_win_probability"],
                draw=poisson["draw_probability"],
                away=poisson["away_win_probability"],
                outcome=outcome,
            ))
            entry["evaluated"] += 1

    if not all_rows:
        return [], []

    # Chronological split: first fraction for calibration, rest for test
    split_idx = max(1, int(len(all_rows) * calibration_fraction))
    calibration_set = all_rows[:split_idx]
    test_set = all_rows[split_idx:]

    return calibration_set, test_set


def run_calibration_study(
    dataset: IntelligenceDataset,
    *,
    protocol: ValidationProtocol | None = None,
    calibration_fraction: float = 0.3,
) -> CalibrationResult:
    """Run comprehensive calibration study.

    Splits data chronologically into calibration and test sets.
    Fits calibration parameters on calibration set, evaluates on test set.
    """

    if protocol is None:
        protocol = ValidationProtocol()

    # Collect calibration and test data
    calibration_data, test_data = _collect_calibration_data(
        dataset, protocol=protocol, calibration_fraction=calibration_fraction
    )

    if not calibration_data or not test_data:
        return CalibrationResult(
            protocol_version=CALIBRATION_PROTOCOL_VERSION,
            evaluation_version=CALIBRATION_EVALUATION_VERSION,
            evaluated=False,
            reason="insufficient_data_for_calibration_study",
        )

    context = dataset.research_context(protocol_version=protocol.protocol_version)

    # Evaluate raw (uncalibrated) predictions on test set
    test_rows = [CalibrationPoint(
        match_id=cp.match_id, competition_id=cp.competition_id,
        season_id=cp.season_id, kickoff_utc=cp.kickoff_utc,
        home=cp.home, draw=cp.draw, away=cp.away, outcome=cp.outcome
    ) for cp in test_data]

    # Raw evaluation
    raw_eval = _evaluate_rows(test_rows, context=context, protocol=protocol)

    # Fit temperature scaling on calibration set
    calibration_logits = [[log(max(1e-12, cp.home)), log(max(1e-12, cp.draw)), log(max(1e-12, cp.away))]
                          for cp in calibration_data]
    calibration_outcomes = [cp.outcome for cp in calibration_data]

    temperature, calibration_loss = fit_temperature_scaling(
        calibration_logits, calibration_outcomes
    )

    # Apply temperature scaling to test set
    test_logits = [[log(max(1e-12, cp.home)), log(max(1e-12, cp.draw)), log(max(1e-12, cp.away))]
                   for cp in test_data]
    calibrated_probs = apply_temperature_scaling(test_logits, temperature)

    calibrated_rows = [CalibrationPoint(
        match_id=cp.match_id, competition_id=cp.competition_id,
        season_id=cp.season_id, kickoff_utc=cp.kickoff_utc,
        home=calibrated_probs[i][0], draw=calibrated_probs[i][1], away=calibrated_probs[i][2],
        outcome=cp.outcome
    ) for i, cp in enumerate(test_data)]

    calibrated_eval = _evaluate_rows(calibrated_rows, context=context, protocol=protocol)

    # Fit isotonic regression on calibration set (per class)
    calibration_probs_per_class = [
        [cp.home for cp in calibration_data],
        [cp.draw for cp in calibration_data],
        [cp.away for cp in calibration_data],
    ]
    isotonic_mappings = []
    for class_idx in range(3):
        class_probs = calibration_probs_per_class[class_idx]
        class_outcomes = [1 if o == class_idx else 0 for o in calibration_outcomes]
        mapping = fit_isotonic_regression(class_probs, class_outcomes)
        isotonic_mappings.append(mapping)

    # Apply isotonic to test set
    test_probs_per_class = [
        [cp.home for cp in test_data],
        [cp.draw for cp in test_data],
        [cp.away for cp in test_data],
    ]
    isotonic_calibrated = []
    for class_idx in range(3):
        class_probs = test_probs_per_class[class_idx]
        class_outcomes = [1 if o == class_idx else 0 for o in [cp.outcome for cp in test_data]]
        calibrated_class = apply_isotonic_calibration([[p] for p in class_probs], isotonic_mappings[class_idx])
        isotonic_calibrated.append([c[0] for c in calibrated_class])

    # Combine isotonic calibrated probabilities
    isotonic_rows = [CalibrationPoint(
        match_id=cp.match_id, competition_id=cp.competition_id,
        season_id=cp.season_id, kickoff_utc=cp.kickoff_utc,
        home=isotonic_calibrated[0][i], draw=isotonic_calibrated[1][i], away=isotonic_calibrated[2][i],
        outcome=cp.outcome
    ) for i, cp in enumerate(test_data)]

    isotonic_eval = _evaluate_rows(isotonic_rows, context=context, protocol=protocol)

    # Overall calibration metrics
    per_class_calibration = raw_eval.get("calibration", [])
    ece_values = [item["expected_calibration_error"] for item in per_class_calibration if item["expected_calibration_error"] is not None]
    mce_values = [item["maximum_calibration_error"] for item in per_class_calibration if item["maximum_calibration_error"] is not None]
    overall_ece = sum(ece_values) / len(ece_values) if ece_values else None
    overall_mce = max(mce_values) if mce_values else None

    # Per-competition calibration
    per_competition_calibration = []
    for competition_id in sorted(set(cp.competition_id for cp in test_data)):
        comp_rows = [cp for cp in test_rows if cp.competition_id == competition_id]
        if len(comp_rows) >= 10:
            comp_eval = _evaluate_rows(comp_rows, context=context, protocol=protocol)
            per_competition_calibration.append({
                "competition_id": competition_id,
                "sample_size": len(comp_rows),
                "ece": comp_eval.get("expected_calibration_error"),
                "mce": comp_eval.get("maximum_calibration_error"),
                "calibration": comp_eval.get("calibration", []),
            })

    # Per-season calibration
    per_season_calibration = []
    season_groups = {}
    for cp in test_rows:
        key = (cp.competition_id, cp.season_id)
        season_groups.setdefault(key, []).append(cp)

    for (comp_id, season_id), rows in sorted(season_groups.items()):
        if len(rows) >= 10:
            season_eval = _evaluate_rows(rows, context=context, protocol=protocol)
            per_season_calibration.append({
                "competition_id": comp_id,
                "season_id": season_id,
                "sample_size": len(rows),
                "ece": season_eval.get("expected_calibration_error"),
                "mce": season_eval.get("maximum_calibration_error"),
            })

    # Probability range calibration (by predicted probability quantiles)
    probability_range_calibration = []
    for class_idx, class_label in enumerate(["home", "draw", "away"]):
        class_probs = [getattr(cp, class_label) for cp in test_rows]
        class_outcomes = [1 if cp.outcome == class_idx else 0 for cp in test_rows]

        # Sort by predicted probability
        pairs = sorted(zip(class_probs, class_outcomes))
        n = len(pairs)
        if n < 50:
            continue

        # Divide into 5 quantile bins
        bin_size = n // 5
        for b in range(5):
            start = b * bin_size
            end = (b + 1) * bin_size if b < 4 else n
            bin_pairs = pairs[start:end]
            bin_probs = [p for p, o in bin_pairs]
            bin_outcomes = [o for p, o in bin_pairs]
            mean_prob = sum(bin_probs) / len(bin_probs)
            obs_rate = sum(bin_outcomes) / len(bin_outcomes)

            probability_range_calibration.append({
                "class_label": class_label,
                "bin": b,
                "prob_lower": round(min(bin_probs), 3),
                "prob_upper": round(max(bin_probs), 3),
                "sample_size": len(bin_pairs),
                "mean_probability": round(mean_prob, 4),
                "observed_rate": round(obs_rate, 4),
                "calibration_gap": round(obs_rate - mean_prob, 4),
            })

    # Draw bias analysis
    draw_probs = [cp.draw for cp in test_data]
    draw_outcomes = [1 if cp.outcome == 1 else 0 for cp in test_data]
    draw_rate = sum(draw_outcomes) / len(draw_outcomes)
    mean_draw_prob = sum(draw_probs) / len(draw_probs)
    draw_bias = draw_rate - mean_draw_prob

    # Draw calibration by probability range
    draw_pairs = sorted(zip(draw_probs, draw_outcomes))
    draw_bins = []
    for b in range(5):
        start = b * (len(draw_pairs) // 5)
        end = (b + 1) * (len(draw_pairs) // 5) if b < 4 else len(draw_pairs)
        bin_pairs = draw_pairs[start:end]
        if bin_pairs:
            bin_probs = [p for p, o in bin_pairs]
            bin_outcomes = [o for p, o in bin_pairs]
            mean_prob = sum(bin_probs) / len(bin_probs)
            obs_rate = sum(bin_outcomes) / len(bin_outcomes)
            draw_bins.append({
                "bin": b,
                "prob_lower": round(min(bin_probs), 3),
                "prob_upper": round(max(bin_probs), 3),
                "sample_size": len(bin_pairs),
                "mean_probability": round(mean_prob, 4),
                "observed_rate": round(obs_rate, 4),
                "gap": round(obs_rate - mean_prob, 4),
            })

    draw_bias_analysis = {
        "overall_draw_rate": round(draw_rate, 4),
        "mean_predicted_draw_prob": round(mean_draw_prob, 4),
        "draw_bias": round(draw_bias, 4),
        "bias_direction": "under-prediction" if draw_bias > 0 else "over-prediction",
        "per_bin": draw_bins,
    }

    return CalibrationResult(
        protocol_version=CALIBRATION_PROTOCOL_VERSION,
        evaluation_version=CALIBRATION_EVALUATION_VERSION,
        evaluated=True,
        sample_size=len(test_data),
        overall_ece=round(overall_ece, 4) if overall_ece is not None else None,
        overall_mce=round(overall_mce, 4) if overall_mce is not None else None,
        per_class_calibration=per_class_calibration,
        per_competition_calibration=per_competition_calibration,
        per_season_calibration=per_season_calibration,
        probability_range_calibration=probability_range_calibration,
        draw_bias_analysis=draw_bias_analysis,
        notes=[
            f"Calibration set size: {len(calibration_data)}, test set size: {len(test_data)}",
            f"Temperature scaling: T={temperature:.4f}, calibration NLL={calibration_loss:.4f}",
            f"Raw test ECE: {raw_eval.get('expected_calibration_error')}, calibrated: {calibrated_eval.get('expected_calibration_error')}, isotonic: {isotonic_eval.get('expected_calibration_error')}",
            "Calibration parameters fitted on chronologically earlier calibration set only",
            "No model selection or parameter tuning on test set",
        ],
    )


def run_calibration_study_raw_only(
    dataset: IntelligenceDataset,
    *,
    protocol: ValidationProtocol | None = None,
) -> CalibrationResult:
    """Run calibration analysis without fitting correction (diagnostic only)."""

    if protocol is None:
        protocol = ValidationProtocol()

    calibration_data, test_data = _collect_calibration_data(
        dataset, protocol=protocol, calibration_fraction=0.3
    )

    if not calibration_data or not test_data:
        return CalibrationResult(
            protocol_version=CALIBRATION_PROTOCOL_VERSION,
            evaluation_version=CALIBRATION_EVALUATION_VERSION,
            evaluated=False,
            reason="insufficient_data_for_calibration_study",
        )

    context = dataset.research_context(protocol_version=protocol.protocol_version)

    test_rows = [CalibrationPoint(
        match_id=cp.match_id, competition_id=cp.competition_id,
        season_id=cp.season_id, kickoff_utc=cp.kickoff_utc,
        home=cp.home, draw=cp.draw, away=cp.away, outcome=cp.outcome
    ) for cp in test_data]

    raw_eval = _evaluate_rows(test_rows, context=context, protocol=protocol)

    per_class_calibration = raw_eval.get("calibration", [])
    ece_values = [item["expected_calibration_error"] for item in per_class_calibration if item["expected_calibration_error"] is not None]
    mce_values = [item["maximum_calibration_error"] for item in per_class_calibration if item["maximum_calibration_error"] is not None]
    overall_ece = sum(ece_values) / len(ece_values) if ece_values else None
    overall_mce = max(mce_values) if mce_values else None

    # Per-competition calibration
    per_competition_calibration = []
    for competition_id in sorted(set(cp.competition_id for cp in test_data)):
        comp_rows = [cp for cp in test_rows if cp.competition_id == competition_id]
        if len(comp_rows) >= 10:
            comp_eval = _evaluate_rows(comp_rows, context=context, protocol=protocol)
            per_competition_calibration.append({
                "competition_id": competition_id,
                "sample_size": len(comp_rows),
                "ece": comp_eval.get("expected_calibration_error"),
                "mce": comp_eval.get("maximum_calibration_error"),
            })

    # Per-season calibration
    per_season_calibration = []
    season_groups = {}
    for cp in test_rows:
        key = (cp.competition_id, cp.season_id)
        season_groups.setdefault(key, []).append(cp)

    for (comp_id, season_id), rows in sorted(season_groups.items()):
        if len(rows) >= 10:
            season_eval = _evaluate_rows(rows, context=context, protocol=protocol)
            per_season_calibration.append({
                "competition_id": comp_id,
                "season_id": season_id,
                "sample_size": len(rows),
                "ece": season_eval.get("expected_calibration_error"),
                "mce": season_eval.get("maximum_calibration_error"),
            })

    # Probability range calibration
    probability_range_calibration = []
    for class_idx, class_label in enumerate(["home", "draw", "away"]):
        class_probs = [getattr(cp, class_label) for cp in test_rows]
        class_outcomes = [1 if cp.outcome == class_idx else 0 for cp in test_rows]

        pairs = sorted(zip(class_probs, class_outcomes))
        n = len(pairs)
        if n < 50:
            continue

        bin_size = n // 5
        for b in range(5):
            start = b * bin_size
            end = (b + 1) * bin_size if b < 4 else n
            bin_pairs = pairs[start:end]
            bin_probs = [p for p, o in bin_pairs]
            bin_outcomes = [o for p, o in bin_pairs]
            mean_prob = sum(bin_probs) / len(bin_probs)
            obs_rate = sum(bin_outcomes) / len(bin_outcomes)

            probability_range_calibration.append({
                "class_label": class_label,
                "bin": b,
                "prob_lower": round(min(bin_probs), 3),
                "prob_upper": round(max(bin_probs), 3),
                "sample_size": len(bin_pairs),
                "mean_probability": round(mean_prob, 4),
                "observed_rate": round(obs_rate, 4),
                "calibration_gap": round(obs_rate - mean_prob, 4),
            })

    # Draw bias analysis
    draw_probs = [cp.draw for cp in test_data]
    draw_outcomes = [1 if cp.outcome == 1 else 0 for cp in test_data]
    draw_rate = sum(draw_outcomes) / len(draw_outcomes)
    mean_draw_prob = sum(draw_probs) / len(draw_probs)
    draw_bias = draw_rate - mean_draw_prob

    draw_pairs = sorted(zip(draw_probs, draw_outcomes))
    draw_bins = []
    for b in range(5):
        start = b * (len(draw_pairs) // 5)
        end = (b + 1) * (len(draw_pairs) // 5) if b < 4 else len(draw_pairs)
        bin_pairs = draw_pairs[start:end]
        if bin_pairs:
            bin_probs = [p for p, o in bin_pairs]
            bin_outcomes = [o for p, o in bin_pairs]
            mean_prob = sum(bin_probs) / len(bin_probs)
            obs_rate = sum(bin_outcomes) / len(bin_outcomes)
            draw_bins.append({
                "bin": b,
                "prob_lower": round(min(bin_probs), 3),
                "prob_upper": round(max(bin_probs), 3),
                "sample_size": len(bin_pairs),
                "mean_probability": round(mean_prob, 4),
                "observed_rate": round(obs_rate, 4),
                "gap": round(obs_rate - mean_prob, 4),
            })

    draw_bias_analysis = {
        "overall_draw_rate": round(draw_rate, 4),
        "mean_predicted_draw_prob": round(mean_draw_prob, 4),
        "draw_bias": round(draw_bias, 4),
        "bias_direction": "under-prediction" if draw_bias > 0 else "over-prediction",
        "per_bin": draw_bins,
    }

    return CalibrationResult(
        protocol_version=CALIBRATION_PROTOCOL_VERSION,
        evaluation_version=CALIBRATION_EVALUATION_VERSION,
        evaluated=True,
        sample_size=len(test_data),
        overall_ece=round(overall_ece, 4) if overall_ece is not None else None,
        overall_mce=round(overall_mce, 4) if overall_mce is not None else None,
        per_class_calibration=per_class_calibration,
        per_competition_calibration=per_competition_calibration,
        per_season_calibration=per_season_calibration,
        probability_range_calibration=probability_range_calibration,
        draw_bias_analysis=draw_bias_analysis,
        notes=[
            f"Calibration set size: {len(calibration_data)}, test set size: {len(test_data)}",
            "No calibration correction applied — diagnostic only",
            "Calibration analysis on chronologically earlier calibration set only",
        ],
    )