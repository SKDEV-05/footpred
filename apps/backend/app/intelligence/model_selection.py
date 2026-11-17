"""Per-model match prediction used by model selection and comparison.

Phase 7 exposes three models side by side. This module is the only place that maps a
public model key to an implementation, so a request can never be silently answered by a
different model:

* ``poisson`` — the permanent baseline (``poisson-v1.1.0``).
* ``dixon_coles`` — same rates, fitted low-score dependence (``dixon-coles-v1.0.0``).
* ``elo`` — chronological replay plus a Davidson outcome mapping (``elo-v1.0.0``).

Every function takes a point-in-time dataset: the caller is responsible for loading only
results observed before the target kickoff. Nothing here re-checks the clock, and nothing
here reaches outside the supplied matches.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Sequence

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
    elo_outcome_probabilities,
    fit_davidson,
    outcome_index,
)
from app.intelligence.prediction import (
    FEATURE_VERSION,
    MODEL_ID,
    MODEL_VERSION,
    PredictionStatus,
    estimate_goal_rates,
    predict_from_features,
    probability_triplet,
)
from app.intelligence.probabilities import (
    both_teams_to_score,
    over_probability,
    top_scorelines,
)
from app.intelligence.types import HistoricalMatch, IntelligenceDataset, ResearchContext

# Minimum competition matches used to fit rho or the Davidson mapping. The same
# thresholds are used by the backtest, so the live and evaluated configurations match.
MIN_FIT_MATCHES = 30


@dataclass(frozen=True)
class ModelSpec:
    key: str
    model_id: str
    model_version: str
    label: str


MODEL_SPECS = (
    ModelSpec("poisson", MODEL_ID, MODEL_VERSION, "Independent Poisson"),
    ModelSpec("dixon_coles", DC_MODEL_ID, DC_MODEL_VERSION, "Dixon-Coles"),
    ModelSpec("elo", ELO_MODEL_ID, ELO_MODEL_VERSION, "Elo (Davidson)"),
)

MODEL_BY_KEY = {spec.key: spec for spec in MODEL_SPECS}
DEFAULT_MODEL_KEY = "poisson"


def allowed_model_keys() -> tuple[str, ...]:
    return tuple(spec.key for spec in MODEL_SPECS)


def require_model_spec(key: str) -> ModelSpec:
    spec = MODEL_BY_KEY.get(key)
    if spec is None:
        raise ValueError(
            f"unknown model {key!r}; allowed models are {', '.join(allowed_model_keys())}"
        )
    return spec


def _outcome(home_goals: int, away_goals: int) -> int:
    return outcome_index(home_goals, away_goals)


def _competition_rates(
    matches: Sequence[HistoricalMatch],
) -> tuple[float, float] | None:
    if not matches:
        return None
    home = sum(item.home_goals for item in matches) / len(matches)
    away = sum(item.away_goals for item in matches) / len(matches)
    if home <= 0 or away <= 0:
        return None
    return home, away


def _kickoff_groups(
    matches: Sequence[HistoricalMatch],
) -> list[list[HistoricalMatch]]:
    ordered = sorted(matches, key=lambda item: (item.kickoff_utc, item.match_id))
    groups: list[list[HistoricalMatch]] = []
    current: datetime | None = None
    for match in ordered:
        if current is not None and match.kickoff_utc != current:
            groups.append([])
        elif current is None:
            groups.append([])
        current = match.kickoff_utc
        groups[-1].append(match)
    return groups


def replay_elo(
    matches: Sequence[HistoricalMatch],
    *,
    competition_id: str,
    reference_kickoff: datetime,
) -> dict[str, Any]:
    """Replay the corpus chronologically and prepare the Elo inputs for one fixture.

    Matches at or after ``reference_kickoff`` are ignored even if a caller supplies
    them, so the target fixture (or a simultaneous unplayed fixture) can never
    influence the ratings it is predicted from. Pre-match ratings are captured before
    each kickoff group is applied, which makes the Davidson fit a training-only fit.
    """

    eligible = [item for item in matches if item.kickoff_utc < reference_kickoff]
    elo = ChronologicalElo()
    training: list[tuple[float, float, int]] = []
    rated_teams: set[str] = set()

    for group in _kickoff_groups(eligible):
        for match in group:
            if match.competition_id != competition_id:
                continue
            home_rating = elo.rating(match.home_team_id)
            away_rating = elo.rating(match.away_team_id)
            if home_rating is None or away_rating is None:
                continue
            training.append(
                (
                    home_rating,
                    away_rating,
                    _outcome(match.home_goals, match.away_goals),
                )
            )
        elo.apply_batch(group)
        for match in group:
            rated_teams.add(match.home_team_id)
            rated_teams.add(match.away_team_id)

    fit = fit_davidson(training, minimum_matches=MIN_FIT_MATCHES)
    return {
        "elo": elo,
        "fit": fit,
        "training_matches": len(training),
        "rated_teams": rated_teams,
        "reference_kickoff": reference_kickoff,
    }


def _dixon_coles_prediction(
    dataset: IntelligenceDataset,
    features: dict[str, Any],
    *,
    competition_id: str,
    kickoff_utc: datetime,
    context: ResearchContext,
) -> dict[str, Any]:
    rates = estimate_goal_rates(features)
    if rates["status"] != PredictionStatus.READY:
        return {**rates, "model_id": DC_MODEL_ID, "model_version": DC_MODEL_VERSION}

    expected_home = rates["expected_home_goals"]
    expected_away = rates["expected_away_goals"]

    competition_matches = [
        item for item in dataset.matches if item.competition_id == competition_id
    ]
    rate_pair = _competition_rates(competition_matches)
    observations = (
        [
            LowScoreObservation(
                home_rate=rate_pair[0],
                away_rate=rate_pair[1],
                home_goals=item.home_goals,
                away_goals=item.away_goals,
                kickoff_utc=item.kickoff_utc,
            )
            for item in competition_matches
        ]
        if rate_pair
        else []
    )
    rho_fit = (
        fit_rho(observations, reference_kickoff=kickoff_utc)
        if observations
        else None
    )
    rho = (
        clip_rho(rho_fit, expected_home, expected_away)
        if rho_fit is not None
        else 0.0
    )
    matrix = dixon_coles_score_matrix(
        expected_home, expected_away, rho, context=context
    )
    home, draw, away = probability_triplet(matrix)

    p_over_1_5 = round(over_probability(matrix, 1.5), 4)
    p_over_2_5 = round(over_probability(matrix, 2.5), 4)
    p_over_3_5 = round(over_probability(matrix, 3.5), 4)
    btts = round(both_teams_to_score(matrix).yes, 4)
    scorelines = [
        {"home_goals": h, "away_goals": a, "probability": round(p, 4)}
        for h, a, p in top_scorelines(matrix, limit=5)
    ]

    limitations = [
        "dixon_coles_low_score_correction",
        "two_stage_rate_and_rho_estimation_not_joint_mle",
        "rho_fitted_on_training_matches_only",
        "opponent_strength_estimated_from_historical_averages",
        "in_match_statistics_unavailable_on_free_tier",
        "no_lineup_or_injury_data",
        "probabilities_are_estimates_not_guarantees",
        "no_real_world_performance_claim",
    ]

    return {
        "status": PredictionStatus.READY,
        "model_id": DC_MODEL_ID,
        "model_version": DC_MODEL_VERSION,
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
        "h2h_sample_size": None,
        "model_parameters": {
            **rates["parameters"],
            "rho": round(rho, 6),
            "rho_fit": {
                "status": rho_fit.status if rho_fit else "NO_FIT",
                "matches_used": rho_fit.matches_used if rho_fit else 0,
                "half_life_days": rho_fit.half_life_days if rho_fit else None,
                "bound_lower": rho_fit.bound_lower if rho_fit else None,
                "bound_upper": rho_fit.bound_upper if rho_fit else None,
            },
        },
        "explanation": {
            "model_rationale": (
                "Dixon-Coles applies the same competition-baselined expected goals as "
                "Poisson, then adjusts the 0-0, 1-0, 0-1 and 1-1 cells with a rho "
                "estimated on earlier matches in this competition. Positive rho raises "
                "draw mass; negative rho lowers it."
            ),
            "expected_goals_breakdown": {
                "home": (
                    f"{expected_home:.2f} expected goals = baseline "
                    f"{rates['parameters']['baseline_avg_home_goals']:.3f} x home attack "
                    f"{rates['parameters']['home_attack_strength']:.3f} x away defence "
                    f"{rates['parameters']['away_defence_strength']:.3f}"
                ),
                "away": (
                    f"{expected_away:.2f} expected goals = baseline "
                    f"{rates['parameters']['baseline_avg_away_goals']:.3f} x away attack "
                    f"{rates['parameters']['away_attack_strength']:.3f} x home defence "
                    f"{rates['parameters']['home_defence_strength']:.3f}"
                ),
            },
            "form_impact": (
                "Form weighting is identical to the Poisson baseline; Dixon-Coles only "
                "changes the low-score dependence."
            ),
            "h2h_impact": (
                "Head-to-head is not used to fit rho or the goal rates."
            ),
        },
        "limitations": limitations,
        "rho": round(rho, 6),
    }


def _elo_prediction(
    dataset: IntelligenceDataset,
    features: dict[str, Any],
    *,
    home_team_id: str,
    away_team_id: str,
    competition_id: str,
    kickoff_utc: datetime,
) -> dict[str, Any]:
    state = replay_elo(
        dataset.matches,
        competition_id=competition_id,
        reference_kickoff=kickoff_utc,
    )
    elo: ChronologicalElo = state["elo"]
    fit = state["fit"]
    rated: set[str] = state["rated_teams"]

    home_rating = elo.rating(home_team_id)
    away_rating = elo.rating(away_team_id)
    if home_rating is None and away_rating is None:
        return {
            "status": PredictionStatus.INSUFFICIENT_DATA,
            "reason": (
                "Neither team has a prior result in the stored history; Elo cannot "
                "produce a rating-based probability."
            ),
            "model_id": ELO_MODEL_ID,
            "model_version": ELO_MODEL_VERSION,
            "limitations": ["no_historical_ratings", "predictions_abstained"],
        }

    initial = 1500.0
    home_value = home_rating if home_rating is not None else initial
    away_value = away_rating if away_rating is not None else initial
    home, draw, away = elo_outcome_probabilities(
        home_value,
        away_value,
        home_advantage=fit.home_advantage,
        draw_nu=fit.draw_nu,
    )
    home = round(home, 4)
    draw = round(draw, 4)
    away = round(1.0 - home - draw, 4)

    limitations = [
        "elo_outcome_only_no_score_distribution",
        "elo_ratings_ignore_goals_margin",
        "davidson_draw_mapping_fitted_on_earlier_matches",
        "in_match_statistics_unavailable_on_free_tier",
        "no_lineup_or_injury_data",
        "probabilities_are_estimates_not_guarantees",
        "no_real_world_performance_claim",
    ]
    if home_team_id not in rated:
        limitations.append("home_team_uses_initial_elo_rating")
    if away_team_id not in rated:
        limitations.append("away_team_uses_initial_elo_rating")
    if fit.status != "FITTED":
        limitations.append("davidson_mapping_uses_default_parameters")

    return {
        "status": PredictionStatus.READY,
        "model_id": ELO_MODEL_ID,
        "model_version": ELO_MODEL_VERSION,
        "feature_version": None,
        "expected_home_goals": None,
        "expected_away_goals": None,
        "home_win_probability": home,
        "draw_probability": draw,
        "away_win_probability": away,
        # Elo is a 1X2 baseline: it carries no scoreline, no BTTS and no over/under.
        "btts_probability": None,
        "over_1_5_probability": None,
        "under_1_5_probability": None,
        "over_2_5_probability": None,
        "under_2_5_probability": None,
        "over_3_5_probability": None,
        "under_3_5_probability": None,
        "scoreline_probabilities": [],
        "home_sample_size": None,
        "away_sample_size": None,
        "h2h_sample_size": None,
        "model_parameters": {
            "home_rating": round(home_value, 3),
            "away_rating": round(away_value, 3),
            "rating_difference": round(home_value - away_value, 3),
            "home_advantage": fit.home_advantage,
            "draw_nu": fit.draw_nu,
            "k_factor": elo.config.k_factor,
            "initial_rating": elo.config.initial_rating,
            "scale": elo.config.scale,
            "training_matches": state["training_matches"],
            "fit_status": fit.status,
        },
        "explanation": {
            "model_rationale": (
                "Ratings are updated after every match in kickoff order. The pre-match "
                "rating difference plus a fitted home-advantage offset drives a "
                "Davidson draw model, which maps the difference to home/draw/away "
                "probabilities. Elo produces no score distribution."
            ),
            "expected_goals_breakdown": {},
            "form_impact": (
                "Recent results affect the rating through the fixed K-factor; there is "
                "no separate form term."
            ),
            "h2h_impact": "Head-to-head is not used by the Elo replay.",
        },
        "limitations": limitations,
    }


def compute_model_prediction(
    dataset: IntelligenceDataset,
    features: dict[str, Any],
    *,
    model_key: str,
    home_team_id: str,
    away_team_id: str,
    competition_id: str,
    kickoff_utc: datetime,
) -> dict[str, Any]:
    """Dispatch to one model. Never substitutes another model on failure."""

    spec = require_model_spec(model_key)
    context = dataset.research_context(protocol_version="phase7-v1")

    if spec.key == "poisson":
        result = predict_from_features(features, context=context)
    elif spec.key == "dixon_coles":
        result = _dixon_coles_prediction(
            dataset,
            features,
            competition_id=competition_id,
            kickoff_utc=kickoff_utc,
            context=context,
        )
    elif spec.key == "elo":
        result = _elo_prediction(
            dataset,
            features,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            competition_id=competition_id,
            kickoff_utc=kickoff_utc,
        )
    else:  # pragma: no cover - guarded by require_model_spec
        raise ValueError(f"unhandled model key {spec.key!r}")

    result.setdefault("model_id", spec.model_id)
    result.setdefault("model_version", spec.model_version)
    result["requested_model"] = spec.key
    result["dataset_id"] = dataset.dataset_id
    result["dataset_digest"] = dataset.digest
    return result
