"""Provider-defined team match statistics.

One row per (match, team, metric). Absence of a row means unavailable; a row with value
0 means a measured zero. This is the schema-level enforcement of data rule D2.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UTCDateTime


class TeamMatchStatistics(TimestampMixin, Base):
    __tablename__ = "team_match_statistics"
    __table_args__ = (
        UniqueConstraint(
            "match_id", "team_id", "metric", name="uq_team_match_statistics_metric"
        ),
        CheckConstraint("value >= 0", name="value_non_negative"),
        CheckConstraint("length(metric) > 0", name="metric_non_empty"),
        Index("ix_team_match_statistics_match_id", "match_id"),
        Index("ix_team_match_statistics_team_id_metric", "team_id", "metric"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="RESTRICT"), nullable=False
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    metric: Mapped[str] = mapped_column(String(64), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    provider_last_updated: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    raw_payload_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_payloads.id", ondelete="SET NULL"), nullable=True
    )
    sync_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("data_sync_runs.id", ondelete="SET NULL"), nullable=True
    )

    match: Mapped["Match"] = relationship(back_populates="statistics", viewonly=True)
    team: Mapped["Team"] = relationship(viewonly=True)


if TYPE_CHECKING:
    from app.models.core import Match, Team
