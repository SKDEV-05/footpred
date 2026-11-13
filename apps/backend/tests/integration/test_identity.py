"""Identity resolution: mapping first, exact natural key second, never fuzzy.

Every DTO here is synthetic test data. No provider is contacted.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.exceptions import IdentityAmbiguityError, RecordValidationError
from app.ingestion.identity import (
    resolve_competition,
    resolve_country,
    resolve_match,
    resolve_season,
    resolve_team,
    resolve_team_from_ref,
)
from app.ingestion.outcomes import ensure_data_provider
from app.models.core import Competition, Country, Match, Season, Team
from app.models.provenance import (
    ProviderCompetitionMapping,
    ProviderMatchMapping,
    ProviderSeasonMapping,
    ProviderTeamMapping,
)
from app.normalization.status import competition_type
from app.providers.dto import ProviderCompetition, ProviderSeason, ProviderTeam
from tests.factories import (
    SYNTHETIC_AWAY,
    SYNTHETIC_COMPETITION,
    SYNTHETIC_HOME,
    SYNTHETIC_SEASON,
    make_team,
)

KICKOFF = datetime(2026, 8, 15, 15, 0, tzinfo=timezone.utc)


def _provider(session, code: str = "test_provider") -> int:
    provider = ensure_data_provider(session, code=code, name=code)
    return provider.id


def _competition(session, provider_id: int, dto=SYNTHETIC_COMPETITION):
    return resolve_competition(
        session,
        provider_id=provider_id,
        competition=dto,
        competition_type=competition_type(dto.type),
    )


def test_country_resolution_is_exact_and_accent_insensitive(session):
    first = resolve_country(session, name="Examplia", code="EX")
    second = resolve_country(session, name="Examplía")
    third = resolve_country(session, name="Examplia City")

    assert first == second
    assert third != first
    country = session.get(Country, first)
    assert country is not None
    assert country.name == "Examplia"
    assert country.iso_code == "EX"
    assert session.scalar(select(func.count(Country.id))) == 2


def test_country_does_not_fuzzy_merge_different_names(session):
    a = resolve_country(session, name="Example United")
    b = resolve_country(session, name="Example United FC")
    assert a != b


def test_competition_mapping_is_reused_and_enriched(session):
    provider_id = _provider(session)
    first = _competition(session, provider_id)
    assert first.created is True

    renamed = ProviderCompetition(
        external_id=SYNTHETIC_COMPETITION.external_id,
        name="Example League Renamed",
        code="EL",
        type="LEAGUE",
        country_name="Examplia",
        country_code="EX",
        seasons=(),
    )
    second = _competition(session, provider_id, renamed)
    assert second.entity_id == first.entity_id
    assert second.created is False

    competition = session.get(Competition, first.entity_id)
    assert competition is not None
    assert competition.name == "Example League Renamed"
    assert competition.normalized_name == "example league renamed"
    assert session.scalar(select(func.count(ProviderCompetitionMapping.id))) == 1


def test_competition_natural_key_matches_across_providers(session):
    first_provider = _provider(session, "provider_a")
    second_provider = _provider(session, "provider_b")

    first = _competition(session, first_provider)
    second = _competition(session, second_provider)

    assert second.entity_id == first.entity_id
    assert second.confidence == pytest.approx(0.95)
    assert session.scalar(select(func.count(Competition.id))) == 1
    assert session.scalar(select(func.count(ProviderCompetitionMapping.id))) == 2


def test_season_is_resolved_by_competition_and_label(session):
    provider_id = _provider(session)
    competition = _competition(session, provider_id)

    first = resolve_season(
        session,
        provider_id=provider_id,
        competition_id=competition.entity_id,
        season=SYNTHETIC_SEASON,
    )
    assert first.created is True

    same_label_other_external_id = ProviderSeason(
        external_id="7002",
        start_date=SYNTHETIC_SEASON.start_date,
        end_date=SYNTHETIC_SEASON.end_date,
        current_matchday=13,
        is_current=True,
    )
    # One provider may not map two external ids to the same season (ADR-0006).
    with pytest.raises(IdentityAmbiguityError):
        resolve_season(
            session,
            provider_id=provider_id,
            competition_id=competition.entity_id,
            season=same_label_other_external_id,
        )
    assert session.scalar(select(func.count(Season.id))) == 1
    assert session.scalar(select(func.count(ProviderSeasonMapping.id))) == 1


def test_season_natural_key_matches_across_providers(session):
    first_provider = _provider(session, "provider_a")
    second_provider = _provider(session, "provider_b")

    first_competition = _competition(session, first_provider)
    second_competition = _competition(session, second_provider)

    first = resolve_season(
        session,
        provider_id=first_provider,
        competition_id=first_competition.entity_id,
        season=SYNTHETIC_SEASON,
    )
    second = resolve_season(
        session,
        provider_id=second_provider,
        competition_id=second_competition.entity_id,
        season=SYNTHETIC_SEASON,
    )

    assert second.entity_id == first.entity_id
    assert second.confidence == pytest.approx(0.95)
    assert session.scalar(select(func.count(Season.id))) == 1
    assert session.scalar(select(func.count(ProviderSeasonMapping.id))) == 2


def test_season_cannot_move_between_competitions(session):
    provider_id = _provider(session)
    first_competition = _competition(session, provider_id)
    resolve_season(
        session,
        provider_id=provider_id,
        competition_id=first_competition.entity_id,
        season=SYNTHETIC_SEASON,
    )

    other = ProviderCompetition(
        external_id="9002",
        name="Other League",
        code="OL",
        type="LEAGUE",
        country_name="Examplia",
        country_code="EX",
        seasons=(),
    )
    second_competition = _competition(session, provider_id, other)

    with pytest.raises(IdentityAmbiguityError):
        resolve_season(
            session,
            provider_id=provider_id,
            competition_id=second_competition.entity_id,
            season=SYNTHETIC_SEASON,
        )


def test_team_reference_and_team_resource_converge_on_one_entity(session):
    provider_id = _provider(session)

    from_ref = resolve_team_from_ref(
        session,
        provider_id=provider_id,
        team=SYNTHETIC_HOME,
        country_name="Examplia",
        country_code="EX",
    )
    full = resolve_team(session, provider_id=provider_id, team=make_team())

    assert full.entity_id == from_ref.entity_id
    assert session.scalar(select(func.count(Team.id))) == 1
    assert session.scalar(select(func.count(ProviderTeamMapping.id))) == 1
    team = session.get(Team, full.entity_id)
    assert team is not None
    assert team.tla == "EXH"
    assert team.country is not None and team.country.name == "Examplia"


def test_team_natural_key_matches_across_providers(session):
    first_provider = _provider(session, "provider_a")
    second_provider = _provider(session, "provider_b")

    first = resolve_team(session, provider_id=first_provider, team=make_team())
    second = resolve_team(session, provider_id=second_provider, team=make_team())

    assert second.entity_id == first.entity_id
    assert session.scalar(select(func.count(Team.id))) == 1
    assert session.scalar(select(func.count(ProviderTeamMapping.id))) == 2


def test_ambiguous_team_is_rejected_not_merged(session):
    provider_id = _provider(session)
    country_id = resolve_country(session, name="Examplia", code="EX")
    for _ in range(2):
        session.add(
            Team(
                name="Duplicate FC",
                normalized_name="duplicate fc",
                country_id=country_id,
            )
        )
    session.flush()

    with pytest.raises(IdentityAmbiguityError):
        resolve_team(
            session,
            provider_id=provider_id,
            team=ProviderTeam(
                external_id="123",
                name="Duplicate FC",
                short_name=None,
                tla=None,
                country_name="Examplia",
            ),
        )

    # No mapping may be created for an ambiguous record.
    assert session.scalar(select(func.count(ProviderTeamMapping.id))) == 0


def _match_fixture(session, provider_id: int):
    competition = _competition(session, provider_id)
    season = resolve_season(
        session,
        provider_id=provider_id,
        competition_id=competition.entity_id,
        season=SYNTHETIC_SEASON,
    )
    home = resolve_team_from_ref(
        session,
        provider_id=provider_id,
        team=SYNTHETIC_HOME,
        country_name="Examplia",
        country_code="EX",
    )
    away = resolve_team_from_ref(
        session,
        provider_id=provider_id,
        team=SYNTHETIC_AWAY,
        country_name="Examplia",
        country_code="EX",
    )
    return competition, season, home, away


def test_match_is_resolved_by_mapping_then_kickoff_window(session):
    provider_id = _provider(session)
    competition, season, home, away = _match_fixture(session, provider_id)

    first = resolve_match(
        session,
        provider_id=provider_id,
        external_id="8001",
        competition_id=competition.entity_id,
        season_id=season.entity_id,
        home_team_id=home.entity_id,
        away_team_id=away.entity_id,
        kickoff_utc=KICKOFF,
        kickoff_window_minutes=180,
    )
    assert first.created is True

    # A second external id from the same provider that falls inside the window matches
    # an already-mapped fixture. It is a conflict for review, not a silent second
    # mapping to the same internal match.
    with pytest.raises(IdentityAmbiguityError):
        resolve_match(
            session,
            provider_id=provider_id,
            external_id="8002",
            competition_id=competition.entity_id,
            season_id=season.entity_id,
            home_team_id=home.entity_id,
            away_team_id=away.entity_id,
            kickoff_utc=KICKOFF + timedelta(hours=2),
            kickoff_window_minutes=180,
        )

    # Beyond the window it is a distinct fixture, never an overwrite.
    outside_window = resolve_match(
        session,
        provider_id=provider_id,
        external_id="8003",
        competition_id=competition.entity_id,
        season_id=season.entity_id,
        home_team_id=home.entity_id,
        away_team_id=away.entity_id,
        kickoff_utc=KICKOFF + timedelta(hours=8),
        kickoff_window_minutes=180,
    )
    assert outside_window.entity_id != first.entity_id
    assert session.scalar(select(func.count(Match.id))) == 2
    assert session.scalar(select(func.count(ProviderMatchMapping.id))) == 2


def test_match_natural_key_matches_across_providers(session):
    first_provider = _provider(session, "provider_a")
    second_provider = _provider(session, "provider_b")

    first_competition, first_season, home, away = _match_fixture(
        session, first_provider
    )
    second_competition, second_season, _, _ = _match_fixture(session, second_provider)

    first = resolve_match(
        session,
        provider_id=first_provider,
        external_id="8001",
        competition_id=first_competition.entity_id,
        season_id=first_season.entity_id,
        home_team_id=home.entity_id,
        away_team_id=away.entity_id,
        kickoff_utc=KICKOFF,
        kickoff_window_minutes=180,
    )
    second = resolve_match(
        session,
        provider_id=second_provider,
        external_id="A-1",
        competition_id=second_competition.entity_id,
        season_id=second_season.entity_id,
        home_team_id=home.entity_id,
        away_team_id=away.entity_id,
        kickoff_utc=KICKOFF + timedelta(minutes=30),
        kickoff_window_minutes=180,
    )

    assert second.entity_id == first.entity_id
    assert second.confidence == pytest.approx(0.95)
    assert session.scalar(select(func.count(Match.id))) == 1
    assert session.scalar(select(func.count(ProviderMatchMapping.id))) == 2


def test_match_mapping_is_reused_even_when_kickoff_moves_outside_window(session):
    provider_id = _provider(session)
    competition, season, home, away = _match_fixture(session, provider_id)

    first = resolve_match(
        session,
        provider_id=provider_id,
        external_id="8001",
        competition_id=competition.entity_id,
        season_id=season.entity_id,
        home_team_id=home.entity_id,
        away_team_id=away.entity_id,
        kickoff_utc=KICKOFF,
        kickoff_window_minutes=180,
    )
    moved = resolve_match(
        session,
        provider_id=provider_id,
        external_id="8001",
        competition_id=competition.entity_id,
        season_id=season.entity_id,
        home_team_id=home.entity_id,
        away_team_id=away.entity_id,
        kickoff_utc=KICKOFF + timedelta(days=30),
        kickoff_window_minutes=180,
    )
    assert moved.entity_id == first.entity_id
    assert session.scalar(select(func.count(Match.id))) == 1


def test_invalid_competition_type_is_rejected_before_persistence(session):
    provider_id = _provider(session)
    bad = ProviderCompetition(
        external_id="9999",
        name="Bad Competition",
        code="BAD",
        type="FRIENDLY",
    )
    with pytest.raises(RecordValidationError):
        _competition(session, provider_id, bad)
    assert session.scalar(select(func.count(Competition.id))) == 0
