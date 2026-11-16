"""Competition and season ingestion."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ingestion.identity import resolve_competition, resolve_season
from app.ingestion.outcomes import UpsertOutcome, UpsertResult, diff_fields
from app.models.core import Competition, Season
from app.normalization.status import competition_type
from app.providers.dto import ProviderCompetition, ProviderSeason
from app.validation.rules import validate_competition, validate_season


def upsert_competition(
    session: Session,
    *,
    provider_id: int,
    dto: ProviderCompetition,
) -> UpsertResult:
    validate_competition(dto)
    canonical_type = competition_type(dto.type)
    resolved = resolve_competition(
        session,
        provider_id=provider_id,
        competition=dto,
        competition_type=canonical_type,
    )
    if resolved.created:
        return UpsertResult(resolved.entity_id, UpsertOutcome.CREATED)

    competition = session.get(Competition, resolved.entity_id)
    assert competition is not None
    incoming = {
        "name": competition.name,
        "code": competition.code,
        "type": competition.type,
        "country_id": competition.country_id,
        "emblem_url": competition.emblem_url,
    }
    change = diff_fields(resolved.previous or {}, incoming)
    if change.has_changes:
        return UpsertResult(
            resolved.entity_id, UpsertOutcome.UPDATED, change.changed_fields
        )
    return UpsertResult(resolved.entity_id, UpsertOutcome.UNCHANGED)


def upsert_season(
    session: Session,
    *,
    provider_id: int,
    competition_id: int,
    dto: ProviderSeason,
) -> UpsertResult:
    validate_season(dto)
    resolved = resolve_season(
        session,
        provider_id=provider_id,
        competition_id=competition_id,
        season=dto,
    )
    if resolved.created:
        return UpsertResult(resolved.entity_id, UpsertOutcome.CREATED)

    season = session.get(Season, resolved.entity_id)
    assert season is not None
    incoming = {
        "competition_id": season.competition_id,
        "label": season.label,
        "start_date": season.start_date,
        "end_date": season.end_date,
        "current_matchday": season.current_matchday,
        "is_current": season.is_current,
    }
    change = diff_fields(resolved.previous or {}, incoming)
    if change.has_changes:
        return UpsertResult(
            resolved.entity_id, UpsertOutcome.UPDATED, change.changed_fields
        )
    return UpsertResult(resolved.entity_id, UpsertOutcome.UNCHANGED)


def ingest_competition_detail(
    session: Session,
    *,
    provider_id: int,
    dto: ProviderCompetition,
) -> tuple[UpsertResult, list[UpsertResult]]:
    """Upsert a competition and every season the provider included with it."""

    competition_result = upsert_competition(session, provider_id=provider_id, dto=dto)
    season_results: list[UpsertResult] = []
    for season_dto in dto.seasons:
        season_results.append(
            upsert_season(
                session,
                provider_id=provider_id,
                competition_id=competition_result.entity_id,
                dto=season_dto,
            )
        )
    if dto.current_season is not None:
        season_results.append(
            upsert_season(
                session,
                provider_id=provider_id,
                competition_id=competition_result.entity_id,
                dto=dto.current_season,
            )
        )
    return competition_result, season_results
