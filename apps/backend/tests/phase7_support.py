"""Deterministic synthetic fixtures for Phase 7 model and backtest tests.

Everything here is invented. The schedule, scores, and identifiers are constructed to
exercise the models without any network access or stored data. ``SYNTHETIC TEST DATA``
classifications are used throughout so a real-data claim can never be made by accident.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from app.intelligence.types import (
    DataClassification,
    HistoricalMatch,
    IntelligenceDataset,
)

COMPETITION_ID = "comp_alpha"
SEASON_ID = "season_alpha"
FIRST_KICKOFF = datetime(2026, 1, 3, 15, 0, tzinfo=timezone.utc)
TEAMS = tuple(f"team_{index}" for index in range(8))


def _round_pairs(round_index: int) -> list[tuple[str, str]]:
    """Circle-method pairing that uses every team exactly once per round."""

    pairs: list[tuple[str, str]] = []
    for slot in range(len(TEAMS) // 2):
        home = TEAMS[(slot + round_index) % len(TEAMS)]
        away = TEAMS[(len(TEAMS) - 1 - slot + round_index) % len(TEAMS)]
        pairs.append((home, away))
    return pairs


def build_synthetic_matches(
    *,
    rounds: int = 16,
    competition_id: str = COMPETITION_ID,
) -> tuple[HistoricalMatch, ...]:
    if rounds <= 0:
        raise ValueError("rounds must be positive")
    matches: list[HistoricalMatch] = []
    for round_index in range(rounds):
        kickoff = FIRST_KICKOFF + timedelta(days=7 * round_index)
        for slot, (home, away) in enumerate(_round_pairs(round_index)):
            home_goals = (round_index + slot) % 4
            away_goals = (2 * round_index + slot) % 3
            matches.append(
                HistoricalMatch(
                    match_id=f"m_{competition_id}_{round_index:02d}_{slot}",
                    competition_id=competition_id,
                    season_id=SEASON_ID,
                    kickoff_utc=kickoff,
                    observed_at=kickoff,
                    home_team_id=home,
                    away_team_id=away,
                    home_goals=home_goals,
                    away_goals=away_goals,
                    neutral_venue=False,
                )
            )
    return tuple(matches)


def build_synthetic_dataset(
    *,
    rounds: int = 16,
    competition_id: str = COMPETITION_ID,
    dataset_id: str = "ds_phase7_synthetic",
) -> IntelligenceDataset:
    return IntelligenceDataset(
        dataset_id=dataset_id,
        classification=DataClassification.SYNTHETIC_TEST,
        matches=build_synthetic_matches(
            rounds=rounds, competition_id=competition_id
        ),
    )


def target_kickoff(matches: Sequence[HistoricalMatch]) -> datetime:
    """The next kickoff after the supplied history."""

    return max(item.kickoff_utc for item in matches) + timedelta(days=7)
