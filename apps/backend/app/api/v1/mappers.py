"""ORM to response-schema mapping.

Explicit mapping keeps the HTTP contract independent of storage column names and makes
the "missing is not zero" rule visible: a score is only produced from a final result.
"""

from __future__ import annotations

from app.models.core import Competition, Match, Season, Team
from app.models.statistics import TeamMatchStatistics
from app.schemas.fixtures import (
    CompetitionRef,
    FixtureDetail,
    FixtureSummary,
    ResultOut,
    ScoreOut,
    SeasonRef,
    TeamRef,
    TeamStatisticsOut,
)
from app.schemas.reference import (
    CompetitionDetail,
    CompetitionSummary,
    CountryOut,
    SeasonSummary,
    TeamDetail,
    TeamSummary,
)
from app.schemas.sync import SyncRunOut
from app.models.provenance import DataSyncRun


def country_out(country) -> CountryOut | None:
    if country is None:
        return None
    return CountryOut(id=country.id, name=country.name, iso_code=country.iso_code)


def competition_summary(competition: Competition) -> CompetitionSummary:
    return CompetitionSummary(
        id=competition.id,
        name=competition.name,
        code=competition.code,
        type=competition.type.value,
        country=country_out(competition.country),
        emblem_url=competition.emblem_url,
    )


def competition_detail(competition: Competition, *, season_count: int) -> CompetitionDetail:
    return CompetitionDetail(
        id=competition.id,
        name=competition.name,
        code=competition.code,
        type=competition.type.value,
        country=country_out(competition.country),
        emblem_url=competition.emblem_url,
        season_count=season_count,
    )


def season_summary(season: Season) -> SeasonSummary:
    return SeasonSummary(
        id=season.id,
        competition_id=season.competition_id,
        label=season.label,
        start_date=season.start_date,
        end_date=season.end_date,
        current_matchday=season.current_matchday,
        is_current=season.is_current,
    )


def team_summary(team: Team) -> TeamSummary:
    return TeamSummary(
        id=team.id,
        name=team.name,
        short_name=team.short_name,
        tla=team.tla,
        country=country_out(team.country),
        crest_url=team.crest_url,
    )


def team_detail(team: Team, *, match_count: int) -> TeamDetail:
    return TeamDetail(
        id=team.id,
        name=team.name,
        short_name=team.short_name,
        tla=team.tla,
        country=country_out(team.country),
        crest_url=team.crest_url,
        venue_name=team.venue_name,
        founded=team.founded,
        match_count=match_count,
    )


def fixture_summary(match: Match) -> FixtureSummary:
    result = match.result
    score = None
    if (
        result is not None
        and result.is_final
        and result.home_score is not None
        and result.away_score is not None
    ):
        score = ScoreOut(home=result.home_score, away=result.away_score)

    return FixtureSummary(
        id=match.id,
        competition=CompetitionRef(
            id=match.competition.id,
            name=match.competition.name,
            code=match.competition.code,
            country=country_out(match.competition.country),
            emblem_url=match.competition.emblem_url,
        ),
        season=SeasonRef(id=match.season.id, label=match.season.label),
        home_team=TeamRef(
            id=match.home_team.id,
            name=match.home_team.name,
            crest_url=match.home_team.crest_url,
        ),
        away_team=TeamRef(
            id=match.away_team.id,
            name=match.away_team.name,
            crest_url=match.away_team.crest_url,
        ),
        kickoff_utc=match.kickoff_utc,
        status=match.status.value,
        matchday=match.matchday,
        stage=match.stage,
        venue_name=match.venue_name,
        score=score,
    )


def fixture_detail(match: Match, *, statistics_available: bool) -> FixtureDetail:
    summary = fixture_summary(match)
    result = match.result
    result_out = None
    if result is not None and result.is_final:
        result_out = ResultOut(
            home_score=result.home_score,
            away_score=result.away_score,
            ht_home_score=result.ht_home_score,
            ht_away_score=result.ht_away_score,
            winner=result.winner.value if result.winner is not None else None,
            duration=result.duration.value if result.duration is not None else None,
            is_final=result.is_final,
            resolved_at=result.resolved_at,
        )
    return FixtureDetail(
        **summary.model_dump(),
        attendance=match.attendance,
        last_synced_at=match.last_synced_at,
        provider_last_updated=match.provider_last_updated,
        statistics_available=statistics_available,
        result=result_out,
    )


def team_statistics(
    match: Match, rows: list[TeamMatchStatistics]
) -> list[TeamStatisticsOut]:
    by_team: dict[int, dict[str, float]] = {
        match.home_team_id: {},
        match.away_team_id: {},
    }
    for row in rows:
        bucket = by_team.setdefault(row.team_id, {})
        bucket[row.metric] = row.value

    teams = {match.home_team_id: match.home_team, match.away_team_id: match.away_team}
    output: list[TeamStatisticsOut] = []
    for team_id in (match.home_team_id, match.away_team_id):
        team = teams[team_id]
        output.append(
            TeamStatisticsOut(
                team_id=team.id,
                team_name=team.name,
                metrics=by_team.get(team_id, {}),
            )
        )
    return output


def sync_run_out(run: DataSyncRun) -> SyncRunOut:
    return SyncRunOut(
        id=run.id,
        job_type=run.job_type,
        status=run.status.value,
        started_at=run.started_at,
        finished_at=run.finished_at,
        records_fetched=run.records_fetched,
        records_created=run.records_created,
        records_updated=run.records_updated,
        records_unchanged=run.records_unchanged,
        records_rejected=run.records_rejected,
        error_count=run.error_count,
    )
