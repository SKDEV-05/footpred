"""Reference baselines for probability evaluation.

A football model is only useful if it beats something trivial. These baselines are
computed from the same training window as the models under test:

* ``uniform`` — 1/3 for every outcome.
* ``competition_frequency`` — the observed home/draw/away share in the same competition
  before the target match, with a documented fallback to the whole corpus and then to
  uniform when the sample is too small.

No baseline is fitted on the match it predicts.
"""

from __future__ import annotations

from typing import Sequence

from app.intelligence.types import HistoricalMatch

UNIFORM_MODEL_ID = "uniform_baseline"
UNIFORM_MODEL_VERSION = "uniform-v1.0.0"

FREQUENCY_MODEL_ID = "competition_frequency_baseline"
FREQUENCY_MODEL_VERSION = "frequency-v1.0.0"

MIN_FREQUENCY_SAMPLE = 20


def uniform_probabilities() -> tuple[float, float, float]:
    return (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)


def _shares(matches: Sequence[HistoricalMatch]) -> tuple[float, float, float] | None:
    if not matches:
        return None
    home = draw = away = 0
    for match in matches:
        if match.home_goals > match.away_goals:
            home += 1
        elif match.home_goals == match.away_goals:
            draw += 1
        else:
            away += 1
    total = len(matches)
    return (home / total, draw / total, away / total)


def competition_frequency_probabilities(
    prior_matches: Sequence[HistoricalMatch],
    *,
    competition_id: str,
) -> tuple[tuple[float, float, float], str]:
    """Return the expanding historical outcome share and the source actually used."""

    same_competition = [
        match for match in prior_matches if match.competition_id == competition_id
    ]
    shares = _shares(same_competition) if len(same_competition) >= MIN_FREQUENCY_SAMPLE else None
    if shares is not None:
        return shares, "competition"
    shares = _shares(prior_matches) if len(prior_matches) >= MIN_FREQUENCY_SAMPLE else None
    if shares is not None:
        return shares, "all_competitions"
    return uniform_probabilities(), "uniform_fallback"
