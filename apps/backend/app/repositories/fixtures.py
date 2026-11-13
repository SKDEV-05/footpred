"""Fixture and statistics read queries.

No provider access, no writes. Callers receive ORM entities; the API layer maps them to
explicit response schemas.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.time import end_of_utc_day_exclusive, start_of_utc_day
from app.models.core import Match
from app.models.enums import MatchStatus
from app.models.statistics import TeamMatchStatistics
from app.repositories.base import Page, count_of, fetch_page


def _fixture_statement(
    *,
    date_from: date | None = None,
    date_to: date | None = None,
    competition_id: int | None = None,
    season_id: int | None = None,
    team_id: int | None = None,
    status: MatchStatus | None = None,
) -> Select:
    statement = select(Match)
    if date_from is not None:
        statement = statement.where(
            Match.kickoff_utc >= start_of_utc_day(date_from)
        )
    if date_to is not None:
        statement = statement.where(
            Match.kickoff_utc < end_of_utc_day_exclusive(date_to)
        )
    if competition_id is not None:
        statement = statement.where(Match.competition_id == competition_id)
    if season_id is not None:
        statement = statement.where(Match.season_id == season_id)
    if team_id is not None:
        statement = statement.where(
            or_(Match.home_team_id == team_id, Match.away_team_id == team_id)
        )
    if status is not None:
        statement = statement.where(Match.status == status)
    return statement


def list_fixtures(
    session: Session,
    *,
    page: int,
    page_size: int,
    date_from: date | None = None,
    date_to: date | None = None,
    competition_id: int | None = None,
    season_id: int | None = None,
    team_id: int | None = None,
    status: MatchStatus | None = None,
) -> Page[Match]:
    statement = _fixture_statement(
        date_from=date_from,
        date_to=date_to,
        competition_id=competition_id,
        season_id=season_id,
        team_id=team_id,
        status=status,
    ).options(
        joinedload(Match.competition),
        joinedload(Match.season),
        joinedload(Match.home_team),
        joinedload(Match.away_team),
        joinedload(Match.result),
    )
    statement = statement.order_by(Match.kickoff_utc.asc(), Match.id.asc())
    return fetch_page(
        session,
        statement=statement,
        count_statement=count_of(statement),
        page=page,
        page_size=page_size,
    )


def get_match(session: Session, match_id: int) -> Match | None:
    return session.execute(
        select(Match)
        .where(Match.id == match_id)
        .options(
            joinedload(Match.competition),
            joinedload(Match.season),
            joinedload(Match.home_team),
            joinedload(Match.away_team),
            joinedload(Match.result),
        )
    ).scalars().first()


def fixtures_in_window(
    session: Session,
    *,
    start_utc,
    end_utc,
    competition_id: int | None = None,
) -> list[Match]:
    statement = (
        select(Match)
        .where(Match.kickoff_utc >= start_utc, Match.kickoff_utc < end_utc)
        .options(
            joinedload(Match.competition),
            joinedload(Match.season),
            joinedload(Match.home_team),
            joinedload(Match.away_team),
            joinedload(Match.result),
        )
        .order_by(Match.kickoff_utc.asc(), Match.id.asc())
    )
    if competition_id is not None:
        statement = statement.where(Match.competition_id == competition_id)
    return list(session.execute(statement).scalars().all())


def team_matches(
    session: Session,
    *,
    team_id: int,
    page: int,
    page_size: int,
    date_from: date | None = None,
    date_to: date | None = None,
) -> Page[Match]:
    statement = _fixture_statement(
        date_from=date_from, date_to=date_to, team_id=team_id
    ).options(
        joinedload(Match.competition),
        joinedload(Match.season),
        joinedload(Match.home_team),
        joinedload(Match.away_team),
        joinedload(Match.result),
    )
    statement = statement.order_by(Match.kickoff_utc.desc(), Match.id.desc())
    return fetch_page(
        session,
        statement=statement,
        count_statement=count_of(statement),
        page=page,
        page_size=page_size,
    )


def statistics_for_match(
    session: Session, match_id: int
) -> list[TeamMatchStatistics]:
    return list(
        session.execute(
            select(TeamMatchStatistics)
            .where(TeamMatchStatistics.match_id == match_id)
            .order_by(TeamMatchStatistics.team_id.asc(), TeamMatchStatistics.metric.asc())
        ).scalars().all()
    )
