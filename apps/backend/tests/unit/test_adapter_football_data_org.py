"""Adapter parsing against documented v4 structure with synthetic payloads."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.exceptions import ProviderResponseError, UnsupportedCapabilityError
from app.providers.adapters.football_data_org import FootballDataOrgAdapter
from app.providers.dto import RawResponse
from tests.factories import RecordingArchive

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _load(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


class StaticHttp:
    def __init__(self, routes: dict[str, bytes], *, status: int = 200) -> None:
        self.routes = routes
        self.status = status
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, path: str, *, params=None) -> RawResponse:
        self.calls.append((path, dict(params or {})))
        return RawResponse(
            url=f"https://api.example.test/v4{path}",
            path=path,
            params=dict(params or {}),
            status_code=self.status,
            headers={"content-type": "application/json"},
            content=self.routes[path],
            fetched_at=datetime(2026, 8, 1, tzinfo=timezone.utc),
        )


def _adapter(routes: dict[str, bytes], *, status: int = 200):
    archive = RecordingArchive()
    http = StaticHttp(routes, status=status)
    return FootballDataOrgAdapter(http=http, archive=archive), archive, http


def test_parse_competitions_and_seasons():
    adapter, archive, _ = _adapter(
        {"/competitions": _load("football_data_org_competitions.json")}
    )
    fetched = adapter.fetch_competitions()

    assert fetched.raw_payload_id == 1
    assert len(archive.entries) == 1
    assert archive.entries[0][1] == "competitions"

    competition = fetched.items[0]
    assert competition.external_id == "9001"
    assert competition.name == "Example League"
    assert competition.type == "LEAGUE"
    assert competition.country_name == "Examplia"
    assert [season.external_id for season in competition.seasons] == ["7001", "7000"]
    assert competition.current_season is not None
    assert competition.current_season.current_matchday == 12


def test_parse_matches_including_null_score_fields():
    adapter, _, _ = _adapter(
        {"/matches": _load("football_data_org_matches.json")}
    )
    fetched = adapter.fetch_matches(
        date_from=datetime(2026, 8, 1).date(),
        date_to=datetime(2026, 8, 31).date(),
    )

    finished, scheduled = fetched.items
    assert finished.external_id == "8001"
    assert finished.status == "FINISHED"
    assert finished.score is not None
    assert (finished.score.home, finished.score.away) == (2, 1)
    assert (finished.score.ht_home, finished.score.ht_away) == (1, 0)
    assert finished.score.winner == "HOME_TEAM"
    assert finished.kickoff_utc == datetime(2026, 8, 15, 15, 0, tzinfo=timezone.utc)

    assert scheduled.external_id == "8002"
    assert scheduled.score is not None
    assert scheduled.score.home is None and scheduled.score.away is None
    assert scheduled.venue_name is None


def test_parse_match_detail_preserves_null_versus_zero():
    adapter, _, _ = _adapter(
        {"/matches/8001": _load("football_data_org_match_detail.json")}
    )
    detail = adapter.fetch_match_detail("8001").items

    home = next(
        stats for stats in detail.statistics if stats.team_external_id == "501"
    )
    assert home.metrics["ball_possession"] == 55.0
    assert home.metrics["fouls"] == 0.0
    assert "shots_on_goal" not in home.metrics  # null is unavailable, not zero


def test_payload_is_archived_before_parsing_even_when_invalid():
    archive_sink = RecordingArchive()
    http = StaticHttp({"/competitions": b"{not-json"})
    adapter = FootballDataOrgAdapter(http=http, archive=archive_sink)

    with pytest.raises(ProviderResponseError):
        adapter.fetch_competitions()

    assert len(archive_sink.entries) == 1


def test_unexpected_root_shape_is_rejected():
    adapter, _, _ = _adapter({"/competitions": b'{"unexpected": []}'})
    with pytest.raises(ProviderResponseError):
        adapter.fetch_competitions()


def test_non_object_root_is_rejected():
    adapter, _, _ = _adapter({"/competitions": b"[]"})
    with pytest.raises(ProviderResponseError):
        adapter.fetch_competitions()


def test_non_integer_identifier_is_rejected():
    bad = json.dumps(
        {
            "competitions": [
                {"id": "9001", "name": "X", "type": "LEAGUE", "seasons": []}
            ]
        }
    ).encode()
    adapter, _, _ = _adapter({"/competitions": bad})
    with pytest.raises(ProviderResponseError):
        adapter.fetch_competitions()


def test_naive_datetime_is_rejected():
    payload = {
        "competitions": [],
        "matches": [
            {
                "id": 1,
                "competition": {"id": 1, "name": "X", "type": "LEAGUE"},
                "season": {
                    "id": 2,
                    "startDate": "2026-08-01",
                    "endDate": "2027-05-31",
                },
                "utcDate": "2026-08-15T15:00:00",
                "status": "TIMED",
                "homeTeam": {"id": 3, "name": "H"},
                "awayTeam": {"id": 4, "name": "A"},
            }
        ],
    }
    adapter, _, _ = _adapter({"/matches": json.dumps(payload).encode()})
    with pytest.raises(ProviderResponseError):
        adapter.fetch_matches(
            date_from=datetime(2026, 8, 1).date(),
            date_to=datetime(2026, 8, 31).date(),
        )


def test_unsupported_capability_fails_loudly():
    adapter, _, _ = _adapter({})
    assert adapter.capabilities.lineups is False
    with pytest.raises(UnsupportedCapabilityError):
        adapter.fetch_lineups("8001")
    with pytest.raises(UnsupportedCapabilityError):
        adapter.require("lineups")


def test_competition_based_match_query_uses_documented_path_and_params():
    adapter, _, http = _adapter({"/competitions/EL/matches": b'{"matches": []}'})
    adapter.fetch_matches(
        date_from=datetime(2026, 8, 1).date(),
        date_to=datetime(2026, 8, 31).date(),
        competition_external_id="EL",
        season_external_id="7001",
        status="FINISHED",
    )
    path, params = http.calls[0]
    assert path == "/competitions/EL/matches"
    assert params == {
        "dateFrom": "2026-08-01",
        "dateTo": "2026-08-31",
        "season": "7001",
        "status": "FINISHED",
    }


def _match_payload() -> dict:
    return json.loads(_load("football_data_org_matches.json"))


def test_match_area_fills_competition_country_and_media_is_captured():
    payload = _match_payload()
    payload["matches"][0]["competition"]["emblem"] = "https://crests.example/el.png"
    payload["matches"][0]["homeTeam"]["crest"] = "https://crests.example/home.png"

    adapter, _, _ = _adapter({"/matches": json.dumps(payload).encode()})
    fetched = adapter.fetch_matches(
        date_from=datetime(2026, 8, 1).date(),
        date_to=datetime(2026, 8, 31).date(),
    )

    match = fetched.items[0]
    assert match.competition.country_name == "Examplia"
    assert match.competition.country_code == "EX"
    assert match.competition.emblem == "https://crests.example/el.png"
    assert match.home_team.crest == "https://crests.example/home.png"
    assert match.away_team.crest is None


def test_unassigned_knockout_fixture_is_counted_and_skipped():
    payload = _match_payload()
    tbd = json.loads(json.dumps(payload["matches"][0]))
    tbd["id"] = 8999
    tbd["homeTeam"] = {"id": None, "name": None, "shortName": None, "tla": None}
    tbd["awayTeam"] = {"id": None, "name": None, "shortName": None, "tla": None}
    payload["matches"].insert(0, tbd)

    adapter, _, _ = _adapter({"/matches": json.dumps(payload).encode()})
    fetched = adapter.fetch_matches(
        date_from=datetime(2026, 8, 1).date(),
        date_to=datetime(2026, 8, 31).date(),
    )

    assert fetched.skipped == 1
    assert [match.external_id for match in fetched.items] == ["8001", "8002"]


def test_non_http_media_url_is_rejected():
    payload = _match_payload()
    payload["matches"][0]["homeTeam"]["crest"] = "javascript:alert(1)"

    adapter, _, _ = _adapter({"/matches": json.dumps(payload).encode()})
    with pytest.raises(ProviderResponseError):
        adapter.fetch_matches(
            date_from=datetime(2026, 8, 1).date(),
            date_to=datetime(2026, 8, 31).date(),
        )
