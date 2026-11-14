"""Synthetic-only evaluation arithmetic and temporal partition mechanics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import isfinite, log
from typing import Sequence

from app.intelligence.types import ResearchContext, require_context

MAX_EVALUATION_ROWS = 100_000
MAX_RELIABILITY_BINS = 1_000
MAX_FOLDS = 10_000
MAX_EMITTED_FOLD_IDS = 1_000_000


def _validate_probability(value: float) -> None:
    if not isfinite(value) or not 0 <= value <= 1:
        raise ValueError("probabilities must be finite and in [0, 1]")


def _validate_lengths(probabilities: Sequence[object], outcomes: Sequence[object]) -> None:
    if len(probabilities) != len(outcomes) or not probabilities:
        raise ValueError("probabilities and outcomes must have equal non-zero length")
    if len(probabilities) > MAX_EVALUATION_ROWS:
        raise ValueError("evaluation input exceeds the 100000-row safety limit")


@dataclass(frozen=True)
class ScoreSummary:
    metric: str
    convention: str
    sample_size: int
    value: float
    context: ResearchContext
    class_labels: tuple[str, ...] = ()


def binary_brier_score(
    probabilities: Sequence[float],
    outcomes: Sequence[int],
    *,
    context: ResearchContext,
) -> ScoreSummary:
    require_context(context)
    _validate_lengths(probabilities, outcomes)
    for probability in probabilities:
        _validate_probability(probability)
    if any(outcome not in (0, 1) for outcome in outcomes):
        raise ValueError("binary outcomes must be zero or one")
    value = sum(
        (probability - outcome) ** 2
        for probability, outcome in zip(probabilities, outcomes, strict=True)
    ) / len(outcomes)
    return ScoreSummary("brier", "binary_mean_squared_error", len(outcomes), value, context)


def binary_log_loss(
    probabilities: Sequence[float],
    outcomes: Sequence[int],
    *,
    context: ResearchContext,
) -> ScoreSummary:
    require_context(context)
    _validate_lengths(probabilities, outcomes)
    if any(outcome not in (0, 1) for outcome in outcomes):
        raise ValueError("binary outcomes must be zero or one")
    total = 0.0
    for probability, outcome in zip(probabilities, outcomes, strict=True):
        _validate_probability(probability)
        if (outcome == 1 and probability == 0) or (outcome == 0 and probability == 1):
            total = float("inf")
            break
        total -= log(probability) if outcome == 1 else log(1.0 - probability)
    return ScoreSummary("log_loss", "binary_natural_log", len(outcomes), total / len(outcomes), context)


def _validate_multiclass(
    probabilities: Sequence[Sequence[float]],
    outcomes: Sequence[int],
    class_labels: Sequence[str],
) -> int:
    _validate_lengths(probabilities, outcomes)
    classes = len(class_labels)
    if classes < 2 or len(set(class_labels)) != classes or any(not label for label in class_labels):
        raise ValueError("at least two unique non-empty class labels are required")
    for row, outcome in zip(probabilities, outcomes, strict=True):
        if len(row) != classes or outcome not in range(classes):
            raise ValueError("inconsistent class count or outcome")
        for probability in row:
            _validate_probability(probability)
        if abs(sum(row) - 1.0) > 1e-12:
            raise ValueError("each probability row must sum to one")
    return classes


def multiclass_brier_score(
    probabilities: Sequence[Sequence[float]],
    outcomes: Sequence[int],
    *,
    class_labels: Sequence[str],
    context: ResearchContext,
) -> ScoreSummary:
    require_context(context)
    _validate_multiclass(probabilities, outcomes, class_labels)
    total = sum(
        sum(
            (probability - (1.0 if index == outcome else 0.0)) ** 2
            for index, probability in enumerate(row)
        )
        for row, outcome in zip(probabilities, outcomes, strict=True)
    )
    return ScoreSummary(
        "brier",
        "multiclass_unnormalized",
        len(outcomes),
        total / len(outcomes),
        context,
        tuple(class_labels),
    )


def multiclass_log_loss(
    probabilities: Sequence[Sequence[float]],
    outcomes: Sequence[int],
    *,
    class_labels: Sequence[str],
    context: ResearchContext,
) -> ScoreSummary:
    require_context(context)
    _validate_multiclass(probabilities, outcomes, class_labels)
    total = 0.0
    for row, outcome in zip(probabilities, outcomes, strict=True):
        true_probability = row[outcome]
        if true_probability == 0:
            total = float("inf")
            break
        total -= log(true_probability)
    return ScoreSummary(
        "log_loss",
        "multiclass_natural_log",
        len(outcomes),
        total / len(outcomes),
        context,
        tuple(class_labels),
    )


@dataclass(frozen=True)
class ReliabilityBin:
    lower: float
    upper: float
    sample_size: int
    mean_probability: float | None
    observed_rate: float | None
    absolute_gap: float | None


@dataclass(frozen=True)
class ReliabilitySummary:
    sample_size: int
    bins: tuple[ReliabilityBin, ...]
    expected_calibration_error: float | None
    maximum_calibration_error: float | None
    context: ResearchContext
    class_label: str


def reliability_bins(
    probabilities: Sequence[float],
    outcomes: Sequence[int],
    *,
    context: ResearchContext,
    class_label: str,
    bin_count: int = 10,
) -> ReliabilitySummary:
    require_context(context)
    if not class_label:
        raise ValueError("class_label must not be empty")
    if type(bin_count) is not int or not 0 < bin_count <= MAX_RELIABILITY_BINS:
        raise ValueError("bin_count must be an integer in [1, 1000]")
    if len(probabilities) != len(outcomes):
        raise ValueError("probabilities and outcomes must have equal length")
    if len(probabilities) > MAX_EVALUATION_ROWS:
        raise ValueError("evaluation input exceeds the 100000-row safety limit")
    buckets: list[list[tuple[float, int]]] = [[] for _ in range(bin_count)]
    for probability, outcome in zip(probabilities, outcomes, strict=True):
        _validate_probability(probability)
        if outcome not in (0, 1):
            raise ValueError("binary outcomes must be zero or one")
        index = min(int(probability * bin_count), bin_count - 1)
        buckets[index].append((probability, outcome))
    result = []
    gaps = []
    for index, bucket in enumerate(buckets):
        mean = sum(item[0] for item in bucket) / len(bucket) if bucket else None
        observed = sum(item[1] for item in bucket) / len(bucket) if bucket else None
        gap = abs(mean - observed) if mean is not None and observed is not None else None
        result.append(
            ReliabilityBin(
                lower=index / bin_count,
                upper=(index + 1) / bin_count,
                sample_size=len(bucket),
                mean_probability=mean,
                observed_rate=observed,
                absolute_gap=gap,
            )
        )
        if gap is not None:
            gaps.append((len(bucket), gap))
    total = len(probabilities)
    ece = sum(count * gap for count, gap in gaps) / total if total else None
    mce = max((gap for _, gap in gaps), default=None)
    return ReliabilitySummary(total, tuple(result), ece, mce, context, class_label)


def multiclass_reliability(
    probabilities: Sequence[Sequence[float]],
    outcomes: Sequence[int],
    *,
    class_labels: Sequence[str],
    context: ResearchContext,
    bin_count: int = 10,
) -> tuple[ReliabilitySummary, ...]:
    require_context(context)
    classes = _validate_multiclass(probabilities, outcomes, class_labels)
    return tuple(
        reliability_bins(
            tuple(row[index] for row in probabilities),
            tuple(1 if outcome == index else 0 for outcome in outcomes),
            context=context,
            class_label=class_labels[index],
            bin_count=bin_count,
        )
        for index in range(classes)
    )


@dataclass(frozen=True)
class TemporalObservation:
    observation_id: str
    occurred_at: datetime
    available_at: datetime

    def __post_init__(self) -> None:
        if (
            self.occurred_at.tzinfo is None
            or self.available_at.tzinfo is None
            or self.occurred_at.utcoffset() is None
            or self.available_at.utcoffset() is None
        ):
            raise ValueError("temporal observation timestamps must be timezone-aware")
        if (
            self.occurred_at.utcoffset().total_seconds() != 0
            or self.available_at.utcoffset().total_seconds() != 0
        ):
            raise ValueError("temporal observation timestamps must be UTC")
        if self.available_at < self.occurred_at:
            raise ValueError("available_at cannot precede occurred_at")


@dataclass(frozen=True)
class TemporalFold:
    train_ids: tuple[str, ...]
    validation_ids: tuple[str, ...]
    context: ResearchContext


@dataclass(frozen=True)
class TemporalPartition:
    train_ids: tuple[str, ...]
    calibration_ids: tuple[str, ...]
    test_ids: tuple[str, ...]
    final_holdout_ids: tuple[str, ...]
    context: ResearchContext


def _ordered_unique(
    observations: Sequence[TemporalObservation],
    context: ResearchContext,
) -> list[TemporalObservation]:
    require_context(context)
    if len(observations) > MAX_EVALUATION_ROWS:
        raise ValueError("temporal input exceeds the 100000-row safety limit")
    ordered = sorted(observations, key=lambda item: (item.occurred_at, item.observation_id))
    if len({item.observation_id for item in ordered}) != len(ordered):
        raise ValueError("duplicate observation ids are not allowed")
    return ordered


def rolling_origin_folds(
    observations: Sequence[TemporalObservation],
    *,
    minimum_train_size: int,
    validation_size: int,
    context: ResearchContext,
    step: int | None = None,
) -> tuple[TemporalFold, ...]:
    """Create non-overlapping validation folds; this does not fit a model."""

    ordered = _ordered_unique(observations, context)
    if minimum_train_size <= 0 or validation_size <= 0:
        raise ValueError("fold sizes must be positive")
    increment = validation_size if step is None else step
    if increment < validation_size:
        raise ValueError("step must be at least validation_size to avoid overlap")
    folds = []
    emitted_ids = 0
    train_end = minimum_train_size
    while train_end + validation_size <= len(ordered):
        if len(folds) >= MAX_FOLDS:
            raise ValueError("fold count exceeds the 10000-fold safety limit")
        if ordered[train_end - 1].occurred_at == ordered[train_end].occurred_at:
            raise ValueError("equal-time observations cannot cross a fold boundary")
        validation_end = train_end + validation_size
        if (
            validation_end < len(ordered)
            and ordered[validation_end - 1].occurred_at == ordered[validation_end].occurred_at
        ):
            raise ValueError("equal-time observations cannot cross a fold boundary")
        validation = ordered[train_end:validation_end]
        cutoff = validation[0].occurred_at
        training = [item for item in ordered[:train_end] if item.available_at < cutoff]
        if len(training) != train_end:
            raise ValueError("training observation was not available before validation")
        emitted_ids += len(training) + len(validation)
        if emitted_ids > MAX_EMITTED_FOLD_IDS:
            raise ValueError("fold output exceeds the 1000000-id safety limit")
        folds.append(
            TemporalFold(
                tuple(item.observation_id for item in training),
                tuple(item.observation_id for item in validation),
                context,
            )
        )
        train_end += increment
    return tuple(folds)


def temporal_partition(
    observations: Sequence[TemporalObservation],
    *,
    train_size: int,
    calibration_size: int,
    test_size: int,
    holdout_size: int,
    context: ResearchContext,
) -> TemporalPartition:
    """Create one explicit chronological train/calibration/test/final-holdout partition."""

    ordered = _ordered_unique(observations, context)
    sizes = (train_size, calibration_size, test_size, holdout_size)
    if any(type(size) is not int or size <= 0 for size in sizes):
        raise ValueError("all partition sizes must be positive integers")
    if sum(sizes) != len(ordered):
        raise ValueError("partition sizes must consume every observation")
    boundaries = (
        train_size,
        train_size + calibration_size,
        train_size + calibration_size + test_size,
    )
    for boundary in boundaries:
        if ordered[boundary - 1].occurred_at == ordered[boundary].occurred_at:
            raise ValueError("equal-time observations cannot cross a partition boundary")
    segments = (
        ordered[: boundaries[0]],
        ordered[boundaries[0] : boundaries[1]],
        ordered[boundaries[1] : boundaries[2]],
        ordered[boundaries[2] :],
    )
    for earlier, later in zip(segments, segments[1:], strict=False):
        cutoff = later[0].occurred_at
        if any(item.available_at >= cutoff for item in earlier):
            raise ValueError("earlier partition label was unavailable before the next partition")
    return TemporalPartition(
        *(tuple(item.observation_id for item in segment) for segment in segments),
        context=context,
    )
