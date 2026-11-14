# Components

**Status:** Phase 3 modules are implemented in `apps/backend/app/`. Phase 4 offline modules are
implemented but synthetic-test-only. Fitting, persistence, delivery, and interface work remain
design-only. Components are modules in one codebase, not services.

## 1. Module catalogue

| Component | Responsibility | Owns data | Phase | Status |
| --- | --- | --- | --- | --- |
| `core.config` | Typed environment configuration, secret wrapping, fail-fast validation | none | 3 | Implemented |
| `core.logging` | JSON logs, request correlation, redaction | none | 3 | Implemented |
| `core.exceptions` | Typed application errors and API mapping | none | 3 | Implemented |
| `database.session` | Engine, SQLite pragmas, session factory, unit of work | connection state | 3 | Implemented |
| `models` | Canonical entities, provider mappings, provenance, statistics | schema definition | 3 | Implemented |
| `repositories` | Read queries, filters, pagination | none (reads) | 3 | Implemented |
| `providers.base` | Adapter contract and capability declaration | none | 3 | Implemented |
| `providers.http` | Timeouts, retries, backoff, rate limiting, typed errors | none | 3 | Implemented |
| `providers.adapters.*` | Vendor transport and parsing | adapter config | 3 | Implemented (live-unverified) |
| `ingestion.raw_archive` | Content-addressed payload storage | raw payload files + rows | 3 | Implemented |
| `normalization` | Names, enums, UTC, season labels, metric keys | none | 3 | Implemented |
| `validation` | Field, range, and cross-field checks | none | 3 | Implemented |
| `ingestion.identity` | Internal identity and provider mappings | mapping tables | 3 | Implemented |
| `ingestion.*` | Competitions, teams, fixtures, results, statistics | canonical tables | 3 | Implemented |
| `sync.engine` | Run lifecycle, counts, status, error capture | sync tables | 3 | Implemented |
| `sync.scheduler` | Periodic single-worker scheduling | schedule config | 3 | Implemented |
| `cli` | Manual operations and operator status | none | 3 | Implemented |
| `api.v1` | Read-only HTTP contract | none | 3 | Implemented |
| Feature builder | Point-in-time descriptive features, no persistence | none | 4 | Implemented (synthetic-only) |
| Team/match intelligence | Form, venue splits, context, H2H, quality | none | 4 | Implemented (synthetic-only) |
| Statistical primitives | Poisson, Dixon-Coles, Elo, market arithmetic | none | 4 | Implemented (mathematically verified) |
| Evaluation mechanics | Proper scores, reliability, temporal folds | none | 4 | Implemented (no historical run) |
| Model fitting and calibration | Deterministic probabilities and versioned maps | prediction tables | 5 | Not implemented |
| Prediction persistence/API | Stored, immutable prediction records | prediction tables | 5 | Not implemented |
| Explanation engine | Read-only reasons over stored outputs | explanation records | 6 | Not implemented |
| Frontend | Presentation | none | 5 | Not implemented |

## 2. Boundaries and dependency direction

```
api ──► repositories ──► models/database
 │
 └──► schemas

cli / worker ──► sync ──► ingestion ──► providers
                    │          │
                    │          ├──► normalization
                    │          ├──► validation
                    │          └──► identity ──► repositories/models
                    └──► raw_archive
```

Rules enforced by review and tests:

- `api` never imports `providers` or `ingestion`.
- `providers` never imports `models`, `repositories`, or `api`.
- `models` never imports `providers`.
- Ingestion may import all of the above; nothing imports ingestion except `sync` and `cli`.
- No module writes another module's tables through private code paths; ingestion owns writes,
  repositories own reads.

## 3. Component contracts

### Provider adapter

- Methods: `fetch_competitions`, `fetch_competition`, `fetch_seasons`, `fetch_teams`,
  `fetch_matches`, `fetch_match_detail`.
- Unsupported operations raise `UnsupportedCapabilityError`.
- Parsing returns internal DTOs; vendor JSON does not leave the adapter except in the archive.
- No adapter writes to the database.

### Ingestion

- Accepts a session, a provider, a run, and explicit parameters.
- Returns counts (`fetched`, `created`, `updated`, `unchanged`, `rejected`).
- Never swallows a failure; per-item failures are recorded and counted.
- Idempotent: the same input twice yields the same canonical state.

### Repositories

- Expose typed query methods with bounded pagination.
- Return ORM entities or lightweight projections; never expose sessions to the API layer.
- No provider calls and no writes.

### Sync engine

- Creates and finalises `data_sync_runs`.
- Converts unexpected exceptions into a visible `failed` run with a redacted summary.
- Does not retry validation failures and does not continue after an unrecoverable job error.

### API

- Read-only in Phase 3.
- One error envelope, generated OpenAPI, bounded pages.
- No raw payloads, no provider fields, no credentials.

## 4. Failure ownership

| Failure | Owner | Visible state |
| --- | --- | --- |
| Provider transport/retry | `providers.http` | Typed error → failed run |
| Parsing/schema drift | Adapter | Parse error → failed run |
| Invalid record | `validation` | Quarantine + rejected count |
| Ambiguous identity | `ingestion.identity` | Quarantine + rejected count |
| Duplicate constraint | Ingestion/persistence | Quarantine + rejected count |
| Database outage | `database.session` | Failed run; API 503 |
| Stale data | `sync` + health endpoint | `data_is_stale`, last success timestamp |
| API contract misuse | `api` | 404/422 in the common envelope |

## 5. Deliberately not separated

Provider adapters, ingestion, and the sync engine are in-process modules, not services. They
have different rate-of-change and failure characteristics but no independent scaling or trust
boundary that would justify a network contract today. Extraction remains possible because the
adapter contract and ingestion functions are explicit.
