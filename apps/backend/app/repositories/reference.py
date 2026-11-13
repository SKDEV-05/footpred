"""Competition, season, and team read queries."""

from __future__ import annotations

from sqlalchemy import Select, distinct, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.core import Competition, Match, Season, Team
from app.normalization.names import normalize_name
from app.repositories.base import Page, count_of, fetch_page


def _competition_statement(
    *, country_id: int | None = None, query: str | None = None
) -> Select:
    statement = select(Competition)
    if country_id is not None:
        statement = statement.where(Competition.country_id == country_id)
    if query:
        statement = statement.where(
            Competition.normalized_name.contains(normalize_name(query))
        )
    return statement


def list_competitions(
    session: Session,
    *,
    page: int,
    page_size: int,
    country_id: int | None = None,
    query: str | None = None,
) -> Page[Competition]:
    statement = _competition_statement(country_id=country_id, query=query).options(
        joinedload(Competition.country)
    )
    statement = statement.order_by(Competition.name.asc(), Competition.id.asc())
    return fetch_page(
        session,
        statement=statement,
        count_statement=count_of(statement),
        page=page,
        page_size=page_size,
    )


def get_competition(session: Session, competition_id: int) -> Competition | None:
    return session.execute(
        select(Competition)
        .where(Competition.id == competition_id)
        .options(joinedload(Competition.country))
    ).scalars().first()


def season_count(session: Session, competition_id: int) -> int:
    return int(
        session.execute(
            select(func.count(Season.id)).where(
                Season.competition_id == competition_id
            )
        ).scalar_one()
    )


def list_seasons(
    session: Session,
    *,
    page: int,
    page_size: int,
    competition_id: int | None = None,
) -> Page[Season]:
    statement = select(Season)
    if competition_id is not None:
        statement = statement.where(Season.competition_id == competition_id)
    statement = statement.order_by(Season.start_date.desc(), Season.id.desc())
    return fetch_page(
        session,
        statement=statement,
        count_statement=count_of(statement),
        page=page,
        page_size=page_size,
    )


def get_season(session: Session, season_id: int) -> Season | None:
    return session.get(Season, season_id)


def _team_statement(
    *, country_id: int | None = None, query: str | None = None
) -> Select:
    statement = select(Team)
    if country_id is not None:
        statement = statement.where(Team.country_id == country_id)
    if query:
        statement = statement.where(
            Team.normalized_name.contains(normalize_name(query))
        )
    return statement


def list_teams(
    session: Session,
    *,
    page: int,
    page_size: int,
    country_id: int | None = None,
    query: str | None = None,
) -> Page[Team]:
    statement = _team_statement(country_id=country_id, query=query).options(
        joinedload(Team.country)
    )
    statement = statement.order_by(Team.name.asc(), Team.id.asc())
    return fetch_page(
        session,
        statement=statement,
        count_statement=count_of(statement),
        page=page,
        page_size=page_size,
    )


def get_team(session: Session, team_id: int) -> Team | None:
    return session.execute(
        select(Team).where(Team.id == team_id).options(joinedload(Team.country))
    ).scalars().first()


def match_count_for_team(session: Session, team_id: int) -> int:
    return int(
        session.execute(
            select(func.count(distinct(Match.id))).where(
                (Match.home_team_id == team_id) | (Match.away_team_id == team_id)
            )
        ).scalar_one()
    )
