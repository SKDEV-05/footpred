"""Identity resolution: provider identifiers to stable internal entities.

Resolution order is fixed and deliberately narrow:

1. An existing provider mapping for ``(provider, external_id)``.
2. An exact natural key (normalised name + country for reference data; season + teams +
   kickoff window for a match).
3. Create a new internal entity plus a mapping.

Name similarity is never used. If step 2 returns more than one candidate the record is
ambiguous and is quarantined: the system prefers duplicates over a wrong merge
(ADR-0006).

Each resolver also returns a snapshot of the affected row *before* any enrichment, so
the caller can report exactly which fields changed without guessing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Mapping

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.exceptions import IdentityAmbiguityError
from app.core.time import utc_now
from app.models.core import Competition, Country, Match, Season, Team
from app.models.enums import CompetitionType, MatchStatus
from app.models.provenance import (
    ProviderCompetitionMapping,
    ProviderMatchMapping,
    ProviderSeasonMapping,
    ProviderTeamMapping,
)
from app.normalization.names import clean_display_name, normalize_code, normalize_name
from app.normalization.status import season_label
from app.providers.dto import (
    ProviderCompetition,
    ProviderSeason,
    ProviderTeam,
    ProviderTeamRef,
)

logger = logging.getLogger(__name__)

CONFIDENCE_MAPPING_HIT = 1.0
CONFIDENCE_NATURAL_KEY = 0.95
CONFIDENCE_CREATED = 1.0


@dataclass(frozen=True)
class Resolved:
    entity_id: int
    created: bool
    confidence: float
    previous: Mapping[str, Any] | None = None


def _single_or_none(statement: Select, session: Session, *, label: str):
    rows = session.execute(statement).scalars().all()
    if len(rows) > 1:
        raise IdentityAmbiguityError(
            f"Multiple internal {label} candidates matched; the record needs review."
        )
    return rows[0] if rows else None


def _assert_mapping_available(
    session: Session,
    *,
    mapping_model,
    internal_attr: str,
    entity_id: int,
    provider_id: int,
    external_id: str,
    label: str,
) -> None:
    """Enforce one mapping per provider and internal entity (ADR-0006).

    A provider presenting a second external id for an entity already mapped by that
    provider is an identity conflict, not a merge. It is surfaced for review rather than
    silently absorbing two provider records into one internal row.
    """

    existing = session.execute(
        select(mapping_model).where(
            mapping_model.provider_id == provider_id,
            getattr(mapping_model, internal_attr) == entity_id,
        )
    ).scalars().first()
    if existing is not None and existing.external_id != external_id:
        raise IdentityAmbiguityError(
            f"Provider {provider_id} already maps {label} {entity_id} to external id "
            f"{existing.external_id!r}; refusing to add {external_id!r} without review."
        )


# -- countries -------------------------------------------------------------------


def resolve_country(
    session: Session, *, name: str | None, code: str | None = None
) -> int | None:
    """Resolve a country by exact normalised name.

    Countries have no provider mapping table: they are shared reference data and the
    provider's area payload is not an identity assertion.
    """

    if not name:
        return None
    display = clean_display_name(name, max_length=120)
    key = normalize_name(display)
    existing = session.execute(
        select(Country).where(Country.normalized_name == key)
    ).scalars().first()
    if existing is not None:
        if code and existing.iso_code is None:
            existing.iso_code = _iso_code_or_none(code)
        return existing.id

    country = Country(
        name=display,
        normalized_name=key,
        iso_code=_iso_code_or_none(code),
    )
    session.add(country)
    session.flush()
    return country.id


def _iso_code_or_none(code: str | None) -> str | None:
    if not code:
        return None
    candidate = normalize_code(code)
    if candidate is None or len(candidate) > 3:
        return None
    return candidate


# -- competitions ----------------------------------------------------------------


def resolve_competition(
    session: Session,
    *,
    provider_id: int,
    competition: ProviderCompetition,
    competition_type: CompetitionType,
) -> Resolved:
    now = utc_now()
    mapping = session.execute(
        select(ProviderCompetitionMapping).where(
            ProviderCompetitionMapping.provider_id == provider_id,
            ProviderCompetitionMapping.external_id == competition.external_id,
        )
    ).scalars().first()
    if mapping is not None:
        mapping.last_seen_at = now
        mapping.is_active = True
        existing = session.get(Competition, mapping.competition_id)
        if existing is None:
            raise IdentityAmbiguityError(
                "A provider competition mapping points at a missing internal competition."
            )
        country_id = resolve_country(
            session, name=competition.country_name, code=competition.country_code
        )
        previous = _competition_snapshot(existing)
        _apply_competition(existing, competition, competition_type, country_id)
        return Resolved(
            existing.id,
            created=False,
            confidence=mapping.confidence,
            previous=previous,
        )

    name = clean_display_name(competition.name, max_length=160)
    normalized = normalize_name(name)
    country_id = resolve_country(
        session, name=competition.country_name, code=competition.country_code
    )

    candidate_statement = select(Competition).where(
        Competition.normalized_name == normalized
    )
    if country_id is None:
        candidate_statement = candidate_statement.where(Competition.country_id.is_(None))
    else:
        candidate_statement = candidate_statement.where(
            Competition.country_id == country_id
        )
    candidate = _single_or_none(candidate_statement, session, label="competition")

    created = False
    if candidate is None:
        candidate = Competition(
            name=name,
            normalized_name=normalized,
            code=normalize_code(competition.code),
            type=competition_type,
            country_id=country_id,
        )
        session.add(candidate)
        session.flush()
        created = True
        confidence = CONFIDENCE_CREATED
        previous: Mapping[str, Any] | None = None
    else:
        previous = _competition_snapshot(candidate)
        _apply_competition(candidate, competition, competition_type, country_id)
        confidence = CONFIDENCE_NATURAL_KEY

    _assert_mapping_available(
        session,
        mapping_model=ProviderCompetitionMapping,
        internal_attr="competition_id",
        entity_id=candidate.id,
        provider_id=provider_id,
        external_id=competition.external_id,
        label="competition",
    )
    session.add(
        ProviderCompetitionMapping(
            provider_id=provider_id,
            external_id=competition.external_id,
            competition_id=candidate.id,
            confidence=confidence,
            is_active=True,
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    session.flush()
    return Resolved(candidate.id, created=created, confidence=confidence, previous=previous)


def _competition_snapshot(competition: Competition) -> Mapping[str, Any]:
    return {
        "name": competition.name,
        "code": competition.code,
        "type": competition.type,
        "country_id": competition.country_id,
    }


def _apply_competition(
    competition: Competition,
    dto: ProviderCompetition,
    competition_type: CompetitionType,
    country_id: int | None,
) -> None:
    name = clean_display_name(dto.name, max_length=160)
    if competition.name != name:
        competition.name = name
        competition.normalized_name = normalize_name(name)
    code = normalize_code(dto.code)
    if code and competition.code != code:
        competition.code = code
    if competition.type != competition_type:
        competition.type = competition_type
    if country_id is not None and competition.country_id != country_id:
        competition.country_id = country_id


# -- seasons ---------------------------------------------------------------------


def resolve_season(
    session: Session,
    *,
    provider_id: int,
    competition_id: int,
    season: ProviderSeason,
) -> Resolved:
    now = utc_now()
    mapping = session.execute(
        select(ProviderSeasonMapping).where(
            ProviderSeasonMapping.provider_id == provider_id,
            ProviderSeasonMapping.external_id == season.external_id,
        )
    ).scalars().first()
    if mapping is not None:
        mapping.last_seen_at = now
        mapping.is_active = True
        existing = session.get(Season, mapping.season_id)
        if existing is None:
            raise IdentityAmbiguityError(
                "A provider season mapping points at a missing internal season."
            )
        previous = _season_snapshot(existing)
        _apply_season(existing, season, competition_id)
        return Resolved(
            existing.id, created=False, confidence=mapping.confidence, previous=previous
        )

    label = season_label(season.start_date, season.end_date)
    candidate = _single_or_none(
        select(Season).where(
            Season.competition_id == competition_id, Season.label == label
        ),
        session,
        label="season",
    )

    created = False
    if candidate is None:
        candidate = Season(
            competition_id=competition_id,
            label=label,
            start_date=season.start_date,
            end_date=season.end_date,
            current_matchday=season.current_matchday,
            is_current=bool(season.is_current),
        )
        session.add(candidate)
        session.flush()
        created = True
        confidence = CONFIDENCE_CREATED
        previous: Mapping[str, Any] | None = None
    else:
        previous = _season_snapshot(candidate)
        _apply_season(candidate, season, competition_id)
        confidence = CONFIDENCE_NATURAL_KEY

    _assert_mapping_available(
        session,
        mapping_model=ProviderSeasonMapping,
        internal_attr="season_id",
        entity_id=candidate.id,
        provider_id=provider_id,
        external_id=season.external_id,
        label="season",
    )
    session.add(
        ProviderSeasonMapping(
            provider_id=provider_id,
            external_id=season.external_id,
            season_id=candidate.id,
            confidence=confidence,
            is_active=True,
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    session.flush()
    return Resolved(candidate.id, created=created, confidence=confidence, previous=previous)


def _season_snapshot(season: Season) -> Mapping[str, Any]:
    return {
        "competition_id": season.competition_id,
        "label": season.label,
        "start_date": season.start_date,
        "end_date": season.end_date,
        "current_matchday": season.current_matchday,
        "is_current": season.is_current,
    }


def _apply_season(season: Season, dto: ProviderSeason, competition_id: int) -> None:
    if season.competition_id != competition_id:
        # A season cannot move between competitions; that would break the composite key
        # that matches rely on. Surface it instead of rewriting identity.
        raise IdentityAmbiguityError(
            "A provider season changed competition; the mapping needs review."
        )
    if season.start_date != dto.start_date:
        season.start_date = dto.start_date
    if season.end_date != dto.end_date:
        season.end_date = dto.end_date
    if dto.current_matchday is not None:
        season.current_matchday = dto.current_matchday
    if dto.is_current is not None:
        season.is_current = bool(dto.is_current)


# -- teams -----------------------------------------------------------------------


def resolve_team_from_ref(
    session: Session,
    *,
    provider_id: int,
    team: ProviderTeamRef,
    country_name: str | None = None,
    country_code: str | None = None,
) -> Resolved:
    return _resolve_team(
        session,
        provider_id=provider_id,
        external_id=team.external_id,
        name=team.name,
        short_name=team.short_name,
        tla=team.tla,
        country_name=country_name,
        country_code=country_code,
        venue_name=None,
        founded=None,
    )


def resolve_team(
    session: Session,
    *,
    provider_id: int,
    team: ProviderTeam,
) -> Resolved:
    return _resolve_team(
        session,
        provider_id=provider_id,
        external_id=team.external_id,
        name=team.name,
        short_name=team.short_name,
        tla=team.tla,
        country_name=team.country_name,
        country_code=team.country_code,
        venue_name=team.venue_name,
        founded=team.founded,
    )


def _resolve_team(
    session: Session,
    *,
    provider_id: int,
    external_id: str,
    name: str,
    short_name: str | None,
    tla: str | None,
    country_name: str | None,
    country_code: str | None,
    venue_name: str | None,
    founded: int | None,
) -> Resolved:
    now = utc_now()
    mapping = session.execute(
        select(ProviderTeamMapping).where(
            ProviderTeamMapping.provider_id == provider_id,
            ProviderTeamMapping.external_id == external_id,
        )
    ).scalars().first()
    if mapping is not None:
        mapping.last_seen_at = now
        mapping.is_active = True
        team = session.get(Team, mapping.team_id)
        if team is None:
            raise IdentityAmbiguityError(
                "A provider team mapping points at a missing internal team."
            )
        previous = _team_snapshot(team)
        _apply_team_enrichment(team, short_name, tla, venue_name, founded)
        return Resolved(
            team.id, created=False, confidence=mapping.confidence, previous=previous
        )

    display = clean_display_name(name, max_length=160)
    normalized = normalize_name(display)
    country_id = resolve_country(session, name=country_name, code=country_code)

    candidate_statement = select(Team).where(Team.normalized_name == normalized)
    if country_id is not None:
        candidate_statement = candidate_statement.where(Team.country_id == country_id)
    candidate = _single_or_none(candidate_statement, session, label="team")

    created = False
    if candidate is None:
        candidate = Team(
            name=display,
            normalized_name=normalized,
            short_name=short_name,
            tla=normalize_code(tla),
            country_id=country_id,
            venue_name=venue_name,
            founded=founded,
        )
        session.add(candidate)
        session.flush()
        created = True
        confidence = CONFIDENCE_CREATED
        previous: Mapping[str, Any] | None = None
    else:
        previous = _team_snapshot(candidate)
        _apply_team_enrichment(candidate, short_name, tla, venue_name, founded)
        confidence = CONFIDENCE_NATURAL_KEY

    _assert_mapping_available(
        session,
        mapping_model=ProviderTeamMapping,
        internal_attr="team_id",
        entity_id=candidate.id,
        provider_id=provider_id,
        external_id=external_id,
        label="team",
    )
    session.add(
        ProviderTeamMapping(
            provider_id=provider_id,
            external_id=external_id,
            team_id=candidate.id,
            confidence=confidence,
            is_active=True,
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    session.flush()
    return Resolved(candidate.id, created=created, confidence=confidence, previous=previous)


def _team_snapshot(team: Team) -> Mapping[str, Any]:
    return {
        "name": team.name,
        "short_name": team.short_name,
        "tla": team.tla,
        "country_id": team.country_id,
        "venue_name": team.venue_name,
        "founded": team.founded,
    }


def _apply_team_enrichment(
    team: Team,
    short_name: str | None,
    tla: str | None,
    venue_name: str | None,
    founded: int | None,
) -> None:
    """Fill or update only fields the provider actually supplied.

    The canonical display name is never overwritten by a match-embedded team reference:
    a rename must come from the team resource, and reference renames are recorded as a
    known limitation rather than applied silently from a fixture payload.
    """

    if short_name:
        team.short_name = short_name
    if tla:
        team.tla = normalize_code(tla)
    if venue_name:
        team.venue_name = venue_name
    if founded is not None:
        team.founded = founded


# -- matches ---------------------------------------------------------------------


def resolve_match(
    session: Session,
    *,
    provider_id: int,
    external_id: str,
    competition_id: int,
    season_id: int,
    home_team_id: int,
    away_team_id: int,
    kickoff_utc: datetime,
    kickoff_window_minutes: int,
) -> Resolved:
    now = utc_now()
    mapping = session.execute(
        select(ProviderMatchMapping).where(
            ProviderMatchMapping.provider_id == provider_id,
            ProviderMatchMapping.external_id == external_id,
        )
    ).scalars().first()
    if mapping is not None:
        mapping.last_seen_at = now
        mapping.is_active = True
        existing = session.get(Match, mapping.match_id)
        if existing is None:
            raise IdentityAmbiguityError(
                "A provider match mapping points at a missing internal match."
            )
        return Resolved(
            existing.id,
            created=False,
            confidence=mapping.confidence,
            previous=_match_identity_snapshot(existing),
        )

    window = timedelta(minutes=kickoff_window_minutes)
    candidate = _single_or_none(
        select(Match).where(
            Match.season_id == season_id,
            Match.home_team_id == home_team_id,
            Match.away_team_id == away_team_id,
            Match.kickoff_utc >= kickoff_utc - window,
            Match.kickoff_utc <= kickoff_utc + window,
        ),
        session,
        label="match",
    )

    created = False
    if candidate is None:
        candidate = Match(
            competition_id=competition_id,
            season_id=season_id,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            kickoff_utc=kickoff_utc,
            status=MatchStatus.SCHEDULED,
            first_seen_at=now,
            last_synced_at=now,
        )
        session.add(candidate)
        session.flush()
        created = True
        confidence = CONFIDENCE_CREATED
        previous: Mapping[str, Any] | None = None
    else:
        previous = _match_identity_snapshot(candidate)
        confidence = CONFIDENCE_NATURAL_KEY

    _assert_mapping_available(
        session,
        mapping_model=ProviderMatchMapping,
        internal_attr="match_id",
        entity_id=candidate.id,
        provider_id=provider_id,
        external_id=external_id,
        label="match",
    )
    session.add(
        ProviderMatchMapping(
            provider_id=provider_id,
            external_id=external_id,
            match_id=candidate.id,
            confidence=confidence,
            is_active=True,
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    session.flush()
    return Resolved(candidate.id, created=created, confidence=confidence, previous=previous)


def _match_identity_snapshot(match: Match) -> Mapping[str, Any]:
    return {
        "competition_id": match.competition_id,
        "season_id": match.season_id,
        "home_team_id": match.home_team_id,
        "away_team_id": match.away_team_id,
        "kickoff_utc": match.kickoff_utc,
    }
