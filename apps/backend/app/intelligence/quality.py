"""Configurable data-coverage classification and abstention."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.intelligence.types import ResearchContext, require_context


class Coverage(StrEnum):
    HIGH = "high_data_coverage"
    MODERATE = "moderate_data_coverage"
    LOW = "low_data_coverage"
    INSUFFICIENT = "insufficient_data"


@dataclass(frozen=True)
class CoveragePolicy:
    """Research defaults, not validated predictive thresholds."""

    policy_id: str
    minimum_matches: int
    moderate_matches: int
    high_matches: int

    def __post_init__(self) -> None:
        if not self.policy_id:
            raise ValueError("coverage policy id must not be empty")
        if not 0 < self.minimum_matches <= self.moderate_matches <= self.high_matches:
            raise ValueError("coverage thresholds must be positive and ordered")


@dataclass(frozen=True)
class QualityAssessment:
    policy_id: str
    coverage: Coverage
    sample_size: int
    required_minimum: int
    eligible: bool
    reasons: tuple[str, ...]
    context: ResearchContext


def assess_sample(
    sample_size: int,
    policy: CoveragePolicy,
    *,
    context: ResearchContext,
) -> QualityAssessment:
    require_context(context)
    if sample_size < 0:
        raise ValueError("sample_size must be non-negative")
    if sample_size < policy.minimum_matches:
        coverage = Coverage.INSUFFICIENT
    elif sample_size < policy.moderate_matches:
        coverage = Coverage.LOW
    elif sample_size < policy.high_matches:
        coverage = Coverage.MODERATE
    else:
        coverage = Coverage.HIGH
    eligible = sample_size >= policy.minimum_matches
    return QualityAssessment(
        policy_id=policy.policy_id,
        coverage=coverage,
        sample_size=sample_size,
        required_minimum=policy.minimum_matches,
        eligible=eligible,
        reasons=() if eligible else ("historical_sample_below_minimum",),
        context=context,
    )
