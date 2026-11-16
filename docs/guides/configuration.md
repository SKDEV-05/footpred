# Configuration Guide

**Scope:** every environment variable read by the Phase 3 backend.
**Source of truth:** `apps/backend/app/core/config.py` and `.env.example`. This page explains
them; if the two disagree, the code is authoritative.
**Secrets:** `FOOTBALL_DATA_ORG_TOKEN` is wrapped in `SecretStr`, redacted from logs, and never
serialised into an API response or the raw archive.

## 1. How settings are loaded

Settings come from environment variables or a `.env` file in the process working directory.
Names are case-insensitive. Unknown variables are ignored (`extra="ignore"`), so a typo in a
variable name fails silently by using the default: verify the effective value rather than
assuming it was applied. Invalid values (empty database URL, non-positive counts) fail at
startup with a clear error.

`get_settings()` is cached per process. Changing `.env` requires a restart. Tests clear the
cache explicitly.

## 2. Application

| Variable | Default | Meaning |
| --- | --- | --- |
| `APP_NAME` | `Football Intelligence Platform` | OpenAPI title |
| `APP_ENV` | `development` | One of `development`, `test`, `production`. Descriptive only; no behaviour branch depends on it except tests |
| `LOG_LEVEL` | `INFO` | Root log level. Logs are JSON objects on stdout |

## 3. Database

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+pysqlite:///./data/football.db` | Must start with `sqlite`. A non-SQLite URL raises `ConfigurationError` at engine creation |
| `SQLITE_WAL_ENABLED` | `true` | Enables write-ahead logging for file databases. Ignored for in-memory databases |
| `SQLITE_BUSY_TIMEOUT_MS` | `5000` | How long a writer waits for a lock before failing |

SQLite pragmas applied per connection: `foreign_keys=ON`, `busy_timeout`, and (for file
databases) `journal_mode=WAL`. Foreign-key enforcement is not optional. PostgreSQL is not
installed, tested, or supported in Phase 3; see `ADR-0003`.

## 4. Raw archive

| Variable | Default | Meaning |
| --- | --- | --- |
| `RAW_STORAGE_DIR` | `./data/raw` | Root for content-addressed provider payloads |

Relative `DATABASE_URL` paths, `RAW_STORAGE_DIR`, and the `env_file` location are resolved
against the repository root, not the process working directory. The API, the worker, and
`app.cli` therefore read and write the same files when started from anywhere.

Files are written under `<dir>/<provider_code>/<first-two-hash-chars>/<sha256>.<ext>`. The
archive is committed before parsing. Back it up with the database; a database row whose file is
missing is an audit gap. See `docs/data/data-provenance.md`.

## 5. API

| Variable | Default | Meaning |
| --- | --- | --- |
| `API_PAGE_SIZE_DEFAULT` | `25` | Page size when the client omits `page_size` |
| `API_PAGE_SIZE_MAX` | `100` | Maximum accepted page size; larger values are a validation error |
| `API_DOCS_ENABLED` | `true` | Serves `/docs` and `/openapi.json`. Disable to reduce surface in a hosted environment |
| `DATA_STALE_AFTER_MINUTES` | `360` | Age after which readiness and sync status report `data_is_stale=true` |

`API_PAGE_SIZE_DEFAULT` must not exceed `API_PAGE_SIZE_MAX`; startup fails otherwise.

## 6. Provider

| Variable | Default | Meaning |
| --- | --- | --- |
| `FOOTBALL_DATA_ORG_TOKEN` | empty | Provider API token. Empty means "not configured": live calls are refused, not faked |
| `FOOTBALL_DATA_ORG_BASE_URL` | `https://api.football-data.org/v4` | Base URL from the provider's documented quickstart |
| `PROVIDER_REQUESTS_PER_MINUTE` | `10` | Token-bucket rate. The default matches the provider's documented free-plan limit and must not be raised beyond the plan actually held |

The token is optional by design: a read-only API over stored data must work with no provider
entitlement. See `docs/guides/provider-configuration.md` before any live call.

## 7. HTTP behaviour

| Variable | Default | Meaning |
| --- | --- | --- |
| `HTTP_TIMEOUT_SECONDS` | `15.0` | Connect/read timeout per request |
| `HTTP_MAX_RETRIES` | `3` | Retries after the first attempt, for timeout, 5xx, and 429 |
| `HTTP_BACKOFF_BASE_SECONDS` | `1.0` | Base for exponential backoff with jitter |

Authentication failures (401/403) and malformed JSON are not retried: repeating them wastes
the quota and cannot succeed.

## 8. Synchronisation

| Variable | Default | Meaning |
| --- | --- | --- |
| `SYNC_ENABLED` | `false` | The worker schedules nothing unless this is true |
| `SYNC_INTERVAL_MINUTES` | `60` | Base interval for the fixtures job |
| `SYNC_LOOKBACK_DAYS` | `3` | Days before today included in fixture/result windows |
| `SYNC_LOOKAHEAD_DAYS` | `30` | Days after today included in the fixture window |
| `SYNC_COMPETITION_IDS` | empty | Comma-separated provider competition codes. Empty means "all competitions the plan returns", which is rarely what an operator wants |
| `SYNC_STATISTICS_LIMIT_PER_RUN` | `25` | Maximum finished matches whose statistics are requested in one run |
| `SYNC_STALE_RUN_AFTER_MINUTES` | `360` | A `running` run older than this is treated as abandoned and marked failed at the next worker start |

## 9. Identity

| Variable | Default | Meaning |
| --- | --- | --- |
| `IDENTITY_KICKOFF_WINDOW_MINUTES` | `180` | Two records for the same competition, season, and teams are candidates for the same fixture only if kickoffs fall within this window. Ambiguity is quarantined, never merged |

## 10. What must never be configured here

- A second provider is not selected by configuration alone; it needs an adapter and an ADR.
- A non-SQLite database URL is rejected intentionally. Supporting PostgreSQL requires a
  migration plan, test evidence, and developer approval.
- Credentials for other services do not belong in this file. Phase 3 has no other service.
