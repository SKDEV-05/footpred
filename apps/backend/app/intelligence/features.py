"""Versioned, point-in-time descriptive feature construction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite

from app.intelligence.metrics import CompetitionContext, TeamForm
from app.intelligence.types import ResearchContext, Venue, require_context


class FeatureState(StrEnum):
    OBSERVED = "observed"
    MISSING = "missing"
    IMPUTED = "imputed"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class FeatureDefinition:
    name: str
    version: str
    unit: str
    description: str
    missing_policy: str


FEATURE_REGISTRY: tuple[FeatureDefinition, ...] = (
    FeatureDefinition("listed_home_team_venue_points_per_match", "2", "points/match", "Listed home team's target-venue PPM.", "missing"),
    FeatureDefinition("listed_away_team_venue_points_per_match", "2", "points/match", "Listed away team's target-venue PPM.", "missing"),
    FeatureDefinition("listed_home_team_venue_goals_for_per_match", "2", "goals/match", "Listed home team's target-venue scoring rate.", "missing"),
    FeatureDefinition("listed_away_team_venue_goals_for_per_match", "2", "goals/match", "Listed away team's target-venue scoring rate.", "missing"),
    FeatureDefinition("listed_home_team_venue_goals_against_per_match", "2", "goals/match", "Listed home team's target-venue concession rate.", "missing"),
    FeatureDefinition("listed_away_team_venue_goals_against_per_match", "2", "goals/match", "Listed away team's target-venue concession rate.", "missing"),
    FeatureDefinition("venue_points_difference", "2", "points/match", "Listed home minus away team target-venue PPM.", "missing"),
    FeatureDefinition("competition_non_neutral_home_goals_per_match", "2", "goals/match", "Competition listed-home scoring baseline excluding neutral fixtures.", "missing"),
    FeatureDefinition("competition_non_neutral_away_goals_per_match", "2", "goals/match", "Competition listed-away scoring baseline excluding neutral fixtures.", "missing"),
)


@dataclass(frozen=True)
class FeatureValue:
    name: str
    version: str
    value: float | None
    state: FeatureState
    calculated_at: datetime
    cutoff_utc: datetime
    available_at_utc: datetime | None
    window_start_utc: datetime | None
    window_end_utc: datetime
    venue: Venue
    source_match_ids: tuple[str, ...]
    context: ResearchContext
    missing_reason: str | None = None

    def __post_init__(self) -> None:
        require_context(self.context)
        if self.value is not None and not isfinite(self.value):
            raise ValueError("feature values must be finite")
        if self.state is FeatureState.OBSERVED:
            if self.value is None or self.missing_reason is not None:
                raise ValueError("observed features require a value and no missing reason")
        elif self.value is not None or self.missing_reason is None:
            raise ValueError("non-observed features require no value and a reason")
        if self.available_at_utc is not None and self.available_at_utc >= self.cutoff_utc:
            raise ValueError("feature evidence must be available strictly before cutoff")
        if self.window_start_utc is not None and self.window_start_utc >= self.window_end_utc:
            raise ValueError("feature source window must be half-open and increasing")
        if self.window_end_utc != self.cutoff_utc:
            raise ValueError("feature window must end at the prediction cutoff")


def build_features(
    *,
    home_form: TeamForm,
    away_form: TeamForm,
    competition: CompetitionContext,
    as_of: datetime,
    context: ResearchContext,
) -> tuple[FeatureValue, ...]:
    require_context(context)
    if any(item.context != context for item in (home_form, away_form, competition)):
        raise ValueError("all feature inputs must use the same research context")
    definitions = {item.name: item for item in FEATURE_REGISTRY}

    def feature(
        name: str,
        raw: float | None,
        ids: tuple[str, ...],
        available: tuple[datetime, ...],
        kickoffs: tuple[datetime, ...],
        venue: Venue,
    ) -> FeatureValue:
        definition = definitions[name]
        return FeatureValue(
            name=name,
            version=definition.version,
            value=raw,
            state=FeatureState.OBSERVED if raw is not None else FeatureState.MISSING,
            calculated_at=as_of,
            cutoff_utc=as_of,
            available_at_utc=max(available) if available else None,
            window_start_utc=min(kickoffs) if kickoffs else None,
            window_end_utc=as_of,
            venue=venue,
            source_match_ids=ids,
            context=context,
            missing_reason=None if raw is not None else "no_eligible_history",
        )

    difference = (
        home_form.points_per_match - away_form.points_per_match
        if home_form.points_per_match is not None and away_form.points_per_match is not None
        else None
    )
    combined_ids = tuple(dict.fromkeys(home_form.match_ids + away_form.match_ids))
    combined_available = home_form.source_available_at + away_form.source_available_at
    combined_kickoffs = home_form.source_kickoffs + away_form.source_kickoffs
    return (
        feature("listed_home_team_venue_points_per_match", home_form.points_per_match, home_form.match_ids, home_form.source_available_at, home_form.source_kickoffs, home_form.venue),
        feature("listed_away_team_venue_points_per_match", away_form.points_per_match, away_form.match_ids, away_form.source_available_at, away_form.source_kickoffs, away_form.venue),
        feature("listed_home_team_venue_goals_for_per_match", home_form.goals_for_per_match, home_form.match_ids, home_form.source_available_at, home_form.source_kickoffs, home_form.venue),
        feature("listed_away_team_venue_goals_for_per_match", away_form.goals_for_per_match, away_form.match_ids, away_form.source_available_at, away_form.source_kickoffs, away_form.venue),
        feature("listed_home_team_venue_goals_against_per_match", home_form.goals_against_per_match, home_form.match_ids, home_form.source_available_at, home_form.source_kickoffs, home_form.venue),
        feature("listed_away_team_venue_goals_against_per_match", away_form.goals_against_per_match, away_form.match_ids, away_form.source_available_at, away_form.source_kickoffs, away_form.venue),
        feature("venue_points_difference", difference, combined_ids, combined_available, combined_kickoffs, home_form.venue),
        feature("competition_non_neutral_home_goals_per_match", competition.home_goals_per_match, competition.match_ids, competition.source_available_at, competition.source_kickoffs, Venue.HOME),
        feature("competition_non_neutral_away_goals_per_match", competition.away_goals_per_match, competition.match_ids, competition.source_available_at, competition.source_kickoffs, Venue.AWAY),
    )
