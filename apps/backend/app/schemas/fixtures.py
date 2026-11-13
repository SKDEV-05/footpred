"""Fixture, result, and statistics response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field

from app.schemas.common import UtcDatetime


class IdName(BaseModel):
    id: int
    name: str


class SeasonRef(BaseModel):
    id: int
    label: str


class ScoreOut(BaseModel):
    home: int
    away: int


class ResultOut(BaseModel):
    home_score: int | None
    away_score: int | None
    ht_home_score: int | None
    ht_away_score: int | None
    winner: str | None
    duration: str | None
    is_final: bool
    resolved_at: UtcDatetime


class FixtureSummary(BaseModel):
    id: int
    competition: IdName
    season: SeasonRef
    home_team: IdName
    away_team: IdName
    kickoff_utc: UtcDatetime
    status: str
    matchday: int | None
    stage: str | None
    venue_name: str | None
    score: ScoreOut | None = Field(
        default=None,
        description="Full-time score once a final result is stored; null when unavailable.",
    )


class FixtureDetail(FixtureSummary):
    attendance: int | None
    last_synced_at: UtcDatetime
    provider_last_updated: UtcDatetime | None
    statistics_available: bool
    result: ResultOut | None = Field(
        default=None, description="Null when no final result is stored."
    )


class TodayResponse(BaseModel):
    date: date
    timezone: str
    date_from_utc: UtcDatetime
    date_to_utc: UtcDatetime
    items: list[FixtureSummary]


class TeamStatisticsOut(BaseModel):
    team_id: int
    team_name: str
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description=(
            "Normalised metric name to value. An absent key means unavailable; "
            "0 is a measured zero."
        ),
    )


class MatchStatisticsResponse(BaseModel):
    match_id: int
    available: bool
    teams: list[TeamStatisticsOut]
