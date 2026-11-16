"""HTTP contract: read-only endpoints, pagination, errors, and honest nulls.

Data is seeded through the ingestion layer so the test exercises storage, mapping, and
serialisation together.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.database.session import session_scope
from app.ingestion.fixtures import upsert_fixture
from app.ingestion.outcomes import ensure_data_provider
from app.ingestion.statistics import upsert_statistics
from app.models.core import Match
from app.models.enums import SyncStatus
from app.models.provenance import DataSyncRun
from tests.factories import (
    SYNTHETIC_AWAY,
    SYNTHETIC_COMPETITION,
    SYNTHETIC_HOME,
    make_match,
    make_score,
)

SCHEDULED_KICKOFF = datetime(2026, 8, 15, 15, 0, tzinfo=timezone.utc)
FINISHED_KICKOFF = datetime(2026, 8, 16, 15, 0, tzinfo=timezone.utc)


def _seed() -> dict[str, int]:
    with session_scope() as session:
        provider_id = ensure_data_provider(
            session, code="test_provider", name="Test Provider"
        ).id
        scheduled = upsert_fixture(
            session,
            provider_id=provider_id,
            dto=make_match(
                external_id="8001",
                status="SCHEDULED",
                kickoff=SCHEDULED_KICKOFF,
                venue="Example Stadium",
            ),
            sync_run_id=None,
            kickoff_window_minutes=180,
        )
        finished = upsert_fixture(
            session,
            provider_id=provider_id,
            dto=make_match(
                external_id="8002",
                status="FINISHED",
                kickoff=FINISHED_KICKOFF,
                score=make_score(2, 1, ht_home=1, ht_away=0, winner="HOME_TEAM"),
            ),
            sync_run_id=None,
            kickoff_window_minutes=180,
        )
        match = session.get(Match, finished.match_id)
        assert match is not None
        upsert_statistics(
            session,
            match_id=finished.match_id,
            team_id=match.home_team_id,
            metrics={"Ball Possession": 55, "Fouls": 0},
            provider_last_updated=None,
            raw_payload_id=None,
            sync_run_id=None,
        )
        return {
            "scheduled_id": scheduled.match_id,
            "finished_id": finished.match_id,
            "home_id": match.home_team_id,
            "competition_id": match.competition_id,
        }


@pytest.fixture
def seeded(client):
    return _seed()


def test_liveness_does_not_touch_the_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_reports_stale_when_no_sync_has_succeeded(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "ok"
    assert body == {"status": "ok", "database": "ok"}


def test_request_id_is_echoed_and_generated(client):
    echoed = client.get("/health", headers={"X-Request-ID": "test-request-id"})
    assert echoed.headers["X-Request-ID"] == "test-request-id"

    generated = client.get("/health")
    assert generated.headers["X-Request-ID"]

    unsafe = client.get("/health", headers={"X-Request-ID": "bad\nrequest"})
    assert unsafe.headers["X-Request-ID"] != "bad\nrequest"


def test_api_bounds_page_ids_and_search_inputs(client):
    assert client.get("/api/v1/fixtures", params={"page": 10001}).status_code == 422
    assert client.get("/api/v1/fixtures/999999999999999999999999").status_code == 422
    assert client.get("/api/v1/competitions", params={"q": "%%%"}).status_code == 422
    assert client.get(
        "/api/v1/fixtures/today", params={"timezone": "x" * 65}
    ).status_code == 422


def test_sync_run_api_does_not_expose_internal_failure_text(client):
    with session_scope() as session:
        session.add(
            DataSyncRun(
                job_type="fixtures",
                status=SyncStatus.FAILED,
                started_at=SCHEDULED_KICKOFF,
                finished_at=FINISHED_KICKOFF,
                parameters={},
                records_fetched=0,
                records_created=0,
                records_updated=0,
                records_unchanged=0,
                records_rejected=0,
                error_count=1,
                error_summary="SQL SELECT secret_token FROM /private/provider.db",
            )
        )
    response = client.get("/api/v1/sync/runs")
    assert response.status_code == 200
    body = response.text
    assert "secret_token" not in body
    assert "/private/provider.db" not in body
    assert "error_summary" not in body


def test_fixtures_are_filtered_by_utc_date_range(client, seeded):
    response = client.get(
        "/api/v1/fixtures",
        params={"date_from": "2026-08-01", "date_to": "2026-08-31"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["page"] == 1
    assert body["has_next"] is False
    assert [item["id"] for item in body["items"]] == [
        seeded["scheduled_id"],
        seeded["finished_id"],
    ]

    # Timestamps are UTC with an explicit suffix.
    assert body["items"][0]["kickoff_utc"] == "2026-08-15T15:00:00Z"


def test_scheduled_fixture_has_no_invented_score(client, seeded):
    response = client.get(f"/api/v1/fixtures/{seeded['scheduled_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "scheduled"
    assert body["score"] is None
    assert body["result"] is None
    assert body["statistics_available"] is False


def test_finished_fixture_exposes_the_stored_result(client, seeded):
    response = client.get(f"/api/v1/fixtures/{seeded['finished_id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["score"] == {"home": 2, "away": 1}
    assert body["result"]["home_score"] == 2
    assert body["result"]["winner"] == "home_team"
    assert body["result"]["is_final"] is True
    assert body["statistics_available"] is True


def test_statistics_distinguish_measured_zero_from_missing(client, seeded):
    response = client.get(f"/api/v1/fixtures/{seeded['finished_id']}/statistics")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert len(body["teams"]) == 2

    home = next(team for team in body["teams"] if team["team_id"] == seeded["home_id"])
    assert home["metrics"] == {"ball_possession": 55.0, "fouls": 0.0}
    assert "shots_on_goal" not in home["metrics"]

    away = next(team for team in body["teams"] if team["team_id"] != seeded["home_id"])
    assert away["metrics"] == {}


def test_statistics_for_an_unknown_fixture_is_404(client, seeded):
    response = client.get("/api/v1/fixtures/999999/statistics")
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["request_id"]


def test_today_endpoint_uses_the_requested_timezone_window(client, seeded):
    response = client.get(
        "/api/v1/fixtures/today",
        params={"date": "2026-08-15", "timezone": "UTC"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["date"] == "2026-08-15"
    assert body["timezone"] == "UTC"
    assert [item["id"] for item in body["items"]] == [seeded["scheduled_id"]]


def test_unknown_timezone_is_a_validation_error(client):
    response = client.get(
        "/api/v1/fixtures/today",
        params={"date": "2026-08-15", "timezone": "Not/AZone"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"][0]["code"] == "invalid_timezone"


def test_inverted_date_range_is_rejected(client):
    response = client.get(
        "/api/v1/fixtures",
        params={"date_from": "2026-08-31", "date_to": "2026-08-01"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_page_size_above_the_configured_maximum_is_rejected(client):
    response = client.get("/api/v1/teams", params={"page_size": 1000})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["error"]["details"][0]["code"] == "page_size_too_large"


def test_reference_endpoints_return_stored_entities(client, seeded):
    teams = client.get("/api/v1/teams", params={"q": "Example"})
    assert teams.status_code == 200
    assert teams.json()["total"] == 2

    competitions = client.get("/api/v1/competitions")
    assert competitions.status_code == 200
    assert competitions.json()["total"] == 1

    competition_id = seeded["competition_id"]
    detail = client.get(f"/api/v1/competitions/{competition_id}")
    assert detail.status_code == 200
    assert detail.json()["season_count"] == 1

    team_id = seeded["home_id"]
    team = client.get(f"/api/v1/teams/{team_id}")
    assert team.status_code == 200
    assert team.json()["match_count"] == 2


def test_sync_status_is_read_only_and_honest_about_absence(client):
    response = client.get("/api/v1/sync/status")
    assert response.status_code == 200
    body = response.json()
    assert body["last_successful_sync_at"] is None
    assert body["last_run_at"] is None
    assert body["last_run_status"] is None
    assert body["data_is_stale"] is True

    runs = client.get("/api/v1/sync/runs")
    assert runs.status_code == 200
    assert runs.json()["total"] == 0


def test_successful_reference_run_does_not_imply_fresh_fixture_data(client):
    """A successful competitions job must not mark fixture data fresh (F-04)."""
    with session_scope() as session:
        session.add(
            DataSyncRun(
                job_type="competitions",
                status=SyncStatus.SUCCESS,
                started_at=SCHEDULED_KICKOFF,
                finished_at=FINISHED_KICKOFF,
                parameters={},
                records_fetched=5,
                records_created=5,
                records_updated=0,
                records_unchanged=0,
                records_rejected=0,
                error_count=0,
            )
        )
    response = client.get("/api/v1/sync/status")
    body = response.json()
    assert body["data_is_stale"] is True
    assert body["last_successful_sync_at"] is None


def _add_run(
    *,
    job_type: str,
    status: SyncStatus,
    finished_at: datetime,
    records_fetched: int = 0,
    records_created: int = 0,
    records_updated: int = 0,
    records_unchanged: int = 0,
    records_rejected: int = 0,
    error_count: int = 0,
) -> None:
    with session_scope() as session:
        session.add(
            DataSyncRun(
                job_type=job_type,
                status=status,
                started_at=finished_at,
                finished_at=finished_at,
                parameters={},
                records_fetched=records_fetched,
                records_created=records_created,
                records_updated=records_updated,
                records_unchanged=records_unchanged,
                records_rejected=records_rejected,
                error_count=error_count,
            )
        )


def test_a_partial_run_that_stored_records_keeps_data_fresh(client):
    """One unstorable provider fixture must not make a full sync look stale."""

    now = datetime.now(timezone.utc)
    _add_run(
        job_type="fixtures",
        status=SyncStatus.PARTIAL,
        finished_at=now,
        records_fetched=367,
        records_updated=367,
        error_count=1,
    )
    _add_run(
        job_type="results",
        status=SyncStatus.SUCCESS,
        finished_at=now,
        records_fetched=2,
        records_updated=2,
    )

    response = client.get("/api/v1/sync/status")
    assert response.status_code == 200
    body = response.json()
    assert body["data_is_stale"] is False

    fixtures = next(job for job in body["per_job_type"] if job["job_type"] == "fixtures")
    assert fixtures["last_completed_status"] == "partial"
    assert fixtures["last_completed_at"] is not None
    assert fixtures["records_stored"] == 367
    # A partial run is not a success, and the response must not call it one.
    assert fixtures["last_success_at"] is None
    results = next(job for job in body["per_job_type"] if job["job_type"] == "results")
    assert body["last_successful_sync_at"] == results["last_success_at"]


def test_a_partial_run_that_stored_nothing_does_not_refresh_data(client):
    """Rejecting every record is not a refresh, whatever the run status says."""

    now = datetime.now(timezone.utc)
    _add_run(
        job_type="fixtures",
        status=SyncStatus.PARTIAL,
        finished_at=now,
        records_fetched=5,
        records_rejected=5,
        error_count=5,
    )
    _add_run(
        job_type="results",
        status=SyncStatus.SUCCESS,
        finished_at=now,
        records_fetched=2,
        records_updated=2,
    )

    response = client.get("/api/v1/sync/status")
    body = response.json()
    assert body["data_is_stale"] is True

    fixtures = next(job for job in body["per_job_type"] if job["job_type"] == "fixtures")
    assert fixtures["records_stored"] == 0
    assert fixtures["last_completed_status"] == "partial"


def test_there_are_no_write_endpoints(client):
    for method in ("post", "put", "patch", "delete"):
        response = getattr(client, method)("/api/v1/fixtures")
        assert response.status_code == 405
        assert response.json()["error"]["code"] == "method_not_allowed"


def test_media_fields_and_country_filter_use_stored_provider_values(client, seeded):
    with session_scope() as session:
        provider_id = ensure_data_provider(
            session, code="test_provider", name="Test Provider"
        ).id
        other_competition = replace(
            SYNTHETIC_COMPETITION,
            external_id="9002",
            name="Other League",
            code="OL",
            country_name="Otherland",
            country_code="OT",
            emblem="https://crests.example/ol.png",
        )
        upsert_fixture(
            session,
            provider_id=provider_id,
            dto=make_match(
                external_id="8003",
                competition=other_competition,
                # Each competition needs its own season identity; reusing a season id
                # across competitions is an identity change and is rejected by design.
                season=replace(SYNTHETIC_COMPETITION.seasons[0], external_id="7002"),
                home=replace(
                    SYNTHETIC_HOME,
                    external_id="503",
                    name="Other Home FC",
                    crest="https://crests.example/oh.png",
                ),
                away=replace(SYNTHETIC_AWAY, external_id="504", name="Other Away FC"),
                kickoff=datetime(2026, 8, 17, 15, 0, tzinfo=timezone.utc),
            ),
            sync_run_id=None,
            kickoff_window_minutes=180,
        )

    countries = client.get("/api/v1/countries").json()
    otherland = next(
        item for item in countries["items"] if item["name"] == "Otherland"
    )

    response = client.get(
        "/api/v1/fixtures",
        params={
            "date_from": "2026-08-01",
            "date_to": "2026-08-31",
            "country_id": otherland["id"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["competition"]["country"]["name"] == "Otherland"
    assert item["competition"]["emblem_url"] == "https://crests.example/ol.png"
    assert item["home_team"]["crest_url"] == "https://crests.example/oh.png"
    assert item["away_team"]["crest_url"] is None


def test_fixture_search_matches_team_and_competition_names(client, seeded):
    response = client.get(
        "/api/v1/fixtures",
        params={
            "date_from": "2026-08-01",
            "date_to": "2026-08-31",
            "q": "example home",
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2

    response = client.get(
        "/api/v1/fixtures",
        params={
            "date_from": "2026-08-01",
            "date_to": "2026-08-31",
            "q": "example league",
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2

    response = client.get(
        "/api/v1/fixtures",
        params={
            "date_from": "2026-08-01",
            "date_to": "2026-08-31",
            "q": "no such club",
        },
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_fixture_search_rejects_unsearchable_input(client, seeded):
    response = client.get(
        "/api/v1/fixtures",
        params={
            "date_from": "2026-08-01",
            "date_to": "2026-08-31",
            "q": "!!!",
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
