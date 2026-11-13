# Report B — Phase 3 Data Foundation Implementation

**Date:** 2026-11-13; close-out updated 2026-11-14
**Scope:** Python backend, SQLite schema, provider adapter, ingestion, sync, read-only API,
tests, guides, documentation.
**Outcome:** implemented and locally verified. Live provider integration is **BLOCKED**.
**Review status:** both independent review attempts failed at the tool usage limit.
Neither returned findings or sign-off. Human or restored specialist review is still required.

Status vocabulary: **VERIFIED**, **IMPLEMENTED BUT NOT LIVE-VERIFIED**, **PARTIALLY
IMPLEMENTED**, **NOT IMPLEMENTED**, **BLOCKED**.

## 1. What was built

| Area | Deliverable | Status |
| --- | --- | --- |
| Configuration | Typed settings, `.env.example`, `SecretStr` token, fail-closed validation | VERIFIED |
| Logging | JSON logs, request/run ids, credential redaction | VERIFIED |
| Database | SQLite engine, `foreign_keys=ON`, WAL, busy timeout, non-SQLite rejection | VERIFIED |
| Schema | 17 models: reference, matches, results, statistics, provider mappings, provenance | VERIFIED |
| Migrations | Alembic `0001`, `upgrade head`, no metadata drift | VERIFIED |
| Provider contract | Capability flags, DTOs, typed errors | VERIFIED |
| HTTP client | Core paths tested; buffered-size, retry and quota limitations remain | PARTIALLY IMPLEMENTED |
| Reference adapter | football-data.org v4 competitions, seasons, teams, matches, detail | IMPLEMENTED BUT NOT LIVE-VERIFIED |
| Raw archive | SHA-256 file plus `raw_payloads` row, before parsing, sensitive params stripped | VERIFIED |
| Normalisation | Names, enums, statuses, season labels, metric keys | VERIFIED |
| Validation | Core fields/enums tested; shootout and statistics-boundary gaps remain | PARTIALLY IMPLEMENTED |
| Identity | Mapping → exact natural key → create; ambiguity and conflicts quarantined | VERIFIED |
| Ingestion | Core upserts tested; attribution/provenance gaps remain | PARTIALLY IMPLEMENTED |
| Statistics | One row per `(match, team, metric)`; missing ≠ zero | VERIFIED |
| Sync engine | Runs, counts, per-item transactions, errors, quarantine | VERIFIED |
| Scheduler | APScheduler wired, one thread; invalid startup configuration tested; successful scheduling not soak-tested | IMPLEMENTED BUT NOT LIVE-VERIFIED |
| CLI | `migrate`, `status`, `check-provider`, `sweep-runs`, `sync <job>` | VERIFIED |
| API | Read-only `/api/v1`: health, fixtures, today, statistics, reference, sync status | VERIFIED |
| Error contract | One envelope with code, message, details, request id | VERIFIED |
| Tests | 124 unit and integration tests passing locally | VERIFIED (local run) |
| Provenance, freshness, statistics validation | Basic paths exist; outstanding integrity gaps documented | PARTIALLY IMPLEMENTED |
| Independent QA/security reviews | Both blocked by tool usage limit | BLOCKED |
| Guides | Setup, configuration, migrations, provider, sync, testing, troubleshooting | VERIFIED |
| Live provider use | Credentials, coverage, statistics, licence | **BLOCKED** |
| Coverage guarantee | Any competition or season | **NOT IMPLEMENTED** (matrix empty) |
| API auth / rate limiting | — | **NOT IMPLEMENTED** |
| Backup / monitoring / deployment | — | **NOT IMPLEMENTED** |
| Prediction / ML / frontend | — | **NOT IMPLEMENTED** (Phase 4) |

## 2. Verification evidence

Latest verification: 2026-11-14 session from the repository root (host logs use UTC).

```text
PYTHONPATH=apps/backend .venv/bin/python -m pytest
→ 124 passed, 1 third-party Starlette deprecation warning
```

| Check | Result |
| --- | --- |
| Migration on a scratch database | 17 tables plus `alembic_version` |
| `alembic check` | No schema drift |
| Migration idempotency | Repeat `upgrade head` succeeds |
| CLI `status`, `sweep-runs` | JSON, exit 0 |
| CLI `check-provider` with no token | Exit 2, explicit message, no request |
| CLI `sync fixtures` with no token | Exit 1, clear configuration error |
| API | Exercised through `TestClient` |
| Live provider call | **None made** |
| Compilation | Application, migrations and tests compiled; exit 0 |

Not measured: throughput, latency, concurrent load, long-running worker stability, disk usage at
real data volume, restore time.

## 3. Defects found and fixed during implementation

| Defect | Resolution |
| --- | --- |
| `repositories/base.py` used `select` without importing it | Import added; pagination tests pass |
| `FixtureUpsert` lacked `created`/`updated`/`unchanged`, so sync counts could not be incremented | Outcome properties added |
| Statistics ingestion did not pass the archive row id | `raw_payload_id` threaded from the fetched detail |
| A second external id could map to an already-mapped entity | `_assert_mapping_available` added; identity conflict is quarantined |
| CLI `migrate` resolved the repository root one level too high | `parents[4]` corrected to `parents[3]` |
| Token-bucket test assumed no burst, contradicting the design | Test corrected; a separate burst test added |
| `sync_teams` existed but was not registered as a job | Registered in `JOB_HANDLERS`; tests added for success and missing configuration |
| Documentation claimed a bounded batch transaction | Corrected to per-item transactions and identity-conflict behaviour |
| Pagination field validator ran before the maximum was available, accepting invalid defaults | Three failing cases reproduced; model-level validator added, four configuration tests pass |

## 4. Test coverage by boundary

| Boundary | Covered |
| --- | --- |
| Normalisation and validation | Exact keys, unknown enums, score consistency, missing values |
| HTTP client | Retry, backoff, 429, `Retry-After`, bucket burst, size cap, typed errors |
| Adapter parsing | Documented shapes, null vs zero, undocumented structure rejected |
| Identity | Mapping reuse, natural key, ambiguity, one-mapping-per-provider rule |
| Ingestion | Idempotency, corrections, change log, absent field does not erase |
| Statistics | Metric rows, measured zero, missing metric, colliding keys rejected |
| Sync | Success, partial, failure, quarantine, stale-run sweep, teams job |
| API | Filters, pagination limits, UTC format, null score, empty metrics, 404/422/405 |
| Database | FK enforcement, WAL, busy timeout, non-SQLite rejection |
| Migrations | Table set, no drift, idempotent upgrade |
| Archive | Bytes, metadata, deduplication of file, redaction, unwritable root |
| CLI / worker | Process entry points and refusal paths |

Not covered: live provider, PostgreSQL, concurrent load, browser/UI, security penetration,
backup/restore, soak testing. See `docs/guides/testing.md` §5.

## 5. Data correctness posture

- A missing value is represented by absence. A measured zero is stored as zero.
- A result row is created only for final statuses with a supplied score.
- An absent optional field never erases a stored value.
- A match is never deleted because a provider stopped returning it.
- An ambiguous or conflicting identity is quarantined, never merged.
- An update to a fixture or result appends a change-log entry.
- The raw payload is archived before parsing and can be re-examined.

Known gaps: statistics corrections and reference-data renames have no change-log entry. Both are
recorded in `memory/known-limitations.md` (GAP-001, GAP-002).

Further close-out inspection found incomplete run/raw linkage and dataset freshness, buffered
rather than streaming size enforcement, quota/retry caveats, competition-area attribution to
teams, shootout-score validation and statistics-boundary gaps. These remain **PARTIALLY
IMPLEMENTED**, not verified-complete: see GAP-013 through GAP-020. They require review and
regression coverage before accepting live data. Independent review is blocked, not passed.

## 6. Security posture

Implemented:

- token in `SecretStr`; redaction in logs; no secret in API responses;
- sensitive request parameters stripped from the archive;
- internal error details not exposed to clients;
- read-only API, no write surface;
- SQLAlchemy parameter binding, no string-built SQL;
- foreign keys enforced at the database level.

Not implemented:

- authentication, authorisation, rate limiting, TLS, CORS policy;
- secret manager integration;
- audit log beyond sync history and match change log;
- dependency scanning or vulnerability monitoring.

Consequence: the API is not safe for public exposure. Binding to loopback or a trusted network is
mandatory until auth exists. See `docs/architecture/deployment-preparation.md`.

## 7. Operational posture

- JSON logs on stdout with request/run correlation and redaction.
- Durable sync state in `data_sync_runs`, `data_sync_errors`, `quarantined_records`.
- Stale `running` runs are marked failed at worker start.
- Freshness is reported honestly as `data_is_stale`.
- No metrics endpoint, alerting, dashboard, backup automation, or restore rehearsal.
- One worker only. Manual CLI sync should not run concurrently with a scheduled job.

## 8. Blockers

| Blocker | Effect |
| --- | --- |
| No provider token or account | Live verification and all coverage claims are blocked |
| Provider selection, plan, and licence undecided (PD-002/003/004/009) | Cannot populate the coverage matrix or commit to competitions |
| Licence for display/redistribution unresolved (LIM-006) | No public data presentation |
| No independent review yet | Delivery is not signed off |

No paid subscription was purchased, no account was created, and no provider terms were accepted.

## 9. Explicit non-delivery

- No prediction engine, probability model, feature table, backtest, or evaluation report.
- No ML training, LLM analysis, or generated explanation.
- No frontend, branding, or design system.
- No authentication, subscriptions, payments, or betting.
- No Docker, CI/CD, monitoring stack, or hosted environment.
- No PostgreSQL support or compatibility claim.
- No player, lineup, event, injury, venue entity, or odds model.
- No coverage guarantee for any competition, season, or metric.
- No fabricated data: all fixtures are synthetic and labelled; the database starts empty.

## 10. Final status

| Question | Answer |
| --- | --- |
| Does the backend implement the Phase 3 data foundation? | Core paths delivered; outstanding integrity/operational gaps documented |
| Was it verified locally? | Yes: 124 tests, migrations, CLI paths; not exhaustive acceptance |
| Is the provider integration live-verified? | No — **BLOCKED** |
| Is any coverage or accuracy claimed? | No |
| Is it safe to expose publicly? | No |
| Is Phase 4 started? | No |
| Is developer approval recorded? | Not yet |

Phase 3 artefacts are delivered, but acceptance is not complete. Independent review and the
recorded integrity gaps remain outstanding. Phase 4 must not begin without explicit approval;
provider, licence and coverage questions remain unresolved.
