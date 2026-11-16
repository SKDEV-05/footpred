"""Fixture ingestion: identity, field-level change detection, and result hand-off."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.exceptions import IdentityAmbiguityError
from app.core.time import utc_now
from app.ingestion.identity import (
    resolve_competition,
    resolve_match,
    resolve_season,
    resolve_team_from_ref,
)
from app.ingestion.outcomes import UpsertOutcome, UpsertResult, diff_fields
from app.ingestion.results import upsert_result
from app.models.core import Match
from app.models.enums import FINAL_STATUSES, MatchStatus
from app.models.provenance import MatchChangeLog, RawPayload
from app.normalization.status import (
    competition_type,
    group_name,
    match_status,
    stage_name,
)
from app.providers.dto import ProviderMatch
from app.validation.rules import validate_match


@dataclass(frozen=True)
class FixtureUpsert:
    match_id: int
    outcome: UpsertOutcome
    changed_fields: tuple[str, ...]
    result: UpsertResult | None = None

    @property
    def created(self) -> bool:
        return self.outcome is UpsertOutcome.CREATED

    @property
    def updated(self) -> bool:
        return self.outcome is UpsertOutcome.UPDATED

    @property
    def unchanged(self) -> bool:
        return self.outcome is UpsertOutcome.UNCHANGED


def upsert_fixture(
    session: Session,
    *,
    provider_id: int,
    dto: ProviderMatch,
    sync_run_id: int | None,
    kickoff_window_minutes: int,
    raw_payload_id: int | None = None,
) -> FixtureUpsert:
    if raw_payload_id is not None and session.get(RawPayload, raw_payload_id) is None:
        raw_payload_id = None
    validate_match(dto)

    canonical_status = match_status(dto.status)
    canonical_type = competition_type(dto.competition.type)

    competition = resolve_competition(
        session,
        provider_id=provider_id,
        competition=dto.competition,
        competition_type=canonical_type,
    )
    season = resolve_season(
        session,
        provider_id=provider_id,
        competition_id=competition.entity_id,
        season=dto.season,
    )

    home = resolve_team_from_ref(
        session,
        provider_id=provider_id,
        team=dto.home_team,
        country_name=dto.home_team.country_name,
        country_code=dto.home_team.country_code,
    )
    away = resolve_team_from_ref(
        session,
        provider_id=provider_id,
        team=dto.away_team,
        country_name=dto.away_team.country_name,
        country_code=dto.away_team.country_code,
    )

    resolved = resolve_match(
        session,
        provider_id=provider_id,
        external_id=dto.external_id,
        competition_id=competition.entity_id,
        season_id=season.entity_id,
        home_team_id=home.entity_id,
        away_team_id=away.entity_id,
        kickoff_utc=dto.kickoff_utc,
        kickoff_window_minutes=kickoff_window_minutes,
        raw_payload_id=raw_payload_id,
    )

    match = session.get(Match, resolved.entity_id)
    assert match is not None

    if not resolved.created:
        _assert_identity_unchanged(
            match,
            competition_id=competition.entity_id,
            season_id=season.entity_id,
            home_team_id=home.entity_id,
            away_team_id=away.entity_id,
        )

    incoming: dict[str, Any] = {
        "competition_id": competition.entity_id,
        "season_id": season.entity_id,
        "home_team_id": home.entity_id,
        "away_team_id": away.entity_id,
        "kickoff_utc": dto.kickoff_utc,
        "status": canonical_status,
        "matchday": dto.matchday,
        "stage": stage_name(dto.stage),
        "group_name": group_name(dto.group_name),
        "venue_name": dto.venue_name,
        "attendance": dto.attendance,
        "provider_last_updated": dto.provider_last_updated,
        "raw_payload_id": raw_payload_id,
    }

    previous = {} if resolved.created else _fixture_snapshot(match)
    change = diff_fields(previous, incoming)

    for field in change.changed_fields:
        setattr(match, field, incoming[field])
    match.last_synced_at = utc_now()

    if resolved.created:
        session.flush()
        outcome = UpsertOutcome.CREATED
        changed_fields: tuple[str, ...] = ()
    elif change.has_changes:
        session.add(
            MatchChangeLog(
                match_id=match.id,
                sync_run_id=sync_run_id,
                change_type="fixture",
                changed_fields=list(change.changed_fields),
                previous_values=change.previous,
                new_values=change.new,
                provider_last_updated=dto.provider_last_updated,
                raw_payload_id=raw_payload_id,
                created_at=utc_now(),
            )
        )
        session.flush()
        outcome = UpsertOutcome.UPDATED
        changed_fields = change.changed_fields
    else:
        session.flush()
        outcome = UpsertOutcome.UNCHANGED
        changed_fields = ()

    result: UpsertResult | None = None
    if canonical_status in FINAL_STATUSES and dto.score is not None:
        result = upsert_result(
            session,
            match_id=match.id,
            score=dto.score,
            status=canonical_status,
            provider_last_updated=dto.provider_last_updated,
            sync_run_id=sync_run_id,
            raw_payload_id=raw_payload_id,
        )
    elif canonical_status not in FINAL_STATUSES:
        _invalidate_result_if_needed(
            session,
            match_id=match.id,
            status=canonical_status,
            sync_run_id=sync_run_id,
            raw_payload_id=raw_payload_id,
        )

    return FixtureUpsert(
        match_id=match.id,
        outcome=outcome,
        changed_fields=changed_fields,
        result=result,
    )


def _invalidate_result_if_needed(
    session: Session,
    *,
    match_id: int,
    status: MatchStatus,
    sync_run_id: int | None,
    raw_payload_id: int | None,
) -> None:
    from app.models.core import MatchResult

    result = session.get(MatchResult, match_id)
    if result is None:
        return
    previous = {"is_final": result.is_final, "status": result.status}
    changed_fields: list[str] = []
    if result.is_final:
        result.is_final = False
        changed_fields.append("is_final")
    if result.status != status:
        result.status = status
        changed_fields.append("status")
    result.raw_payload_id = raw_payload_id
    if not changed_fields:
        return
    session.add(
        MatchChangeLog(
            match_id=match_id,
            sync_run_id=sync_run_id,
            raw_payload_id=raw_payload_id,
            change_type="result_invalidated",
            changed_fields=changed_fields,
            previous_values=previous,
            new_values={"is_final": False, "status": status},
            provider_last_updated=None,
            created_at=utc_now(),
        )
    )


def _assert_identity_unchanged(
    match: Match,
    *,
    competition_id: int,
    season_id: int,
    home_team_id: int,
    away_team_id: int,
) -> None:
    mismatches: list[str] = []
    if match.competition_id != competition_id:
        mismatches.append("competition")
    if match.season_id != season_id:
        mismatches.append("season")
    if match.home_team_id != home_team_id:
        mismatches.append("home team")
    if match.away_team_id != away_team_id:
        mismatches.append("away team")
    if mismatches:
        raise IdentityAmbiguityError(
            "The provider record is mapped to an internal match whose "
            f"{', '.join(mismatches)} differ; the mapping needs review."
        )


def _fixture_snapshot(match: Match) -> Mapping[str, Any]:
    return {
        "competition_id": match.competition_id,
        "season_id": match.season_id,
        "home_team_id": match.home_team_id,
        "away_team_id": match.away_team_id,
        "kickoff_utc": match.kickoff_utc,
        "status": match.status,
        "matchday": match.matchday,
        "stage": match.stage,
        "group_name": match.group_name,
        "venue_name": match.venue_name,
        "attendance": match.attendance,
        "provider_last_updated": match.provider_last_updated,
    }


def final_or_provisional(status: MatchStatus) -> bool:
    """Small helper used by tests and jobs to state the storage rule explicitly."""

    return status in FINAL_STATUSES
