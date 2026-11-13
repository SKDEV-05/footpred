"""Fixture, result, and statistics ingestion: idempotency, corrections, and D2.

The central rule under test: a missing value has no row and is never a zero, while a
measured zero is stored as zero.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from app.core.exceptions import RecordValidationError
from app.ingestion.fixtures import upsert_fixture
from app.ingestion.outcomes import UpsertOutcome, ensure_data_provider
from app.ingestion.statistics import upsert_statistics
from app.models.core import Match, MatchResult
from app.models.enums import MatchStatus
from app.models.provenance import MatchChangeLog
from app.models.statistics import TeamMatchStatistics
from tests.factories import (
    SYNTHETIC_AWAY,
    SYNTHETIC_HOME,
    make_match,
    make_score,
)


def _provider(session) -> int:
    return ensure_data_provider(
        session, code="test_provider", name="Test Provider"
    ).id


def _upsert(session, provider_id: int, dto, *, run_id: int | None = None):
    return upsert_fixture(
        session,
        provider_id=provider_id,
        dto=dto,
        sync_run_id=run_id,
        kickoff_window_minutes=180,
    )


def test_creating_a_fixture_builds_reference_data_once(session):
    provider_id = _provider(session)
    dto = make_match()

    first = _upsert(session, provider_id, dto)
    assert first.outcome is UpsertOutcome.CREATED
    assert first.created is True
    assert first.result is None

    match = session.get(Match, first.match_id)
    assert match is not None
    assert match.status is MatchStatus.SCHEDULED
    assert match.home_team.name == SYNTHETIC_HOME.name
    assert match.away_team.name == SYNTHETIC_AWAY.name
    assert match.competition.name == "Example League"
    assert match.season.label == "2026/2027"
    assert match.stage == "regular_season"

    assert session.scalar(select(func.count(Match.id))) == 1
    assert session.scalar(select(func.count(MatchChangeLog.id))) == 0


def test_repeating_the_same_fixture_is_a_no_op(session):
    provider_id = _provider(session)
    dto = make_match()

    first = _upsert(session, provider_id, dto)
    second = _upsert(session, provider_id, dto)

    assert second.outcome is UpsertOutcome.UNCHANGED
    assert second.match_id == first.match_id
    assert second.changed_fields == ()
    assert session.scalar(select(func.count(Match.id))) == 1
    assert session.scalar(select(func.count(MatchChangeLog.id))) == 0


def test_fixture_corrections_are_updated_and_change_logged(session):
    provider_id = _provider(session)
    first = _upsert(session, provider_id, make_match())

    rescheduled = make_match(
        kickoff=make_match().kickoff_utc + timedelta(hours=3),
        venue="Example Stadium",
        attendance=12345,
    )
    corrected = _upsert(session, provider_id, rescheduled)

    assert corrected.outcome is UpsertOutcome.UPDATED
    assert corrected.match_id == first.match_id
    assert set(corrected.changed_fields) == {"kickoff_utc", "venue_name", "attendance"}

    match = session.get(Match, first.match_id)
    assert match is not None
    assert match.venue_name == "Example Stadium"
    assert match.attendance == 12345

    log = session.execute(select(MatchChangeLog)).scalars().one()
    assert log.change_type == "fixture"
    assert set(log.changed_fields) == {"kickoff_utc", "venue_name", "attendance"}
    assert log.previous_values["venue_name"] is None
    assert log.new_values["venue_name"] == "Example Stadium"


def test_absent_optional_fields_never_erase_stored_values(session):
    provider_id = _provider(session)
    _upsert(session, provider_id, make_match(venue="Example Stadium"))

    # A later payload omits the venue entirely.
    result = _upsert(session, provider_id, make_match(venue=None))
    assert result.outcome is UpsertOutcome.UNCHANGED

    match = session.get(Match, result.match_id)
    assert match is not None
    assert match.venue_name == "Example Stadium"


def test_finished_match_creates_a_final_result(session):
    provider_id = _provider(session)
    dto = make_match(
        status="FINISHED",
        score=make_score(2, 1, ht_home=1, ht_away=0, winner="HOME_TEAM"),
    )

    upsert = _upsert(session, provider_id, dto)
    assert upsert.result is not None
    assert upsert.result.created is True

    result = session.get(MatchResult, upsert.match_id)
    assert result is not None
    assert (result.home_score, result.away_score) == (2, 1)
    assert (result.ht_home_score, result.ht_away_score) == (1, 0)
    assert result.winner.value == "home_team"
    assert result.is_final is True

    match = session.get(Match, upsert.match_id)
    assert match is not None
    assert match.status is MatchStatus.FINISHED


def test_result_correction_is_change_logged(session):
    provider_id = _provider(session)
    original = make_match(
        status="FINISHED",
        score=make_score(2, 1, ht_home=1, ht_away=0, winner="HOME_TEAM"),
    )
    first = _upsert(session, provider_id, original)

    corrected_dto = make_match(
        status="FINISHED",
        score=make_score(3, 2, ht_home=2, ht_away=1, winner="HOME_TEAM"),
    )
    corrected = _upsert(session, provider_id, corrected_dto)

    assert corrected.outcome is UpsertOutcome.UNCHANGED
    assert corrected.result is not None
    assert corrected.result.updated is True
    assert set(corrected.result.changed_fields) == {
        "home_score",
        "away_score",
        "ht_home_score",
        "ht_away_score",
    }

    result = session.get(MatchResult, first.match_id)
    assert result is not None
    assert (result.home_score, result.away_score) == (3, 2)

    log = session.execute(
        select(MatchChangeLog).where(MatchChangeLog.change_type == "result")
    ).scalars().one()
    assert log.previous_values["home_score"] == 2
    assert log.new_values["home_score"] == 3


def test_unchanged_result_writes_no_change_log(session):
    provider_id = _provider(session)
    dto = make_match(
        status="FINISHED",
        score=make_score(1, 1, ht_home=1, ht_away=1, winner="DRAW"),
    )
    _upsert(session, provider_id, dto)
    repeat = _upsert(session, provider_id, dto)

    assert repeat.result is not None
    assert repeat.result.unchanged is True
    assert session.scalar(select(func.count(MatchChangeLog.id))) == 0


def test_in_play_score_is_not_stored_as_a_result(session):
    provider_id = _provider(session)
    dto = make_match(status="IN_PLAY", score=make_score(1, 0))

    upsert = _upsert(session, provider_id, dto)
    assert upsert.result is None
    assert session.scalar(select(func.count(MatchResult.match_id))) == 0


def test_zero_zero_is_a_measured_result_not_missing(session):
    provider_id = _provider(session)
    dto = make_match(
        status="FINISHED",
        score=make_score(0, 0, ht_home=0, ht_away=0, winner="DRAW"),
    )
    upsert = _upsert(session, provider_id, dto)

    result = session.get(MatchResult, upsert.match_id)
    assert result is not None
    assert result.home_score == 0
    assert result.away_score == 0
    assert result.home_score is not None


def test_statistics_distinguish_missing_from_zero(session):
    provider_id = _provider(session)
    fixture = _upsert(
        session,
        provider_id,
        make_match(status="FINISHED", score=make_score(1, 0, winner="HOME_TEAM")),
    )

    match = session.get(Match, fixture.match_id)
    assert match is not None
    home_id = match.home_team_id

    first = upsert_statistics(
        session,
        match_id=fixture.match_id,
        team_id=home_id,
        metrics={"Ball Possession": 55, "Fouls": 0},
        provider_last_updated=None,
        raw_payload_id=None,
        sync_run_id=None,
    )
    assert (first.created, first.updated, first.unchanged) == (2, 0, 0)

    rows = {
        row.metric: row.value
        for row in session.execute(
            select(TeamMatchStatistics).where(
                TeamMatchStatistics.match_id == fixture.match_id
            )
        ).scalars().all()
    }
    assert rows == {"ball_possession": 55.0, "fouls": 0.0}
    assert "shots_on_goal" not in rows

    # A later payload that omits fouls must not delete or zero it.
    second = upsert_statistics(
        session,
        match_id=fixture.match_id,
        team_id=home_id,
        metrics={"ball_possession": 56},
        provider_last_updated=None,
        raw_payload_id=None,
        sync_run_id=None,
    )
    assert (second.created, second.updated, second.unchanged) == (0, 1, 0)

    refreshed = {
        row.metric: row.value
        for row in session.execute(
            select(TeamMatchStatistics).where(
                TeamMatchStatistics.match_id == fixture.match_id
            )
        ).scalars().all()
    }
    assert refreshed == {"ball_possession": 56.0, "fouls": 0.0}


def test_colliding_metric_keys_with_different_values_are_rejected(session):
    provider_id = _provider(session)
    fixture = _upsert(session, provider_id, make_match())
    match = session.get(Match, fixture.match_id)
    assert match is not None

    with pytest.raises(RecordValidationError):
        upsert_statistics(
            session,
            match_id=fixture.match_id,
            team_id=match.home_team_id,
            metrics={"Ball Possession": 55, "ball_possession": 56},
            provider_last_updated=None,
            raw_payload_id=None,
            sync_run_id=None,
        )


def test_unknown_status_is_quarantined_by_validation_not_stored(session):
    provider_id = _provider(session)
    with pytest.raises(RecordValidationError):
        _upsert(session, provider_id, make_match(status="ABANDONED_BY_REFEREE"))
    assert session.scalar(select(func.count(Match.id))) == 0
    assert session.scalar(select(func.count(MatchResult.match_id))) == 0
