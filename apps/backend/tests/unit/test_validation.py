"""Validation must reject bad records and never coerce them into plausible ones."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from app.core.exceptions import RecordValidationError
from app.providers.dto import ProviderTeamStatistics
from app.validation.rules import (
    validate_competition,
    validate_date_range,
    validate_match,
    validate_season,
    validate_statistics,
    validate_team,
)
from tests.factories import (
    SYNTHETIC_COMPETITION,
    SYNTHETIC_HOME,
    SYNTHETIC_SEASON,
    make_match,
    make_score,
    make_team,
)


def _codes(exc: RecordValidationError) -> set[str]:
    return {issue.code for issue in exc.issues}


def test_valid_scheduled_match_passes():
    validate_match(make_match(status="TIMED"))


def test_valid_finished_match_passes():
    validate_match(
        make_match(
            status="FINISHED",
            score=make_score(2, 1, ht_home=1, ht_away=0, winner="HOME_TEAM"),
        )
    )


def test_finished_match_without_score_is_rejected():
    with pytest.raises(RecordValidationError) as excinfo:
        validate_match(make_match(status="FINISHED", score=make_score(None, None)))
    assert "final_without_score" in _codes(excinfo.value)


def test_incomplete_score_is_rejected():
    with pytest.raises(RecordValidationError) as excinfo:
        validate_match(make_match(status="IN_PLAY", score=make_score(1, None)))
    assert "incomplete_score" in _codes(excinfo.value)


def test_winner_must_match_score():
    with pytest.raises(RecordValidationError) as excinfo:
        validate_match(
            make_match(status="FINISHED", score=make_score(2, 1, winner="AWAY_TEAM"))
        )
    assert "winner_score_mismatch" in _codes(excinfo.value)


def test_same_team_on_both_sides_is_rejected():
    with pytest.raises(RecordValidationError) as excinfo:
        validate_match(make_match(status="TIMED", away=SYNTHETIC_HOME))
    assert "same_team" in _codes(excinfo.value)


def test_naive_kickoff_is_rejected():
    naive = datetime(2026, 8, 15, 15, 0)
    with pytest.raises(RecordValidationError) as excinfo:
        validate_match(make_match(kickoff=naive))
    assert "naive_kickoff" in _codes(excinfo.value)


def test_implausibly_old_kickoff_is_rejected():
    with pytest.raises(RecordValidationError) as excinfo:
        validate_match(make_match(kickoff=datetime(1899, 1, 1, tzinfo=timezone.utc)))
    assert "implausible_kickoff" in _codes(excinfo.value)


def test_negative_attendance_is_rejected():
    with pytest.raises(RecordValidationError) as excinfo:
        validate_match(make_match(status="TIMED", attendance=-5))
    assert "negative_attendance" in _codes(excinfo.value)


def test_unknown_status_is_rejected():
    with pytest.raises(RecordValidationError):
        validate_match(make_match(status="ABANDONED"))


def test_half_time_cannot_exceed_full_time():
    with pytest.raises(RecordValidationError) as excinfo:
        validate_match(
            make_match(
                status="FINISHED", score=make_score(1, 0, ht_home=2, ht_away=0)
            )
        )
    assert "half_time_exceeds_full_time" in _codes(excinfo.value)


def test_zero_zero_is_valid_and_not_treated_as_missing():
    validate_match(
        make_match(
            status="FINISHED", score=make_score(0, 0, ht_home=0, ht_away=0, winner="DRAW")
        )
    )


def test_competition_unknown_type_is_rejected():
    from app.providers.dto import ProviderCompetition

    competition = ProviderCompetition(
        external_id="1", name="X", code="X", type="FRIENDLY"
    )
    with pytest.raises(RecordValidationError):
        validate_competition(competition)


def test_season_dates_must_be_ordered():
    from app.providers.dto import ProviderSeason

    with pytest.raises(RecordValidationError):
        validate_season(
            ProviderSeason(
                external_id="1",
                start_date=date(2026, 6, 1),
                end_date=date(2026, 5, 1),
                current_matchday=None,
            )
        )


def test_team_founded_year_is_bounded():
    from app.providers.dto import ProviderTeam

    with pytest.raises(RecordValidationError):
        validate_team(
            ProviderTeam(
                external_id="1",
                name="Example",
                short_name=None,
                tla=None,
                founded=1200,
            )
        )


def test_statistics_reject_negative_and_non_finite_values():
    with pytest.raises(RecordValidationError) as excinfo:
        validate_statistics(
            ProviderTeamStatistics(team_external_id="1", metrics={"shots": -1})
        )
    assert "negative_metric" in _codes(excinfo.value)

    with pytest.raises(RecordValidationError) as excinfo:
        validate_statistics(
            ProviderTeamStatistics(team_external_id="1", metrics={"xg": float("nan")})
        )
    assert "non_finite_metric" in _codes(excinfo.value)


def test_statistics_accept_measured_zero():
    validate_statistics(ProviderTeamStatistics(team_external_id="1", metrics={"goals": 0}))


def test_date_range_guard():
    validate_date_range(date(2026, 8, 1), date(2026, 8, 31))
    with pytest.raises(RecordValidationError):
        validate_date_range(date(2026, 8, 31), date(2026, 8, 1))
    with pytest.raises(RecordValidationError):
        validate_date_range(date(2026, 1, 1), date(2027, 12, 31))


def test_synthetic_fixtures_are_labelled():
    from tests.factories import SYNTHETIC_NOTICE

    assert SYNTHETIC_NOTICE == "SYNTHETIC TEST DATA"
    assert SYNTHETIC_COMPETITION.name == "Example League"
    assert SYNTHETIC_SEASON.external_id == "7001"
    assert SYNTHETIC_HOME.name == "Example Home FC"
    assert make_team().external_id == "501"
