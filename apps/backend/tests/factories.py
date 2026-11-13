"""SYNTHETIC TEST DATA and reusable doubles.

Every identifier, name, score, and date here is invented. The structure mirrors the
documented provider shape so the parser can be exercised without any network access.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.providers.base import ProviderAdapter, ProviderCapabilities
from app.providers.dto import (
    Fetched,
    ProviderCompetition,
    ProviderMatch,
    ProviderMatchDetail,
    ProviderScore,
    ProviderSeason,
    ProviderTeam,
    ProviderTeamRef,
    ProviderTeamStatistics,
)

SYNTHETIC_NOTICE = "SYNTHETIC TEST DATA"

SYNTHETIC_SEASON = ProviderSeason(
    external_id="7001",
    start_date=date(2026, 8, 1),
    end_date=date(2027, 5, 31),
    current_matchday=12,
    is_current=True,
)

SYNTHETIC_COMPETITION = ProviderCompetition(
    external_id="9001",
    name="Example League",
    code="EL",
    type="LEAGUE",
    country_name="Examplia",
    country_code="EX",
    seasons=(SYNTHETIC_SEASON,),
)

SYNTHETIC_HOME = ProviderTeamRef(
    external_id="501", name="Example Home FC", short_name="Home", tla="EXH"
)
SYNTHETIC_AWAY = ProviderTeamRef(
    external_id="502", name="Example Away FC", short_name="Away", tla="EXA"
)

SYNTHETIC_KICKOFF = datetime(2026, 8, 15, 15, 0, tzinfo=timezone.utc)


def make_score(
    home: int | None,
    away: int | None,
    *,
    ht_home: int | None = None,
    ht_away: int | None = None,
    winner: str | None = None,
    duration: str | None = "REGULAR",
) -> ProviderScore:
    return ProviderScore(
        home=home,
        away=away,
        ht_home=ht_home,
        ht_away=ht_away,
        winner=winner,
        duration=duration,
    )


def make_match(
    *,
    external_id: str = "8001",
    status: str = "SCHEDULED",
    kickoff: datetime = SYNTHETIC_KICKOFF,
    competition: ProviderCompetition = SYNTHETIC_COMPETITION,
    season: ProviderSeason | None = None,
    home: ProviderTeamRef = SYNTHETIC_HOME,
    away: ProviderTeamRef = SYNTHETIC_AWAY,
    score: ProviderScore | None = None,
    matchday: int | None = 1,
    stage: str | None = "REGULAR_SEASON",
    attendance: int | None = None,
    venue: str | None = None,
) -> ProviderMatch:
    return ProviderMatch(
        external_id=external_id,
        competition=competition,
        season=season or competition.seasons[0],
        kickoff_utc=kickoff,
        status=status,
        matchday=matchday,
        stage=stage,
        group_name=None,
        home_team=home,
        away_team=away,
        venue_name=venue,
        attendance=attendance,
        score=score,
        provider_last_updated=datetime(2026, 8, 15, 16, 0, tzinfo=timezone.utc),
    )


def make_team(external_id: str = "501", name: str = "Example Home FC") -> ProviderTeam:
    return ProviderTeam(
        external_id=external_id,
        name=name,
        short_name="Home",
        tla="EXH",
        country_name="Examplia",
        country_code="EX",
        venue_name=None,
        founded=1990,
    )


def make_detail(
    match: ProviderMatch,
    *,
    home_metrics: dict[str, float] | None = None,
    away_metrics: dict[str, float] | None = None,
) -> ProviderMatchDetail:
    statistics = []
    if home_metrics is not None:
        statistics.append(
            ProviderTeamStatistics(
                team_external_id=match.home_team.external_id, metrics=home_metrics
            )
        )
    if away_metrics is not None:
        statistics.append(
            ProviderTeamStatistics(
                team_external_id=match.away_team.external_id, metrics=away_metrics
            )
        )
    return ProviderMatchDetail(match=match, statistics=tuple(statistics))


class RecordingArchive:
    """In-memory archive sink for adapter tests."""

    def __init__(self) -> None:
        self.entries: list[tuple[object, str]] = []

    def store(self, response, *, resource_type: str) -> int:
        self.entries.append((response, resource_type))
        return len(self.entries)


class FakeAdapter(ProviderAdapter):
    """Adapter double with fixed payloads, used to test the sync engine."""

    code = "fake_provider"
    name = "Fake Provider"
    capabilities = ProviderCapabilities(
        competitions=True,
        seasons=True,
        teams=True,
        fixtures=True,
        results=True,
        match_statistics=True,
    )

    def __init__(
        self,
        *,
        competitions: tuple[ProviderCompetition, ...] = (),
        matches: tuple[ProviderMatch, ...] = (),
        details: dict[str, ProviderMatchDetail] | None = None,
        fail_matches: bool = False,
        raw_payload_id: int | None = 1,
    ) -> None:
        self.competitions = competitions
        self.matches = matches
        self.details = details or {}
        self.fail_matches = fail_matches
        self.raw_payload_id = raw_payload_id

    def _fetched(self, value):
        return Fetched(items=value, raw_payload_id=self.raw_payload_id)

    def fetch_competitions(self):
        return self._fetched(list(self.competitions))

    def fetch_competition(self, external_id: str):
        for competition in self.competitions:
            if competition.external_id == external_id:
                return self._fetched(competition)
        raise AssertionError(f"unknown competition {external_id}")

    def fetch_seasons(self, competition_external_id: str):
        competition = self.fetch_competition(competition_external_id).items
        return self._fetched(list(competition.seasons))

    def fetch_teams(self, competition_external_id: str, season_external_id=None):
        return self._fetched([make_team()])

    def fetch_matches(
        self,
        *,
        date_from,
        date_to,
        competition_external_id=None,
        season_external_id=None,
        status=None,
    ):
        if self.fail_matches:
            from app.core.exceptions import ProviderError

            raise ProviderError("synthetic provider outage")
        return self._fetched(
            [match for match in self.matches if status is None or match.status == status]
        )

    def fetch_match_detail(self, match_external_id: str):
        return self._fetched(self.details[match_external_id])
