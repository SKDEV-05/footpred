"""Concrete synchronisation jobs.

Each job fetches a bounded list, then persists per item. Provider I/O never happens
inside an open database transaction. A rejected record is quarantined and the job
continues; a failed list fetch fails the run.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Callable, Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AppError,
    IdentityAmbiguityError,
    RecordValidationError,
    ValidationIssue,
)
from app.core.logging import redact_text
from app.core.time import utc_now
from app.ingestion.competitions import ingest_competition_detail, upsert_competition
from app.ingestion.fixtures import upsert_fixture
from app.ingestion.outcomes import UpsertResult
from app.ingestion.statistics import upsert_statistics
from app.ingestion.teams import upsert_team
from app.models.core import Competition, Match
from app.models.enums import FINAL_STATUSES
from app.models.provenance import ProviderMatchMapping, ProviderTeamMapping
from app.sync.engine import SyncContext

logger = logging.getLogger(__name__)


def _window_chunks(
    date_from: date, date_to: date, *, max_days: int
) -> list[tuple[date, date]]:
    """Split a date range into inclusive chunks of at most ``max_days`` each.

    football-data.org's Free tier rejects any window over 10 days with HTTP 400
    ("Specified period must not exceed 10 days"), so a 14-day sync window must be
    fetched in two requests. The chunk bound comes from configuration, not a constant,
    so a different plan can raise it without a code change.
    """

    if max_days < 1:
        raise ValueError("max_days must be at least 1")
    if date_to < date_from:
        raise ValueError("date_to must not precede date_from")
    chunks: list[tuple[date, date]] = []
    start = date_from
    while start <= date_to:
        end = min(start + timedelta(days=max_days - 1), date_to)
        chunks.append((start, end))
        start = end + timedelta(days=1)
    return chunks


class _Skip(Exception):
    """A provider record is valid but cannot be persisted yet."""


def _process(
    ctx: SyncContext,
    items: Sequence[Any],
    *,
    entity_type: str,
    external_id_of: Callable[[Any], str | None],
    handler: Callable[[Session, Any], UpsertResult | list[UpsertResult] | None],
    excerpt_of: Callable[[Any], Any] | None = None,
    raw_payload_id: int | None = None,
) -> None:
    ctx.observe_raw_payload(raw_payload_id)
    for item in items:
        external_id = external_id_of(item)
        try:
            with ctx.session() as session:
                results = handler(session, item)
                if results is None:
                    ctx.count_rejected(session)
                else:
                    for result in results if isinstance(results, list) else [results]:
                        ctx.count(session, result)
        except (RecordValidationError, IdentityAmbiguityError) as exc:
            _quarantine(ctx, entity_type, external_id, exc, item, excerpt_of, raw_payload_id)
        except ValueError:
            _quarantine(
                ctx,
                entity_type,
                external_id,
                RecordValidationError(
                    [
                        ValidationIssue(
                            code="provider_boundary_validation",
                            message="provider record failed boundary validation",
                            field=entity_type,
                        )
                    ]
                ),
                item,
                excerpt_of,
                raw_payload_id,
            )
        except IntegrityError:
            logger.warning(
                "database constraint rejected a provider record",
                extra={
                    "event": "sync.integrity_error",
                    "component": "sync",
                    "error_code": "integrity_error",
                },
            )
            _quarantine(
                ctx,
                entity_type,
                external_id,
                _IntegrityFailure(),
                item,
                excerpt_of,
                raw_payload_id,
            )
        except _Skip as exc:
            with ctx.session() as session:
                ctx.record_error(
                    session,
                    stage="ingestion",
                    code="record_skipped",
                    message=str(exc),
                    entity_type=entity_type,
                    external_id=external_id,
                )


class _IntegrityFailure(Exception):
    def __init__(self) -> None:
        # The database message can include bound values; keep it generic.
        super().__init__("a duplicate or constraint violation prevented the write")
        self.code = "integrity_error"


def _quarantine(
    ctx: SyncContext,
    entity_type: str,
    external_id: str | None,
    exc: Exception,
    item: Any,
    excerpt_of: Callable[[Any], Any] | None,
    raw_payload_id: int | None = None,
) -> None:
    code = getattr(exc, "code", "validation_error")
    message = redact_text(str(exc))
    excerpt = excerpt_of(item) if excerpt_of is not None else None
    with ctx.session() as session:
        ctx.reject(
            session,
            entity_type=entity_type,
            external_id=external_id,
            code=str(code),
            message=message,
            raw_payload_id=raw_payload_id,
            payload_excerpt=excerpt,
        )


# -- jobs ------------------------------------------------------------------------


def sync_competitions(ctx: SyncContext) -> None:
    ctx.adapter.require("competitions")
    fetched = ctx.adapter.fetch_competitions()
    _process(
        ctx,
        fetched.items,
        entity_type="competition",
        external_id_of=lambda dto: dto.external_id,
        handler=lambda session, dto: upsert_competition(
            session, provider_id=ctx.provider_id, dto=dto
        ),
        raw_payload_id=fetched.raw_payload_id,
    )


def sync_competition_details(ctx: SyncContext) -> None:
    ctx.adapter.require("seasons")
    codes = ctx.settings.competition_ids
    if not codes:
        raise AppError(
            "SYNC_COMPETITION_IDS is empty. Set at least one provider competition code "
            "before syncing competition details.",
            code="missing_competition_ids",
        )
    for code in codes:
        fetched = ctx.adapter.fetch_competition(code)
        ctx.observe_raw_payload(fetched.raw_payload_id)
        try:
            with ctx.session() as session:
                competition_result, season_results = ingest_competition_detail(
                    session, provider_id=ctx.provider_id, dto=fetched.items
                )
                ctx.count(session, competition_result)
                ctx.count_many(session, season_results)
        except (RecordValidationError, IdentityAmbiguityError) as exc:
            _quarantine(ctx, "competition", code, exc, fetched.items, None, fetched.raw_payload_id)
        except IntegrityError:
            _quarantine(
                ctx, "competition", code, _IntegrityFailure(), fetched.items, None,
                fetched.raw_payload_id
            )


def sync_teams(ctx: SyncContext) -> None:
    ctx.adapter.require("teams")
    codes = ctx.settings.competition_ids
    if not codes:
        raise AppError(
            "SYNC_COMPETITION_IDS is empty. Set at least one provider competition code "
            "before syncing teams.",
            code="missing_competition_ids",
        )
    for code in codes:
        fetched = ctx.adapter.fetch_teams(code)
        _process(
            ctx,
            fetched.items,
            entity_type="team",
            external_id_of=lambda dto: dto.external_id,
            handler=lambda session, dto: upsert_team(
                session, provider_id=ctx.provider_id, dto=dto
            ),
            raw_payload_id=fetched.raw_payload_id,
        )


def sync_fixtures(ctx: SyncContext) -> None:
    ctx.adapter.require("fixtures")
    settings = ctx.settings
    date_from = date.fromisoformat(ctx.parameters["date_from"])
    date_to = date.fromisoformat(ctx.parameters["date_to"])
    chunks = _window_chunks(
        date_from, date_to, max_days=settings.provider_max_window_days
    )

    codes: Sequence[str | None] = settings.competition_ids or (None,)
    for code in codes:
        for chunk_from, chunk_to in chunks:
            fetched = ctx.adapter.fetch_matches(
                date_from=chunk_from,
                date_to=chunk_to,
                competition_external_id=code,
            )
            _report_skipped(ctx, fetched)
            _process(
                ctx,
                fetched.items,
                entity_type="match",
                external_id_of=lambda dto: dto.external_id,
                handler=lambda session, dto: upsert_fixture(
                    session,
                    provider_id=ctx.provider_id,
                    dto=dto,
                    sync_run_id=ctx.run_id,
                    kickoff_window_minutes=settings.identity_kickoff_window_minutes,
                    raw_payload_id=fetched.raw_payload_id,
                ),
                excerpt_of=_match_excerpt,
                raw_payload_id=fetched.raw_payload_id,
            )



def sync_results(ctx: SyncContext) -> None:
    ctx.adapter.require("results")
    settings = ctx.settings
    date_from = date.fromisoformat(ctx.parameters["date_from"])
    date_to = date.fromisoformat(ctx.parameters["date_to"])
    chunks = _window_chunks(
        date_from, date_to, max_days=settings.provider_max_window_days
    )

    codes: Sequence[str | None] = settings.competition_ids or (None,)
    for code in codes:
        for chunk_from, chunk_to in chunks:
            fetched = ctx.adapter.fetch_matches(
                date_from=chunk_from,
                date_to=chunk_to,
                competition_external_id=code,
                status="FINISHED",
            )
            _report_skipped(ctx, fetched)
            _process(
                ctx,
                fetched.items,
                entity_type="match",
                external_id_of=lambda dto: dto.external_id,
                handler=lambda session, dto: upsert_fixture(
                    session,
                    provider_id=ctx.provider_id,
                    dto=dto,
                    sync_run_id=ctx.run_id,
                    kickoff_window_minutes=settings.identity_kickoff_window_minutes,
                    raw_payload_id=fetched.raw_payload_id,
                ),
                excerpt_of=_match_excerpt,
                raw_payload_id=fetched.raw_payload_id,
            )


def sync_history(ctx: SyncContext) -> None:
    """Synchronise historical finished matches for entitled competitions and seasons."""
    ctx.adapter.require("results")
    settings = ctx.settings

    seasons_param = ctx.parameters.get("seasons")
    if seasons_param:
        if isinstance(seasons_param, str):
            seasons = [s.strip() for s in seasons_param.split(",") if s.strip()]
        else:
            seasons = [str(s) for s in seasons_param]
    else:
        seasons = ["2026", "2025"]

    codes_param = ctx.parameters.get("competition_ids")
    if codes_param:
        if isinstance(codes_param, str):
            codes = [c.strip() for c in codes_param.split(",") if c.strip()]
        else:
            codes = list(codes_param)
    elif settings.competition_ids:
        codes = list(settings.competition_ids)
    else:
        with ctx.session() as session:
            db_codes = session.execute(
                select(Competition.code).where(Competition.code.isnot(None))
            ).scalars().all()
            codes = [
                c for c in db_codes
                if c in {"PL", "PD", "BL1", "SA", "FL1", "ELC", "DED", "PPL", "BSA", "CL", "CLI"}
            ]

    for code in codes:
        for season in seasons:
            try:
                fetched = ctx.adapter.fetch_matches(
                    competition_external_id=code,
                    season_external_id=str(season),
                    status="FINISHED",
                )
            except AppError as exc:
                logger.warning(
                    "historical match fetch failed for competition %s season %s: %s",
                    code,
                    season,
                    exc,
                    extra={
                        "event": "sync.history_fetch_failed",
                        "component": "sync",
                        "competition": code,
                        "season": season,
                    },
                )
                with ctx.session() as session:
                    ctx.record_error(
                        session,
                        stage="fetch",
                        code=getattr(exc, "code", "fetch_error"),
                        message=f"fetch failed for {code} season {season}: {exc}",
                        entity_type="match",
                    )
                continue

            _report_skipped(ctx, fetched)
            _process(
                ctx,
                fetched.items,
                entity_type="match",
                external_id_of=lambda dto: dto.external_id,
                handler=lambda session, dto: upsert_fixture(
                    session,
                    provider_id=ctx.provider_id,
                    dto=dto,
                    sync_run_id=ctx.run_id,
                    kickoff_window_minutes=settings.identity_kickoff_window_minutes,
                    raw_payload_id=fetched.raw_payload_id,
                ),
                excerpt_of=_match_excerpt,
                raw_payload_id=fetched.raw_payload_id,
            )


def sync_statistics(ctx: SyncContext) -> None:
    ctx.adapter.require("match_statistics")
    limit = ctx.settings.sync_statistics_limit_per_run

    for match_id, external_id in _statistics_candidates(ctx, limit=limit):
        # Fetch outside any transaction: the archive commits its own row.
        try:
            fetched = ctx.adapter.fetch_match_detail(external_id)
            ctx.observe_raw_payload(fetched.raw_payload_id)
        except AppError as exc:
            with ctx.session() as session:
                ctx.record_error(
                    session,
                    stage="provider",
                    code=getattr(exc, "code", "provider_error"),
                    message=str(exc),
                    entity_type="match_statistics",
                    external_id=external_id,
                )
            continue

        for team_stats in fetched.items.statistics:
            detail = type(fetched.items)(
                match=fetched.items.match,
                statistics=(team_stats,),
            )
            try:
                with ctx.session() as session:
                    outcomes = _persist_statistics(
                        ctx,
                        session,
                        match_id,
                        detail,
                        raw_payload_id=fetched.raw_payload_id,
                    )
                    for outcome in outcomes:
                        ctx.count(session, outcome)
            except (RecordValidationError, IdentityAmbiguityError) as exc:
                _quarantine(
                    ctx,
                    "match_statistics",
                    external_id,
                    exc,
                    {"match_id": match_id, "team_external_id": team_stats.team_external_id},
                    None,
                    fetched.raw_payload_id,
                )
            except IntegrityError:
                _quarantine(
                    ctx,
                    "match_statistics",
                    external_id,
                    _IntegrityFailure(),
                    {"match_id": match_id, "team_external_id": team_stats.team_external_id},
                    None,
                    fetched.raw_payload_id,
                )


# -- helpers ---------------------------------------------------------------------


def _statistics_candidates(ctx: SyncContext, *, limit: int) -> list[tuple[int, str]]:
    if ctx.provider_id is None:
        return []
    with ctx.session() as session:
        rows = session.execute(
            select(Match.id, ProviderMatchMapping.external_id)
            .join(ProviderMatchMapping, ProviderMatchMapping.match_id == Match.id)
            .where(
                ProviderMatchMapping.provider_id == ctx.provider_id,
                ProviderMatchMapping.is_active.is_(True),
                Match.status.in_(tuple(FINAL_STATUSES)),
            )
            .order_by(Match.kickoff_utc.desc(), Match.id.desc())
            .limit(limit)
        ).all()
    return [(row[0], row[1]) for row in rows]


def _persist_statistics(
    ctx: SyncContext,
    session: Session,
    match_id: int,
    detail,
    *,
    raw_payload_id: int | None,
):
    outcomes = []
    for team_stats in detail.statistics:
        team_id = session.execute(
            select(ProviderTeamMapping.team_id).where(
                ProviderTeamMapping.provider_id == ctx.provider_id,
                ProviderTeamMapping.external_id == team_stats.team_external_id,
                ProviderTeamMapping.is_active.is_(True),
            )
        ).scalars().first()
        if team_id is None:
            raise RecordValidationError(
                [
                    ValidationIssue(
                        code="unmapped_team",
                        message=(
                            f"team {team_stats.team_external_id} has no internal mapping; "
                            "statistics cannot be attributed"
                        ),
                        field="statistics.team_external_id",
                    )
                ]
            )
        outcomes.append(
            upsert_statistics(
                session,
                match_id=match_id,
                team_id=team_id,
                metrics=team_stats.metrics,
                provider_last_updated=detail.match.provider_last_updated,
                raw_payload_id=raw_payload_id,
                sync_run_id=ctx.run_id,
            )
        )
    return outcomes


def _report_skipped(ctx: SyncContext, fetched: Any) -> None:
    """Record provider records that could not be stored without inventing data."""

    skipped = getattr(fetched, "skipped", 0)
    if not skipped:
        return
    with ctx.session() as session:
        ctx.record_error(
            session,
            stage="provider",
            code="match_without_participants",
            message=(
                f"{skipped} provider fixtures named no participants and were not stored."
            ),
            entity_type="match",
            raw_payload_id=fetched.raw_payload_id,
        )


def _match_excerpt(dto) -> dict[str, Any]:
    return {
        "external_id": dto.external_id,
        "competition": dto.competition.external_id,
        "season": dto.season.external_id,
        "kickoff_utc": dto.kickoff_utc,
        "status": dto.status,
        "home_team": dto.home_team.external_id,
        "away_team": dto.away_team.external_id,
    }
