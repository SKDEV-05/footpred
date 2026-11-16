"""Orchestration for deterministic, offline match intelligence."""

from __future__ import annotations

from datetime import datetime

from app.intelligence.features import build_features
from app.intelligence.metrics import (
    calculate_competition_context,
    calculate_head_to_head,
    calculate_team_form,
)
from app.intelligence.quality import CoveragePolicy, assess_sample
from app.intelligence.reports import AnalysisConfiguration, MatchIntelligenceReport
from app.intelligence.types import (
    DataClassification,
    IntelligenceDataset,
    MatchRequest,
    PointsPolicy,
    Venue,
)


class IntelligenceEngine:
    def __init__(
        self,
        *,
        coverage_policy: CoveragePolicy,
        points_policy: PointsPolicy,
    ) -> None:
        self._policy = coverage_policy
        self._points_policy = points_policy

    def analyze(
        self,
        request: MatchRequest,
        dataset: IntelligenceDataset,
        *,
        generated_at: datetime,
        form_window: int = 10,
        h2h_window: int = 5,
    ) -> MatchIntelligenceReport:
        if generated_at < request.as_of:
            raise ValueError("generated_at cannot precede analysis as_of")
        if generated_at.tzinfo is None or generated_at.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")
        if generated_at.utcoffset().total_seconds() != 0:
            raise ValueError("generated_at must be UTC")
        if dataset.classification is DataClassification.SYNTHETIC_TEST:
            pass
        elif dataset.classification is DataClassification.VERIFIED_REAL:
            if dataset.evidence is None:
                raise ValueError("VERIFIED_REAL datasets require a DatasetEvidence block")
        else:
            raise ValueError("Phase 4/5 offline engine accepts synthetic_test_data or verified_real_data only")
        if not 0 < form_window <= 1_000 or not 0 < h2h_window <= 1_000:
            raise ValueError("analysis windows must be in [1, 1000]")
        if any(match.match_id == request.match_id for match in dataset.matches):
            raise ValueError("target fixture must not appear in its own history dataset")
        materialized = dataset.matches
        context = dataset.research_context()
        configuration = AnalysisConfiguration(
            competition_id=request.competition_id,
            season_id=request.season_id,
            kickoff_utc=request.kickoff_utc,
            neutral_venue=request.neutral_venue,
            analysis_as_of=request.as_of,
            form_window=form_window,
            h2h_window=h2h_window,
            points_policy=self._points_policy,
            coverage_policy=self._policy,
            protocol_version=context.protocol_version,
        )
        home_venue = Venue.NEUTRAL if request.neutral_venue else Venue.HOME
        away_venue = Venue.NEUTRAL if request.neutral_venue else Venue.AWAY
        home = calculate_team_form(
            materialized,
            team_id=request.home_team_id,
            as_of=request.as_of,
            window=form_window,
            venue=home_venue,
            competition_id=request.competition_id,
            points_policy=self._points_policy,
            context=context,
        )
        away = calculate_team_form(
            materialized,
            team_id=request.away_team_id,
            as_of=request.as_of,
            window=form_window,
            venue=away_venue,
            competition_id=request.competition_id,
            points_policy=self._points_policy,
            context=context,
        )
        competition = calculate_competition_context(
            materialized,
            competition_id=request.competition_id,
            as_of=request.as_of,
            points_policy=self._points_policy,
            context=context,
        )
        h2h = calculate_head_to_head(
            materialized,
            home_team_id=request.home_team_id,
            away_team_id=request.away_team_id,
            as_of=request.as_of,
            window=h2h_window,
            competition_id=request.competition_id,
            context=context,
        )
        home_quality = assess_sample(home.sample_size, self._policy, context=context)
        away_quality = assess_sample(away.sample_size, self._policy, context=context)
        limitations = [
            "descriptive_metrics_not_validated_predictors",
            "opponent_strength_not_adjusted",
            "no_squad_or_lineup_information",
        ]
        if dataset.classification is DataClassification.SYNTHETIC_TEST:
            limitations.insert(0, "offline_synthetic_test_only")
        else:
            limitations.insert(0, "verified_real_data")
        if h2h.sample_size < h2h_window:
            limitations.append("limited_head_to_head_sample")
        if not home_quality.eligible or not away_quality.eligible:
            limitations.append("insufficient_venue_specific_history")
        return MatchIntelligenceReport(
            match_id=request.match_id,
            dataset_id=dataset.dataset_id,
            data_classification=dataset.classification,
            input_digest=dataset.digest,
            configuration=configuration,
            config_digest=configuration.digest,
            generated_at=generated_at,
            analysis_as_of=request.as_of,
            home_form=home,
            away_form=away,
            competition_context=competition,
            head_to_head=h2h,
            features=build_features(
                home_form=home,
                away_form=away,
                competition=competition,
                as_of=request.as_of,
                context=context,
            ),
            home_quality=home_quality,
            away_quality=away_quality,
            eligible_for_research_calculation=(
                home_quality.eligible and away_quality.eligible
            ),
            limitations=tuple(limitations),
        )
