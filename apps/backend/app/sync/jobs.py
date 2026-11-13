"""Concrete synchronisation jobs.

Each job fetches a bounded list, then persists per item. Provider I/O never happens
inside an open database transaction. A rejected record is quarantined and the job
continues; a failed list fetch fails the run.
"""

from __future__ import annotations

import logging
from datetime import timedelta
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
from app.models.core import Match
from app.models.enums import FINAL_STATUSES
from app.models.provenance import ProviderMatchMapping, ProviderTeamMapping
from app.sync.engine import SyncContext

logger = logging.getLogger(__name__)


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
) -> None:
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
            _quarantine(ctx, entity_type, external_id, exc, item, excerpt_of)
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
    )


def sync_competition_details(ctx: SyncContext) -> None:
    ctx.adapter.require("seasons")
    codes = ctx.settings.competition_ids
    if not codes:
        raise AppError(
            "SYNC_COMPETITION_IDS is empty. Set at least one provider competition code "
            "before syncing competition details."
        )
    for code in codes:
        fetched = ctx.adapter.fetch_competition(code)
        try:
            with ctx.session() as session:
                competition_result, season_results = ingest_competition_detail(
                    session, provider_id=ctx.provider_id, dto=fetched.items
                )
                ctx.count(session, competition_result)
                ctx.count_many(session, season_results)
        except (RecordValidationError, IdentityAmbiguityError) as exc:
            _quarantine(ctx, "competition", code, exc, fetched.items, None)
        except IntegrityError:
            _quarantine(
                ctx, "competition", code, _IntegrityFailure(), fetched.items, None
            )


def sync_teams(ctx: SyncContext) -> None:
    ctx.adapter.require("teams")
    codes = ctx.settings.competition_ids
    if not codes:
        raise AppError(
            "SYNC_COMPETITION_IDS is empty. Set at least one provider competition code "
            "before syncing teams."
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
        )


def sync_fixtures(ctx: SyncContext) -> None:
    ctx.adapter.require("fixtures")
    settings = ctx.settings
    today = utc_now().date()
    date_from = today - timedelta(days=settings.sync_lookback_days)
    date_to = today + timedelta(days=settings.sync_lookahead_days)

    codes: Sequence[str | None] = settings.competition_ids or (None,)
    for code in codes:
        fetched = ctx.adapter.fetch_matches(
            date_from=date_from,
            date_to=date_to,
            competition_external_id=code,
        )
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
            ),
            excerpt_of=_match_excerpt,
        )


def sync_results(ctx: SyncContext) -> None:
    ctx.adapter.require("results")
    settings = ctx.settings
    today = utc_now().date()
    date_from = today - timedelta(days=settings.sync_lookback_days)

    codes: Sequence[str | None] = settings.competition_ids or (None,)
    for code in codes:
        fetched = ctx.adapter.fetch_matches(
            date_from=date_from,
            date_to=today,
            competition_external_id=code,
            status="FINISHED",
        )
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
            ),
            excerpt_of=_match_excerpt,
        )


def sync_statistics(ctx: SyncContext) -> None:
    ctx.adapter.require("match_statistics")
    limit = ctx.settings.sync_statistics_limit_per_run

    for match_id, external_id in _statistics_candidates(ctx, limit=limit):
        # Fetch outside any transaction: the archive commits its own row.
        try:
            fetched = ctx.adapter.fetch_match_detail(external_id)
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

        try:
            with ctx.session() as session:
                outcomes = _persist_statistics(
                    ctx,
                    session,
                    match_id,
                    fetched.items,
                    raw_payload_id=fetched.raw_payload_id,
                )
                for outcome in outcomes:
                    ctx.count(session, outcome)
        except (RecordValidationError, IdentityAmbiguityError) as exc:
            _quarantine(
                ctx, "match_statistics", external_id, exc, {"match_id": match_id}, None
            )
        except IntegrityError:
            _quarantine(
                ctx,
                "match_statistics",
                external_id,
                _IntegrityFailure(),
                {"match_id": match_id},
                None,
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
