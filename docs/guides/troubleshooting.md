# Troubleshooting

**Scope:** predictable failures in the Phase 3 backend and what each one actually means.

## `ConfigurationError: Only SQLite is supported`

**Cause:** `DATABASE_URL` does not start with `sqlite`. The application fails closed rather than
pretending portability has been verified.

**Action:** use a SQLite URL such as `sqlite+pysqlite:///./data/football.db`. PostgreSQL support
requires a migration plan, test evidence, and approval (`ADR-0003`).

## `alembic.ini not found`

**Cause:** `python -m app.cli migrate` locates the repository root from the installed source
tree. Running from a copied script or a partial checkout can break that assumption.

**Action:** run from a full checkout, or use `PYTHONPATH=apps/backend .venv/bin/alembic upgrade
head` from the repository root.

## CLI ignores my `.env`

**Cause:** `.env` is resolved from the process working directory, not from the package
location.

**Action:** start commands from the repository root, or use absolute paths in `.env`. Confirm
with `python -m app.cli status`, which prints whether a provider is configured.

## `check-provider` exits 2

**Cause:** `FOOTBALL_DATA_ORG_TOKEN` is empty. This is not a bug; the command refuses to fake a
verification.

**Action:** set the token, or accept that live sync is unavailable. The API and tests work
without it.

## `SYNC_COMPETITION_IDS is empty`

**Cause:** `competition_details` and `teams` need explicit provider competition codes.

**Action:** set a comma-separated list, for example `SYNC_COMPETITION_IDS=PL,BL1`. Codes are
provider-specific; verify them from the provider's own competition list, not from memory.

## `database is locked`

**Cause:** SQLite allows one writer. A second process (API plus worker plus a manual CLI sync)
can contend. Long transactions make it worse.

**Action:** keep one worker; avoid running a manual sync while the worker is mid-run; increase
`SQLITE_BUSY_TIMEOUT_MS` only after understanding the contention. Do not switch to autocommit as
a workaround.

## `ArchiveError` / permission denied

**Cause:** `RAW_STORAGE_DIR` is missing, not a directory, or not writable.

**Action:** fix the path and permissions, then re-run. The archive is written before parsing and
is required evidence; do not skip it.

## Sync status is `partial`

**Cause:** at least one record was quarantined or skipped. Useful work usually completed.

**Action:** inspect `data_sync_errors` and `quarantined_records` for the run, decide whether the
adapter, the mapping, or the provider data is wrong, and re-run only after the cause is fixed.
Re-running without a fix produces the same quarantine.

## Sync status is `failed`

**Cause:** the job could not complete: missing configuration, provider error, authentication
failure, invalid payload, or a fatal database error.

**Action:** read `error_summary`, the `data_sync_errors` rows, and the JSON log line for the
run. A 401/403 is a credential problem and is not retried. A 429 means the request budget is
exhausted; lower the rate and wait.

## `data_is_stale: true`

**Cause:** no successful run exists, or the last success is older than
`DATA_STALE_AFTER_MINUTES`.

**Action:** this is a correct report, not an error to suppress. Run a sync if credentials
exist. If they do not, the platform genuinely has no fresh data and must say so.

## API returns 422 for a valid-looking request

**Cause:** the error envelope's `details` names the failing field. Common cases: inverted date
range, unknown IANA timezone, `page_size` above `API_PAGE_SIZE_MAX`.

**Action:** read `error.details[].field` and `error.details[].code`. The message is intentionally
stable and does not leak internals.

## API returns 404 for a fixture that exists

**Cause:** the id is internal, not a provider id. Provider ids are never exposed as the primary
key.

**Action:** list fixtures through `/api/v1/fixtures` and use the returned `id`.

## Statistics are missing for a finished match

**Cause (expected):** the provider did not return statistics for that match or plan, or the
statistics job has not reached it yet (`SYNC_STATISTICS_LIMIT_PER_RUN` bounds each run).

**Action:** check `statistics_available` and the raw archive. Missing is reported as missing;
it is never filled with zeros. Do not "fix" it by imputing values.

## Times look shifted

**Cause:** the API returns UTC with a `Z` suffix. Local calendar windows are computed only when
the client passes `date` and `timezone` to `/api/v1/fixtures/today`.

**Action:** convert in the client. The database stores UTC; SQLite does not preserve offsets.

## Tests pass but a live call fails

**Cause:** the suite never contacts a provider. It proves parsing and persistence against
documented shapes, not current entitlement or availability.

**Action:** run `check-provider`, inspect the archived response, and record the outcome. A live
failure does not invalidate the unit tests, and a passing suite does not prove the integration.

## Where to look

| Evidence | Location |
| --- | --- |
| Application logs | stdout, one JSON object per line, includes `request_id` or `sync_run_id` |
| Sync runs and counts | `data_sync_runs`; `GET /api/v1/sync/runs` |
| Item errors | `data_sync_errors` |
| Rejected records | `quarantined_records` |
| Provider response bytes | `RAW_STORAGE_DIR` plus `raw_payloads` |
| Accepted corrections | `match_change_log` |
