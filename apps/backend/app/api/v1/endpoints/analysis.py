"""Match analysis and prediction endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.api.v1.mappers import country_out
from app.core.exceptions import AppError, NotFoundError
from app.core.time import utc_now
from app.intelligence.model_selection import (
    allowed_model_keys,
    compute_model_prediction,
    require_model_spec,
)
from app.intelligence.prediction import (
    EVALUATION_VERSION,
    MODEL_ID,
    MODEL_VERSION,
    calculate_match_features,
    compute_historical_backtest_evaluation,
    run_statistical_prediction,
)
from app.models.analysis import AnalysisStatus, MatchAnalysis
from app.models.core import Match
from app.models.enums import MatchStatus
from app.repositories.analysis import DatasetProvenanceError, load_point_in_time_dataset
from app.schemas.analysis import (
    AnalysisHistoryItem,
    DataQualityOut,
    EvaluationOut,
    ExplanationOut,
    HeadToHeadOut,
    HistoricalContextOut,
    MatchAnalysisOut,
    MatchOverviewOut,
    ModelComparisonItemOut,
    ModelComparisonOut,
    ScorelineProbabilityOut,
    StatisticalModelOut,
    TeamContextOut,
    TeamRecordOut,
)
from app.schemas.fixtures import CompetitionRef, SeasonRef, TeamRef

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])

UNPLAYABLE_STATUSES = frozenset(
    {
        MatchStatus.CANCELLED,
        MatchStatus.AWARDED,
        MatchStatus.POSTPONED,
        MatchStatus.SUSPENDED,
        MatchStatus.ABANDONED,
        MatchStatus.IN_PLAY,
        MatchStatus.PAUSED,
        MatchStatus.EXTRA_TIME,
        MatchStatus.PENALTY_SHOOTOUT,
        MatchStatus.FINISHED,
    }
)

STATISTICS_NOTE = (
    "In-match statistics (shots, possession, fouls) are not supplied by the free "
    "provider tier. No statistic has been estimated or filled with zero."
)


def _overview(match: Match) -> MatchOverviewOut:
    return MatchOverviewOut(
        match_id=match.id,
        competition=CompetitionRef(
            id=match.competition.id,
            name=match.competition.name,
            code=match.competition.code,
            country=country_out(match.competition.country),
            emblem_url=match.competition.emblem_url,
        ),
        season=SeasonRef(id=match.season.id, label=match.season.label),
        home_team=TeamRef(
            id=match.home_team.id,
            name=match.home_team.name,
            crest_url=match.home_team.crest_url,
        ),
        away_team=TeamRef(
            id=match.away_team.id,
            name=match.away_team.name,
            crest_url=match.away_team.crest_url,
        ),
        kickoff_utc=match.kickoff_utc,
    )


def _map_analysis_out(record: MatchAnalysis, match: Match) -> MatchAnalysisOut:
    """Map a persisted analysis row to the API contract."""

    hist_context = None
    quality_data: dict[str, Any] = {}
    missing_features: list[str] = []
    if record.features:
        features = record.features
        quality_data = features.get("data_quality", {}) or {}
        missing_features = features.get("missing_features", []) or []
        home_team = features.get("home_team", {})
        away_team = features.get("away_team", {})
        head_to_head = features.get("head_to_head", {})
        competition = features.get("competition", {})

        hist_context = HistoricalContextOut(
            home_team=TeamContextOut(
                overall=TeamRecordOut(**home_team.get("overall", {})),
                venue_specific=TeamRecordOut(**home_team.get("home", {})),
                recent_form=home_team.get("recent_form", ""),
                recent_matches=home_team.get("recent_matches", 0),
                recent_goals_for_avg=home_team.get("recent_goals_for_avg"),
                recent_goals_against_avg=home_team.get("recent_goals_against_avg"),
                sample_size=home_team.get("sample_size", 0),
            ),
            away_team=TeamContextOut(
                overall=TeamRecordOut(**away_team.get("overall", {})),
                venue_specific=TeamRecordOut(**away_team.get("away", {})),
                recent_form=away_team.get("recent_form", ""),
                recent_matches=away_team.get("recent_matches", 0),
                recent_goals_for_avg=away_team.get("recent_goals_for_avg"),
                recent_goals_against_avg=away_team.get("recent_goals_against_avg"),
                sample_size=away_team.get("sample_size", 0),
            ),
            head_to_head=HeadToHeadOut(
                meetings_count=head_to_head.get("meetings_count", 0),
                home_wins=head_to_head.get("home_wins", 0),
                draws=head_to_head.get("draws", 0),
                away_wins=head_to_head.get("away_wins", 0),
                home_goals=head_to_head.get("home_goals", 0),
                away_goals=head_to_head.get("away_goals", 0),
                limited_sample=head_to_head.get("limited_sample", True),
            ),
            competition_matches_analyzed=competition.get("matches_analyzed", 0),
            competition_avg_home_goals=competition.get("avg_home_goals", 0.0),
            competition_avg_away_goals=competition.get("avg_away_goals", 0.0),
            home_advantage_ratio=competition.get("home_advantage_ratio"),
            baseline_source=competition.get("baseline_source", "unknown"),
            baseline_sample_sufficient=competition.get(
                "baseline_sample_sufficient", False
            ),
        )

    model_out = None
    if record.status == AnalysisStatus.READY:
        scorelines = [
            ScorelineProbabilityOut(**item)
            for item in (record.scoreline_probabilities or [])
        ]
        model_out = StatisticalModelOut(
            model_id=record.model_id,
            model_version=record.model_version,
            feature_version=(record.features or {}).get("feature_version"),
            expected_home_goals=record.expected_home_goals,
            expected_away_goals=record.expected_away_goals,
            home_win_probability=record.home_win_probability,
            draw_probability=record.draw_probability,
            away_win_probability=record.away_win_probability,
            btts_probability=record.btts_probability,
            over_1_5_probability=record.over_1_5_probability,
            under_1_5_probability=record.under_1_5_probability,
            over_2_5_probability=record.over_2_5_probability,
            under_2_5_probability=record.under_2_5_probability,
            over_3_5_probability=record.over_3_5_probability,
            under_3_5_probability=record.under_3_5_probability,
            scoreline_probabilities=scorelines,
            model_parameters=(
                (record.explanation or {}).get("model_parameters")
                if isinstance(record.explanation, dict)
                else None
            ),
        )

    quality = DataQualityOut(
        data_classification=record.data_classification,
        dataset_id=record.dataset_id,
        dataset_digest=record.dataset_digest,
        provider_code=quality_data.get("provider_code"),
        historical_matches=quality_data.get("historical_matches"),
        competition_matches=quality_data.get("competition_matches"),
        excluded_extra_time_or_shootout=quality_data.get(
            "excluded_extra_time_or_shootout"
        ),
        earliest_kickoff=quality_data.get("earliest_kickoff"),
        latest_kickoff=quality_data.get("latest_kickoff"),
        retrieval_from=quality_data.get("retrieval_from"),
        retrieval_to=quality_data.get("retrieval_to"),
        home_sample_size=record.home_sample_size,
        away_sample_size=record.away_sample_size,
        h2h_sample_size=record.h2h_sample_size,
        statistics_available=False,
        statistics_note=STATISTICS_NOTE,
        missing_features=missing_features,
        limitations=record.limitations or [],
        data_freshness_note=quality_data.get("data_freshness_note"),
    )

    explanation_out = None
    if record.explanation:
        explanation_out = ExplanationOut(
            model_rationale=record.explanation.get("model_rationale", ""),
            expected_goals_breakdown=record.explanation.get(
                "expected_goals_breakdown", {}
            ),
            form_impact=record.explanation.get("form_impact", ""),
            h2h_impact=record.explanation.get("h2h_impact", ""),
        )

    evaluation_out = None
    if record.evaluation_metrics:
        evaluation_out = EvaluationOut(**record.evaluation_metrics)

    return MatchAnalysisOut(
        id=record.id,
        match_id=record.match_id,
        status=record.status,
        generated_at=record.generated_at,
        analysis_as_of=record.analysis_as_of,
        match_overview=_overview(match),
        historical_context=hist_context,
        statistical_model=model_out,
        data_quality=quality,
        explanation=explanation_out,
        evaluation=evaluation_out,
        error_message=record.error_message,
    )


def _base_fields(match: Match, *, as_of, now, model_id: str | None = None, model_version: str | None = None) -> dict[str, Any]:
    return {
        "match_id": match.id,
        "model_id": model_id or MODEL_ID,
        "model_version": model_version or MODEL_VERSION,
        "data_classification": "verified_real_data",
        "home_team_id": match.home_team_id,
        "away_team_id": match.away_team_id,
        "competition_id": match.competition_id,
        "season_id": match.season_id,
        "kickoff_utc": match.kickoff_utc,
        "analysis_as_of": as_of,
        "generated_at": now,
    }


def _reuse_existing(
    session: Session,
    *,
    match_id: int,
    status: str,
    dataset_digest: str | None,
    model_version: str,
    evaluation_version: str | None = None,
) -> MatchAnalysis | None:
    """Return an identical prior report so repeated requests are idempotent."""

    query = select(MatchAnalysis).where(
        MatchAnalysis.match_id == match_id,
        MatchAnalysis.status == status,
        MatchAnalysis.model_version == model_version,
    )
    if dataset_digest is None:
        query = query.where(MatchAnalysis.dataset_digest.is_(None))
    else:
        query = query.where(MatchAnalysis.dataset_digest == dataset_digest)
    records = session.execute(
        query.order_by(desc(MatchAnalysis.id)).limit(5)
    ).scalars().all()
    for record in records:
        if evaluation_version is not None:
            stored = (record.evaluation_metrics or {}).get("evaluation_version")
            if stored != evaluation_version:
                continue
        return record
    return None


def _persist_unavailable(
    session: Session,
    *,
    match: Match,
    as_of,
    now,
    status: str,
    reason: str,
    limitations: list[str],
    dataset_digest: str | None = None,
    force: bool = False,
    model_id: str | None = None,
    model_version: str | None = None,
) -> MatchAnalysisOut:
    if not force:
        existing = _reuse_existing(
            session,
            match_id=match.id,
            status=status,
            dataset_digest=dataset_digest,
            model_version=model_version or MODEL_VERSION,
        )
        if existing is not None:
            return _map_analysis_out(existing, match)

    record = MatchAnalysis(
        **_base_fields(
            match,
            as_of=as_of,
            now=now,
            model_id=model_id,
            model_version=model_version,
        ),
        status=status,
        dataset_digest=dataset_digest,
        error_message=reason,
        limitations=limitations,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return _map_analysis_out(record, match)


@router.post("/matches/{match_id}", response_model=MatchAnalysisOut)
def analyze_match(
    match_id: int = Path(..., ge=1, description="Internal match identifier."),
    model: str = Query(
        "poisson",
        description=(
            "Model to run: poisson, dixon_coles, or elo. An unknown model is rejected; "
            "the endpoint never substitutes another model."
        ),
    ),
    force: bool = Query(
        False,
        description="Regenerate even when an identical report already exists.",
    ),
    session: Session = Depends(get_session),
) -> MatchAnalysisOut:
    """Generate or retrieve a statistical prediction analysis for an upcoming fixture."""

    try:
        spec = require_model_spec(model)
    except ValueError as exc:
        raise AppError(
            str(exc),
            code="unknown_model",
            http_status=422,
            details={"field": "model", "allowed": list(allowed_model_keys())},
        ) from exc

    match = session.get(Match, match_id)
    if match is None:
        raise NotFoundError(f"Match {match_id} does not exist.")

    now = utc_now()
    kickoff = match.kickoff_utc
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=now.tzinfo)
    as_of = now

    if match.status in UNPLAYABLE_STATUSES:
        return _persist_unavailable(
            session,
            match=match,
            as_of=as_of,
            now=now,
            status=AnalysisStatus.DATA_UNAVAILABLE,
            reason=f"Match status is {match.status.value}; a pre-match analysis is not available.",
            limitations=["match_not_analysable_in_current_state"],
            force=force,
            model_id=spec.model_id,
            model_version=spec.model_version,
        )

    if as_of >= kickoff:
        return _persist_unavailable(
            session,
            match=match,
            as_of=as_of,
            now=now,
            status=AnalysisStatus.DATA_UNAVAILABLE,
            reason="Kickoff has passed; the pre-match analysis window is closed.",
            limitations=["analysis_window_closed"],
            force=force,
            model_id=spec.model_id,
            model_version=spec.model_version,
        )

    try:
        dataset, meta = load_point_in_time_dataset(session, fixture=match, as_of=as_of)
        if dataset is None:
            return _persist_unavailable(
                session,
                match=match,
                as_of=as_of,
                now=now,
                status=AnalysisStatus.INSUFFICIENT_DATA,
                reason=(
                    "No completed matches were observed before kickoff. The platform "
                    "abstains rather than producing a prediction from prior assumptions."
                ),
                limitations=[
                    "no_historical_results",
                    "insufficient_match_history",
                    "predictions_abstained",
                ],
                force=force,
                model_id=spec.model_id,
                model_version=spec.model_version,
            )

        features = calculate_match_features(
            dataset,
            home_team_id=str(match.home_team_id),
            away_team_id=str(match.away_team_id),
            competition_id=str(match.competition_id),
        )
        features["data_quality"] = {
            "provider_code": meta.get("provider_code"),
            "historical_matches": meta.get("historical_matches"),
            "competition_matches": meta.get("competition_matches"),
            "excluded_extra_time_or_shootout": meta.get(
                "excluded_extra_time_or_shootout"
            ),
            "earliest_kickoff": meta.get("earliest_kickoff"),
            "latest_kickoff": meta.get("latest_kickoff"),
            "retrieval_from": meta.get("retrieval_from"),
            "retrieval_to": meta.get("retrieval_to"),
            "data_freshness_note": (
                "Dataset contains results observed up to "
                f"{meta.get('latest_observed') or 'the analysis checkpoint'}; "
                "in-match statistics and lineups are unavailable."
            ),
        }
        if spec.key == "elo":
            # Elo uses ratings, not the Poisson feature set; reporting a feature
            # version would imply inputs it never consumed.
            features["feature_version"] = None

        if spec.key == "poisson":
            prediction = run_statistical_prediction(
                dataset,
                features,
                home_team_id=str(match.home_team_id),
                away_team_id=str(match.away_team_id),
                competition_id=str(match.competition_id),
            )
        else:
            prediction = compute_model_prediction(
                dataset,
                features,
                model_key=spec.key,
                home_team_id=str(match.home_team_id),
                away_team_id=str(match.away_team_id),
                competition_id=str(match.competition_id),
                kickoff_utc=kickoff,
            )
        prediction.setdefault("model_id", spec.model_id)
        prediction.setdefault("model_version", spec.model_version)
        status = prediction["status"]

        if not force:
            reusable = _reuse_existing(
                session,
                match_id=match.id,
                status=status,
                dataset_digest=dataset.digest,
                model_version=prediction.get("model_version", spec.model_version),
                evaluation_version=(
                    EVALUATION_VERSION
                    if status == AnalysisStatus.READY and spec.key == "poisson"
                    else None
                ),
            )
            if reusable is not None:
                return _map_analysis_out(reusable, match)

        evaluation = None
        if status == AnalysisStatus.READY and spec.key == "poisson":
            # The rolling-origin block is a Poisson-specific evaluation. Attaching it
            # to another model's report would misdescribe what was measured.
            evaluation = compute_historical_backtest_evaluation(
                dataset, competition_id=str(match.competition_id)
            )

        explanation = prediction.get("explanation")
        if explanation is not None:
            explanation = {
                **explanation,
                "model_parameters": prediction.get("model_parameters"),
            }

        record = MatchAnalysis(
            **_base_fields(
                match,
                as_of=as_of,
                now=now,
                model_id=prediction.get("model_id"),
                model_version=prediction.get("model_version"),
            ),
            status=status,
            dataset_id=dataset.dataset_id,
            dataset_digest=dataset.digest,
            expected_home_goals=prediction.get("expected_home_goals"),
            expected_away_goals=prediction.get("expected_away_goals"),
            home_win_probability=prediction.get("home_win_probability"),
            draw_probability=prediction.get("draw_probability"),
            away_win_probability=prediction.get("away_win_probability"),
            btts_probability=prediction.get("btts_probability"),
            over_1_5_probability=prediction.get("over_1_5_probability"),
            under_1_5_probability=prediction.get("under_1_5_probability"),
            over_2_5_probability=prediction.get("over_2_5_probability"),
            under_2_5_probability=prediction.get("under_2_5_probability"),
            over_3_5_probability=prediction.get("over_3_5_probability"),
            under_3_5_probability=prediction.get("under_3_5_probability"),
            home_sample_size=prediction.get("home_sample_size"),
            away_sample_size=prediction.get("away_sample_size"),
            h2h_sample_size=prediction.get("h2h_sample_size"),
            scoreline_probabilities=prediction.get("scoreline_probabilities"),
            features=features,
            limitations=prediction.get("limitations"),
            explanation=explanation,
            evaluation_metrics=evaluation,
            error_message=prediction.get("reason"),
        )
        session.add(record)
        session.commit()
        session.refresh(record)
        return _map_analysis_out(record, match)

    except DatasetProvenanceError as exc:
        session.rollback()
        logger.warning(
            "analysis provenance check failed",
            extra={
                "event": "analysis.provenance_failure",
                "component": "analysis",
                "match_id": match.id,
            },
        )
        return _persist_unavailable(
            session,
            match=match,
            as_of=as_of,
            now=now,
            status=AnalysisStatus.ANALYSIS_FAILED,
            reason=str(exc),
            limitations=["dataset_provenance_incomplete"],
            force=True,
            model_id=spec.model_id,
            model_version=spec.model_version,
        )
    except Exception as exc:  # noqa: BLE001 - persist an explicit failure state
        session.rollback()
        logger.exception(
            "match analysis failed",
            extra={
                "event": "analysis.failed",
                "component": "analysis",
                "match_id": match.id,
                "error_code": "analysis_failed",
            },
        )
        return _persist_unavailable(
            session,
            match=match,
            as_of=as_of,
            now=now,
            status=AnalysisStatus.ANALYSIS_FAILED,
            reason=f"Analysis failed: {type(exc).__name__}: {exc}",
            limitations=["internal_calculation_failure"],
            force=True,
            model_id=spec.model_id,
            model_version=spec.model_version,
        )


def _persist_comparison_model(
    session: Session,
    *,
    match: Match,
    dataset,
    features: dict[str, Any],
    prediction: dict[str, Any],
    spec,
    as_of,
    now,
) -> MatchAnalysis:
    """Persist one model's comparison output, reusing an identical prior report."""

    status = prediction["status"]
    existing = _reuse_existing(
        session,
        match_id=match.id,
        status=status,
        dataset_digest=dataset.digest,
        model_version=prediction.get("model_version", spec.model_version),
    )
    if existing is not None:
        return existing

    explanation = prediction.get("explanation")
    if explanation is not None:
        explanation = {
            **explanation,
            "model_parameters": prediction.get("model_parameters"),
        }
    record = MatchAnalysis(
        **_base_fields(
            match,
            as_of=as_of,
            now=now,
            model_id=prediction.get("model_id"),
            model_version=prediction.get("model_version"),
        ),
        status=status,
        dataset_id=dataset.dataset_id,
        dataset_digest=dataset.digest,
        expected_home_goals=prediction.get("expected_home_goals"),
        expected_away_goals=prediction.get("expected_away_goals"),
        home_win_probability=prediction.get("home_win_probability"),
        draw_probability=prediction.get("draw_probability"),
        away_win_probability=prediction.get("away_win_probability"),
        btts_probability=prediction.get("btts_probability"),
        over_1_5_probability=prediction.get("over_1_5_probability"),
        under_1_5_probability=prediction.get("under_1_5_probability"),
        over_2_5_probability=prediction.get("over_2_5_probability"),
        under_2_5_probability=prediction.get("under_2_5_probability"),
        over_3_5_probability=prediction.get("over_3_5_probability"),
        under_3_5_probability=prediction.get("under_3_5_probability"),
        home_sample_size=prediction.get("home_sample_size"),
        away_sample_size=prediction.get("away_sample_size"),
        h2h_sample_size=prediction.get("h2h_sample_size"),
        scoreline_probabilities=prediction.get("scoreline_probabilities"),
        features=features,
        limitations=prediction.get("limitations"),
        explanation=explanation,
        error_message=prediction.get("reason"),
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


@router.post("/matches/{match_id}/comparison", response_model=ModelComparisonOut)
def compare_match_models(
    match_id: int = Path(..., ge=1, description="Internal match identifier."),
    session: Session = Depends(get_session),
) -> ModelComparisonOut:
    """Run every supported model on the same point-in-time dataset.

    No model is substituted for another: each entry carries its own status, and an
    abstention is returned as an abstention.
    """

    match = session.get(Match, match_id)
    if match is None:
        raise NotFoundError(f"Match {match_id} does not exist.")

    now = utc_now()
    kickoff = match.kickoff_utc
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=now.tzinfo)
    as_of = now

    specs = [require_model_spec(key) for key in allowed_model_keys()]

    def unavailable(status: str, reason: str) -> ModelComparisonOut:
        return ModelComparisonOut(
            match_id=match.id,
            analysis_as_of=as_of,
            dataset_id=None,
            dataset_digest=None,
            models=[
                ModelComparisonItemOut(
                    key=spec.key,
                    model_id=spec.model_id,
                    model_version=spec.model_version,
                    status=status,
                    home_win_probability=None,
                    draw_probability=None,
                    away_win_probability=None,
                    expected_home_goals=None,
                    expected_away_goals=None,
                    reason=reason,
                    analysis_id=None,
                    limitations=[],
                )
                for spec in specs
            ],
            notes=[reason],
        )

    if match.status in UNPLAYABLE_STATUSES:
        return unavailable(
            AnalysisStatus.DATA_UNAVAILABLE,
            f"Match status is {match.status.value}; a pre-match comparison is not available.",
        )
    if as_of >= kickoff:
        return unavailable(
            AnalysisStatus.DATA_UNAVAILABLE,
            "Kickoff has passed; the pre-match comparison window is closed.",
        )

    try:
        dataset, meta = load_point_in_time_dataset(session, fixture=match, as_of=as_of)
    except DatasetProvenanceError as exc:
        return unavailable(AnalysisStatus.ANALYSIS_FAILED, str(exc))

    if dataset is None:
        return unavailable(
            AnalysisStatus.INSUFFICIENT_DATA,
            "No completed matches were observed before kickoff; every model abstains.",
        )

    features = calculate_match_features(
        dataset,
        home_team_id=str(match.home_team_id),
        away_team_id=str(match.away_team_id),
        competition_id=str(match.competition_id),
    )
    features["data_quality"] = {
        "provider_code": meta.get("provider_code"),
        "historical_matches": meta.get("historical_matches"),
        "competition_matches": meta.get("competition_matches"),
        "excluded_extra_time_or_shootout": meta.get("excluded_extra_time_or_shootout"),
        "earliest_kickoff": meta.get("earliest_kickoff"),
        "latest_kickoff": meta.get("latest_kickoff"),
        "retrieval_from": meta.get("retrieval_from"),
        "retrieval_to": meta.get("retrieval_to"),
        "data_freshness_note": (
            "Comparison uses the same point-in-time dataset for every model; "
            "in-match statistics and lineups are unavailable."
        ),
    }

    items: list[ModelComparisonItemOut] = []
    for spec in specs:
        model_features = dict(features)
        if spec.key == "elo":
            model_features["feature_version"] = None
        if spec.key == "poisson":
            prediction = run_statistical_prediction(
                dataset,
                model_features,
                home_team_id=str(match.home_team_id),
                away_team_id=str(match.away_team_id),
                competition_id=str(match.competition_id),
            )
        else:
            prediction = compute_model_prediction(
                dataset,
                model_features,
                model_key=spec.key,
                home_team_id=str(match.home_team_id),
                away_team_id=str(match.away_team_id),
                competition_id=str(match.competition_id),
                kickoff_utc=kickoff,
            )
        prediction.setdefault("model_id", spec.model_id)
        prediction.setdefault("model_version", spec.model_version)

        record = _persist_comparison_model(
            session,
            match=match,
            dataset=dataset,
            features=model_features,
            prediction=prediction,
            spec=spec,
            as_of=as_of,
            now=now,
        )
        items.append(
            ModelComparisonItemOut(
                key=spec.key,
                model_id=record.model_id,
                model_version=record.model_version,
                status=record.status,
                home_win_probability=record.home_win_probability,
                draw_probability=record.draw_probability,
                away_win_probability=record.away_win_probability,
                expected_home_goals=record.expected_home_goals,
                expected_away_goals=record.expected_away_goals,
                reason=record.error_message,
                analysis_id=record.id,
                limitations=record.limitations or [],
            )
        )

    return ModelComparisonOut(
        match_id=match.id,
        analysis_as_of=as_of,
        dataset_id=dataset.dataset_id,
        dataset_digest=dataset.digest,
        models=items,
        notes=[
            "All models read the same point-in-time dataset and predict the same fixture.",
            "No model is substituted for another; an abstention is shown as an abstention.",
            "Comparing model outputs is not an accuracy claim: read the stored evaluation.",
        ],
    )


@router.get("/{analysis_id}", response_model=MatchAnalysisOut)
def get_analysis(
    analysis_id: int = Path(..., ge=1, description="Analysis identifier."),
    session: Session = Depends(get_session),
) -> MatchAnalysisOut:
    """Retrieve a previously generated match analysis report by its ID."""

    record = session.get(MatchAnalysis, analysis_id)
    if record is None:
        raise NotFoundError(f"Analysis {analysis_id} does not exist.")
    match = session.get(Match, record.match_id)
    if match is None:
        raise NotFoundError(f"Match {record.match_id} does not exist.")
    return _map_analysis_out(record, match)


@router.get("/matches/{match_id}/history", response_model=list[AnalysisHistoryItem])
def get_match_analysis_history(
    match_id: int = Path(..., ge=1, description="Internal match identifier."),
    session: Session = Depends(get_session),
) -> list[AnalysisHistoryItem]:
    """Retrieve historical analysis runs generated for this match."""

    match = session.get(Match, match_id)
    if match is None:
        raise NotFoundError(f"Match {match_id} does not exist.")

    query = (
        select(MatchAnalysis)
        .where(MatchAnalysis.match_id == match_id)
        .order_by(desc(MatchAnalysis.created_at), desc(MatchAnalysis.id))
        .limit(20)
    )
    records = session.execute(query).scalars().all()
    return [
        AnalysisHistoryItem(
            id=record.id,
            match_id=record.match_id,
            status=record.status,
            model_version=record.model_version,
            generated_at=record.generated_at,
            home_win_probability=record.home_win_probability,
            draw_probability=record.draw_probability,
            away_win_probability=record.away_win_probability,
        )
        for record in records
    ]
