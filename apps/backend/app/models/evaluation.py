"""Persisted model-evaluation runs.

An evaluation run is a versioned, append-only document: the protocol, evaluation
version, dataset digest, and report body are stored together so a dashboard can never
display numbers that were not actually computed from the stored corpus.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, Index, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin, UTCDateTime


class ModelEvaluation(TimestampMixin, Base):
    __tablename__ = "model_evaluations"
    __table_args__ = (
        UniqueConstraint(
            "protocol_version",
            "evaluation_version",
            "dataset_digest",
            name="uq_model_evaluations_protocol_version_dataset",
        ),
        CheckConstraint("sample_size >= 0", name="model_evaluations_sample_non_negative"),
        Index("ix_model_evaluations_generated_at", "generated_at"),
        Index("ix_model_evaluations_dataset_digest", "dataset_digest"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    protocol_version: Mapped[str] = mapped_column(String(32), nullable=False)
    evaluation_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(String(96), nullable=True)
    dataset_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    provider_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    window_from: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    window_to: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    report: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
