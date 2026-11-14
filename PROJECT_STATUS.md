# Project Status

**Project:** Football Intelligence Platform
**Current phase:** Phase 4 — Offline synthetic-test-only intelligence foundation
**Phase 4:** Accepted by the developer on 2026-11-14 as an offline, synthetic-test-only
foundation
**Phase 5:** Not approved; entry gates pending
**Last updated:** 2026-11-14

## Phase summary

| Phase | Scope | Status |
| --- | --- | --- |
| 1 | Foundation: instructions, agents, skills, commands, docs, rules, memory | Complete |
| 2 | System architecture: stack, database, provider abstraction, API, identity, sync | Complete |
| 3 | Python backend, SQLite schema, ingestion, read-only API, tests, guides | **QA FAIL; private development only with conditions; public/live exposure rejected** |
| 4 | Offline intelligence, mathematical primitives, evaluation mechanics | **Accepted by developer (synthetic-only); Phase 3 review pending** |
| 5 | Fitted prediction system, persistence/API, frontend | **Not started; not approved** |

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
| Tests | 124 Phase 3 unit/integration tests (58 unit + 66 integration) passing locally; full suite is 208 | VERIFIED (local run) |
| Provenance / freshness | Archive and run metadata exist; exact replay and dataset freshness incomplete | PARTIALLY IMPLEMENTED |
| Independent QA review | **FAIL**; 208 local tests pass, but GAP-013…GAP-020 remain open | FAIL |
| Independent security review | **ACCEPT WITH CONDITIONS** for private loopback-only use; **REJECT** public exposure | PARTIALLY IMPLEMENTED |
| Provider evaluation | Read-only comparison completed; no entitlement or licence approved | IMPLEMENTED BUT NOT VERIFIED |
| Live provider integration | Real credential, coverage, statistics, licence | **BLOCKED** |
| Coverage guarantee | Any competition or season | **NOT IMPLEMENTED** (matrix empty by design) |
| API auth / rate limiting | — | **NOT IMPLEMENTED** |
| Backup automation | — | **NOT IMPLEMENTED** |
| PostgreSQL support | — | **NOT IMPLEMENTED** (not supported) |
| Offline team/match intelligence | Pure descriptive metrics and reports | VERIFIED (synthetic tests only) |
| Feature engineering | Point-in-time, versioned features and provenance IDs | VERIFIED (synthetic tests only) |
| Probability primitives | Supplied-rate Poisson and Dixon-Coles score matrices | VERIFIED mathematically; NOT REAL-WORLD VALIDATED |
| Elo primitive | Deterministic sequential supplied-policy rating updates | VERIFIED mathematically; NOT REAL-WORLD VALIDATED |
| Evaluation mechanics | Brier/log loss, reliability bins, rolling-origin folds | VERIFIED mathematically; no historical run |
| Prediction fitting / calibration / frontend | — | **NOT IMPLEMENTED** (Phase 5) |

## Verification evidence

Latest local verification: 2026-11-14 session (process logs use the host's UTC clock).
Earlier CLI refusal/sweep checks were executed on 2026-11-13.

| Check | Result |
| --- | --- |
| `PYTHONPATH=apps/backend .venv/bin/python -m pytest` | 208 passed, 1 third-party deprecation warning |
| Phase 4 intelligence tests | 84 passed |
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
evidence of provider compatibility, and the Phase 4 tests are not evidence of football accuracy,
calibration, or predictive usefulness.

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
| ADR-0008 | Phase 4/5 entry gates | Approved — gates partly unmet |
| ADR-0009 | Pure offline intelligence boundary | Approved — implemented, amended after review |

"Proposed — implemented" means the code exists and is tested, but the decision still needs
developer sign-off.

## Deliberately not built

- Fitted or calibrated prediction model, real historical backtest, performance claim.
- Prediction persistence, write API, machine learning, LLM analysis, generated explanations.
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
| — | Phase 3 independent QA review | FAIL; remediation required; acceptance withheld |
| — | Phase 3 security conditions | S-01…S-19; public exposure rejected until addressed |
| — | Provider evaluation and selection | Research complete; licence and coverage remain unverified |

No paid subscription was purchased, no provider account was created, and no provider terms were
accepted on the developer's behalf.

## Next

1. Remediate or explicitly risk-accept the QA findings F-01…F-10 and GAP-013…GAP-020.
2. Remediate or explicitly risk-accept S-01…S-19; public/shared-network exposure remains
   rejected.
3. Decide provider, plan, competitions, seasons, and the public-display licence using the
   completed provider evaluation.
4. Record one bounded live verification and populate the coverage matrix with evidence.
5. Obtain a fresh independent QA/security review after remediation.
6. Do not begin Phase 5 implementation until every entry gate in ADR-0008 passes.

Reports: [A — Phase 2](docs/reports/phase-2-architecture-report.md),
[B — Phase 3](docs/reports/phase-3-implementation-report.md), and
[C — Phase 4 audit](docs/research/phase-4-final-audit.md),
[Phase 3 QA review](docs/research/phase-3-independent-qa-review.md),
[Phase 3 security review](docs/reports/phase-3-security-review.md), and
[security reassessment](docs/security/phase-3-security-reassessment.md),
[remediation roadmap](docs/research/phase-3-remediation-roadmap.md), and
[provider evaluation](docs/research/2026-11-14-provider-evaluation.md).

See [`memory/next-steps.md`](memory/next-steps.md) and
[`memory/known-limitations.md`](memory/known-limitations.md).
