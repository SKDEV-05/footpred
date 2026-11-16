"""Record validation.

Validation is a pure function of a normalised provider record: it never reads the
database, so it can be tested without fixtures. Referential checks (does this season
exist?) belong to identity resolution, which does have database state.

Every check returns issues instead of raising on the first one, so a quarantined record
explains everything that is wrong with it.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from math import isfinite

from app.core.exceptions import RecordValidationError, ValidationIssue
from app.models.enums import FINAL_STATUSES, MatchStatus
from app.normalization.status import competition_type, match_duration, match_status, match_winner
from app.providers.dto import (
    ProviderCompetition,
    ProviderMatch,
    ProviderSeason,
    ProviderTeam,
    ProviderTeamStatistics,
)

# A kickoff outside this range is far more likely to be a parsing or unit defect than a
# real fixture. The bound is a sanity guard, not a product rule.
EARLIEST_PLAUSIBLE_KICKOFF = datetime(1900, 1, 1, tzinfo=timezone.utc)
LATEST_PLAUSIBLE_KICKOFF = datetime(2100, 1, 1, tzinfo=timezone.utc)

MAX_METRIC_VALUE = 1_000_000.0


def _raise_if(issues: list[ValidationIssue]) -> None:
    if issues:
        raise RecordValidationError(issues)


def _require_text(value: str | None, field: str) -> list[ValidationIssue]:
    if value is None or not value.strip():
        return [
            ValidationIssue(
                code="missing_field", message=f"{field} is required", field=field
            )
        ]
    return []


def validate_season(season: ProviderSeason) -> None:
    issues: list[ValidationIssue] = []
    if season.start_date > season.end_date:
        issues.append(
            ValidationIssue(
                code="invalid_season_dates",
                message="season start date is after its end date",
                field="season.start_date",
            )
        )
    if season.current_matchday is not None and season.current_matchday <= 0:
        issues.append(
            ValidationIssue(
                code="invalid_matchday",
                message="current matchday must be positive",
                field="season.current_matchday",
            )
        )
    _raise_if(issues)


def validate_competition(competition: ProviderCompetition) -> None:
    issues: list[ValidationIssue] = []
    issues.extend(_require_text(competition.external_id, "competition.external_id"))
    issues.extend(_require_text(competition.name, "competition.name"))
    if issues:
        _raise_if(issues)
    # Raises UnknownProviderValueError, which is itself a RecordValidationError.
    competition_type(competition.type)
    for season in competition.seasons:
        validate_season(season)


def validate_team(team: ProviderTeam) -> None:
    issues: list[ValidationIssue] = []
    issues.extend(_require_text(team.external_id, "team.external_id"))
    issues.extend(_require_text(team.name, "team.name"))
    if team.founded is not None and not (1850 <= team.founded <= 2100):
        issues.append(
            ValidationIssue(
                code="invalid_founded_year",
                message="founded year must be between 1850 and 2100",
                field="team.founded",
            )
        )
    _raise_if(issues)


def validate_match(match: ProviderMatch) -> None:
    issues: list[ValidationIssue] = []

    issues.extend(_require_text(match.external_id, "match.external_id"))
    issues.extend(_require_text(match.home_team.external_id, "match.home_team.external_id"))
    issues.extend(_require_text(match.away_team.external_id, "match.away_team.external_id"))
    issues.extend(_require_text(match.home_team.name, "match.home_team.name"))
    issues.extend(_require_text(match.away_team.name, "match.away_team.name"))
    issues.extend(_require_text(match.competition.external_id, "match.competition.external_id"))
    issues.extend(_require_text(match.season.external_id, "match.season.external_id"))

    if match.home_team.external_id == match.away_team.external_id:
        issues.append(
            ValidationIssue(
                code="same_team",
                message="a match cannot have the same team on both sides",
                field="match.home_team.external_id",
            )
        )

    kickoff_issues = _validate_kickoff(match.kickoff_utc)
    issues.extend(kickoff_issues)

    if match.attendance is not None and match.attendance < 0:
        issues.append(
            ValidationIssue(
                code="negative_attendance",
                message="attendance must not be negative",
                field="match.attendance",
            )
        )

    if match.matchday is not None and match.matchday <= 0:
        issues.append(
            ValidationIssue(
                code="invalid_matchday",
                message="matchday must be positive",
                field="match.matchday",
            )
        )

    if issues:
        _raise_if(issues)

    # Enum translation is validation: an unknown value must not reach persistence.
    status = match_status(match.status)
    validate_season(match.season)
    competition_type(match.competition.type)

    if match.score is not None:
        issues.extend(_validate_score(match, status))
    elif status in FINAL_STATUSES:
        issues.append(
            ValidationIssue(
                code="final_without_score",
                message="a finished/awarded match must include a score object",
                field="match.score",
            )
        )

    _raise_if(issues)


def _validate_kickoff(value: datetime) -> list[ValidationIssue]:
    if value.tzinfo is None or value.utcoffset() is None:
        return [
            ValidationIssue(
                code="naive_kickoff",
                message="kickoff must include a timezone offset",
                field="match.kickoff_utc",
            )
        ]
    if not (EARLIEST_PLAUSIBLE_KICKOFF <= value <= LATEST_PLAUSIBLE_KICKOFF):
        return [
            ValidationIssue(
                code="implausible_kickoff",
                message="kickoff is outside the plausible range 1900-01-01..2100-01-01",
                field="match.kickoff_utc",
            )
        ]
    return []


def _validate_score(match: ProviderMatch, status: MatchStatus) -> list[ValidationIssue]:
    score = match.score
    assert score is not None
    issues: list[ValidationIssue] = []

    for label, value in (
        ("home", score.home),
        ("away", score.away),
        ("ht_home", score.ht_home),
        ("ht_away", score.ht_away),
        ("extra_home", score.extra_home),
        ("extra_away", score.extra_away),
        ("penalties_home", score.penalties_home),
        ("penalties_away", score.penalties_away),
    ):
        if value is not None and value < 0:
            issues.append(
                ValidationIssue(
                    code="negative_score",
                    message="scores must not be negative",
                    field=f"match.score.{label}",
                )
            )

    if (score.home is None) != (score.away is None):
        issues.append(
            ValidationIssue(
                code="incomplete_score",
                message="full-time scores must be either both present or both absent",
                field="match.score",
            )
        )

    if (score.ht_home is None) != (score.ht_away is None):
        issues.append(
            ValidationIssue(
                code="incomplete_half_time_score",
                message="half-time scores must be either both present or both absent",
                field="match.score",
            )
        )

    if (score.extra_home is None) != (score.extra_away is None):
        issues.append(
            ValidationIssue(
                code="incomplete_extra_time_score",
                message="extra-time scores must be both present or both absent",
                field="match.score.extraTime",
            )
        )
    if (score.penalties_home is None) != (score.penalties_away is None):
        issues.append(
            ValidationIssue(
                code="incomplete_penalty_score",
                message="penalty scores must be both present or both absent",
                field="match.score.penalties",
            )
        )

    duration = score.duration.upper() if score.duration else None
    has_extra = score.extra_home is not None or score.extra_away is not None
    has_penalties = (
        score.penalties_home is not None or score.penalties_away is not None
    )
    if has_extra and duration not in {"EXTRA_TIME", "PENALTY_SHOOTOUT"}:
        issues.append(
            ValidationIssue(
                code="extra_time_duration_mismatch",
                message="extra-time scores require an extra-time or shootout duration",
                field="match.score.duration",
            )
        )
    if has_penalties and duration != "PENALTY_SHOOTOUT":
        issues.append(
            ValidationIssue(
                code="shootout_duration_mismatch",
                message="penalty scores require a penalty-shootout duration",
                field="match.score.duration",
            )
        )
    if duration == "PENALTY_SHOOTOUT":
        if score.penalties_home is None or score.penalties_away is None:
            issues.append(
                ValidationIssue(
                    code="shootout_without_penalties",
                    message="a penalty shootout requires both penalty tallies",
                    field="match.score.penalties",
                )
            )
        elif score.penalties_home == score.penalties_away:
            issues.append(
                ValidationIssue(
                    code="tied_shootout",
                    message="penalty tallies must identify a shootout winner",
                    field="match.score.penalties",
                )
            )
    if (
        score.home is not None
        and score.away is not None
        and score.extra_home is not None
        and score.extra_away is not None
        and (score.extra_home < score.home or score.extra_away < score.away)
    ):
        issues.append(
            ValidationIssue(
                code="extra_time_below_full_time",
                message="cumulative extra-time scores cannot be below full-time scores",
                field="match.score.extraTime",
            )
        )

    if score.home is not None and score.ht_home is not None:
        if score.ht_home > score.home or score.ht_away is None or score.away is None:
            issues.append(
                ValidationIssue(
                    code="half_time_exceeds_full_time",
                    message="half-time score cannot exceed the full-time score",
                    field="match.score",
                )
            )
        elif score.ht_away > score.away:
            issues.append(
                ValidationIssue(
                    code="half_time_exceeds_full_time",
                    message="half-time score cannot exceed the full-time score",
                    field="match.score",
                )
            )

    if status in FINAL_STATUSES:
        if score.home is None or score.away is None:
            issues.append(
                ValidationIssue(
                    code="final_without_score",
                    message="a finished/awarded match must have a full-time score",
                    field="match.score",
                )
            )
        else:
            expected = _expected_winner(score)
            declared = match_winner(score.winner) if score.winner is not None else None
            if declared is not None and status is not MatchStatus.AWARDED and declared.value != expected:
                issues.append(
                    ValidationIssue(
                        code="winner_score_mismatch",
                        message=(
                            f"declared winner {declared.value!r} does not match "
                            f"score {score.home}-{score.away}"
                        ),
                        field="match.score.winner",
                    )
                )

    if score.duration is not None:
        match_duration(score.duration)

    return issues


def _expected_winner(score: ProviderScore) -> str:
    home = score.home
    away = score.away
    if (
        score.penalties_home is not None
        and score.penalties_away is not None
        and score.penalties_home != score.penalties_away
    ):
        home, away = score.penalties_home, score.penalties_away
    elif (
        score.extra_home is not None
        and score.extra_away is not None
        and score.duration in {"EXTRA_TIME", "PENALTY_SHOOTOUT"}
    ):
        home, away = score.extra_home, score.extra_away
    assert home is not None and away is not None
    if home > away:
        return "home_team"
    if away > home:
        return "away_team"
    return "draw"


def validate_statistics(stats: ProviderTeamStatistics) -> None:
    issues: list[ValidationIssue] = []
    issues.extend(_require_text(stats.team_external_id, "statistics.team_external_id"))

    for metric, value in stats.metrics.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            issues.append(
                ValidationIssue(
                    code="non_numeric_metric",
                    message=f"metric {metric!r} is not numeric",
                    field=f"statistics.{metric}",
                )
            )
            continue
        numeric = float(value)
        if not isfinite(numeric):
            issues.append(
                ValidationIssue(
                    code="non_finite_metric",
                    message=f"metric {metric!r} is not finite",
                    field=f"statistics.{metric}",
                )
            )
        elif numeric < 0:
            issues.append(
                ValidationIssue(
                    code="negative_metric",
                    message=f"metric {metric!r} must not be negative",
                    field=f"statistics.{metric}",
                )
            )
        elif numeric > MAX_METRIC_VALUE:
            issues.append(
                ValidationIssue(
                    code="implausible_metric",
                    message=f"metric {metric!r} exceeds the plausible maximum",
                    field=f"statistics.{metric}",
                )
            )

    _raise_if(issues)


def validate_date_range(date_from: date, date_to: date, *, max_days: int = 366) -> None:
    if date_to < date_from:
        raise RecordValidationError(
            [
                ValidationIssue(
                    code="invalid_date_range",
                    message="date_to must not precede date_from",
                    field="date_to",
                )
            ]
        )
    if (date_to - date_from) > timedelta(days=max_days):
        raise RecordValidationError(
            [
                ValidationIssue(
                    code="date_range_too_wide",
                    message=f"date range must not exceed {max_days} days",
                    field="date_to",
                )
            ]
        )
