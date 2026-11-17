"""Integration tests for the persisted model-evaluation API.

These tests exercise the real boundary: synthetic fixtures stored in SQLite, archived
provider payloads for provenance, the chronological engine, and the HTTP contract. The
corpus is deliberately small but large enough to pass the documented minimum history.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.database.session import session_scope
from app.models.core import Match, MatchResult
from app.models.evaluation import ModelEvaluation
from app.providers.dto import ProviderTeamRef
from tests.factories import make_match, make_score
from tests.integration.test_analysis_api import _seed_matches

FIRST_KICKOFF = datetime(2026, 1, 3, 15, 0, tzinfo=timezone.utc)
ROUNDS = 16
TEAMS = tuple(
    ProviderTeamRef(
        external_id=f"9{index:03d}",
        name=f"Synthetic Team {index}",
        short_name=f"T{index}",
        tla=f"T{index}",
    )
    for index in range(8)
)


def _corpus_specs(rounds: int = ROUNDS) -> list[dict]:
    specs: list[dict] = []
    for round_index in range(rounds):
        kickoff = FIRST_KICKOFF + timedelta(days=7 * round_index)
        for slot in range(len(TEAMS) // 2):
            home = TEAMS[(slot + round_index) % len(TEAMS)]
            away = TEAMS[(len(TEAMS) - 1 - slot + round_index) % len(TEAMS)]
            specs.append(
                {
                    "external_id": f"r{round_index:02d}s{slot}",
                    "status": "FINISHED",
                    "kickoff": kickoff,
                    "home": home,
                    "away": away,
                    "score": make_score(
                        home=(round_index + slot) % 4,
                        away=(2 * round_index + slot) % 3,
                    ),
                }
            )
    return specs


def _seed_corpus(database, rounds: int = ROUNDS) -> list[int]:
    ids = _seed_matches(database, _corpus_specs(rounds))
    # Mark each result as observed a few minutes after its own kickoff. Production
    # results are backfilled; the tests must not pretend the observation time is the
    # provider's publication time, only that it is in the past.
    with session_scope() as session:
        for match_id in ids:
            match = session.get(Match, match_id)
            result = session.execute(
                select(MatchResult).where(MatchResult.match_id == match_id)
            ).scalar_one()
            kickoff = match.kickoff_utc
            if kickoff.tzinfo is None:
                kickoff = kickoff.replace(tzinfo=timezone.utc)
            result.resolved_at = kickoff + timedelta(hours=3, minutes=5)
    return ids


def test_evaluation_requires_a_stored_corpus(client):
    response = client.get("/api/v1/evaluation/latest")
    assert response.status_code == 404


def test_evaluation_run_is_persisted_idempotent_and_served(client, database):
    _seed_corpus(database)

    first = client.post("/api/v1/evaluation/run")
    assert first.status_code == 200, first.text
    report = first.json()

    assert report["protocol_version"] == "phase7-v1"
    assert report["evaluation_version"] == "evaluation-v1.2.0"
    assert len(report["dataset_digest"]) == 64
    assert report["provider_code"] == "test_provider"
    assert report["sample_size"] > 0
    assert report["window_from"] < report["window_to"]

    body = report["report"]
    assert body["evaluated"] is True
    assert body["settings"]["result_horizon_hours"] == 3.0
    assert [model["key"] for model in body["models"]] == [
        "poisson",
        "dixon_coles",
        "elo",
        "uniform",
        "competition_frequency",
    ]
    sizes = {model["sample_size"] for model in body["models"]}
    assert len(sizes) == 1
    assert body["sample_size"] == sizes.pop()

    # The stored report must carry its provenance, not just a label.
    assert body["dataset"]["classification"] == "verified_real_data"
    assert body["dataset"]["provider_code"] == "test_provider"
    assert body["dataset"]["dataset_digest"] == report["dataset_digest"]
    assert body["dataset"]["matches"] == len(_corpus_specs())

    # Re-running the identical corpus must return the stored run, not a second row.
    second = client.post("/api/v1/evaluation/run")
    assert second.status_code == 200
    assert second.json()["id"] == report["id"]
    assert second.json()["report"] == body

    with session_scope() as session:
        count = session.execute(select(func.count()).select_from(ModelEvaluation)).scalar_one()
    assert count == 1

    latest = client.get("/api/v1/evaluation/latest")
    assert latest.status_code == 200
    assert latest.json()["id"] == report["id"]

    listing = client.get("/api/v1/evaluation/runs")
    assert listing.status_code == 200
    runs = listing.json()
    assert len(runs) == 1
    assert runs[0]["id"] == report["id"]
    assert runs[0]["model_keys"] == [
        "poisson",
        "dixon_coles",
        "elo",
        "uniform",
        "competition_frequency",
    ]
    assert "report" not in runs[0]

    fetched = client.get(f"/api/v1/evaluation/{report['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["report"] == body

    missing = client.get("/api/v1/evaluation/999999")
    assert missing.status_code == 404


def test_evaluation_rejects_a_future_checkpoint(client, database):
    _seed_corpus(database)
    future = datetime.now(timezone.utc) + timedelta(days=1)
    response = client.post(
        "/api/v1/evaluation/run", params={"as_of": future.isoformat()}
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "evaluation_checkpoint_invalid"


def test_evaluation_refuses_a_corpus_below_the_minimum(client, database):
    _seed_corpus(database, rounds=4)
    response = client.post("/api/v1/evaluation/run")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "evaluation_insufficient_data"
    with session_scope() as session:
        count = session.execute(select(func.count()).select_from(ModelEvaluation)).scalar_one()
    assert count == 0


def test_evaluation_refuses_results_without_provenance(client, database):
    _seed_matches(database, _corpus_specs(), payload=False)
    response = client.post("/api/v1/evaluation/run")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "evaluation_provenance_incomplete"
