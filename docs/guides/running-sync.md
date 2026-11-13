# Running Synchronisation

**Scope:** manual and scheduled ingestion in Phase 3.
**Status:** implemented and covered by tests with synthetic payloads. No live run has been made
in this repository, because no provider credentials are configured.
**Decision:** `ADR-0007`.

## 1. Two ways to run a sync

| Mode | Command | Use |
| --- | --- | --- |
| Manual, one job | `python -m app.cli sync <job>` | Initial load, configured-window reprocessing, retry after an outage |
| Scheduled worker | `python -m app.worker` | Continuous operation, one process |

There is no HTTP endpoint that triggers a sync. The API is read-only by design.

## 2. Prerequisites

1. The database schema exists: `python -m app.cli migrate`.
2. `FOOTBALL_DATA_ORG_TOKEN` is set.
3. For `competition_details` and `teams`, `SYNC_COMPETITION_IDS` lists provider competition
   codes. These jobs fail with an explicit message when it is empty rather than guessing.
4. The archive directory is writable.

## 3. Jobs

| Job | Fetches | Notes |
| --- | --- | --- |
| `competitions` | Competition list | Reference data; safe to run first |
| `competition_details` | One competition per configured code, including its seasons | Requires `SYNC_COMPETITION_IDS` |
| `teams` | Teams for each configured competition | Requires `SYNC_COMPETITION_IDS`; fixtures also create teams from embedded references |
| `fixtures` | Matches from `today - SYNC_LOOKBACK_DAYS` to `today + SYNC_LOOKAHEAD_DAYS` | Creates/updates fixtures and finished results |
| `results` | Matches with status `FINISHED` from `today - SYNC_LOOKBACK_DAYS` to `today` | Corrects late results within the window |
| `statistics` | Match detail for up to `SYNC_STATISTICS_LIMIT_PER_RUN` recent finished matches | Metric rows; missing stays missing |

Suggested first run:

```bash
PYTHONPATH=apps/backend .venv/bin/python -m app.cli sync competitions
PYTHONPATH=apps/backend .venv/bin/python -m app.cli sync competition_details
PYTHONPATH=apps/backend .venv/bin/python -m app.cli sync fixtures
PYTHONPATH=apps/backend .venv/bin/python -m app.cli sync statistics
```

Each command prints JSON with the run id, status, counters, and failure message. Exit code is
`0` for `success` and `1` for `partial` or `failed`. A `partial` run did useful work; read the
errors before re-running.

## 4. Scheduling

```bash
SYNC_ENABLED=true PYTHONPATH=apps/backend .venv/bin/python -m app.worker
```

- The worker refuses to start when `SYNC_ENABLED` is false or no token is configured. A silent
  no-op would hide a broken deployment.
- One thread executes jobs, so two job types cannot run at once. SQLite has one writer and the
  provider has one request budget; both are process-wide assumptions.
- Intervals: fixtures every `SYNC_INTERVAL_MINUTES`; results every `max(5, interval // 4)`
  minutes; statistics every `max(15, interval)` minutes.
- `coalesce`, `max_instances=1`, and a 300-second misfire grace period prevent duplicates after
  a stall. Missed ticks are acceptable because sync windows overlap and ingestion is idempotent.
- On start, runs still marked `running` beyond `SYNC_STALE_RUN_AFTER_MINUTES` are marked
  `failed` with a `stale_run` error. They are not deleted.

## 5. Run lifecycle

```text
running → success | partial | failed
```

| Status | Meaning |
| --- | --- |
| `success` | Completed; no rejected records and no item errors |
| `partial` | Completed; one or more records were quarantined or skipped. Inspect them |
| `failed` | The job could not complete (provider failure, missing configuration, fatal error) |

Counters: `records_fetched`, `records_created`, `records_updated`, `records_unchanged`,
`records_rejected`, `error_count`. Statistics count metric rows, not matches.

Every run starts before provider work and is finalised afterwards. A run is never left
`running` intentionally.

## 6. Idempotency and corrections

- Re-running the same window is safe. Existing mappings are found, fields compared, and only
  changed fields written.
- An unchanged record still has `last_synced_at` refreshed, because the platform observed it.
- A corrected fixture or result updates the current row and appends to `match_change_log` with
  old and new values.
- An absent optional field never erases a stored value; incoming `None` means "not supplied".
- A match that disappears from a provider list is not deleted. Absence is not a correction.
- Statistics: one row per `(match, team, metric)`. A metric not present in the payload is left
  absent, never set to zero. A measured zero is stored as `0`.

## 7. Inspecting state

```bash
PYTHONPATH=apps/backend .venv/bin/python -m app.cli status
PYTHONPATH=apps/backend .venv/bin/python -m app.cli sweep-runs
PYTHONPATH=apps/backend .venv/bin/python -m app.cli check-provider
```

`status` prints the last ten runs and the last successful completion. `sweep-runs` performs the
stale-run sweep manually. The API exposes the same information read-only at
`GET /api/v1/sync/status` and `GET /api/v1/sync/runs`.

## 8. Quarantine review

Invalid or ambiguous records are stored in `quarantined_records` with entity type, external id,
reason code, message, and a redacted payload excerpt. They are not silently dropped and not
auto-retried.

A review must decide one of:

1. correct the adapter/validation if the provider is right and the platform is wrong;
2. correct or create the internal mapping through a reviewed data operation if identity is the
   problem;
3. leave the record quarantined if the provider data is wrong.

There is no admin UI or automatic resolution in Phase 3. Do not delete evidence to make a
counter look clean.

## 9. Recovery

| Situation | Action |
| --- | --- |
| Worker killed mid-run | Restart it; the startup sweep marks the abandoned run `failed` |
| Provider outage | Let the run fail; the API keeps serving stored data and reports staleness |
| Rate limit | Lower `PROVIDER_REQUESTS_PER_MINUTE`; wait; re-run the failed job |
| Bad deploy wrote wrong data | Stop the worker, inspect `match_change_log` and the raw archive, fix forward with a reviewed correction; do not edit rows ad hoc |
| Disk full | The archive write fails first and raises `ArchiveError`; free space and re-run |

## 10. Limits

- No backfill of arbitrary historical seasons through a dedicated command. The CLI runs the
  configured windows only; widening `SYNC_LOOKBACK_DAYS` is a blunt instrument and consumes the
  rate budget.
- No concurrency. One worker by design.
- No automatic retry of quarantined records.
- No coverage guarantee. See `docs/data/coverage-matrix.md`.
- Outstanding attribution, shootout-validation, statistics-boundary, provenance and HTTP
  limitations are indexed in `memory/known-limitations.md` (GAP-013 onward). They have not
  passed independent review. Resolve/review them before accepting live data.
