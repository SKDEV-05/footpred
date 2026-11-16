"""Schemas for match intelligence and statistical prediction reports."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field

from app.schemas.common import UtcDatetime
from app.schemas.fixtures import CompetitionRef, SeasonRef, TeamRef


class ScorelineProbabilityOut(BaseModel):
    home_goals: int
    away_goals: int
    probability: float


class MatchOverviewOut(BaseModel):
    match_id: int
    competition: CompetitionRef
    season: SeasonRef
    home_team: TeamRef
    away_team: TeamRef
    kickoff_utc: UtcDatetime


class TeamRecordOut(BaseModel):
    played: int
    wins: int
    draws: int
    losses: int
    # ``None`` means the subset is empty; a genuine zero stays 0.0.
    win_rate: float | None
    goals_for: int
    goals_against: int
    goals_for_avg: float | None
    goals_against_avg: float | None
    clean_sheets: int
    failed_to_score: int


class TeamContextOut(BaseModel):
    overall: TeamRecordOut
    venue_specific: TeamRecordOut
    recent_form: str
    recent_matches: int = 0
    recent_goals_for_avg: float | None
    recent_goals_against_avg: float | None
    sample_size: int


class HeadToHeadOut(BaseModel):
    meetings_count: int
    home_wins: int
    draws: int
    away_wins: int
    home_goals: int
    away_goals: int
    limited_sample: bool


class HistoricalContextOut(BaseModel):
    home_team: TeamContextOut
    away_team: TeamContextOut
    head_to_head: HeadToHeadOut
    competition_matches_analyzed: int
    competition_avg_home_goals: float
    competition_avg_away_goals: float
    home_advantage_ratio: float | None
    baseline_source: str = "unknown"
    baseline_sample_sufficient: bool = False


class ModelParametersOut(BaseModel):
    baseline_avg_home_goals: float
    baseline_avg_away_goals: float
    baseline_source: str
    home_attack_strength: float
    home_defence_strength: float
    away_attack_strength: float
    away_defence_strength: float
    home_recent_weight: float
    away_recent_weight: float
    expected_goals_bounds: list[float]


class StatisticalModelOut(BaseModel):
    model_id: str
    model_version: str
    feature_version: str | None = None
    expected_home_goals: float | None
    expected_away_goals: float | None
    home_win_probability: float | None
    draw_probability: float | None
    away_win_probability: float | None
    btts_probability: float | None
    over_1_5_probability: float | None
    under_1_5_probability: float | None
    over_2_5_probability: float | None
    under_2_5_probability: float | None
    over_3_5_probability: float | None
    under_3_5_probability: float | None
    scoreline_probabilities: list[ScorelineProbabilityOut] = Field(default_factory=list)
    model_parameters: ModelParametersOut | None = None


class DataQualityOut(BaseModel):
    data_classification: str
    dataset_id: str | None
    dataset_digest: str | None
    provider_code: str | None = None
    historical_matches: int | None = None
    competition_matches: int | None = None
    excluded_extra_time_or_shootout: int | None = None
    earliest_kickoff: str | None = None
    latest_kickoff: str | None = None
    retrieval_from: str | None = None
    retrieval_to: str | None = None
    home_sample_size: int | None
    away_sample_size: int | None
    h2h_sample_size: int | None
    statistics_available: bool
    statistics_note: str
    missing_features: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    data_freshness_note: str | None = None


class ExplanationOut(BaseModel):
    model_rationale: str
    expected_goals_breakdown: dict[str, str] = Field(default_factory=dict)
    form_impact: str
    h2h_impact: str


class CalibrationBinOut(BaseModel):
    lower: float
    upper: float
    sample_size: int
    mean_probability: float | None
    observed_rate: float | None


class ClassCalibrationOut(BaseModel):
    class_label: str
    sample_size: int
    expected_calibration_error: float | None
    maximum_calibration_error: float | None
    bins: list[CalibrationBinOut] = Field(default_factory=list)


class EvaluationOut(BaseModel):
    evaluated: bool
    reason: str | None = None
    sample_size: int | None = None
    brier_score: float | None = None
    log_loss: float | None = None
    uniform_brier_score: float | None = None
    uniform_log_loss: float | None = None
    brier_skill_score: float | None = None
    expected_calibration_error: float | None = None
    maximum_calibration_error: float | None = None
    calibration: list[ClassCalibrationOut] = Field(default_factory=list)
    class_labels: list[str] = Field(default_factory=list)
    model_id: str | None = None
    model_version: str | None = None
    feature_version: str | None = None
    evaluation_version: str | None = None
    dataset_id: str | None = None
    dataset_digest: str | None = None
    evaluation_type: str | None = None
    test_period_from: str | None = None
    test_period_to: str | None = None


class MatchAnalysisOut(BaseModel):
    id: int
    match_id: int
    status: str
    generated_at: UtcDatetime
    analysis_as_of: UtcDatetime
    match_overview: MatchOverviewOut
    historical_context: HistoricalContextOut | None = None
    statistical_model: StatisticalModelOut | None = None
    data_quality: DataQualityOut
    explanation: ExplanationOut | None = None
    evaluation: EvaluationOut | None = None
    error_message: str | None = None


class AnalysisHistoryItem(BaseModel):
    id: int
    match_id: int
    status: str
    model_version: str
    generated_at: UtcDatetime
    home_win_probability: float | None
    draw_probability: float | None
    away_win_probability: float | None
