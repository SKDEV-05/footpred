"""Fixture, result, and statistics endpoints."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Path, Query
from sqlalchemy.orm import Session

from app.api.deps import Pagination, get_session, pagination
from app.api.v1.mappers import fixture_detail, fixture_summary, team_statistics
from app.core.exceptions import NotFoundError
from app.core.time import local_day_window_utc, utc_now
from app.models.enums import MatchStatus
from app.repositories import fixtures as fixtures_repo
from app.schemas.common import Page
from app.schemas.fixtures import (
    FixtureDetail,
    FixtureSummary,
    MatchStatisticsResponse,
    TodayResponse,
)
from app.validation.rules import validate_date_range

router = APIRouter(tags=["fixtures"])


@router.get("/fixtures", response_model=Page[FixtureSummary])
def list_fixtures(
    date_from: date | None = Query(None, description="Inclusive UTC date."),
    date_to: date | None = Query(None, description="Inclusive UTC date."),
    competition_id: int | None = Query(None, ge=1, le=2**63 - 1),
    country_id: int | None = Query(None, ge=1, le=2**63 - 1),
    season_id: int | None = Query(None, ge=1, le=2**63 - 1),
    team_id: int | None = Query(None, ge=1, le=2**63 - 1),
    status: MatchStatus | None = None,
    q: str | None = Query(
        None, max_length=100, description="Search team or competition name."
    ),
    page: Pagination = Depends(pagination),
    session: Session = Depends(get_session),
) -> Page[FixtureSummary]:
    narrowed = any(
        value is not None
        for value in (
            date_from,
            date_to,
            competition_id,
            country_id,
            season_id,
            team_id,
            status,
            q,
        )
    )
    if not narrowed:
        today = utc_now().date()
        date_from = today
        date_to = today + timedelta(days=7)

    if date_from is not None and date_to is not None:
        validate_date_range(date_from, date_to)

    result = fixtures_repo.list_fixtures(
        session,
        page=page.page,
        page_size=page.page_size,
        date_from=date_from,
        date_to=date_to,
        competition_id=competition_id,
        country_id=country_id,
        season_id=season_id,
        team_id=team_id,
        status=status,
        query=q,
    )
    return Page[FixtureSummary](
        items=[fixture_summary(match) for match in result.items],
        page=result.page,
        page_size=result.page_size,
        total=result.total,
        has_next=result.has_next,
    )


@router.get("/fixtures/today", response_model=TodayResponse)
def fixtures_today(
    day: date | None = Query(None, alias="date"),
    timezone: str = Query(
        "UTC",
        max_length=64,
        pattern=r"^[A-Za-z0-9._+/-]+$",
        description="IANA timezone name.",
    ),
    competition_id: int | None = Query(None, ge=1, le=2**63 - 1),
    session: Session = Depends(get_session),
) -> TodayResponse:
    from app.core.time import get_timezone

    zone = get_timezone(timezone)
    resolved_day = day or utc_now().astimezone(zone).date()
    window_start, window_end = local_day_window_utc(resolved_day, timezone)

    matches = fixtures_repo.fixtures_in_window(
        session,
        start_utc=window_start,
        end_utc=window_end,
        competition_id=competition_id,
    )
    return TodayResponse(
        date=resolved_day,
        timezone=timezone,
        date_from_utc=window_start,
        date_to_utc=window_end,
        items=[fixture_summary(match) for match in matches],
    )


@router.get("/fixtures/{match_id}", response_model=FixtureDetail)
def get_fixture(
    match_id: int = Path(..., ge=1, le=2**63 - 1),
    session: Session = Depends(get_session),
) -> FixtureDetail:
    match = fixtures_repo.get_match(session, match_id)
    if match is None:
        raise NotFoundError(f"Fixture {match_id} does not exist.")
    rows = fixtures_repo.statistics_for_match(session, match_id)
    if match.result is None or not match.result.is_final:
        rows = []
    return fixture_detail(match, statistics_available=bool(rows))


@router.get("/fixtures/{match_id}/statistics", response_model=MatchStatisticsResponse)
def get_fixture_statistics(
    match_id: int = Path(..., ge=1, le=2**63 - 1),
    session: Session = Depends(get_session),
) -> MatchStatisticsResponse:
    match = fixtures_repo.get_match(session, match_id)
    if match is None:
        raise NotFoundError(f"Fixture {match_id} does not exist.")
    rows = fixtures_repo.statistics_for_match(session, match_id)
    if match.result is None or not match.result.is_final:
        rows = []
    return MatchStatisticsResponse(
        match_id=match_id,
        available=bool(rows),
        teams=team_statistics(match, rows),
    )
