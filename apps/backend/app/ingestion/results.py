"""Final-result ingestion.

A result row is written only for a final status. A provisional in-play score is never
stored as a result, so a "final" score cannot later be silently overwritten by an
in-play observation. Every accepted change appends to ``match_change_log``.
"""

from __future__ import annotations

from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.ingestion.outcomes import UpsertOutcome, UpsertResult, diff_fields
from app.models.core import MatchResult
from app.models.enums import FINAL_STATUSES, MatchStatus
from app.models.provenance import MatchChangeLog
from app.normalization.status import match_duration, match_winner
from app.providers.dto import ProviderScore


def upsert_result(
    session: Session,
    *,
    match_id: int,
    score: ProviderScore,
    status: MatchStatus,
    provider_last_updated,
    sync_run_id: int | None,
    raw_payload_id: int | None = None,
) -> UpsertResult | None:
    """Persist a final result. Returns ``None`` when the match is not final."""

    if status not in FINAL_STATUSES:
        return None
    if score.home is None or score.away is None:
        # Validation already rejects this, but the storage layer must not create a
        # partial or zero-filled result under any circumstance.
        return None

    income: dict[str, Any] = {
        "home_score": score.home,
        "away_score": score.away,
        "extra_home_score": score.extra_home,
        "extra_away_score": score.extra_away,
        "shootout_home_score": score.penalties_home,
        "shootout_away_score": score.penalties_away,
        "ht_home_score": score.ht_home,
        "ht_away_score": score.ht_away,
        "winner": match_winner(score.winner) if score.winner else None,
        "duration": match_duration(score.duration) if score.duration else None,
        "status": status,
        "is_final": True,
        "provider_last_updated": provider_last_updated,
        "raw_payload_id": raw_payload_id,
    }

    existing = session.get(MatchResult, match_id)

    if existing is None:
        session.add(
            MatchResult(
                match_id=match_id,
                resolved_at=utc_now(),
                **income,
            )
        )
        session.flush()
        return UpsertResult(match_id, UpsertOutcome.CREATED)

    previous = _snapshot(existing)
    change = diff_fields(previous, income)
    if not change.has_changes:
        return UpsertResult(match_id, UpsertOutcome.UNCHANGED)

    for field in change.changed_fields:
        setattr(existing, field, income[field])
    existing.resolved_at = utc_now()

    session.add(
        MatchChangeLog(
            match_id=match_id,
            sync_run_id=sync_run_id,
            change_type="result",
            changed_fields=list(change.changed_fields),
            previous_values=change.previous,
            new_values=change.new,
            provider_last_updated=provider_last_updated,
            raw_payload_id=raw_payload_id,
            created_at=utc_now(),
        )
    )
    session.flush()
    return UpsertResult(match_id, UpsertOutcome.UPDATED, change.changed_fields)


def _snapshot(result: MatchResult) -> Mapping[str, Any]:
    return {
        "home_score": result.home_score,
        "away_score": result.away_score,
        "extra_home_score": result.extra_home_score,
        "extra_away_score": result.extra_away_score,
        "shootout_home_score": result.shootout_home_score,
        "shootout_away_score": result.shootout_away_score,
        "ht_home_score": result.ht_home_score,
        "ht_away_score": result.ht_away_score,
        "winner": result.winner,
        "duration": result.duration,
        "status": result.status,
        "is_final": result.is_final,
        "provider_last_updated": result.provider_last_updated,
        "raw_payload_id": result.raw_payload_id,
    }
