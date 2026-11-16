"""Model evaluation endpoints.

The evaluation is expensive (a full chronological replay of the corpus) and must be
reproducible, so a run is persisted and served from storage. A run's identity is
``(protocol_version, evaluation_version, dataset_digest)``: the same corpus evaluated by
the same protocol cannot create a second row, and a client can never see a number the
engine did not store.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.exceptions import AppError, NotFoundError
from app.core.time import utc_now
from app.models.evaluation import ModelEvaluation
from app.repositories.analysis import DatasetProvenanceError
from app.repositories.evaluation import (
    EvaluationUnavailable,
    evaluate_corpus,
    latest_run,
    list_runs,
)
from app.schemas.evaluation import (
    EvaluationReportBodyOut,
    EvaluationRunOut,
    EvaluationRunSummaryOut,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _map_run(record: ModelEvaluation) -> EvaluationRunOut:
    return EvaluationRunOut(
        id=record.id,
        protocol_version=record.protocol_version,
        evaluation_version=record.evaluation_version,
        dataset_id=record.dataset_id,
        dataset_digest=record.dataset_digest,
        provider_code=record.provider_code,
        sample_size=record.sample_size,
        window_from=record.window_from,
        window_to=record.window_to,
        generated_at=record.generated_at,
        report=EvaluationReportBodyOut(**record.report),
    )


def _summary(record: ModelEvaluation) -> EvaluationRunSummaryOut:
    keys = [item.get("key") for item in (record.report or {}).get("models", [])]
    return EvaluationRunSummaryOut(
        id=record.id,
        protocol_version=record.protocol_version,
        evaluation_version=record.evaluation_version,
        dataset_id=record.dataset_id,
        dataset_digest=record.dataset_digest,
        sample_size=record.sample_size,
        window_from=record.window_from,
        window_to=record.window_to,
        generated_at=record.generated_at,
        model_keys=[key for key in keys if key],
    )


@router.post("/run", response_model=EvaluationRunOut)
def run_evaluation(
    as_of: datetime | None = Query(
        None,
        description=(
            "Corpus checkpoint. Defaults to now. Every stored result observed before "
            "this instant is eligible; no future result can enter the replay."
        ),
    ),
    session: Session = Depends(get_session),
) -> EvaluationRunOut:
    """Evaluate every model on the stored corpus and persist the report.

    Re-running against an unchanged corpus returns the existing stored run rather than
    creating a duplicate or silently recomputing different numbers.
    """

    checkpoint = _aware(as_of) if as_of is not None else utc_now()
    if checkpoint > utc_now():
        raise AppError(
            "The evaluation checkpoint cannot be in the future.",
            code="evaluation_checkpoint_invalid",
            http_status=422,
        )

    try:
        record = evaluate_corpus(session, checkpoint=checkpoint)
    except DatasetProvenanceError as exc:
        raise AppError(
            str(exc),
            code="evaluation_provenance_incomplete",
            http_status=409,
        ) from exc
    except EvaluationUnavailable as exc:
        raise AppError(
            "The stored corpus cannot support a chronological evaluation: "
            f"{exc}.",
            code="evaluation_insufficient_data",
            http_status=409,
        ) from exc

    logger.info(
        "model evaluation served",
        extra={
            "event": "evaluation.served",
            "component": "evaluation",
            "evaluation_id": record.id,
            "sample_size": record.sample_size,
        },
    )
    return _map_run(record)


@router.get("/latest", response_model=EvaluationRunOut)
def get_latest_evaluation(
    session: Session = Depends(get_session),
) -> EvaluationRunOut:
    """Return the most recently generated stored evaluation."""

    record = latest_run(session)
    if record is None:
        raise NotFoundError("No model evaluation has been generated yet.")
    return _map_run(record)


@router.get("/runs", response_model=list[EvaluationRunSummaryOut])
def list_evaluation_runs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: Session = Depends(get_session),
) -> list[EvaluationRunSummaryOut]:
    """List stored evaluation runs, newest first, without their full report bodies."""

    return [_summary(record) for record in list_runs(session, limit=limit, offset=offset)]


@router.get("/{run_id}", response_model=EvaluationRunOut)
def get_evaluation(
    run_id: int = Path(..., ge=1, description="Evaluation run identifier."),
    session: Session = Depends(get_session),
) -> EvaluationRunOut:
    """Retrieve one stored evaluation run by identifier."""

    record = session.get(ModelEvaluation, run_id)
    if record is None:
        raise NotFoundError("evaluation", run_id)
    return _map_run(record)
