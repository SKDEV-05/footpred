"""Market arithmetic with explicit score-overflow uncertainty."""

from __future__ import annotations

from dataclasses import dataclass

from app.intelligence.models.poisson import ScoreMatrix
from app.intelligence.types import ResearchContext, require_context


@dataclass(frozen=True)
class ProbabilityBounds:
    lower: float
    upper: float


@dataclass(frozen=True)
class OutcomeProbabilityBounds:
    home_win: ProbabilityBounds
    draw: ProbabilityBounds
    away_win: ProbabilityBounds
    unresolved_probability: float
    context: ResearchContext


@dataclass(frozen=True)
class DoubleChanceBounds:
    home_or_draw: ProbabilityBounds
    draw_or_away: ProbabilityBounds
    home_or_away: ProbabilityBounds
    context: ResearchContext


@dataclass(frozen=True)
class BothTeamsToScore:
    yes: float
    no: float
    context: ResearchContext


def match_outcomes(matrix: ScoreMatrix) -> OutcomeProbabilityBounds:
    context = matrix.context
    require_context(context)
    home = draw = away = 0.0
    overflow = matrix.overflow_index
    unresolved = matrix.probabilities[overflow][overflow]
    for home_goals, row in enumerate(matrix.probabilities):
        for away_goals, probability in enumerate(row):
            if home_goals == overflow and away_goals == overflow:
                continue
            if home_goals == overflow or home_goals > away_goals:
                home += probability
            elif away_goals == overflow or home_goals < away_goals:
                away += probability
            else:
                draw += probability
    return OutcomeProbabilityBounds(
        home_win=ProbabilityBounds(home, home + unresolved),
        draw=ProbabilityBounds(draw, draw + unresolved),
        away_win=ProbabilityBounds(away, away + unresolved),
        unresolved_probability=unresolved,
        context=context,
    )


def double_chance(outcomes: OutcomeProbabilityBounds) -> DoubleChanceBounds:
    require_context(outcomes.context)
    unresolved = outcomes.unresolved_probability
    return DoubleChanceBounds(
        home_or_draw=ProbabilityBounds(
            outcomes.home_win.lower + outcomes.draw.lower,
            min(1.0, outcomes.home_win.lower + outcomes.draw.lower + unresolved),
        ),
        draw_or_away=ProbabilityBounds(
            outcomes.draw.lower + outcomes.away_win.lower,
            min(1.0, outcomes.draw.lower + outcomes.away_win.lower + unresolved),
        ),
        home_or_away=ProbabilityBounds(
            outcomes.home_win.lower + outcomes.away_win.lower,
            min(1.0, outcomes.home_win.lower + outcomes.away_win.lower + unresolved),
        ),
        context=outcomes.context,
    )


def over_probability(matrix: ScoreMatrix, line: float) -> float:
    require_context(matrix.context)
    if line not in (0.5, 1.5, 2.5, 3.5):
        raise ValueError("only supported half-goal lines are 0.5, 1.5, 2.5 and 3.5")
    overflow = matrix.overflow_index
    return sum(
        probability
        for home_goals, row in enumerate(matrix.probabilities)
        for away_goals, probability in enumerate(row)
        if home_goals == overflow
        or away_goals == overflow
        or home_goals + away_goals > line
    )


def both_teams_to_score(matrix: ScoreMatrix) -> BothTeamsToScore:
    require_context(matrix.context)
    yes = sum(
        probability
        for home_goals, row in enumerate(matrix.probabilities)
        for away_goals, probability in enumerate(row)
        if home_goals > 0 and away_goals > 0
    )
    return BothTeamsToScore(yes=yes, no=1.0 - yes, context=matrix.context)


def top_scorelines(
    matrix: ScoreMatrix,
    *,
    limit: int = 5,
) -> tuple[tuple[int, int, float], ...]:
    require_context(matrix.context)
    if type(limit) is not int or not 0 < limit <= 100:
        raise ValueError("limit must be an integer in [1, 100]")
    overflow = matrix.overflow_index
    values = [
        (home, away, probability)
        for home, row in enumerate(matrix.probabilities[:overflow])
        for away, probability in enumerate(row[:overflow])
    ]
    values.sort(key=lambda item: (-item[2], item[0], item[1]))
    return tuple(values[:limit])
