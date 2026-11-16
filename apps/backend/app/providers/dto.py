"""Internal provider-neutral data transfer objects.

Vendor JSON never crosses this boundary. Dates, enums, and identifiers are already
normalised enough for domain validation, but provider enum values are kept as strings
so an unknown value can be quarantined by the validation layer instead of silently
defaulting.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Generic, Mapping, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class RawResponse:
    """One archived HTTP response observation."""

    url: str
    path: str
    params: Mapping[str, str]
    status_code: int
    headers: Mapping[str, str]
    content: bytes
    fetched_at: datetime

    @property
    def content_type(self) -> str | None:
        return self.headers.get("content-type")


@dataclass(frozen=True)
class Fetched(Generic[T]):
    """A parsed payload plus the archive row that proves where it came from.

    ``skipped`` counts records the provider returned that cannot be stored yet (for
    example a knockout fixture whose participants are still undecided). They are
    reported by the job, never silently stored with invented teams.
    """

    items: T
    raw_payload_id: int
    skipped: int = 0


@dataclass(frozen=True)
class ProviderSeason:
    external_id: str
    start_date: date
    end_date: date
    current_matchday: int | None
    is_current: bool | None = None


@dataclass(frozen=True)
class ProviderCompetition:
    external_id: str
    name: str
    code: str | None
    type: str
    country_name: str | None = None
    country_code: str | None = None
    emblem: str | None = None
    seasons: tuple[ProviderSeason, ...] = ()
    current_season: ProviderSeason | None = None


@dataclass(frozen=True)
class ProviderTeamRef:
    external_id: str
    name: str
    short_name: str | None = None
    tla: str | None = None
    country_name: str | None = None
    country_code: str | None = None
    crest: str | None = None


@dataclass(frozen=True)
class ProviderTeam:
    external_id: str
    name: str
    short_name: str | None
    tla: str | None
    country_name: str | None = None
    country_code: str | None = None
    venue_name: str | None = None
    founded: int | None = None
    crest: str | None = None


@dataclass(frozen=True)
class ProviderScore:
    home: int | None
    away: int | None
    ht_home: int | None
    ht_away: int | None
    winner: str | None
    duration: str | None
    extra_home: int | None = None
    extra_away: int | None = None
    penalties_home: int | None = None
    penalties_away: int | None = None


@dataclass(frozen=True)
class ProviderMatch:
    external_id: str
    competition: ProviderCompetition
    season: ProviderSeason
    kickoff_utc: datetime
    status: str
    matchday: int | None
    stage: str | None
    group_name: str | None
    home_team: ProviderTeamRef
    away_team: ProviderTeamRef
    venue_name: str | None = None
    attendance: int | None = None
    score: ProviderScore | None = None
    provider_last_updated: datetime | None = None


@dataclass(frozen=True)
class ProviderTeamStatistics:
    team_external_id: str
    metrics: Mapping[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderMatchDetail:
    match: ProviderMatch
    statistics: tuple[ProviderTeamStatistics, ...] = ()
