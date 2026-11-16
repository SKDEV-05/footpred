# API Design

**Status:** Implemented in Phase 3 (read-only) and Phase 5 (analysis `POST`, loopback only).
Example values below are illustrative and are not real football data.
**Decision:** ADR-0005 (read API), ADR-0010 (verified real dataset contract)
**Base path:** `/api/v1`

## 1. Principles

- The API serves the platform's own database. It never calls a provider during a request.
- Provider payload shapes and provider field names are never exposed.
- All responses use explicit Pydantic schemas. Adding a field is backward compatible; renaming
  or removing one requires a new API version.
- Timestamps are ISO-8601 UTC with `Z`.
- Missing values are `null` or an absent metric, never `0`.
- The read API is unauthenticated. It must not be exposed publicly without an authentication
  and rate-limiting layer.
- The single write-shaped endpoint, `POST /analysis/matches/{id}`, persists a derived report.
  It performs no provider I/O, is deterministic for the same stored input, and is restricted to
  private loopback use.
- A probability is published only with its sample size, dataset evidence, model version, and
  out-of-sample evaluation, or not at all.

## 2. Common conventions

### Pagination

All list endpoints accept:

| Parameter | Type | Default | Rules |
| --- | --- | --- | --- |
| `page` | integer | 1 | `>= 1` |
| `page_size` | integer | 25 | `1..100` |

Response envelope:

```json
{
  "items": [],
  "page": 1,
  "page_size": 25,
  "total": 0,
  "has_next": false
}
```

Sorting is deterministic and documented per endpoint. Page-based pagination can drift if data
changes between requests; this is acceptable for reference data and documented as a limitation.

### Errors

```json
{
  "error": {
    "code": "not_found",
    "message": "Fixture 42 does not exist.",
    "details": null,
    "request_id": "b0f0f0f0-0000-4000-8000-000000000000"
  }
}
```

| HTTP | `code` | Meaning |
| --- | --- | --- |
| 404 | `not_found` | Resource does not exist |
| 422 | `validation_error` | Query/path/body validation failed; `details` lists fields |
| 500 | `internal_error` | Unexpected failure; no internal detail is returned |
| 503 | `not_ready` | Database or required dependency unavailable |

`request_id` is generated per request, returned in the `X-Request-ID` response header, and
appears in structured logs. It never contains user data.

### Date and time

- `date_from`, `date_to`, `date` accept `YYYY-MM-DD`.
- `timezone` accepts an IANA name (for example `Europe/London`). Invalid names return 422.
- Stored kickoff times are UTC. Local times are computed only at the response edge.

## 3. Endpoints

### 3.1 Health

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness: process responds, no dependency checks |
| GET | `/api/v1/health` | Minimal readiness: database reachable |

`/api/v1/health` returns `200` when the database answers `SELECT 1`, otherwise `503`. It does
not disclose provider configuration or freshness to anonymous callers. Detailed synchronization
freshness is available from the operator-facing `/api/v1/sync/status` contract.

```json
{
  "status": "ok",
  "database": "ok"
}
```

`/api/v1/sync/status` reports freshness per job type. Its global `data_is_stale` flag requires
recent `fixtures` and `results` work that actually stored records; reference-data or unrelated
empty jobs cannot make match data appear fresh. A `partial` run counts as a refresh because it
stored the records it could — the rejected or skipped remainder stays visible in the run status,
`data_sync_errors`, and `quarantined_records`. A run that stored nothing, or failed, does not
count. `last_successful_sync_at` remains literal: only unqualified successes of the required
datasets set it. Each `per_job_type` entry also carries `last_completed_at`,
`last_completed_status`, and `records_stored`, so a partial refresh is never displayed as a
success. This remains a job-level signal, not a coverage guarantee.

### 3.2 Fixtures

#### `GET /api/v1/fixtures`

| Parameter | Type | Notes |
| --- | --- | --- |
| `date_from` | date | inclusive, UTC date |
| `date_to` | date | inclusive, UTC date |
| `competition_id` | integer | |
| `country_id` | integer | matches the competition's country |
| `season_id` | integer | |
| `team_id` | integer | matches either home or away |
| `status` | enum | canonical match status |
| `q` | string | case/diacritic-insensitive search over stored team and competition names; unsearchable input is a 422 |
| `page`, `page_size` | integer | |

If no narrowing filter is supplied, the endpoint defaults to `date_from = today (UTC)` and
`date_to = today + 7 days` to avoid an unbounded scan. Sort: `kickoff_utc ASC, id ASC`.

Item schema `FixtureSummary`:

```json
{
  "id": 1,
  "competition": {
    "id": 1,
    "name": "Example League",
    "code": "EL",
    "country": {"id": 1, "name": "Examplia", "iso_code": "EX"},
    "emblem_url": "https://crests.example/el.png"
  },
  "season": {"id": 1, "label": "2025/2026"},
  "home_team": {
    "id": 1,
    "name": "Example Home FC",
    "crest_url": "https://crests.example/home.png"
  },
  "away_team": {"id": 2, "name": "Example Away FC", "crest_url": null},
  "kickoff_utc": "2026-11-14T15:00:00Z",
  "status": "scheduled",
  "matchday": 12,
  "stage": "regular_season",
  "venue_name": null,
  "score": null
}
```

`crest_url`, `emblem_url`, and `country` are stored provider values passed through verbatim.
They are `null` when the provider supplies nothing; no placeholder image URL is invented.

`score` is `null` until a final result is stored; it is never `{"home": 0, "away": 0}` by
default.

#### `GET /api/v1/fixtures/today`

| Parameter | Type | Default |
| --- | --- | --- |
| `date` | date | today in the requested timezone |
| `timezone` | IANA string | `UTC` |
| `competition_id` | integer | none |

Returns the fixtures whose kickoff falls inside `[local midnight, next local midnight)` converted
to UTC. The response states the computed window explicitly:

```json
{
  "date": "2026-11-14",
  "timezone": "Europe/London",
  "date_from_utc": "2026-11-14T00:00:00Z",
  "date_to_utc": "2026-11-15T00:00:00Z",
  "items": []
}
```

#### `GET /api/v1/fixtures/{match_id}`

Returns `FixtureDetail`: the summary fields plus `attendance`, `last_synced_at`,
`provider_last_updated`, `statistics_available`, and a `result` object:

```json
{
  "result": {
    "home_score": 2,
    "away_score": 1,
    "ht_home_score": 1,
    "ht_away_score": 0,
    "winner": "home_team",
    "duration": "regular",
    "is_final": true,
    "resolved_at": "2026-11-14T17:05:00Z"
  }
}
```

`result` is `null` when no final result is stored. A missing result is not a 0–0 score.

#### `GET /api/v1/fixtures/{match_id}/statistics`

Returns `200` even when no statistics exist, because "not available" is a data state:

```json
{
  "match_id": 1,
  "available": false,
  "teams": [
    {"team_id": 1, "team_name": "Example Home FC", "metrics": {}},
    {"team_id": 2, "team_name": "Example Away FC", "metrics": {}}
  ]
}
```

When metrics exist, `metrics` maps the normalised metric name to a number. Units are documented
in `docs/data/coverage-matrix.md`. A metric absent from the object is unavailable; a metric with
`0` is a measured zero.

### 3.3 Competitions, countries, and seasons

| Method | Path | Parameters | Response |
| --- | --- | --- | --- |
| GET | `/api/v1/countries` | `page`, `page_size` | `Page[Country]` |
| GET | `/api/v1/competitions` | `country_id`, `q`, `page`, `page_size` | `Page[CompetitionSummary]` |
| GET | `/api/v1/competitions/{competition_id}` | — | `CompetitionDetail` |
| GET | `/api/v1/seasons` | `competition_id`, `page`, `page_size` | `Page[SeasonSummary]` |

`q` is a case-insensitive substring search on the display name, bounded to 100 characters.
A competition detail includes `country`, `type`, `code`, `emblem_url`, and `season_count`; it
does not inline every season, to keep the response bounded.

`/countries` lists only countries that reference data has stored. It is the source for the
country filter; the API never derives a country list from a hard-coded provider catalogue.

### 3.4 Teams

| Method | Path | Parameters | Response |
| --- | --- | --- | --- |
| GET | `/api/v1/teams` | `country_id`, `q`, `page`, `page_size` | `Page[TeamSummary]` |
| GET | `/api/v1/teams/{team_id}` | — | `TeamDetail` |
| GET | `/api/v1/teams/{team_id}/matches` | `date_from`, `date_to`, `page`, `page_size` | `Page[FixtureSummary]` |

Team matches default to the last 365 days when no range is supplied and sort
`kickoff_utc DESC, id DESC`.

### 3.5 Synchronisation status

| Method | Path | Parameters | Response |
| --- | --- | --- | --- |
| GET | `/api/v1/sync/runs` | `job_type`, `status`, `page`, `page_size` | `Page[SyncRunSummary]` |
| GET | `/api/v1/sync/status` | — | `SyncStatus` |

`SyncRunSummary` exposes counts, timestamps, status, and a short error summary. It never exposes
credentials, request headers, or full provider payloads.

`SyncStatus` includes the last successful run, the last run of any status, stale-run count, and
per-job-type last success. It is the operator's primary freshness view.

### 3.6 Match analysis

| Method | Path | Parameters | Response |
| --- | --- | --- | --- |
| POST | `/api/v1/analysis/matches/{match_id}` | `force` (boolean, default `false`) | `MatchAnalysis` |
| GET | `/api/v1/analysis/{analysis_id}` | — | `MatchAnalysis` |
| GET | `/api/v1/analysis/matches/{match_id}/history` | — | `[AnalysisHistoryItem]` |

`POST` generates a report from stored results and persists it. It is not a provider call and
does not mutate football data. A match that does not exist returns `404`; an existing match in a
state that cannot be analysed returns `200` with an abstention status, because the abstention is
a data state rather than a transport error.

Report statuses:

| Status | Meaning |
| --- | --- |
| `READY` | Probabilities were produced from a sufficient, provenance-backed corpus |
| `INSUFFICIENT_DATA` | The verified history is below the documented threshold |
| `DATA_UNAVAILABLE` | The match is finished, started, cancelled, postponed, or the kickoff has passed |
| `ANALYSIS_FAILED` | The calculation or provenance check failed; no numbers are published |

A `READY` report includes:

- `match_overview` and `historical_context` (team records, venue splits, recent form, H2H);
- `statistical_model` with 1X2 probabilities summing to 1.0, expected goals, secondary markets,
  top scorelines, and the fitted `model_parameters`;
- `data_quality` with the classification, provider, dataset id and digest, retrieved and
  observed windows, sample sizes, missing features, and limitations;
- `explanation` (why the expected goals and probabilities exist);
- `evaluation` with the rolling-origin sample size, Brier, log loss, uniform baselines, Brier
  skill, calibration bins, model/feature/evaluation versions, and the test period.

Abstentions carry `error_message` and `limitations`, and leave `statistical_model` null. The API
never fills a missing statistic with zero and never invents a provider payload id.

Idempotency: a repeated `POST` reuses the latest report when the match, status, dataset digest,
model version, and evaluation version match. `?force=true` regenerates and appends a new history
row. Reports are append-only; `GET /analysis/{id}` returns the persisted snapshot unchanged.

Analysis is private and loopback-only. It has no authentication and must not be exposed on a
shared or public network.

## 4. Validation and status codes

- Path and query types are validated by FastAPI/Pydantic. Failures return 422 in the common
  error envelope.
- Unknown query parameters are ignored by FastAPI by default; the documented parameters are the
  contract. Strict rejection of unknown filters is a future option.
- `page_size > 100` returns 422 rather than being silently clamped, so callers see the limit.
- Invalid enum values return 422 with the allowed values.
- Unknown IDs return 404, never an empty object.
- Analysis abstentions return 200 with an explicit status; they are not hidden as 4xx errors.
- No endpoint returns a provider error code or provider message.

## 5. Versioning policy

- `/api/v1` is the contract. Additive fields are allowed within v1.
- Removing a field, changing its type or meaning, or changing default behaviour requires
  `/api/v2` and an ADR.
- The OpenAPI document is generated at runtime and is the machine-readable contract.

## 6. Security notes

- The API must not be exposed publicly: there is no authentication, authorisation, or
  per-client rate limit.
- Analysis reports expose stored real results and are restricted to private loopback use until
  the display/redistribution licence (LIM-006) is resolved.
- No provider token is present in the API process configuration path that could leak through a
  response; secrets are never included in models or logs.
- Error responses omit stack traces and internal identifiers beyond the internal resource ID.
- Request logging redacts `Authorization`, `X-Auth-Token`, cookies, and query parameters whose
  names look secret.

## 7. Deliberately absent endpoints

- `PUT`, `PATCH`, and `DELETE`.
- Users, sessions, subscriptions, payments.
- Raw provider payload download.
- Odds, lineups, events, injuries.
- Any endpoint that promises a guaranteed outcome or a fixed accuracy figure.
