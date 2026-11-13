"""Normalisation must be deterministic, lossless for display, and strict."""

from __future__ import annotations

from datetime import date

import pytest

from app.core.exceptions import RecordValidationError
from app.normalization.names import clean_display_name, normalize_code, normalize_name
from app.normalization.status import (
    competition_type,
    group_name,
    match_duration,
    match_status,
    match_winner,
    season_label,
    snake_case,
    stage_name,
)
from app.models.enums import CompetitionType, MatchDuration, MatchStatus, MatchWinner


def test_display_name_trims_and_collapses_whitespace():
    assert clean_display_name("  Atlético \n de   Madrid ") == "Atlético de Madrid"


def test_display_name_rejects_empty_and_control_characters():
    with pytest.raises(ValueError):
        clean_display_name("   ")
    with pytest.raises(ValueError):
        clean_display_name("Bad\x00Name")


def test_normalize_name_is_accent_and_case_insensitive():
    assert normalize_name("Atlético de Madrid") == "atletico de madrid"
    assert normalize_name("ATLETICO  DE MADRID") == "atletico de madrid"


def test_normalize_name_does_not_merge_different_names():
    assert normalize_name("Example FC") != normalize_name("Example City FC")


def test_normalize_code_uppercases_and_strips():
    assert normalize_code(" exh ") == "EXH"
    assert normalize_code("") is None
    assert normalize_code(None) is None


def test_season_label_same_year_and_cross_year():
    assert season_label(date(2026, 3, 1), date(2026, 10, 1)) == "2026"
    assert season_label(date(2026, 8, 1), date(2027, 5, 31)) == "2026/2027"


def test_season_label_rejects_inverted_dates():
    with pytest.raises(ValueError):
        season_label(date(2027, 1, 1), date(2026, 1, 1))


def test_snake_case_metric_keys():
    assert snake_case("Ball Possession") == "ball_possession"
    assert snake_case("Shots on Goal") == "shots_on_goal"
    assert snake_case("xG") == "xg"
    assert snake_case("2nd Half Shots") == "m_2nd_half_shots"


def test_snake_case_rejects_empty():
    with pytest.raises(ValueError):
        snake_case("!!!")


def test_stage_and_group_normalisation():
    assert stage_name("REGULAR_SEASON") == "regular_season"
    assert stage_name(None) is None
    assert group_name("GROUP_A") == "group_a"
    assert group_name(None) is None


def test_provider_enum_translation_happy_path():
    assert match_status("IN_PLAY") is MatchStatus.IN_PLAY
    assert match_status("in_play") is MatchStatus.IN_PLAY
    assert competition_type("LEAGUE_CUP") is CompetitionType.LEAGUE_CUP
    assert match_winner("DRAW") is MatchWinner.DRAW
    assert match_duration("EXTRA_TIME") is MatchDuration.EXTRA_TIME


def test_unknown_provider_enum_is_rejected_not_defaulted():
    with pytest.raises(RecordValidationError) as excinfo:
        match_status("ABANDONED_BY_REFEREE")
    assert excinfo.value.issues[0].code == "unknown_provider_value"


def test_missing_provider_enum_is_rejected():
    with pytest.raises(RecordValidationError):
        match_status(None)
    with pytest.raises(RecordValidationError):
        competition_type("   ")
