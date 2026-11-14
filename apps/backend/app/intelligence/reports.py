"""Structured offline intelligence reports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json

from app.intelligence.features import FEATURE_REGISTRY, FeatureValue
from app.intelligence.metrics import CompetitionContext, HeadToHead, TeamForm
from app.intelligence.quality import CoveragePolicy, QualityAssessment
from app.intelligence.types import DataClassification, PointsPolicy


@dataclass(frozen=True)
class AnalysisConfiguration:
    """Everything apart from the dataset needed to reproduce a report."""

    competition_id: str
    season_id: str
    kickoff_utc: datetime
    neutral_venue: bool
    analysis_as_of: datetime
    form_window: int
    h2h_window: int
    points_policy: PointsPolicy
    coverage_policy: CoveragePolicy
    protocol_version: str

    @property
    def digest(self) -> str:
        canonical = json.dumps(
            {
                "competition_id": self.competition_id,
                "season_id": self.season_id,
                "kickoff_utc": self.kickoff_utc.isoformat(),
                "neutral_venue": self.neutral_venue,
                "analysis_as_of": self.analysis_as_of.isoformat(),
                "form_window": self.form_window,
                "h2h_window": self.h2h_window,
                "points_policy": {
                    "policy_id": self.points_policy.policy_id,
                    "win": self.points_policy.win_points,
                    "draw": self.points_policy.draw_points,
                    "loss": self.points_policy.loss_points,
                },
                "coverage_policy": {
                    "policy_id": self.coverage_policy.policy_id,
                    "minimum": self.coverage_policy.minimum_matches,
                    "moderate": self.coverage_policy.moderate_matches,
                    "high": self.coverage_policy.high_matches,
                },
                "protocol_version": self.protocol_version,
                "feature_versions": sorted(
                    (item.name, item.version) for item in FEATURE_REGISTRY
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class MatchIntelligenceReport:
    match_id: str
    dataset_id: str
    data_classification: DataClassification
    input_digest: str
    configuration: AnalysisConfiguration
    config_digest: str
    generated_at: datetime
    analysis_as_of: datetime
    home_form: TeamForm
    away_form: TeamForm
    competition_context: CompetitionContext
    head_to_head: HeadToHead
    features: tuple[FeatureValue, ...]
    home_quality: QualityAssessment
    away_quality: QualityAssessment
    eligible_for_research_calculation: bool
    limitations: tuple[str, ...]
