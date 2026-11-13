# Project Status

**Project:** Football Intelligence Platform
**Current phase:** Phase 3 — Data foundation backend (delivered; acceptance pending)
**Phase 4:** Not started; requires explicit developer approval
**Last updated:** 2026-11-14

## Phase summary

| Phase | Scope | Status |
| --- | --- | --- |
| 1 | Foundation: instructions, agents, skills, commands, docs, rules, memory | Complete |
| 2 | System architecture: stack, database, provider abstraction, API, identity, sync | Complete |
| 3 | Python backend, SQLite schema, ingestion, read-only API, tests, guides | Delivered; reviews blocked, live provider unverified |
| 4 | Prediction engine, evaluation, frontend, deployment | **Not started** |

Status vocabulary for deliverables: **VERIFIED**, **IMPLEMENTED BUT NOT LIVE-VERIFIED**,
**PARTIALLY IMPLEMENTED**, **NOT IMPLEMENTED**, **BLOCKED**.

## Phase 3 deliverables

| Area | Deliverable | Status |
| --- | --- | --- |
| Configuration | Typed settings, `SecretStr` token, `.env.example` | VERIFIED |
| Database | SQLite engine, foreign keys, WAL, busy timeout, fail-closed non-SQLite URL | VERIFIED |
| Schema | 17 SQLAlchemy models, constraints, indexes | VERIFIED |
| Migrations | Alembic initial revision; `upgrade head`; no metadata drift | VERIFIED |
| Provider contract | Capability declaration, DTOs, typed errors | VERIFIED |
| Reference adapter | football-data.org v4 parsing, documented fields only | IMPLEMENTED BUT NOT LIVE-VERIFIED |
| HTTP client | Tested transport paths; buffered size check and quota/retry limits remain | PARTIALLY IMPLEMENTED |
| Raw archive | Content-addressed file plus `raw_payloads` row, before parsing | VERIFIED |
| Normalisation | Names, enums, statuses, season labels, metric keys | VERIFIED |
| Validation | Core checks tested; shootout/statistics-boundary gaps remain | PARTIALLY IMPLEMENTED |
| Identity | Mapping → exact natural key → create; ambiguity and conflicts quarantined | VERIFIED |
| Ingestion | Core upserts tested; team-area attribution and provenance gaps remain | PARTIALLY IMPLEMENTED |
| Statistics model | One row per `(match, team, metric)`; missing ≠ zero | VERIFIED |
| Sync engine | Runs, counts, per-item transactions, errors, quarantine, stale-run sweep | VERIFIED |
| Scheduler / worker | Wiring inspected; invalid startup tested, successful scheduling unverified | IMPLEMENTED BUT NOT LIVE-VERIFIED |
| CLI | `migrate`, `status`, `check-provider`, `sweep-runs`, `sync <job>` | VERIFIED |
| API | Read-only `/api/v1`, filters, pagination, error envelope, UTC | VERIFIED |
| Tests | 124 unit/integration tests passing locally | VERIFIED (local run) |
| Provenance / freshness | Archive and run metadata exist; exact replay and dataset freshness incomplete | PARTIALLY IMPLEMENTED |
| Independent QA/security reviews | Both attempts failed at the tool usage limit; no findings returned | BLOCKED |
| Live provider integration | Real credential, coverage, statistics, licence | **BLOCKED** |
| Coverage guarantee | Any competition or season | **NOT IMPLEMENTED** (matrix empty by design) |
| API auth / rate limiting | — | **NOT IMPLEMENTED** |
| Backup automation | — | **NOT IMPLEMENTED** |
| PostgreSQL support | — | **NOT IMPLEMENTED** (not supported) |
| Prediction / ML / frontend | — | **NOT IMPLEMENTED** (Phase 4) |

## Verification evidence

Latest local verification: 2026-11-14 session (process logs use the host's UTC clock).
Earlier CLI refusal/sweep checks were executed on 2026-11-13.

| Check | Result |
| --- | --- |
| `PYTHONPATH=apps/backend .venv/bin/python -m pytest` | 124 passed, 1 third-party deprecation warning |
| `python -m compileall` over application, migrations, tests | Exit 0 |
| `python -m app.cli migrate` on a scratch database | Created all 17 tables plus `alembic_version` |
| `alembic check` | No drift between models and migrated schema |
| `python -m app.cli status` | JSON output, exit 0 |
| `python -m app.cli sweep-runs` | JSON output, exit 0 |
| `python -m app.cli check-provider` without a token | Exit 2 with an explicit message; no request sent |
| `python -m app.cli sync fixtures` without a token | Exit 1 with a clear configuration error |
| API | Exercised through FastAPI `TestClient`; no long-running server was benchmarked |
| Provider | **No live call was made**; no token exists |

The test suite uses synthetic payloads labelled `SYNTHETIC TEST DATA`. A passing suite is not
evidence of provider compatibility.

## Architecture decisions

| ADR | Decision | Status |
| --- | --- | --- |
| ADR-0001 | Project foundation | Proposed — per its recorded status |
| ADR-0002 | Python backend stack | Proposed — implemented |
| ADR-0003 | SQLite primary database | Proposed — implemented |
| ADR-0004 | Provider abstraction | Proposed — implemented, live-unverified |
| ADR-0005 | Read-only API contract | Proposed — implemented |
| ADR-0006 | Identity and provenance | Proposed — implemented |
| ADR-0007 | Synchronisation model | Proposed — implemented |

"Proposed — implemented" means the code exists and is tested, but the decision still needs
developer sign-off.

## Deliberately not built

- Prediction model, probability engine, features, backtests, evaluation harness.
- Machine learning, LLM analysis, generated explanations.
- Frontend, UI components, design system.
- Authentication, authorisation, subscriptions, payments, betting.
- Live-score push, news, notifications.
- Docker, CI/CD, monitoring stack, public deployment.
- PostgreSQL, message broker, cache, multi-worker execution.

## Blockers and pending decisions

| ID | Item | Impact |
| --- | --- | --- |
| PD-002 | Final provider selection | Adapter is a reference implementation, not a commitment |
| PD-003 | Competition and season coverage | Coverage matrix cannot be populated |
| PD-004 | Data budget / plan | Pricing, quota, and history depth remain unverified |
| LIM-006 | Display/redistribution licence | Public data display is blocked |
| — | Provider credentials | All live verification is blocked |

No paid subscription was purchased, no provider account was created, and no provider terms were
accepted on the developer's behalf.

## Next

1. Restore review access or obtain human QA/security review; no independent approval exists.
2. Developer review of Phases 2 and 3.
3. Address the recorded data-integrity/transport gaps and decide provider, plan, competitions,
   and licence position before an authorised live verification.
4. Only then consider Phase 4.

Reports: [A — Phase 2](docs/reports/phase-2-architecture-report.md),
[B — Phase 3](docs/reports/phase-3-implementation-report.md).

See [`memory/next-steps.md`](memory/next-steps.md) and
[`memory/known-limitations.md`](memory/known-limitations.md).
