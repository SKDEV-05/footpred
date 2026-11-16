"""Schemas for persisted model-evaluation runs.

The evaluation report is a stored document, not a recomputation: every number a client
sees came from the corpus at the digest below. Nested metric blocks are typed so a
schema change in the engine cannot silently reach the dashboard unannounced.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.analysis import CalibrationBinOut, ClassCalibrationOut
from app.schemas.common import UtcDatetime

__all__ = [
    "CalibrationBinOut",
    "ClassCalibrationOut",
    "CompetitionEvaluationOut",
    "EvaluationDatasetOut",
    "EvaluationReportBodyOut",
    "EvaluationRunOut",
    "EvaluationRunSummaryOut",
    "EvaluationSettingsOut",
    "EvaluationWindowOut",
    "ModelMetricsOut",
    "OutcomeMetricsOut",
    "PairedComparisonOut",
    "PerMatchDifferenceOut",
    "SeasonEvaluationOut",
    "TimelineBucketOut",
]


class BootstrapOut(BaseModel):
    resamples: int
    seed: int
    brier_ci: dict[str, float] | None = None
    log_loss_ci: dict[str, float] | None = None


class OutcomeMetricsOut(BaseModel):
    """Binary view of one outcome class ("draws are under-predicted" made measurable)."""

    sample_size: int
    observed_rate: float | None = None
    mean_probability: float | None = None
    calibration_gap: float | None = None
    brier_score: float | None = None
    log_loss: float | None = None


class ModelMetricsOut(BaseModel):
    key: str
    model_id: str
    model_version: str
    label: str
    role: str
    evaluated: bool = False
    reason: str | None = None
    sample_size: int = 0
    brier_score: float | None = None
    log_loss: float | None = None
    brier_skill_score_vs_uniform: float | None = None
    expected_calibration_error: float | None = None
    maximum_calibration_error: float | None = None
    calibration: list[ClassCalibrationOut] = Field(default_factory=list)
    mean_probabilities: dict[str, float] = Field(default_factory=dict)
    observed_frequencies: dict[str, float] = Field(default_factory=dict)
    per_outcome: dict[str, OutcomeMetricsOut] = Field(default_factory=dict)
    top_pick_accuracy: float | None = None
    bootstrap: BootstrapOut | None = None


class PerMatchDifferenceOut(BaseModel):
    mean: float | None = None
    lower: float | None = None
    upper: float | None = None
    interpretation: str | None = None


class PairedComparisonOut(BaseModel):
    reference: str
    candidate: str
    evaluated: bool = False
    reason: str | None = None
    sample_size: int | None = None
    brier_difference: PerMatchDifferenceOut | None = None
    log_loss_difference: PerMatchDifferenceOut | None = None


class CompetitionDiagnosticsOut(BaseModel):
    evaluated: int = 0
    skipped_model_abstention: int = 0
    skipped_history: int = 0


class FittedParametersOut(BaseModel):
    rho: float | None = None
    rho_status: str | None = None
    rho_matches: int | None = None
    elo_home_advantage: float | None = None
    elo_draw_nu: float | None = None
    elo_status: str | None = None
    training_matches: int | None = None


class CompetitionEvaluationOut(BaseModel):
    competition_id: str
    sample_size: int
    status: str
    diagnostics: CompetitionDiagnosticsOut = Field(default_factory=CompetitionDiagnosticsOut)
    fitted_parameters: FittedParametersOut | None = None
    models: dict[str, ModelMetricsOut] = Field(default_factory=dict)


class SeasonEvaluationOut(BaseModel):
    competition_id: str
    season_id: str
    sample_size: int
    models: dict[str, ModelMetricsOut] = Field(default_factory=dict)


class TimelinePointOut(BaseModel):
    brier_score: float | None = None
    sample_size: int = 0


class TimelineBucketOut(BaseModel):
    from_: UtcDatetime = Field(alias="from")
    to: UtcDatetime
    sample_size: int
    models: dict[str, TimelinePointOut | None] = Field(default_factory=dict)

    model_config = ConfigDict(populate_by_name=True)


class EvaluationSettingsOut(BaseModel):
    min_prior_matches: int
    max_test_per_competition: int
    result_horizon_hours: float
    bootstrap_resamples: int
    bootstrap_seed: int
    calibration_bins: int
    timeline_bucket_size: int


class EvaluationDatasetOut(BaseModel):
    dataset_id: str | None = None
    dataset_digest: str | None = None
    classification: str | None = None
    matches: int | None = None
    competitions: int | None = None
    provider_code: str | None = None
    retrieval_from: str | None = None
    observed_to: str | None = None


class EvaluationWindowOut(BaseModel):
    from_: UtcDatetime = Field(alias="from")
    to: UtcDatetime

    model_config = ConfigDict(populate_by_name=True)


class InsufficientCompetitionOut(BaseModel):
    competition_id: str
    status: str
    sample_size: int
    required: int


class EvaluationReportBodyOut(BaseModel):
    evaluated: bool
    reason: str | None = None
    protocol_version: str
    evaluation_version: str
    settings: EvaluationSettingsOut | None = None
    dataset: EvaluationDatasetOut | None = None
    window: EvaluationWindowOut | None = None
    sample_size: int = 0
    models: list[ModelMetricsOut] = Field(default_factory=list)
    comparisons: list[PairedComparisonOut] = Field(default_factory=list)
    competitions: list[CompetitionEvaluationOut] = Field(default_factory=list)
    seasons: list[SeasonEvaluationOut] = Field(default_factory=list)
    timeline: list[TimelineBucketOut] = Field(default_factory=list)
    insufficient_competitions: list[InsufficientCompetitionOut] = Field(
        default_factory=list
    )
    notes: list[str] = Field(default_factory=list)


class EvaluationRunOut(BaseModel):
    """One persisted run: identity, provenance, and the full stored report."""

    id: int
    protocol_version: str
    evaluation_version: str
    dataset_id: str | None
    dataset_digest: str
    provider_code: str | None
    sample_size: int
    window_from: UtcDatetime | None
    window_to: UtcDatetime | None
    generated_at: UtcDatetime
    report: EvaluationReportBodyOut


class EvaluationRunSummaryOut(BaseModel):
    """Compact catalogue entry so the runs list stays small."""

    id: int
    protocol_version: str
    evaluation_version: str
    dataset_id: str | None
    dataset_digest: str
    sample_size: int
    window_from: UtcDatetime | None
    window_to: UtcDatetime | None
    generated_at: UtcDatetime
    model_keys: list[str] = Field(default_factory=list)
