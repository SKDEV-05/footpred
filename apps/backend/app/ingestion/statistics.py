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
from app.models.statistics import TeamMatchStatistics
from app.normalization.status import snake_case


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
    normalised: dict[str, float] = {}
    for key, value in metrics.items():
        metric = snake_case(key)
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
