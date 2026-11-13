"""Competition, season, and team endpoints."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_session, pagination
from app.api.v1.mappers import (
    competition_detail,
    competition_summary,
    fixture_summary,
    season_summary,
    team_detail,
    team_summary,
)
from app.core.exceptions import NotFoundError
from app.core.time import utc_now
from app.repositories import reference as reference_repo
from app.repositories import fixtures as fixtures_repo
from app.schemas.common import Page
from app.schemas.fixtures import FixtureSummary
from app.schemas.reference import (
    CompetitionDetail,
    CompetitionSummary,
    SeasonSummary,
    TeamDetail,
    TeamSummary,
)
from app.validation.rules import validate_date_range

router = APIRouter(tags=["reference"])


@router.get("/competitions", response_model=Page[CompetitionSummary])
def list_competitions(
    country_id: int | None = None,
    q: str | None = Query(None, max_length=100),
    page: Pagination = Depends(pagination),
    session: Session = Depends(get_session),
) -> Page[CompetitionSummary]:
    result = reference_repo.list_competitions(
        session, page=page.page, page_size=page.page_size, country_id=country_id, query=q
    )
    return Page[CompetitionSummary](
        items=[competition_summary(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )


@router.get("/competitions/{competition_id}", response_model=CompetitionDetail)
def get_competition(
    competition_id: int,
    session: Session = Depends(get_session),
) -> CompetitionDetail:
    competition = reference_repo.get_competition(session, competition_id)
    if competition is None:
        raise NotFoundError(f"Competition {competition_id} does not exist.")
    return competition_detail(
        competition,
        season_count=reference_repo.season_count(session, competition_id),
    )


@router.get("/seasons", response_model=Page[SeasonSummary])
def list_seasons(
    competition_id: int | None = None,
    page: Pagination = Depends(pagination),
    session: Session = Depends(get_session),
) -> Page[SeasonSummary]:
    result = reference_repo.list_seasons(
        session,
        page=page.page,
        page_size=page.page_size,
        competition_id=competition_id,
    )
    return Page[SeasonSummary](
        items=[season_summary(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )


@router.get("/teams", response_model=Page[TeamSummary])
def list_teams(
    country_id: int | None = None,
    q: str | None = Query(None, max_length=100),
    page: Pagination = Depends(pagination),
    session: Session = Depends(get_session),
) -> Page[TeamSummary]:
    result = reference_repo.list_teams(
        session, page=page.page, page_size=page.page_size, country_id=country_id, query=q
    )
    return Page[TeamSummary](
        items=[team_summary(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )


@router.get("/teams/{team_id}", response_model=TeamDetail)
def get_team(
    team_id: int,
    session: Session = Depends(get_session),
) -> TeamDetail:
    team = reference_repo.get_team(session, team_id)
    if team is None:
        raise NotFoundError(f"Team {team_id} does not exist.")
    return team_detail(
        team, match_count=reference_repo.match_count_for_team(session, team_id)
    )


@router.get("/teams/{team_id}/matches", response_model=Page[FixtureSummary])
def get_team_matches(
    team_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    page: Pagination = Depends(pagination),
    session: Session = Depends(get_session),
) -> Page[FixtureSummary]:
    team = reference_repo.get_team(session, team_id)
    if team is None:
        raise NotFoundError(f"Team {team_id} does not exist.")

    if date_from is None and date_to is None:
        today = utc_now().date()
        date_from = today - timedelta(days=365)
        date_to = today
    if date_from is not None and date_to is not None:
        validate_date_range(date_from, date_to)

    result = fixtures_repo.team_matches(
        session,
        team_id=team_id,
        page=page.page,
        page_size=page.page_size,
        date_from=date_from,
        date_to=date_to,
    )
    return Page[FixtureSummary](
        items=[fixture_summary(item) for item in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )
