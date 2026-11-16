"""Match analysis persistence models.

Stores statistical analysis runs, expected goals, 1X2 probabilities, score distributions,
feature sets, model versions, and audit trails.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Mapping

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UTCDateTime


class AnalysisStatus(StrEnum):
    READY = "READY"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    ANALYSIS_FAILED = "ANALYSIS_FAILED"


class MatchAnalysis(TimestampMixin, Base):
    __tablename__ = "match_analyses"
    __table_args__ = (
        CheckConstraint(
            "home_win_probability IS NULL OR (home_win_probability >= 0.0 AND home_win_probability <= 1.0)",
            name="home_win_prob_range",
        ),
        CheckConstraint(
            "draw_probability IS NULL OR (draw_probability >= 0.0 AND draw_probability <= 1.0)",
            name="draw_prob_range",
        ),
        CheckConstraint(
            "away_win_probability IS NULL OR (away_win_probability >= 0.0 AND away_win_probability <= 1.0)",
            name="away_win_prob_range",
        ),
        CheckConstraint(
            "expected_home_goals IS NULL OR expected_home_goals >= 0.0",
            name="exp_home_goals_non_negative",
        ),
        CheckConstraint(
            "expected_away_goals IS NULL OR expected_away_goals >= 0.0",
            name="exp_away_goals_non_negative",
        ),
        Index("ix_match_analyses_match_id", "match_id"),
        Index("ix_match_analyses_status", "status"),
        Index("ix_match_analyses_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    model_id: Mapped[str] = mapped_column(String(64), nullable=False)
    model_version: Mapped[str] = mapped_column(String(32), nullable=False)
    dataset_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dataset_digest: Mapped[str | None] = mapped_column(String(64), nullable=True)
    data_classification: Mapped[str] = mapped_column(String(32), nullable=False)

    home_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    away_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False
    )
    season_id: Mapped[int] = mapped_column(Integer, nullable=False)

    kickoff_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    analysis_as_of: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    # Expected goals
    expected_home_goals: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_away_goals: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 1X2 Probabilities
    home_win_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    draw_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    away_win_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Secondary market probabilities
    btts_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    over_1_5_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    under_1_5_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    over_2_5_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    under_2_5_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    over_3_5_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    under_3_5_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Sample sizes
    home_sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    h2h_sample_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # JSON payloads for complete fidelity
    scoreline_probabilities: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True
    )
    features: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    limitations: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    evaluation_metrics: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
