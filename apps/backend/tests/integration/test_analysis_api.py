"""Integration tests for the match analysis and prediction API endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.core.time import utc_now
from app.database.session import session_scope
from app.ingestion.fixtures import upsert_fixture
from app.ingestion.outcomes import ensure_data_provider
from app.ingestion.raw_archive import RawArchive
from app.main import create_app
from app.repositories.analysis import load_point_in_time_dataset
from app.providers.dto import RawResponse
from tests.factories import (
    SYNTHETIC_AWAY,
    SYNTHETIC_COMPETITION,
    SYNTHETIC_HOME,
    make_match,
    make_score,
)

KICKOFF_FUTURE = datetime(2026, 12, 1, 15, 0, tzinfo=timezone.utc)


def _archive_payload(database, provider_id: int) -> int:
    archive = RawArchive(
        provider_code="test_provider",
        provider_id=provider_id,
        storage_root=database.raw_dir,
    )
    return archive.store(
        RawResponse(
            url="https://api.example.test/v4/matches",
            path="/matches",
            params={"status": "FINISHED"},
            status_code=200,
            headers={"content-type": "application/json"},
            content=b'{"matches": []}',
            fetched_at=utc_now() - timedelta(hours=1),
        ),
        resource_type="matches",
    )


def _seed_test_matches(database) -> dict[str, int]:
    """Seed historical finished matches and one upcoming target fixture."""
    with session_scope() as session:
        provider_id = ensure_data_provider(
            session, code="test_provider", name="Test Provider"
        ).id

    # The archive writes in its own transaction; do not hold a write transaction open.
    raw_payload_id = _archive_payload(database, provider_id)

    with session_scope() as session:
        # Seed 6 historical finished matches for team A and team B
        for i in range(1, 7):
            dt = datetime(2026, 10, i, 15, 0, tzinfo=timezone.utc)
            upsert_fixture(
                session,
                provider_id=provider_id,
                dto=make_match(
                    external_id=f"hist_{i}",
                    status="FINISHED",
                    kickoff=dt,
                    score=make_score(home=2, away=1),
                ),
                sync_run_id=None,
                kickoff_window_minutes=180,
                raw_payload_id=raw_payload_id,
            )

        # Seed upcoming target match
        upcoming = upsert_fixture(
            session,
            provider_id=provider_id,
            dto=make_match(
                external_id="target_upcoming",
                status="SCHEDULED",
                kickoff=KICKOFF_FUTURE,
            ),
            sync_run_id=None,
            kickoff_window_minutes=180,
            raw_payload_id=raw_payload_id,
        )

        return {"upcoming_match_id": upcoming.match_id}


def test_analyze_match_not_found(client):
    response = client.post("/api/v1/analysis/matches/99999999")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"


def test_analyze_match_end_to_end(client, database):
    ids = _seed_test_matches(database)
    match_id = ids["upcoming_match_id"]

    # Trigger analysis via POST
    response = client.post(f"/api/v1/analysis/matches/{match_id}")
    assert response.status_code == 200
    report = response.json()

    assert report["match_id"] == match_id
    assert report["status"] in ("READY", "INSUFFICIENT_DATA")
    assert "match_overview" in report
    assert report["match_overview"]["match_id"] == match_id
    assert report["match_overview"]["home_team"]["name"] == SYNTHETIC_HOME.name
    assert report["match_overview"]["away_team"]["name"] == SYNTHETIC_AWAY.name

    assert "data_quality" in report
    assert report["data_quality"]["statistics_available"] is False
    assert len(report["data_quality"]["limitations"]) > 0

    if report["status"] == "READY":
        model = report["statistical_model"]
        assert model["model_id"] == "poisson_baseline"
        assert model["expected_home_goals"] > 0
        assert model["expected_away_goals"] > 0

        # Probabilities sum strictly to 1.0
        p_sum = (
            model["home_win_probability"]
            + model["draw_probability"]
            + model["away_win_probability"]
        )
        assert p_sum == 1.0
        assert model["model_parameters"] is not None
        assert report["evaluation"] is not None

        # Check scorelines
        assert len(model["scoreline_probabilities"]) == 5

        # Check explanation
        assert report["explanation"] is not None
        assert "expected_goals_breakdown" in report["explanation"]

    analysis_id = report["id"]

    # Verify retrieval by analysis ID via GET
    get_res = client.get(f"/api/v1/analysis/{analysis_id}")
    assert get_res.status_code == 200
    saved = get_res.json()
    assert saved["id"] == analysis_id
    assert saved["match_id"] == match_id

    # Verify history endpoint
    hist_res = client.get(f"/api/v1/analysis/matches/{match_id}/history")
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) >= 1
    assert history[0]["id"] == analysis_id


def _seed_matches(database, specs, *, payload: bool = True):
    """Seed fixtures, optionally with an archived payload they can be traced to."""

    with session_scope() as session:
        provider_id = ensure_data_provider(
            session, code="test_provider", name="Test Provider"
        ).id

    raw_payload_id = _archive_payload(database, provider_id) if payload else None
    ids: list[int] = []
    with session_scope() as session:
        for spec in specs:
            upserted = upsert_fixture(
                session,
                provider_id=provider_id,
                dto=make_match(**spec),
                sync_run_id=None,
                kickoff_window_minutes=180,
                raw_payload_id=raw_payload_id,
            )
            ids.append(upserted.match_id)
    return ids


def _history_specs(count: int = 6) -> list[dict]:
    return [
        {
            "external_id": f"hist_{i}",
            "status": "FINISHED",
            "kickoff": datetime(2026, 10, i, 15, 0, tzinfo=timezone.utc),
            "score": make_score(home=2, away=1),
        }
        for i in range(1, count + 1)
    ]


def _upcoming_spec(external_id: str = "target_upcoming") -> dict:
    return {
        "external_id": external_id,
        "status": "SCHEDULED",
        "kickoff": KICKOFF_FUTURE,
    }


def test_repeated_post_is_idempotent_and_force_regenerates(client, database):
    ids = _seed_matches(database, [*_history_specs(), _upcoming_spec()])
    match_id = ids[-1]

    first = client.post(f"/api/v1/analysis/matches/{match_id}").json()
    second = client.post(f"/api/v1/analysis/matches/{match_id}").json()
    assert first["status"] == "READY"
    assert second["id"] == first["id"]
    assert (
        second["data_quality"]["dataset_digest"]
        == first["data_quality"]["dataset_digest"]
    )

    forced = client.post(f"/api/v1/analysis/matches/{match_id}?force=true").json()
    assert forced["id"] != first["id"]
    assert forced["status"] == "READY"


def test_future_results_are_not_used_in_analysis(client, database):
    future = {
        "external_id": "future_result",
        "status": "FINISHED",
        "kickoff": datetime(2026, 12, 5, 15, 0, tzinfo=timezone.utc),
        "score": make_score(home=10, away=0),
    }
    ids = _seed_matches(database, [*_history_specs(), _upcoming_spec(), future])
    match_id = ids[-2]

    report = client.post(f"/api/v1/analysis/matches/{match_id}").json()
    assert report["status"] == "READY"

    quality = report["data_quality"]
    assert quality["historical_matches"] == 6
    assert quality["home_sample_size"] == 6
    assert datetime.fromisoformat(
        quality["latest_kickoff"].replace("Z", "+00:00")
    ) < KICKOFF_FUTURE
    # The 10-0 future result would dominate any goal average; it must be absent.
    assert report["historical_context"]["home_team"]["overall"]["goals_for"] == 12


def test_missing_provenance_is_analysis_failed_not_fabricated(client, database):
    ids = _seed_matches(
        database, [*_history_specs(), _upcoming_spec()], payload=False
    )

    report = client.post(f"/api/v1/analysis/matches/{ids[-1]}").json()
    assert report["status"] == "ANALYSIS_FAILED"
    assert report["statistical_model"] is None
    assert "dataset_provenance_incomplete" in report["data_quality"]["limitations"]
    assert "archived raw payload" in report["error_message"]


def test_no_prior_history_returns_insufficient_data(client, database):
    ids = _seed_matches(database, [_upcoming_spec()])

    report = client.post(f"/api/v1/analysis/matches/{ids[0]}").json()
    assert report["status"] == "INSUFFICIENT_DATA"
    assert report["statistical_model"] is None
    assert report["data_quality"]["historical_matches"] is None or (
        report["data_quality"]["historical_matches"] == 0
    )
    assert "no_historical_results" in report["data_quality"]["limitations"]


def test_finished_match_is_not_analysable(client, database):
    finished = {
        "external_id": "already_played",
        "status": "FINISHED",
        "kickoff": datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc),
        "score": make_score(home=1, away=1),
    }
    ids = _seed_matches(database, [_upcoming_spec(), finished])

    report = client.post(f"/api/v1/analysis/matches/{ids[-1]}").json()
    assert report["status"] == "DATA_UNAVAILABLE"
    assert report["statistical_model"] is None
    assert "match_not_analysable_in_current_state" in report["data_quality"]["limitations"]


def test_cancelled_match_is_not_analysable(client, database):
    cancelled = {
        "external_id": "cancelled_fixture",
        "status": "CANCELLED",
        "kickoff": KICKOFF_FUTURE,
    }
    ids = _seed_matches(database, [*_history_specs(), cancelled])

    report = client.post(f"/api/v1/analysis/matches/{ids[-1]}").json()
    assert report["status"] == "DATA_UNAVAILABLE"


def test_quality_reports_real_evidence_windows(client, database):
    ids = _seed_matches(database, [*_history_specs(), _upcoming_spec()])

    report = client.post(f"/api/v1/analysis/matches/{ids[-1]}").json()
    quality = report["data_quality"]

    assert quality["data_classification"] == "verified_real_data"
    assert quality["provider_code"] == "test_provider"
    assert len(quality["dataset_digest"]) == 64
    assert quality["retrieval_from"] is not None
    assert quality["retrieval_to"] is not None
    assert quality["retrieval_from"] < quality["retrieval_to"]
    assert quality["earliest_kickoff"].startswith("2026-10-01")
    assert quality["latest_kickoff"].startswith("2026-10-06")
    assert quality["statistics_available"] is False
    assert "no_lineup_or_injury_data" in quality["limitations"]


def test_thin_history_abstains_from_backtest(client, database):
    ids = _seed_matches(database, [*_history_specs(), _upcoming_spec()])

    report = client.post(f"/api/v1/analysis/matches/{ids[-1]}").json()
    evaluation = report["evaluation"]
    assert evaluation is not None
    assert evaluation["evaluated"] is False
    assert evaluation["reason"] == "insufficient_competition_matches_for_backtest"
    assert evaluation["calibration"] == []


def test_loader_honours_as_of_observation_boundary(client, database):
    from app.models.core import Match

    ids = _seed_matches(database, [*_history_specs(), _upcoming_spec()])
    target_id = ids[-1]

    with session_scope() as session:
        fixture = session.get(Match, target_id)
        # The results were recorded at ingestion time, so an earlier checkpoint cannot
        # see any of them.
        dataset, meta = load_point_in_time_dataset(
            session, fixture=fixture, as_of=utc_now() - timedelta(days=1)
        )
        assert dataset is None
        assert meta["historical_matches"] == 0

        dataset, meta = load_point_in_time_dataset(
            session, fixture=fixture, as_of=utc_now() + timedelta(minutes=1)
        )
        assert dataset is not None
        assert meta["historical_matches"] == 6
        assert len(dataset.evidence.raw_payload_ids) == 1
        assert dataset.evidence.provider_code == "test_provider"

        with pytest.raises(ValueError, match="before the target kickoff"):
            load_point_in_time_dataset(
                session, fixture=fixture, as_of=KICKOFF_FUTURE
            )
