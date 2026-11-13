"""Core football entities: countries, competitions, seasons, teams, matches, results."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UTCDateTime
from app.models.enums import (
    MatchDuration,
    MatchStatus,
    MatchWinner,
    CompetitionType,
    enum_column,
)

if TYPE_CHECKING:
    from app.models.statistics import TeamMatchStatistics


class Country(TimestampMixin, Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    normalized_name: Mapped[str] = mapped_column(
        String(120), nullable=False, unique=True, index=True
    )
    iso_code: Mapped[str | None] = mapped_column(String(3), nullable=True, index=True)

    competitions: Mapped[list["Competition"]] = relationship(
        back_populates="country", viewonly=True
    )
    teams: Mapped[list["Team"]] = relationship(back_populates="country", viewonly=True)


class Competition(TimestampMixin, Base):
    __tablename__ = "competitions"
    __table_args__ = (
        Index("ix_competitions_name", "name"),
        Index("ix_competitions_normalized_name", "normalized_name"),
        Index("ix_competitions_country_id", "country_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(160), nullable=False)
    code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    type: Mapped[CompetitionType] = mapped_column(
        enum_column(CompetitionType, name="competition_type"), nullable=False
    )
    country_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="SET NULL"), nullable=True
    )

    country: Mapped[Country | None] = relationship(
        back_populates="competitions", viewonly=True
    )
    seasons: Mapped[list["Season"]] = relationship(
        back_populates="competition", viewonly=True
    )


class Season(TimestampMixin, Base):
    __tablename__ = "seasons"
    __table_args__ = (
        UniqueConstraint(
            "competition_id", "label", name="uq_seasons_competition_label"
        ),
        UniqueConstraint("id", "competition_id", name="uq_seasons_id_competition"),
        CheckConstraint("end_date >= start_date", name="season_dates"),
        Index("ix_seasons_competition_id_start_date", "competition_id", "start_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    current_matchday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    competition: Mapped[Competition] = relationship(
        back_populates="seasons", viewonly=True
    )


class Team(TimestampMixin, Base):
    __tablename__ = "teams"
    __table_args__ = (
        Index("ix_teams_name", "name"),
        Index("ix_teams_normalized_name", "normalized_name"),
        Index("ix_teams_country_id", "country_id"),
        CheckConstraint(
            "founded IS NULL OR (founded >= 1850 AND founded <= 2100)",
            name="founded_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(160), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    tla: Mapped[str | None] = mapped_column(String(8), nullable=True)
    country_id: Mapped[int | None] = mapped_column(
        ForeignKey("countries.id", ondelete="SET NULL"), nullable=True
    )
    venue_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    founded: Mapped[int | None] = mapped_column(Integer, nullable=True)

    country: Mapped[Country | None] = relationship(
        back_populates="teams", viewonly=True
    )


class Match(TimestampMixin, Base):
    __tablename__ = "matches"
    __table_args__ = (
        ForeignKeyConstraint(
            ["season_id", "competition_id"],
            ["seasons.id", "seasons.competition_id"],
            name="fk_matches_season_competition",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "season_id",
            "home_team_id",
            "away_team_id",
            "kickoff_utc",
            name="uq_matches_natural_key",
        ),
        CheckConstraint("home_team_id <> away_team_id", name="different_teams"),
        CheckConstraint(
            "attendance IS NULL OR attendance >= 0", name="attendance_non_negative"
        ),
        CheckConstraint("matchday IS NULL OR matchday > 0", name="matchday_positive"),
        Index("ix_matches_kickoff_utc", "kickoff_utc"),
        Index(
            "ix_matches_competition_id_kickoff_utc", "competition_id", "kickoff_utc"
        ),
        Index("ix_matches_home_team_id_kickoff_utc", "home_team_id", "kickoff_utc"),
        Index("ix_matches_away_team_id_kickoff_utc", "away_team_id", "kickoff_utc"),
        Index("ix_matches_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competition_id: Mapped[int] = mapped_column(
        ForeignKey("competitions.id", ondelete="RESTRICT"), nullable=False
    )
    season_id: Mapped[int] = mapped_column(Integer, nullable=False)
    home_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    away_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="RESTRICT"), nullable=False
    )
    kickoff_utc: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    status: Mapped[MatchStatus] = mapped_column(
        enum_column(MatchStatus, name="match_status"), nullable=False
    )
    matchday: Mapped[int | None] = mapped_column(Integer, nullable=True)
    stage: Mapped[str | None] = mapped_column(String(48), nullable=True)
    group_name: Mapped[str | None] = mapped_column(String(16), nullable=True)
    venue_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    attendance: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    last_synced_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)
    provider_last_updated: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )

    competition: Mapped[Competition] = relationship(
        foreign_keys=[competition_id], viewonly=True, overlaps="season"
    )
    season: Mapped[Season] = relationship(
        foreign_keys=[season_id], viewonly=True, overlaps="competition"
    )
    home_team: Mapped[Team] = relationship(
        foreign_keys=[home_team_id], viewonly=True
    )
    away_team: Mapped[Team] = relationship(
        foreign_keys=[away_team_id], viewonly=True
    )
    result: Mapped["MatchResult | None"] = relationship(
        back_populates="match", uselist=False, viewonly=True
    )
    statistics: Mapped[list["TeamMatchStatistics"]] = relationship(
        back_populates="match", viewonly=True
    )


class MatchResult(TimestampMixin, Base):
    __tablename__ = "match_results"
    __table_args__ = (
        CheckConstraint(
            "home_score IS NULL OR home_score >= 0", name="home_score_non_negative"
        ),
        CheckConstraint(
            "away_score IS NULL OR away_score >= 0", name="away_score_non_negative"
        ),
        CheckConstraint(
            "(home_score IS NULL AND away_score IS NULL) OR "
            "(home_score IS NOT NULL AND away_score IS NOT NULL)",
            name="full_time_scores_together",
        ),
        CheckConstraint(
            "(ht_home_score IS NULL AND ht_away_score IS NULL) OR "
            "(ht_home_score IS NOT NULL AND ht_away_score IS NOT NULL)",
            name="half_time_scores_together",
        ),
    )

    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="RESTRICT"), primary_key=True
    )
    home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ht_home_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ht_away_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    winner: Mapped[MatchWinner | None] = mapped_column(
        enum_column(MatchWinner, name="match_winner"), nullable=True
    )
    duration: Mapped[MatchDuration | None] = mapped_column(
        enum_column(MatchDuration, name="match_duration"), nullable=True
    )
    status: Mapped[MatchStatus] = mapped_column(
        enum_column(MatchStatus, name="match_status"), nullable=False
    )
    is_final: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    provider_last_updated: Mapped[datetime | None] = mapped_column(
        UTCDateTime(), nullable=True
    )
    resolved_at: Mapped[datetime] = mapped_column(UTCDateTime(), nullable=False)

    match: Mapped[Match] = relationship(back_populates="result", viewonly=True)


# Re-exported for callers that only import this module.
__all__ = [
    "Country",
    "Competition",
    "Season",
    "Team",
    "Match",
    "MatchResult",
]
