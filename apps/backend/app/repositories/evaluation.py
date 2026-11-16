"""Persistence for model-evaluation runs.

A run is identified by ``(protocol_version, evaluation_version, dataset_digest)``. The
same corpus under the same protocol must not create a second row: recomputation could
drift with unrelated code changes, and an evaluation that silently changes is worse than
no evaluation at all.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.intelligence.backtest import (
    BACKTEST_EVALUATION_VERSION,
    BACKTEST_PROTOCOL_VERSION,
    run_multi_competition_backtest,
)
from app.models.evaluation import ModelEvaluation
from app.repositories.analysis import load_corpus_dataset


class EvaluationUnavailable(ValueError):
    """The stored corpus cannot support a chronological evaluation."""


def find_run_by_identity(
    session: Session,
    *,
    dataset_digest: str,
    protocol_version: str = BACKTEST_PROTOCOL_VERSION,
    evaluation_version: str = BACKTEST_EVALUATION_VERSION,
) -> ModelEvaluation | None:
    return session.execute(
        select(ModelEvaluation).where(
            ModelEvaluation.protocol_version == protocol_version,
            ModelEvaluation.evaluation_version == evaluation_version,
            ModelEvaluation.dataset_digest == dataset_digest,
        )
    ).scalar_one_or_none()


def latest_run(session: Session) -> ModelEvaluation | None:
    return session.execute(
        select(ModelEvaluation)
        .order_by(desc(ModelEvaluation.generated_at), desc(ModelEvaluation.id))
        .limit(1)
    ).scalar_one_or_none()


def list_runs(session: Session, *, limit: int = 20, offset: int = 0) -> list[ModelEvaluation]:
    return list(
        session.execute(
            select(ModelEvaluation)
            .order_by(desc(ModelEvaluation.generated_at), desc(ModelEvaluation.id))
            .limit(limit)
            .offset(offset)
        ).scalars().all()
    )


def _window(report: dict) -> tuple[datetime | None, datetime | None]:
    window = report.get("window") or {}
    start = window.get("from")
    end = window.get("to")
    return (
        datetime.fromisoformat(start) if start else None,
        datetime.fromisoformat(end) if end else None,
    )


def evaluate_corpus(
    session: Session,
    *,
    checkpoint: datetime,
) -> ModelEvaluation:
    """Load, evaluate, and persist the corpus as of ``checkpoint``.

    Raises :class:`EvaluationUnavailable` when the corpus is too small, and lets
    :class:`~app.repositories.analysis.DatasetProvenanceError` propagate so the caller
    cannot present an unevidenced evaluation as verified.
    """

    dataset, _meta = load_corpus_dataset(session, as_of=checkpoint)
    if dataset is None:
        raise EvaluationUnavailable("no_completed_results")

    existing = find_run_by_identity(session, dataset_digest=dataset.digest)
    if existing is not None:
        return existing

    report = run_multi_competition_backtest(dataset)
    if not report.get("evaluated"):
        raise EvaluationUnavailable(report.get("reason") or "evaluation_not_possible")

    window_from, window_to = _window(report)
    record = ModelEvaluation(
        protocol_version=BACKTEST_PROTOCOL_VERSION,
        evaluation_version=BACKTEST_EVALUATION_VERSION,
        dataset_id=report.get("dataset", {}).get("dataset_id"),
        dataset_digest=dataset.digest,
        provider_code=report.get("dataset", {}).get("provider_code"),
        sample_size=int(report.get("sample_size", 0)),
        window_from=window_from,
        window_to=window_to,
        generated_at=utc_now(),
        report=report,
    )
    session.add(record)
    try:
        session.commit()
    except Exception:
        session.rollback()
        concurrent = find_run_by_identity(session, dataset_digest=dataset.digest)
        if concurrent is None:
            raise
        return concurrent
    session.refresh(record)
    return record
