"""Team ingestion from the team resource."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.ingestion.identity import resolve_team
from app.ingestion.outcomes import UpsertOutcome, UpsertResult, diff_fields
from app.models.core import Team
from app.providers.dto import ProviderTeam
from app.validation.rules import validate_team


def upsert_team(
    session: Session,
    *,
    provider_id: int,
    dto: ProviderTeam,
) -> UpsertResult:
    validate_team(dto)
    resolved = resolve_team(session, provider_id=provider_id, team=dto)
    if resolved.created:
        return UpsertResult(resolved.entity_id, UpsertOutcome.CREATED)

    team = session.get(Team, resolved.entity_id)
    assert team is not None
    incoming = {
        "name": team.name,
        "short_name": team.short_name,
        "tla": team.tla,
        "country_id": team.country_id,
        "venue_name": team.venue_name,
        "founded": team.founded,
        "crest_url": team.crest_url,
    }
    change = diff_fields(resolved.previous or {}, incoming)
    if change.has_changes:
        return UpsertResult(resolved.entity_id, UpsertOutcome.UPDATED, change.changed_fields)
    return UpsertResult(resolved.entity_id, UpsertOutcome.UNCHANGED)
