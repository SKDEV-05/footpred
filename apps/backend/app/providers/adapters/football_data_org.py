"""Reference adapter for football-data.org API v4.

Implemented against the documented v4 request/response shapes recorded in
``docs/research/2026-11-13-football-data-org-api.md`` (access date 2026-11-13). Live
behaviour is **not verified**: no account or credentials exist in this environment.

Design rules applied here:

- Only documented fields are read; an absent optional field stays ``None``.
- A structural defect raises ``ProviderResponseError`` (the raw body is already archived).
- Provider enum values are passed through as strings. The validation layer translates
  them, so an unknown value is quarantined instead of silently defaulting.
- Vendor JSON never leaves this module.
"""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from datetime import date, datetime, timezone
from typing import Any, Callable, Mapping, TypeVar

from app.core.exceptions import ProviderResponseError
from app.providers.base import (
    ProviderAdapter,
    ProviderCapabilities,
    ProviderHttpClientProtocol,
    RawArchiveSink,
)
from app.providers.dto import (
    Fetched,
    ProviderCompetition,
    ProviderMatch,
    ProviderMatchDetail,
    ProviderScore,
    ProviderSeason,
    ProviderTeam,
    ProviderTeamRef,
    ProviderTeamStatistics,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")

COMPETITION_PATH = "/competitions"
MATCH_PATH = "/matches"


class FootballDataOrgAdapter(ProviderAdapter):
    code = "football_data_org"
    name = "football-data.org"
    capabilities = ProviderCapabilities(
        competitions=True,
        seasons=True,
        teams=True,
        fixtures=True,
        results=True,
        match_statistics=True,
        lineups=False,
        match_events=False,
    )

    def __init__(
        self,
        *,
        http: "ProviderHttpClientProtocol",
        archive: RawArchiveSink,
    ) -> None:
        self._http = http
        self._archive = archive

    # -- transport ---------------------------------------------------------------

    def _fetch(
        self,
        path: str,
        *,
        params: Mapping[str, str] | None,
        resource_type: str,
        parser: Callable[[Mapping[str, Any]], T | tuple[T, int]],
    ) -> Fetched[T]:
        response = self._http.get(path, params=params)
        # Archive ALL responses (including failures) for forensic replay.
        raw_payload_id = self._archive.store(response, resource_type=resource_type)
        if response.status_code != 200:
            raise ProviderResponseError(
                f"Provider returned HTTP {response.status_code} for {path}."
            )
        payload = _decode_json_object(response.content, path)
        try:
            parsed = parser(payload)
        except ProviderResponseError:
            raise
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderResponseError(
                f"Provider payload for {path} did not match the documented structure."
            ) from exc
        if isinstance(parsed, tuple):
            items, skipped = parsed
        else:
            items, skipped = parsed, 0
        return Fetched(items=items, raw_payload_id=raw_payload_id, skipped=skipped)

    # -- competitions ------------------------------------------------------------

    def fetch_competitions(self) -> Fetched[list[ProviderCompetition]]:
        return self._fetch(
            COMPETITION_PATH,
            params=None,
            resource_type="competitions",
            parser=lambda payload: [
                _parse_competition(item)
                for item in _require_list(payload, "competitions")
            ],
        )

    def fetch_competition(self, external_id: str) -> Fetched[ProviderCompetition]:
        if not external_id.strip():
            raise ValueError("competition external_id must not be empty")
        return self._fetch(
            f"{COMPETITION_PATH}/{external_id}",
            params=None,
            resource_type="competition_detail",
            parser=_parse_competition,
        )

    def fetch_seasons(
        self, competition_external_id: str
    ) -> Fetched[list[ProviderSeason]]:
        if not competition_external_id.strip():
            raise ValueError("competition external_id must not be empty")
        return self._fetch(
            f"{COMPETITION_PATH}/{competition_external_id}",
            params=None,
            resource_type="competition_detail",
            parser=lambda payload: _parse_competition(payload).seasons,
        )

    # -- teams -------------------------------------------------------------------

    def fetch_teams(
        self,
        competition_external_id: str,
        season_external_id: str | None = None,
    ) -> Fetched[list[ProviderTeam]]:
        if not competition_external_id.strip():
            raise ValueError("competition external_id must not be empty")
        params: dict[str, str] = {}
        if season_external_id:
            params["season"] = season_external_id
        return self._fetch(
            f"{COMPETITION_PATH}/{competition_external_id}/teams",
            params=params or None,
            resource_type="teams",
            parser=lambda payload: [
                _parse_team(item) for item in _require_list(payload, "teams")
            ],
        )

    # -- matches -----------------------------------------------------------------

    def fetch_matches(
        self,
        *,
        date_from: date | None = None,
        date_to: date | None = None,
        competition_external_id: str | None = None,
        season_external_id: str | None = None,
        status: str | None = None,
    ) -> Fetched[list[ProviderMatch]]:
        params: dict[str, str] = {}
        if date_from is not None and date_to is not None:
            params["dateFrom"] = date_from.isoformat()
            params["dateTo"] = date_to.isoformat()
        elif (date_from is None) != (date_to is None):
            raise ValueError("date_from and date_to must be provided together")
        if status:
            params["status"] = status
        if competition_external_id:
            if season_external_id:
                params["season"] = season_external_id
            path = f"{COMPETITION_PATH}/{competition_external_id}/matches"
        else:
            path = MATCH_PATH
        return self._fetch(
            path,
            params=params or None,
            resource_type="matches",
            parser=_parse_match_list,
        )

    def fetch_match_detail(self, match_external_id: str) -> Fetched[ProviderMatchDetail]:
        if not match_external_id.strip():
            raise ValueError("match external_id must not be empty")
        return self._fetch(
            f"{MATCH_PATH}/{match_external_id}",
            params=None,
            resource_type="match_detail",
            parser=_parse_match_detail,
        )


# -- decoding and primitive parsing ----------------------------------------------


def _decode_json_object(content: bytes, path: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(content)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ProviderResponseError(
            f"Provider response for {path} is not valid JSON."
        ) from exc
    if not isinstance(payload, Mapping):
        raise ProviderResponseError(
            f"Provider response for {path} is not a JSON object."
        )
    return payload


def _require_mapping(payload: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ProviderResponseError(f"Expected an object at '{key}'.")
    return value


def _require_list(payload: Mapping[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ProviderResponseError(f"Expected a list at '{key}'.")
    return value


def _require_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ProviderResponseError(f"Expected a non-empty string at '{key}'.")
    return value.strip()


def _optional_str(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProviderResponseError(f"Expected a string at '{key}'.")
    stripped = value.strip()
    return stripped or None


def _optional_int(payload: Mapping[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProviderResponseError(f"Expected an integer at '{key}'.")
    return value


def _optional_url(payload: Mapping[str, Any], key: str) -> str | None:
    value = _optional_str(payload, key)
    if value is None:
        return None
    lowered = value.lower()
    if not (lowered.startswith("https://") or lowered.startswith("http://")):
        raise ProviderResponseError(f"Expected an HTTP(S) URL at '{key}'.")
    return value


def _require_external_id(payload: Mapping[str, Any]) -> str:
    value = payload.get("id")
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ProviderResponseError("Expected a positive integer identifier at 'id'.")
    return str(value)


def _optional_datetime(payload: Mapping[str, Any], key: str) -> datetime | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProviderResponseError(f"Expected an ISO-8601 string at '{key}'.")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ProviderResponseError(
            f"Value at '{key}' is not a valid ISO-8601 datetime."
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ProviderResponseError(f"Value at '{key}' has no timezone offset.")
    return parsed.astimezone(timezone.utc)


def _require_datetime(payload: Mapping[str, Any], key: str) -> datetime:
    value = _optional_datetime(payload, key)
    if value is None:
        raise ProviderResponseError(f"Expected a datetime at '{key}'.")
    return value


def _optional_date(payload: Mapping[str, Any], key: str) -> date | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ProviderResponseError(f"Expected an ISO-8601 date at '{key}'.")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ProviderResponseError(
            f"Value at '{key}' is not a valid ISO-8601 date."
        ) from exc


def _require_date(payload: Mapping[str, Any], key: str) -> date:
    value = _optional_date(payload, key)
    if value is None:
        raise ProviderResponseError(f"Expected a date at '{key}'.")
    return value


# -- entity parsing --------------------------------------------------------------


def _parse_area(payload: Mapping[str, Any]) -> tuple[str | None, str | None]:
    area = payload.get("area")
    if area is None:
        return None, None
    if not isinstance(area, Mapping):
        raise ProviderResponseError("Expected an object at 'area'.")
    return _optional_str(area, "name"), _optional_str(area, "code")


def _parse_season(payload: Mapping[str, Any]) -> ProviderSeason:
    return ProviderSeason(
        external_id=_require_external_id(payload),
        start_date=_require_date(payload, "startDate"),
        end_date=_require_date(payload, "endDate"),
        current_matchday=_optional_int(payload, "currentMatchday"),
        is_current=payload.get("isCurrent") if isinstance(payload.get("isCurrent"), bool) else None,
    )


def _parse_competition(payload: Mapping[str, Any]) -> ProviderCompetition:
    if not isinstance(payload, Mapping):
        raise ProviderResponseError("Expected a competition object.")
    country_name, country_code = _parse_area(payload)
    seasons_payload = payload.get("seasons")
    if seasons_payload is None:
        # A list resource may omit seasons; an empty tuple is an accurate fact.
        seasons: tuple[ProviderSeason, ...] = ()
    elif isinstance(seasons_payload, list):
        seasons = tuple(_parse_season(item) for item in seasons_payload)
    else:
        raise ProviderResponseError("Expected a list at 'seasons'.")

    current_season = payload.get("currentSeason")
    current: ProviderSeason | None = None
    if isinstance(current_season, Mapping):
        current = _parse_season(current_season)
    elif current_season is not None:
        raise ProviderResponseError("Expected an object at 'currentSeason'.")

    return ProviderCompetition(
        external_id=_require_external_id(payload),
        name=_require_str(payload, "name"),
        code=_optional_str(payload, "code"),
        type=_require_str(payload, "type"),
        country_name=country_name,
        country_code=country_code,
        emblem=_optional_url(payload, "emblem"),
        seasons=seasons,
        current_season=current,
    )


def _parse_team_ref(payload: Mapping[str, Any], *, label: str) -> ProviderTeamRef:
    if not isinstance(payload, Mapping):
        raise ProviderResponseError(f"Expected a team object at '{label}'.")
    country_name, country_code = _parse_area(payload)
    return ProviderTeamRef(
        external_id=_require_external_id(payload),
        name=_require_str(payload, "name"),
        short_name=_optional_str(payload, "shortName"),
        tla=_optional_str(payload, "tla"),
        country_name=country_name,
        country_code=country_code,
        crest=_optional_url(payload, "crest"),
    )


def _parse_team(payload: Mapping[str, Any]) -> ProviderTeam:
    if not isinstance(payload, Mapping):
        raise ProviderResponseError("Expected a team object.")
    country_name, country_code = _parse_area(payload)
    venue = _optional_str(payload, "venue")
    return ProviderTeam(
        external_id=_require_external_id(payload),
        name=_require_str(payload, "name"),
        short_name=_optional_str(payload, "shortName"),
        tla=_optional_str(payload, "tla"),
        country_name=country_name,
        country_code=country_code,
        venue_name=venue,
        founded=_optional_int(payload, "founded"),
        crest=_optional_url(payload, "crest"),
    )


def _parse_score(payload: Mapping[str, Any]) -> ProviderScore | None:
    if not isinstance(payload, Mapping):
        raise ProviderResponseError("Expected an object at 'score'.")
    full_time = payload.get("fullTime")
    half_time = payload.get("halfTime")
    extra_time = payload.get("extraTime")
    penalties = payload.get("penalties")
    if full_time is not None and not isinstance(full_time, Mapping):
        raise ProviderResponseError("Expected an object at 'score.fullTime'.")
    if half_time is not None and not isinstance(half_time, Mapping):
        raise ProviderResponseError("Expected an object at 'score.halfTime'.")
    if extra_time is not None and not isinstance(extra_time, Mapping):
        raise ProviderResponseError("Expected an object at 'score.extraTime'.")
    if penalties is not None and not isinstance(penalties, Mapping):
        raise ProviderResponseError("Expected an object at 'score.penalties'.")
    winner = _optional_str(payload, "winner")
    duration = _optional_str(payload, "duration")
    return ProviderScore(
        home=_optional_int(full_time or {}, "home"),
        away=_optional_int(full_time or {}, "away"),
        ht_home=_optional_int(half_time or {}, "home"),
        ht_away=_optional_int(half_time or {}, "away"),
        winner=winner.upper() if winner else None,
        duration=duration.upper() if duration else None,
        extra_home=_optional_int(extra_time or {}, "home"),
        extra_away=_optional_int(extra_time or {}, "away"),
        penalties_home=_optional_int(penalties or {}, "home"),
        penalties_away=_optional_int(penalties or {}, "away"),
    )


def _parse_match(payload: Mapping[str, Any]) -> ProviderMatch:
    if not isinstance(payload, Mapping):
        raise ProviderResponseError("Expected a match object.")

    competition_payload = _require_mapping(payload, "competition")
    season_payload = _require_mapping(payload, "season")

    # The embedded competition omits its area; the match-level area describes the same
    # competition and is the only source of its country in this resource.
    competition = _parse_competition(competition_payload)
    if competition.country_name is None and competition.country_code is None:
        area_name, area_code = _parse_area(payload)
        if area_name is not None or area_code is not None:
            competition = replace(
                competition, country_name=area_name, country_code=area_code
            )

    score_payload = payload.get("score")
    if score_payload is None:
        score = None
    elif isinstance(score_payload, Mapping):
        score = _parse_score(score_payload)
    else:
        raise ProviderResponseError("Expected an object at 'score'.")

    return ProviderMatch(
        external_id=_require_external_id(payload),
        competition=competition,
        season=_parse_season(season_payload),
        kickoff_utc=_require_datetime(payload, "utcDate"),
        status=_require_str(payload, "status"),
        matchday=_optional_int(payload, "matchday"),
        stage=_optional_str(payload, "stage"),
        group_name=_optional_str(payload, "group"),
        home_team=_parse_team_ref(
            _require_mapping(payload, "homeTeam"), label="homeTeam"
        ),
        away_team=_parse_team_ref(
            _require_mapping(payload, "awayTeam"), label="awayTeam"
        ),
        venue_name=_optional_str(payload, "venue"),
        attendance=_optional_int(payload, "attendance"),
        score=score,
        provider_last_updated=_optional_datetime(payload, "lastUpdated"),
    )


def _participant_assigned(payload: Any) -> bool:
    """A fixture can be published before its participants are decided."""

    if not isinstance(payload, Mapping):
        return False
    identifier = payload.get("id")
    return (
        isinstance(identifier, int)
        and not isinstance(identifier, bool)
        and identifier > 0
    )


def _parse_match_list(payload: Mapping[str, Any]) -> tuple[list[ProviderMatch], int]:
    """Parse a match list, skipping fixtures whose participants are not yet assigned.

    A knockout bracket entry can have ``homeTeam: {id: null, name: null}``. Such a record
    has no identity that can be stored without inventing a team, so it is counted and
    reported by the job instead of aborting the whole list.
    """

    parsed: list[ProviderMatch] = []
    skipped = 0
    for item in _require_list(payload, "matches"):
        if not isinstance(item, Mapping):
            raise ProviderResponseError("Expected a match object.")
        if not (
            _participant_assigned(item.get("homeTeam"))
            and _participant_assigned(item.get("awayTeam"))
        ):
            skipped += 1
            continue
        parsed.append(_parse_match(item))
    if skipped:
        logger.warning(
            "provider returned fixtures without assigned participants",
            extra={
                "event": "provider.matches_without_participants",
                "component": "provider",
                "count": skipped,
            },
        )
    return parsed, skipped


def _parse_statistics(
    team_payload: Mapping[str, Any], *, label: str
) -> ProviderTeamStatistics | None:
    raw = team_payload.get("statistics")
    if raw is None:
        return None
    if not isinstance(raw, Mapping):
        raise ProviderResponseError(f"Expected an object at '{label}.statistics'.")
    metrics: dict[str, float] = {}
    for key, value in raw.items():
        if value is None:
            # A null statistic is unavailable, not zero. Omission keeps the distinction.
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ProviderResponseError(
                f"Statistic '{key}' at '{label}' is not numeric."
            )
        metrics[str(key)] = float(value)
    return ProviderTeamStatistics(
        team_external_id=_require_external_id(team_payload), metrics=metrics
    )


def _parse_match_detail(payload: Mapping[str, Any]) -> ProviderMatchDetail:
    match = _parse_match(payload)
    statistics: list[ProviderTeamStatistics] = []
    for key in ("homeTeam", "awayTeam"):
        team_payload = _require_mapping(payload, key)
        parsed = _parse_statistics(team_payload, label=key)
        if parsed is not None:
            statistics.append(parsed)
    return ProviderMatchDetail(match=match, statistics=tuple(statistics))
