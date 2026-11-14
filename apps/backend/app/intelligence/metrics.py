"""Descriptive team, competition and head-to-head calculations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from typing import Iterable

from app.intelligence.types import (
    HistoricalMatch,
    PointsPolicy,
    ResearchContext,
    Venue,
    require_context,
)


@dataclass(frozen=True)
class TeamForm:
    team_id: str
    venue: Venue
    window_requested: int
    sample_size: int
    wins: int
    draws: int
    losses: int
    points: int
    points_policy_id: str
    goals_for: int
    goals_against: int
    goal_difference: int
    points_per_match: float | None
    goals_for_per_match: float | None
    goals_against_per_match: float | None
    scoring_rate: float | None
    clean_sheet_rate: float | None
    failed_to_score_rate: float | None
    btts_rate: float | None
    over_1_5_rate: float | None
    over_2_5_rate: float | None
    over_3_5_rate: float | None
    goals_for_stddev: float | None
    goals_against_stddev: float | None
    match_ids: tuple[str, ...]
    source_available_at: tuple[datetime, ...]
    source_kickoffs: tuple[datetime, ...]
    context: ResearchContext


@dataclass(frozen=True)
class CompetitionContext:
    competition_id: str
    sample_size: int
    neutral_sample_size: int
    home_goals_per_match: float | None
    away_goals_per_match: float | None
    total_goals_per_match: float | None
    home_points_per_match: float | None
    match_ids: tuple[str, ...]
    source_available_at: tuple[datetime, ...]
    source_kickoffs: tuple[datetime, ...]
    context: ResearchContext


@dataclass(frozen=True)
class HeadToHead:
    home_team_id: str
    away_team_id: str
    sample_size: int
    home_wins: int
    draws: int
    away_wins: int
    home_goals: int
    away_goals: int
    btts_rate: float | None
    over_2_5_rate: float | None
    match_ids: tuple[str, ...]
    context: ResearchContext


def eligible_history(
    matches: Iterable[HistoricalMatch],
    *,
    as_of: datetime,
    competition_id: str | None = None,
    context: ResearchContext,
) -> tuple[HistoricalMatch, ...]:
    """Return observations known strictly before ``as_of`` in descending kickoff order."""

    require_context(context)
    selected = [
        match
        for match in matches
        if match.kickoff_utc < as_of
        and match.observed_at < as_of
        and (competition_id is None or match.competition_id == competition_id)
    ]
    return tuple(sorted(selected, key=lambda item: (item.kickoff_utc, item.match_id), reverse=True))


def _mean(values: list[int]) -> float | None:
    return sum(values) / len(values) if values else None


def _population_stddev(values: list[int]) -> float | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    return sqrt(sum((value - mean) ** 2 for value in values) / len(values))


def calculate_team_form(
    matches: Iterable[HistoricalMatch],
    *,
    team_id: str,
    as_of: datetime,
    window: int,
    venue: Venue = Venue.OVERALL,
    competition_id: str | None = None,
    points_policy: PointsPolicy,
    context: ResearchContext,
) -> TeamForm:
    require_context(context)
    if type(window) is not int or not 0 < window <= 1_000:
        raise ValueError("window must be an integer in [1, 1000]")
    history = eligible_history(
        matches,
        as_of=as_of,
        competition_id=competition_id,
        context=context,
    )
    selected: list[HistoricalMatch] = []
    for match in history:
        if not match.involves(team_id):
            continue
        actual_venue = match.venue_for(team_id)
        if venue != Venue.OVERALL and actual_venue != venue:
            continue
        selected.append(match)
        if len(selected) == window:
            break

    goals_for = [match.goals_for(team_id) for match in selected]
    goals_against = [match.goals_against(team_id) for match in selected]
    wins = sum(gf > ga for gf, ga in zip(goals_for, goals_against, strict=True))
    draws = sum(gf == ga for gf, ga in zip(goals_for, goals_against, strict=True))
    losses = len(selected) - wins - draws
    sample = len(selected)

    def rate(count: int) -> float | None:
        return count / sample if sample else None

    return TeamForm(
        team_id=team_id,
        venue=venue,
        window_requested=window,
        sample_size=sample,
        wins=wins,
        draws=draws,
        losses=losses,
        points=(
            points_policy.win_points * wins
            + points_policy.draw_points * draws
            + points_policy.loss_points * losses
        ),
        points_policy_id=points_policy.policy_id,
        goals_for=sum(goals_for),
        goals_against=sum(goals_against),
        goal_difference=sum(goals_for) - sum(goals_against),
        points_per_match=(
            (
                points_policy.win_points * wins
                + points_policy.draw_points * draws
                + points_policy.loss_points * losses
            )
            / sample
            if sample
            else None
        ),
        goals_for_per_match=_mean(goals_for),
        goals_against_per_match=_mean(goals_against),
        scoring_rate=rate(sum(value > 0 for value in goals_for)),
        clean_sheet_rate=rate(sum(value == 0 for value in goals_against)),
        failed_to_score_rate=rate(sum(value == 0 for value in goals_for)),
        btts_rate=rate(
            sum(gf > 0 and ga > 0 for gf, ga in zip(goals_for, goals_against, strict=True))
        ),
        over_1_5_rate=rate(
            sum(gf + ga > 1.5 for gf, ga in zip(goals_for, goals_against, strict=True))
        ),
        over_2_5_rate=rate(
            sum(gf + ga > 2.5 for gf, ga in zip(goals_for, goals_against, strict=True))
        ),
        over_3_5_rate=rate(
            sum(gf + ga > 3.5 for gf, ga in zip(goals_for, goals_against, strict=True))
        ),
        goals_for_stddev=_population_stddev(goals_for),
        goals_against_stddev=_population_stddev(goals_against),
        match_ids=tuple(match.match_id for match in selected),
        source_available_at=tuple(match.observed_at for match in selected),
        source_kickoffs=tuple(match.kickoff_utc for match in selected),
        context=context,
    )


def calculate_competition_context(
    matches: Iterable[HistoricalMatch],
    *,
    competition_id: str,
    as_of: datetime,
    window: int | None = None,
    points_policy: PointsPolicy,
    context: ResearchContext,
) -> CompetitionContext:
    require_context(context)
    if window is not None and (
        type(window) is not int or not 0 < window <= 100_000
    ):
        raise ValueError("window must be an integer in [1, 100000] when supplied")
    all_selected = eligible_history(
        matches,
        as_of=as_of,
        competition_id=competition_id,
        context=context,
    )
    if window is not None:
        all_selected = all_selected[:window]
    neutral_sample = sum(match.neutral_venue for match in all_selected)
    selected = tuple(match for match in all_selected if not match.neutral_venue)
    sample = len(selected)
    home_points = sum(
        points_policy.win_points
        if match.home_goals > match.away_goals
        else points_policy.draw_points
        if match.home_goals == match.away_goals
        else points_policy.loss_points
        for match in selected
    )
    return CompetitionContext(
        competition_id=competition_id,
        sample_size=sample,
        neutral_sample_size=neutral_sample,
        home_goals_per_match=(
            sum(match.home_goals for match in selected) / sample if sample else None
        ),
        away_goals_per_match=(
            sum(match.away_goals for match in selected) / sample if sample else None
        ),
        total_goals_per_match=(
            sum(match.home_goals + match.away_goals for match in selected) / sample
            if sample
            else None
        ),
        home_points_per_match=home_points / sample if sample else None,
        match_ids=tuple(match.match_id for match in selected),
        source_available_at=tuple(match.observed_at for match in selected),
        source_kickoffs=tuple(match.kickoff_utc for match in selected),
        context=context,
    )


def calculate_head_to_head(
    matches: Iterable[HistoricalMatch],
    *,
    home_team_id: str,
    away_team_id: str,
    as_of: datetime,
    window: int = 5,
    competition_id: str | None = None,
    context: ResearchContext,
) -> HeadToHead:
    require_context(context)
    if type(window) is not int or not 0 < window <= 1_000:
        raise ValueError("window must be an integer in [1, 1000]")
    selected = [
        match
        for match in eligible_history(
            matches,
            as_of=as_of,
            competition_id=competition_id,
            context=context,
        )
        if {match.home_team_id, match.away_team_id} == {home_team_id, away_team_id}
    ][:window]
    home_goals = [
        match.goals_for(home_team_id)
        for match in selected
    ]
    away_goals = [
        match.goals_for(away_team_id)
        for match in selected
    ]
    sample = len(selected)

    def rate(count: int) -> float | None:
        return count / sample if sample else None

    return HeadToHead(
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        sample_size=sample,
        home_wins=sum(h > a for h, a in zip(home_goals, away_goals, strict=True)),
        draws=sum(h == a for h, a in zip(home_goals, away_goals, strict=True)),
        away_wins=sum(h < a for h, a in zip(home_goals, away_goals, strict=True)),
        home_goals=sum(home_goals),
        away_goals=sum(away_goals),
        btts_rate=rate(
            sum(h > 0 and a > 0 for h, a in zip(home_goals, away_goals, strict=True))
        ),
        over_2_5_rate=rate(
            sum(h + a > 2.5 for h, a in zip(home_goals, away_goals, strict=True))
        ),
        match_ids=tuple(match.match_id for match in selected),
        context=context,
    )
