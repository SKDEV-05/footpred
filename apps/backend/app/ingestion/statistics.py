"""Team match statistics ingestion.

One row per ``(match, team, metric)``. A metric the provider did not supply has **no
row**; a supplied zero is stored as ``value = 0``. Nothing here defaults, fills, or
zero-substitutes a missing value (data rule D2).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import RecordValidationError, ValidationIssue
from app.models.core import Match
from app.models.statistics import TeamMatchStatistics
from app.normalization.status import snake_case
from app.providers.dto import ProviderTeamStatistics
from app.validation.rules import validate_statistics


@dataclass(frozen=True)
class StatisticsUpsert:
    created: int
    updated: int
    unchanged: int

    @property
    def total(self) -> int:
        return self.created + self.updated + self.unchanged


def upsert_statistics(
    session: Session,
    *,
    match_id: int,
    team_id: int,
    metrics: Mapping[str, float],
    provider_last_updated: datetime | None,
    raw_payload_id: int | None,
    sync_run_id: int | None,
) -> StatisticsUpsert:
    match = session.get(Match, match_id)
    if match is None:
        raise RecordValidationError(
            [ValidationIssue(code="unknown_match", message="statistics reference an unknown match", field="match_id")]
        )
    if team_id not in {match.home_team_id, match.away_team_id}:
        raise RecordValidationError(
            [
                ValidationIssue(
                    code="team_not_match_participant",
                    message="statistics team is not a participant in the match",
                    field="team_id",
                )
            ]
        )
    validate_statistics(
        ProviderTeamStatistics(team_external_id=str(team_id), metrics=metrics)
    )
    normalised: dict[str, float] = {}
    for key, value in metrics.items():
        try:
            metric = snake_case(key)
        except ValueError as exc:
            raise RecordValidationError(
                [
                    ValidationIssue(
                        code="invalid_metric_key",
                        message="metric key is invalid",
                        field="statistics.metric",
                    )
                ]
            ) from exc
        if not metric or len(metric) > 64:
            raise RecordValidationError(
                [
                    ValidationIssue(
                        code="invalid_metric_key",
                        message="metric key must be between 1 and 64 characters",
                        field="statistics.metric",
                    )
                ]
            )
        if metric in normalised and normalised[metric] != float(value):
            raise RecordValidationError(
                [
                    ValidationIssue(
                        code="metric_key_collision",
                        message=(
                            f"provider metrics collapse to the same key {metric!r} "
                            "with different values"
                        ),
                        field=f"statistics.{metric}",
                    )
                ]
            )
        normalised[metric] = float(value)

    created = updated = unchanged = 0
    for metric, value in normalised.items():
        existing = session.execute(
            select(TeamMatchStatistics).where(
                TeamMatchStatistics.match_id == match_id,
                TeamMatchStatistics.team_id == team_id,
                TeamMatchStatistics.metric == metric,
            )
        ).scalars().first()

        if existing is None:
            session.add(
                TeamMatchStatistics(
                    match_id=match_id,
                    team_id=team_id,
                    metric=metric,
                    value=value,
                    provider_last_updated=provider_last_updated,
                    raw_payload_id=raw_payload_id,
                    sync_run_id=sync_run_id,
                )
            )
            created += 1
            continue

        if existing.value != value:
            existing.value = value
            existing.provider_last_updated = provider_last_updated
            existing.raw_payload_id = raw_payload_id
            existing.sync_run_id = sync_run_id
            updated += 1
        else:
            unchanged += 1

    session.flush()
    return StatisticsUpsert(created=created, updated=updated, unchanged=unchanged)
