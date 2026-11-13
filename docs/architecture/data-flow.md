# Data Flow

**Status:** Implemented for the Phase 3 ingestion path. Long-term intelligence stages are
described as future boundaries only.
**Owners:** data-engineer, backend-architect

## 1. End-to-end path

```
Football provider (HTTP, rate-limited)
        │
        ▼
Provider HTTP client ── timeout, retries, backoff, retry-after, token bucket
        │
        ▼
Raw archive ── body written to content-addressed file + raw_payloads row, BEFORE parsing
        │
        ▼
Provider adapter ── vendor JSON → internal DTOs; unknown fields rejected where strict
        │
        ▼
Normalisation ── names, enums, statuses, UTC times, metric names
        │
        ▼
Validation ── required fields, ranges, score consistency, references
        │
        ▼
Identity resolution ── provider mapping → natural key → create; ambiguity quarantined
        │
        ▼
Persistence ── upsert + change log, one short transaction per record
        │
        ▼
Sync history ── counts, errors, quarantine, freshness
        │
        ▼
Internal REST API (reads database only)
```

No stage is allowed to skip validation or to invent a value. A record either becomes canonical,
or it is recorded as rejected/quarantined with a reason.

## 2. Stage contracts

### 2.1 Provider HTTP client

Inputs: base URL, path, query parameters, credentials from configuration.
Outputs: HTTP status, headers, body bytes, fetch timestamp, final path.

Controls:

- Connect/read timeout per request.
- Bounded retries for timeouts, connection errors, HTTP 429, and 5xx. No retry for 400/401/403/404.
- Exponential backoff with jitter. Numeric `Retry-After` on 429 is capped at 60 seconds;
  HTTP-date values fall back to backoff, and 503 uses backoff.
- Token-bucket rate limiter; the configured default is 10 requests/minute with a burst
  capacity of 10. This is not a strict rolling-minute ceiling.
- Credentials are sent in headers and never logged or stored.

Failure behaviour: after retries are exhausted the client raises a typed provider error. The
sync run records the failure and stops that job; it does not continue with partial assumptions.

### 2.2 Raw archive

Inputs: response bytes and request metadata.
Outputs: `raw_payloads.id` and a file path.

Controls:

- The body is written to `RAW_STORAGE_DIR/<provider>/<hash-prefix>/<sha256>.json` before any
  parsing. An existing identical file is reused; a new observation row is still inserted.
- Request parameters are stored, but the authentication header and any token-like parameter are
  removed.
- The archive write happens before the adapter sees the body. If the archive write fails, the
  item fails; nothing is parsed from unarchived bytes.

Failure behaviour: disk or database failure aborts the item and is surfaced in the run. It is
never swallowed so that parsing can "continue anyway".

### 2.3 Provider adapter

Inputs: archived body plus provider metadata.
Outputs: internal DTOs (`ProviderCompetition`, `ProviderTeam`, `ProviderSeason`, `ProviderMatch`,
`ProviderMatchDetail`).

Controls:

- JSON decode errors and unexpected root shapes raise `ProviderResponseError`.
- Only documented fields are read. A missing optional field remains `None`.
- Provider enums are translated explicitly; an unknown value raises a validation error rather
  than becoming a default.
- Capabilities are declared; an unsupported dataset raises `UnsupportedCapabilityError`.

Failure behaviour: the raw payload is already archived, so the failure can be diagnosed and the
parser fixed without re-fetching. The run records a parsing error.

### 2.4 Normalisation

Inputs: provider DTOs.
Outputs: normalised values ready for validation and persistence.

Rules:

- Names are trimmed and internal whitespace collapsed. Display names keep their original case
  and diacritics; a separate normalised form is used only for exact-match lookup.
- Status, competition type, winner, and duration are mapped to the canonical enums.
- Date-times are parsed as ISO-8601 and converted to UTC. Naive values are rejected.
- Season labels are derived deterministically from the season's start and end dates.
- Statistic keys are converted to snake_case. Values that are `null` are omitted, not zeroed.
- Unknown metrics are preserved as their normalised key, because the provider defines the
  metric set; the coverage matrix documents known units.

Failure behaviour: a value that cannot be normalised is a validation failure for that record.

### 2.5 Validation

Inputs: normalised records.
Outputs: a list of `ValidationIssue`s or acceptance.

Checks include required identifiers, non-empty names, kickoff range, home ≠ away, known enum
values, non-negative scores/attendance/statistics, score/winner consistency for regulation-time
results, and presence of both full-time scores for a final result. Referential checks happen at
resolution/persistence time because they need database state.

Failure behaviour: validation issues quarantine the record and increment `records_rejected`.
The rest of the batch continues. A run with any rejection ends as `partial`.

### 2.6 Identity resolution

Inputs: normalised record plus provider identity.
Outputs: internal entity ID and mapping, or an ambiguity/quarantine outcome.

Order:

1. Existing `(provider, external_id)` mapping.
2. Exact natural key (competition name + country; team normalised name + country; season
   competition + label; match season + home + away + kickoff window).
3. Create a new internal entity and mapping.

Any step producing more than one candidate is ambiguous and is quarantined. Similar names are
never merged automatically. Every new mapping records confidence and observation times.

Mapping uniqueness is per direction: one `(provider, external_id)` maps to one internal entity,
and one internal entity has at most one mapping per provider. If a provider presents a second
external id for an entity it already maps, that is an identity conflict for review, not a second
mapping. It is quarantined rather than silently merging two provider records into one internal row.

Failure behaviour: ambiguity is visible in `quarantined_records` and blocks only that record.

### 2.7 Persistence

Inputs: resolved records.
Outputs: inserted/updated rows, change-log entries, counts.

Controls:

- Provider I/O happens outside any database transaction. The archive commits its own row first.
- Each record is persisted in its own short transaction. A rejected record cannot roll back
  records that already committed.
- Field-level comparison decides `created`, `updated`, or `unchanged`. An update appends a
  `match_change_log` row with previous/new values.
- `last_synced_at` is refreshed even when nothing changed, because it records observation.
- Unique constraints are the final duplicate guard. A constraint violation is caught per record,
  quarantined, and does not abort the run.

Failure behaviour: expected validation, identity and integrity failures roll back that item,
are quarantined, and allow processing to continue. Unexpected errors stop the job and mark it
`failed`; earlier committed items remain stored. A list-fetch failure also stops the job.

### 2.8 Sync history and freshness

Inputs: per-item outcomes.
Outputs: `data_sync_runs`, `data_sync_errors`, `quarantined_records`.

- A run starts as `running`. The engine accepts optional parameters, but CLI/scheduled jobs
  currently do not persist their effective configuration or date windows (a known gap).
- Final status: `success` (no rejections/errors), `partial` (some records rejected but work
  completed), `failed` (job could not complete).
- Counts: fetched, created, updated, unchanged, rejected, error count.
- Stale `running` runs are marked `failed` by the next worker start with an explanatory error.

### 2.9 Internal API

Inputs: HTTP requests.
Outputs: JSON built from canonical tables only.

- No provider call, no sync trigger, no write.
- Missing statistics are returned as `available: false`, not as a 404 or zero values.
- Response `last_synced_at` lets a client see how old the observation is.

## 3. Failure matrix

| Failure | Detection | Handling | Visible as |
| --- | --- | --- | --- |
| Connect/read timeout | HTTPX exception | Retry with backoff; then fail the job | Run `failed`, error row |
| Rate limit (429) | Status + `Retry-After` | Wait and retry within budget; then fail | Run `failed`, error row |
| Auth failure (401/403) | Status | No retry; fail the job | Run `failed`, error row |
| Provider 5xx | Status | Bounded retry; then fail | Run `failed`, error row |
| Invalid JSON | Decode error | No retry; archive retained | Run `failed`, parse error |
| Missing required field | Adapter or domain validation | Adapter parse failure stops the list; domain validation quarantines the item | Failed run or quarantine row |
| Unknown enum value | Normalisation/validation | Quarantine item; continue | Quarantine row with reason |
| Duplicate provider record | Mapping lookup | Update existing record | `records_updated`/`unchanged` |
| Ambiguous identity | Multiple candidates | Quarantine; no merge | Quarantine row |
| Duplicate natural key race | Unique constraint | Catch per item; quarantine | Quarantine row |
| Partial batch | Per-item outcomes | Commit successes, record failures | Run `partial` |
| Database unavailable | Connection/query error | Stop work; recording failure may itself be impossible | Readiness 503 for a failed connectivity check; schema/query failures can be 500 |
| Provider outage | HTTP errors | Retries then failure; API keeps serving stored data | Run `failed`, stale flag |
| Stale data | Freshness threshold | Report `data_is_stale`; never fabricate a refresh | Health/sync status |
| Worker crash mid-run | Startup sweep | Mark stale `running` as `failed` | Run `failed` with reason |

## 4. What the pipeline deliberately does not do

- It does not retry validation failures; the data is wrong, not the network.
- It does not fill missing scores, statistics, or attendance.
- It does not delete a canonical row because a provider stopped returning it.
- It does not merge entities by fuzzy name.
- It does not parse a payload before archiving it.
- It does not call the provider from the API request path.
- It does not compute predictions or features. Those layers are Phase 4 and will consume the
  stored history through explicit, versioned contracts.
