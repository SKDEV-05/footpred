"""Repository functions for historical point-in-time analysis datasets.

The loader is the boundary that turns stored football results into a
``VERIFIED_REAL`` dataset. It must never invent provenance: raw payload ids come from
the archived provider responses, observation times come from the result row that first
recorded the current score, and a dataset with no evidence is returned as ``None``
instead of being certified with placeholder values.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.intelligence.types import (
    DataClassification,
    DatasetEvidence,
    HistoricalMatch,
    IntelligenceDataset,
    materialized_content_digest,
)
from app.models.core import Match, MatchResult
from app.models.enums import MatchStatus
from app.models.provenance import DataProvider, RawPayload


class DatasetProvenanceError(ValueError):
    """Stored results cannot be tied to archived provider payloads."""


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def load_point_in_time_dataset(
    session: Session,
    *,
    fixture: Match,
    as_of: datetime,
) -> tuple[IntelligenceDataset | None, dict[str, Any]]:
    """Load results observed strictly before ``as_of`` and the target kickoff.

    A result row is eligible only when the current score was first recorded before
    ``as_of`` (``MatchResult.resolved_at``). ``Match.last_synced_at`` is not used: it
    changes on every refresh even when the score did not, which would make identical
    analyses non-reproducible.
    """

    as_of = _aware(as_of)
    target_kickoff = _aware(fixture.kickoff_utc)
    if as_of >= target_kickoff:
        raise ValueError("analysis as_of must be before the target kickoff")

    query = (
        select(Match, MatchResult)
        .join(MatchResult, MatchResult.match_id == Match.id)
        .where(
            Match.status == MatchStatus.FINISHED,
            Match.kickoff_utc < target_kickoff,
            MatchResult.resolved_at < as_of,
            MatchResult.home_score.isnot(None),
            MatchResult.away_score.isnot(None),
            # Only regulation-time results belong to the contract. Extra time and
            # shootouts change the meaning of the score and are excluded, not merged.
            MatchResult.extra_home_score.is_(None),
            MatchResult.extra_away_score.is_(None),
            MatchResult.shootout_home_score.is_(None),
            MatchResult.shootout_away_score.is_(None),
        )
        .order_by(Match.kickoff_utc.asc(), Match.id.asc())
    )
    rows = session.execute(query).all()

    excluded_extra_time = session.execute(
        select(func.count())
        .select_from(Match)
        .join(MatchResult, MatchResult.match_id == Match.id)
        .where(
            Match.status == MatchStatus.FINISHED,
            Match.kickoff_utc < target_kickoff,
            MatchResult.resolved_at < as_of,
            (
                MatchResult.extra_home_score.isnot(None)
                | MatchResult.shootout_home_score.isnot(None)
            ),
        )
    ).scalar_one()

    historical_matches: list[HistoricalMatch] = []
    raw_payload_ids: set[int] = set()
    kickoffs: list[datetime] = []
    observations: list[datetime] = []

    for match, result in rows:
        kickoff = _aware(match.kickoff_utc)
        observed_at = _aware(result.resolved_at)
        if observed_at < kickoff:
            observed_at = kickoff

        for payload_id in (match.raw_payload_id, result.raw_payload_id):
            if payload_id is not None:
                raw_payload_ids.add(payload_id)

        kickoffs.append(kickoff)
        observations.append(observed_at)
        historical_matches.append(
            HistoricalMatch(
                match_id=str(match.id),
                competition_id=str(match.competition_id),
                season_id=str(match.season_id),
                kickoff_utc=kickoff,
                observed_at=observed_at,
                home_team_id=str(match.home_team_id),
                away_team_id=str(match.away_team_id),
                home_goals=result.home_score,
                away_goals=result.away_score,
                neutral_venue=False,
                half_time_home_goals=result.ht_home_score,
                half_time_away_goals=result.ht_away_score,
            )
        )

    meta: dict[str, Any] = {
        "historical_matches": len(historical_matches),
        "competition_matches": sum(
            1 for item in historical_matches if item.competition_id == str(fixture.competition_id)
        ),
        "excluded_extra_time_or_shootout": int(excluded_extra_time),
        "earliest_kickoff": kickoffs[0].isoformat() if kickoffs else None,
        "latest_kickoff": kickoffs[-1].isoformat() if kickoffs else None,
        "earliest_observed": min(observations).isoformat() if observations else None,
        "latest_observed": max(observations).isoformat() if observations else None,
        "raw_payload_count": 0,
        "provider_code": None,
    }

    if not historical_matches:
        return None, meta

    if not raw_payload_ids:
        raise DatasetProvenanceError(
            "No archived raw payload is linked to the stored results; a VERIFIED_REAL "
            "dataset cannot be certified without provenance."
        )

    payload_rows = session.execute(
        select(RawPayload.id, RawPayload.fetched_at, DataProvider.code)
        .join(DataProvider, DataProvider.id == RawPayload.provider_id)
        .where(RawPayload.id.in_(sorted(raw_payload_ids)))
    ).all()
    if not payload_rows:
        raise DatasetProvenanceError(
            "The archived raw payload references are missing from the raw archive."
        )

    fetched = [_aware(row[1]) for row in payload_rows]
    provider_codes = sorted({row[2] for row in payload_rows})
    if len(provider_codes) != 1:
        raise DatasetProvenanceError(
            "Stored results reference more than one provider; a single evidence block "
            "cannot certify a mixed dataset."
        )

    retrieval_from = min(fetched)
    retrieval_to = as_of
    if retrieval_from >= retrieval_to:
        raise DatasetProvenanceError(
            "Raw payload retrieval time is not before the analysis checkpoint."
        )

    observed_from = min(observations)
    observed_to = as_of
    if observed_from >= observed_to:
        raise DatasetProvenanceError(
            "Result observation time is not before the analysis checkpoint."
        )

    content_digest = materialized_content_digest(
        historical_matches, DataClassification.VERIFIED_REAL
    )
    dataset_id = f"ds_match_{fixture.id}_{content_digest[:16]}"

    provisional_evidence = DatasetEvidence(
        provider_code=provider_codes[0],
        raw_payload_ids=tuple(sorted(raw_payload_ids)),
        retrieval_from_utc=retrieval_from,
        retrieval_to_utc=retrieval_to,
        payload_digest="0" * 64,
        observed_from_utc=observed_from,
        observed_to_utc=observed_to,
    )
    provisional = IntelligenceDataset(
        dataset_id=dataset_id,
        classification=DataClassification.VERIFIED_REAL,
        matches=tuple(historical_matches),
        evidence=provisional_evidence,
    )
    payload_digest = provisional.digest

    evidence = DatasetEvidence(
        provider_code=provider_codes[0],
        raw_payload_ids=tuple(sorted(raw_payload_ids)),
        retrieval_from_utc=retrieval_from,
        retrieval_to_utc=retrieval_to,
        payload_digest=payload_digest,
        observed_from_utc=observed_from,
        observed_to_utc=observed_to,
    )
    dataset = IntelligenceDataset(
        dataset_id=dataset_id,
        classification=DataClassification.VERIFIED_REAL,
        matches=tuple(historical_matches),
        evidence=evidence,
    )

    meta.update(
        {
            "raw_payload_count": len(raw_payload_ids),
            "provider_code": provider_codes[0],
            "retrieval_from": retrieval_from.isoformat(),
            "retrieval_to": retrieval_to.isoformat(),
            "observed_from": observed_from.isoformat(),
            "observed_to": observed_to.isoformat(),
            "content_digest": content_digest,
            "dataset_digest": dataset.digest,
        }
    )
    return dataset, meta
