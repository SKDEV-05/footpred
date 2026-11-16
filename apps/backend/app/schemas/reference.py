"""Competition, season, and team response schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class CountryOut(BaseModel):
    id: int
    name: str
    iso_code: str | None


class CompetitionSummary(BaseModel):
    id: int
    name: str
    code: str | None
    type: str
    country: CountryOut | None
    emblem_url: str | None = None


class CompetitionDetail(CompetitionSummary):
    season_count: int


class SeasonSummary(BaseModel):
    id: int
    competition_id: int
    label: str
    start_date: date
    end_date: date
    current_matchday: int | None
    is_current: bool


class TeamSummary(BaseModel):
    id: int
    name: str
    short_name: str | None
    tla: str | None
    country: CountryOut | None
    crest_url: str | None = None


class TeamDetail(TeamSummary):
    venue_name: str | None
    founded: int | None
    match_count: int
