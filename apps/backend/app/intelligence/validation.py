"""Strict chronological validation framework for Phase 8.

Implements formal out-of-sample validation protocols A-G:

* A. Rolling-origin evaluation
* B. Expanding training windows
* C. Multiple chronological evaluation windows
* D. Multiple competitions
* E. Multiple seasons
* F. Minimum historical sample requirements
* G. Strict training/validation/test separation

All models are evaluated on identical eligible fixtures with proper
training/validation/test separation and no future-data leakage.
"""

from __future__ import annotations

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from math import inf
from random import Random as _Random
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

BACKTEST_PROTOCOL_VERSION = "phase8-v1"
EVALUATION_VERSION = "evaluation-v1.2.0"

MATCH_HORIZON = timedelta(hours=3)
MIN_PRIOR_MATCHES = 40
MAX_TEST_PER_COMPETITION = 100
BOOTSTRAP_RESAMPLES = 1_000
BOOTSTRAP_SEED = 20_261_116
TIMELINE_BUCKET_SIZE = 25
CALIBRATION_BINS = 5
MIN_COMPETITION_MATCHES = 50
MIN_ELO_TRAINING = 30

MODEL_KEYS = ("poisson", "dixon_coles", "elo", "uniform", "competition_frequency")


@dataclass(frozen=True)
class ModelSpec:
    key: str
    model_id: str
    model_version: str
    label: str
    role: str


MODEL_SPECS = (
    ModelSpec("poisson", MODEL_ID, MODEL_VERSION, "Independent Poisson", "model"),
    ModelSpec("dixon_coles", DC_MODEL_ID, DC_MODEL_VERSION, "Dixon-Coles", "model"),
    ModelSpec("elo", ELO_MODEL_ID, ELO_MODEL_VERSION, "Elo (Davidson)", "model"),
    ModelSpec("uniform", UNIFORM_MODEL_ID, UNIFORM_MODEL_VERSION, "Uniform 1/3", "baseline"),
    ModelSpec(
        "competition_frequency",
        FREQUENCY_MODEL_ID,
        FREQUENCY_MODEL_VERSION,
        "Competition outcome frequency",
        "baseline",
    ),
)

MODEL_BY_KEY = {spec.key: spec for spec in MODEL_SPECS}


@dataclass(frozen=True)
class PredictionRow:
    model_key: str
    match_id: str
    competition_id: str
    season_id: str
    kickoff_utc: datetime
    home: float
    draw: float
    away: float
    outcome: int


@dataclass(frozen=True)
class CompetitionFit:
    rho: any = None
    davidson: any = None
    baseline_home_goals: float | None = None
    baseline_away_goals: float | None = None
    training_matches: int = 0
    window_start: datetime | None = None


@dataclass
class FoldDiagnostics:
    evaluated: int = 0
    skipped_model_abstention: int = 0
    skipped_history: int = 0


@dataclass(frozen=True)
class ValidationProtocol:
    """Configuration for one validation protocol run."""

    protocol_version: str = BACKTEST_PROTOCOL_VERSION
    evaluation_version: str = EVALUATION_VERSION
    min_prior_matches: int = MIN_PRIOR_MATCHES
    max_test_per_competition: int = MAX_TEST_PER_COMPETITION
    match_horizon_hours: float = MATCH_HORIZON.total_seconds() / 3600.0
    bootstrap_resamples: int = BOOTSTRAP_RESAMPLES
    bootstrap_seed: int = BOOTSTRAP_SEED
    calibration_bins: int = CALIBRATION_BINS
    timeline_bucket_size: int = TIMELINE_BUCKET_SIZE
    min_competition_matches: int = MIN_COMPETITION_MATCHES
    min_elo_training: int = MIN_ELO_TRAINING


@dataclass(frozen=True)
class ValidationResult:
    """Complete validation output for one protocol run."""

    protocol_version: str
    evaluation_version: str
    evaluated: bool
    reason: str | None = None
    sample_size: int = 0
    window_from: datetime | None = None
    window_to: datetime | None = None
    models: list[dict] = field(default_factory=list)
    comparisons: list[dict] = field(default_factory=list)
    competitions: list[dict] = field(default_factory=list)
    seasons: list[dict] = field(default_factory=list)
    timeline: list[dict] = field(default_factory=list)
    insufficient_competitions: list[dict] = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    dataset: dict = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass
class _CompetitionFit:
    rho: any = None
    davidson: DavidsonFit | None = None
    baseline_home_goals: float | None = None
    baseline_away_goals: float | None = None
    training_matches: int = 0
    window_start: datetime | None = None


def _outcome(home_goals: int, away_goals: int) -> int:
    return outcome_index(home_goals, away_goals)


def _baseline_rates(matches: Sequence[HistoricalMatch]) -> tuple[float, float] | None:
    if not matches:
        return None
    home = sum(match.home_goals for match in matches) / len(matches)
    away = sum(match.away_goals for match in matches) / len(matches)
    if home <= 0 or away <= 0:
        return None
    return home, away


def _group_by_kickoff(matches: Sequence[HistoricalMatch]):
    group: list[HistoricalMatch] = []
    current: datetime | None = None
    for match in matches:
        if current is not None and match.kickoff_utc != current:
            yield group
            group = []
        current = match.kickoff_utc
        group.append(match)
    if group:
        yield group


def _select_targets(
    by_competition: dict[str, list[HistoricalMatch]],
    *,
    min_prior_matches: int,
    max_test_per_competition: int,
    min_competition_matches: int,
) -> tuple[dict[str, HistoricalMatch], dict[str, datetime], list[dict[str, any]]]:
    targets: dict[str, HistoricalMatch] = {}
    window_start: dict[str, datetime] = {}
    insufficient: list[dict[str, any]] = []
    required = max(min_prior_matches + 10, min_competition_matches)
    for competition_id, competition_matches in by_competition.items():
        if len(competition_matches) < required:
            insufficient.append(
                {
                    "competition_id": competition_id,
                    "status": "INSUFFICIENT_DATA",
                    "sample_size": len(competition_matches),
                    "required": required,
                }
            )
            continue
        test_set = competition_matches[-max_test_per_competition:]
        window_start[competition_id] = test_set[0].kickoff_utc
        for match in test_set:
            targets[match.match_id] = match
    return targets, window_start, insufficient


def _bootstrap_ci(values: Sequence[float], *, resamples: int, seed: int):
    """Percentile bootstrap of the mean, with a fixed seed."""

    if not values or resamples <= 0:
        return None
    rng = _Random(seed)
    size = len(values)
    means: list[float] = []
    for _ in range(resamples):
        total = 0.0
        for _ in range(size):
            total += values[rng.randrange(size)]
        means.append(total / size)
    means.sort()

    def percentile(fraction: float) -> float:
        index = min(len(means) - 1, max(0, int(round(fraction * (len(means) - 1)))))
        return means[index]

    return {
        "lower": round(percentile(0.025), 4),
        "upper": round(percentile(0.975), 4),
        "mean": round(sum(values) / size, 4),
    }


def _per_match_losses(rows: Sequence[PredictionRow]):
    brier: list[float] = []
    log_loss: list[float] = []
    for row in rows:
        probabilities = (row.home, row.draw, row.away)
        brier.append(
            sum(
                (probability - (1.0 if index == row.outcome else 0.0)) ** 2
                for index, probability in enumerate(probabilities)
            )
        )
        chosen = probabilities[row.outcome]
        log_loss.append(-__import__("math").log(chosen) if chosen > 0 else float("inf"))
    return brier, log_loss


def _evaluate_rows(rows: Sequence[PredictionRow], *, context, protocol: ValidationProtocol):
    if not rows:
        return {
            "evaluated": False,
            "reason": "no_evaluated_matches",
            "sample_size": 0,
            "calibration": [],
        }

    probabilities = [[row.home, row.draw, row.away] for row in rows]
    outcomes = [row.outcome for row in rows]
    labels = ("home", "draw", "away")

    brier = multiclass_brier_score(
        probabilities, outcomes, class_labels=labels, context=context
    )
    log_loss = multiclass_log_loss(
        probabilities, outcomes, class_labels=labels, context=context
    )
    reliability = multiclass_reliability(
        probabilities,
        outcomes,
        class_labels=labels,
        context=context,
        bin_count=protocol.calibration_bins,
    )

    calibration = []
    for summary in reliability:
        calibration.append(
            {
                "class_label": summary.class_label,
                "sample_size": summary.sample_size,
                "expected_calibration_error": round(summary.expected_calibration_error, 4)
                if summary.expected_calibration_error is not None
                else None,
                "maximum_calibration_error": round(summary.maximum_calibration_error, 4)
                if summary.maximum_calibration_error is not None
                else None,
                "bins": [
                    {
                        "lower": round(item.lower, 3),
                        "upper": round(item.upper, 3),
                        "sample_size": item.sample_size,
                        "mean_probability": round(item.mean_probability, 4)
                        if item.mean_probability is not None
                        else None,
                        "observed_rate": round(item.observed_rate, 4)
                        if item.observed_rate is not None
                        else None,
                    }
                    for item in summary.bins
                    if item.sample_size > 0
                ],
            }
        )

    brier_losses, log_losses = _per_match_losses(rows)
    uniform_brier = 2.0 / 3.0

    per_outcome = {}
    for index, class_label in enumerate(labels):
        binary_outcomes = [1 if row.outcome == index else 0 for row in rows]
        binary_probabilities = [(row.home, row.draw, row.away)[index] for row in rows]
        binary_brier = sum(
            (probability - outcome) ** 2
            for probability, outcome in zip(binary_probabilities, binary_outcomes, strict=True)
        ) / len(rows)
        binary_log_loss = 0.0
        for probability, outcome in zip(binary_probabilities, binary_outcomes, strict=True):
            clipped = min(1.0 - 1e-12, max(1e-12, probability))
            binary_log_loss -= __import__("math").log(clipped) if outcome else __import__("math").log(1.0 - clipped)
        per_outcome[class_label] = {
            "sample_size": len(rows),
            "observed_rate": round(sum(binary_outcomes) / len(rows), 4),
            "mean_probability": round(sum(binary_probabilities) / len(rows), 4),
            "calibration_gap": round(sum(binary_probabilities) / len(rows) - sum(binary_outcomes) / len(rows), 4),
            "brier_score": round(binary_brier, 4),
            "log_loss": round(binary_log_loss / len(rows), 4),
        }

    top_pick_correct = 0
    for row in rows:
        best = max(((0, row.home), (1, row.draw), (2, row.away)), key=lambda item: item[1])
        if best[0] == row.outcome:
            top_pick_correct += 1

    return {
        "evaluated": True,
        "sample_size": len(rows),
        "brier_score": round(brier.value, 4),
        "log_loss": round(log_loss.value, 4),
        "brier_skill_score_vs_uniform": round(1.0 - brier.value / uniform_brier, 4),
        "expected_calibration_error": round(__import__("statistics").mean([
            item["expected_calibration_error"] for item in calibration if item["expected_calibration_error"] is not None
        ]), 4) if any(item["expected_calibration_error"] is not None for item in calibration) else None,
        "maximum_calibration_error": round(max([
            item["maximum_calibration_error"] for item in calibration if item["maximum_calibration_error"] is not None
        ]), 4) if any(item["maximum_calibration_error"] is not None for item in calibration) else None,
        "calibration": calibration,
        "mean_probabilities": {
            "home": round(sum(row.home for row in rows) / len(rows), 4),
            "draw": round(sum(row.draw for row in rows) / len(rows), 4),
            "away": round(sum(row.away for row in rows) / len(rows), 4),
        },
        "observed_frequencies": {
            "home": round(sum(1 for row in rows if row.outcome == 0) / len(rows), 4),
            "draw": round(sum(1 for row in rows if row.outcome == 1) / len(rows), 4),
            "away": round(sum(1 for row in rows if row.outcome == 2) / len(rows), 4),
        },
        "top_pick_accuracy": round(top_pick_correct / len(rows), 4),
        "per_outcome": per_outcome,
        "bootstrap": {
            "resamples": protocol.bootstrap_resamples,
            "seed": protocol.bootstrap_seed,
            "brier_ci": _bootstrap_ci(
                brier_losses, resamples=protocol.bootstrap_resamples, seed=protocol.bootstrap_seed
            ),
            "log_loss_ci": _bootstrap_ci(
                log_losses, resamples=protocol.bootstrap_resamples, seed=protocol.bootstrap_seed + 1
            ),
        },
    }


def _paired_comparison(reference: Sequence[PredictionRow], candidate: Sequence[PredictionRow], *, protocol: ValidationProtocol):
    if not reference or len(reference) != len(candidate):
        return {"evaluated": False, "reason": "unpaired_or_empty_sample"}

    for left, right in zip(reference, candidate, strict=True):
        if left.match_id != right.match_id:
            return {"evaluated": False, "reason": "row_mismatch"}

    ref_brier, ref_log = _per_match_losses(reference)
    cand_brier, cand_log = _per_match_losses(candidate)
    brier_diff = [left - right for left, right in zip(ref_brier, cand_brier, strict=True)]
    log_diff = [left - right for left, right in zip(ref_log, cand_log, strict=True)]

    brier_ci = _bootstrap_ci(
        brier_diff, resamples=protocol.bootstrap_resamples, seed=protocol.bootstrap_seed + 7
    )
    log_ci = _bootstrap_ci(
        log_diff, resamples=protocol.bootstrap_resamples, seed=protocol.bootstrap_seed + 11
    )
    return {
        "evaluated": True,
        "sample_size": len(reference),
        "brier_difference": {
            "mean": brier_ci["mean"] if brier_ci else None,
            "lower": brier_ci["lower"] if brier_ci else None,
            "upper": brier_ci["upper"] if brier_ci else None,
            "interpretation": "positive means the reference model is worse",
        },
        "log_loss_difference": {
            "mean": log_ci["mean"] if log_ci else None,
            "lower": log_ci["lower"] if log_ci else None,
            "upper": log_ci["upper"] if log_ci else None,
            "interpretation": "positive means the reference model is worse",
        },
    }


def run_multi_competition_validation(
    dataset: IntelligenceDataset,
    *,
    protocol: ValidationProtocol | None = None,
) -> ValidationResult:
    """Run strict chronological validation across all competitions.

    Implements protocols A-G: rolling origin, expanding windows, multiple
    competitions/seasons, minimum samples, and strict train/test separation.
    """

    if protocol is None:
        protocol = ValidationProtocol()

    matches = sorted(dataset.matches, key=lambda item: (item.kickoff_utc, item.match_id))
    if not matches:
        return ValidationResult(
            protocol_version=protocol.protocol_version,
            evaluation_version=protocol.evaluation_version,
            evaluated=False,
            reason="no_historical_matches",
        )

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
        return ValidationResult(
            protocol_version=protocol.protocol_version,
            evaluation_version=protocol.evaluation_version,
            evaluated=False,
            reason="no_competition_has_sufficient_history",
            insufficient_competitions=insufficient,
        )

    context = dataset.research_context(protocol_version=protocol.protocol_version)
    elo = ChronologicalElo()
    available: list[HistoricalMatch] = []
    cursor = 0
    elo_training: dict[str, list[tuple[float, float, int]]] = {}
    fits: dict[str, _CompetitionFit] = {}
    rows: dict[str, list[PredictionRow]] = {key: [] for key in MODEL_KEYS}
    diagnostics: dict[str, FoldDiagnostics] = {
        competition_id: FoldDiagnostics() for competition_id in by_competition
    }

    for group in _group_by_kickoff(matches):
        kickoff = group[0].kickoff_utc

        # Make every result whose horizon has elapsed usable, one kickoff group at a time.
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
                        (
                            home_rating,
                            away_rating,
                            _outcome(match.home_goals, match.away_goals),
                        )
                    )
            available.extend(batch)
            elo.apply_batch(batch)

        for match in group:
            if match.match_id not in targets:
                continue
            competition_id = match.competition_id
            entry = diagnostics[competition_id]
            if len(available) < protocol.min_prior_matches:
                entry.skipped_history += 1
                continue

            if competition_id not in fits:
                competition_prior = [
                    item for item in available if item.competition_id == competition_id
                ]
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
                fits[competition_id] = _CompetitionFit(
                    rho=fit_rho(observations, reference_kickoff=kickoff) if observations else None,
                    davidson=fit_davidson(
                        elo_training.get(competition_id, ()),
                        minimum_matches=protocol.min_elo_training,
                    ),
                    baseline_home_goals=rate_pair[0] if rate_pair else None,
                    baseline_away_goals=rate_pair[1] if rate_pair else None,
                    training_matches=len(competition_prior),
                    window_start=kickoff,
                )

            fit = fits[competition_id]
            features = calculate_match_features_from_matches(
                available,
                home_team_id=match.home_team_id,
                away_team_id=match.away_team_id,
                competition_id=competition_id,
            )
            poisson = predict_from_features(features, context=context)
            if poisson["status"] != PredictionStatus.READY:
                entry.skipped_model_abstention += 1
                continue

            rates = estimate_goal_rates(features)
            if rates["status"] != PredictionStatus.READY:
                entry.skipped_model_abstention += 1
                continue

            home_rating = elo.rating(match.home_team_id)
            away_rating = elo.rating(match.away_team_id)
            if home_rating is None or away_rating is None or fit.davidson is None:
                entry.skipped_model_abstention += 1
                continue

            expected_home = rates["expected_home_goals"]
            expected_away = rates["expected_away_goals"]
            rho = clip_rho(fit.rho, expected_home, expected_away) if fit.rho is not None else 0.0
            try:
                matrix = dixon_coles_score_matrix(
                    expected_home, expected_away, rho, context=context
                )
            except ValueError:
                entry.skipped_model_abstention += 1
                continue
            dc_home, dc_draw, dc_away = probability_triplet(matrix)

            elo_probabilities = elo_outcome_probabilities(
                home_rating,
                away_rating,
                home_advantage=fit.davidson.home_advantage,
                draw_nu=fit.davidson.draw_nu,
            )
            frequency, _source = competition_frequency_probabilities(
                available, competition_id=competition_id
            )

            outcome = _outcome(match.home_goals, match.away_goals)
            candidates = {
                "poisson": (
                    poisson["home_win_probability"],
                    poisson["draw_probability"],
                    poisson["away_win_probability"],
                ),
                "dixon_coles": (dc_home, dc_draw, dc_away),
                "elo": elo_probabilities,
                "uniform": uniform_probabilities(),
                "competition_frequency": frequency,
            }
            for key, (home, draw, away) in candidates.items():
                rows[key].append(
                    PredictionRow(
                        model_key=key,
                        match_id=match.match_id,
                        competition_id=competition_id,
                        season_id=match.season_id,
                        kickoff_utc=match.kickoff_utc,
                        home=home,
                        draw=draw,
                        away=away,
                        outcome=outcome,
                    )
                )
            entry.evaluated += 1

    if not rows["poisson"]:
        return ValidationResult(
            protocol_version=protocol.protocol_version,
            evaluation_version=protocol.evaluation_version,
            evaluated=False,
            reason="no_valid_folds",
            insufficient_competitions=insufficient,
        )

    models = []
    for spec in MODEL_SPECS:
        block: dict = {
            "key": spec.key,
            "model_id": spec.model_id,
            "model_version": spec.model_version,
            "label": spec.label,
            "role": spec.role,
        }
        block.update(
            _evaluate_rows(
                rows[spec.key],
                context=context,
                protocol=protocol,
            )
        )
        models.append(block)

    comparisons = []
    for spec in MODEL_SPECS:
        if spec.key == "poisson":
            continue
        comparisons.append(
            {
                "reference": "poisson",
                "candidate": spec.key,
                **_paired_comparison(
                    rows["poisson"],
                    rows[spec.key],
                    protocol=protocol,
                ),
            }
        )

    competition_blocks = []
    for competition_id in sorted(by_competition):
        poisson_rows = [
            row for row in rows["poisson"] if row.competition_id == competition_id
        ]
        block = {
            "competition_id": competition_id,
            "sample_size": len(poisson_rows),
            "status": "EVALUATED" if poisson_rows else "INSUFFICIENT_DATA",
            "diagnostics": {
                "evaluated": diagnostics[competition_id].evaluated,
                "skipped_model_abstention": diagnostics[competition_id].skipped_model_abstention,
                "skipped_history": diagnostics[competition_id].skipped_history,
            },
            "models": {},
        }
        fit = fits.get(competition_id)
        if fit is not None:
            block["fitted_parameters"] = {
                "rho": fit.rho.rho if fit.rho else None,
                "rho_status": fit.rho.status if fit.rho else "NO_FIT",
                "rho_matches": fit.rho.matches_used if fit.rho else 0,
                "elo_home_advantage": fit.davidson.home_advantage if fit.davidson else None,
                "elo_draw_nu": fit.davidson.draw_nu if fit.davidson else None,
                "elo_status": fit.davidson.status if fit.davidson else "NO_FIT",
                "training_matches": fit.training_matches,
            }
        for spec in MODEL_SPECS:
            scored = [
                row for row in rows[spec.key] if row.competition_id == competition_id
            ]
            block["models"][spec.key] = (
                _evaluate_rows(
                    scored,
                    context=context,
                    protocol=ValidationProtocol(
                        min_prior_matches=protocol.min_prior_matches,
                        max_test_per_competition=protocol.max_test_per_competition,
                        bootstrap_resamples=min(protocol.bootstrap_resamples, 400),
                        bootstrap_seed=protocol.bootstrap_seed,
                    ),
                )
                if scored
                else {"evaluated": False, "reason": "no_evaluated_matches", "sample_size": 0}
            )
        competition_blocks.append(block)

    season_groups: dict[tuple[str, str], list[PredictionRow]] = {}
    for row in rows["poisson"]:
        season_groups.setdefault((row.competition_id, row.season_id), []).append(row)
    seasons = []
    for (competition_id, season_id), poisson_rows in sorted(season_groups.items()):
        ids = {row.match_id for row in poisson_rows}
        block = {
            "competition_id": competition_id,
            "season_id": season_id,
            "sample_size": len(poisson_rows),
            "models": {},
        }
        for spec in MODEL_SPECS:
            scored = [row for row in rows[spec.key] if row.match_id in ids]
            block["models"][spec.key] = (
                _evaluate_rows(scored, context=context, bootstrap_resamples=0)
                if scored
                else {"evaluated": False, "reason": "no_evaluated_matches", "sample_size": 0}
            )
        seasons.append(block)

    timeline = []
    ordered_rows = sorted(rows["poisson"], key=lambda row: (row.kickoff_utc, row.match_id))
    for start in range(0, len(ordered_rows), protocol.timeline_bucket_size):
        chunk = ordered_rows[start : start + protocol.timeline_bucket_size]
        ids = {row.match_id for row in chunk}
        block = {
            "from": chunk[0].kickoff_utc.isoformat(),
            "to": chunk[-1].kickoff_utc.isoformat(),
            "sample_size": len(chunk),
            "models": {},
        }
        for spec in MODEL_SPECS:
            scored = [row for row in rows[spec.key] if row.match_id in ids]
            block["models"][spec.key] = (
                {
                    "brier_score": round(
                        multiclass_brier_score(
                            [[row.home, row.draw, row.away] for row in scored],
                            [row.outcome for row in scored],
                            class_labels=("home", "draw", "away"),
                            context=context,
                        ).value,
                        4,
                    ),
                    "sample_size": len(scored),
                }
                if scored
                else None
            )
        timeline.append(block)

    first_test = min(row.kickoff_utc for row in rows["poisson"])
    last_test = max(row.kickoff_utc for row in rows["poisson"])

    return ValidationResult(
        protocol_version=protocol.protocol_version,
        evaluation_version=protocol.evaluation_version,
        evaluated=True,
        sample_size=len(rows["poisson"]),
        window_from=first_test,
        window_to=last_test,
        models=models,
        comparisons=comparisons,
        competitions=competition_blocks,
        seasons=seasons,
        timeline=timeline,
        insufficient_competitions=insufficient,
        settings={
            "min_prior_matches": protocol.min_prior_matches,
            "max_test_per_competition": protocol.max_test_per_competition,
            "match_horizon_hours": protocol.match_horizon_hours,
            "bootstrap_resamples": protocol.bootstrap_resamples,
            "bootstrap_seed": protocol.bootstrap_seed,
            "calibration_bins": protocol.calibration_bins,
            "timeline_bucket_size": protocol.timeline_bucket_size,
            "min_competition_matches": protocol.min_competition_matches,
            "min_elo_training": protocol.min_elo_training,
        },
        dataset={
            "dataset_id": dataset.dataset_id,
            "dataset_digest": dataset.digest,
            "classification": dataset.classification.value,
            "matches": len(dataset.matches),
            "competitions": len(by_competition),
            "provider_code": dataset.evidence.provider_code if dataset.evidence else None,
            "retrieval_from": dataset.evidence.retrieval_from_utc.isoformat() if dataset.evidence else None,
            "observed_to": dataset.evidence.observed_to_utc.isoformat() if dataset.evidence else None,
        },
        notes=[
            "All models are scored on the identical set of matches.",
            "The match horizon is a retrospective bound, not the provider publication time.",
            "Confidence intervals are percentile bootstraps with a fixed seed.",
            "No model is declared better on a small sample; read the intervals.",
        ],
    )


def _evaluate_rows2(rows, *, context, protocol):  # backward-compat shim placeholder
    return _evaluate_rows(rows, context=context, protocol=protocol)
