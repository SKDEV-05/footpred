# Current State

**Last updated:** 2026-11-14
**Phase:** 4 — Offline synthetic-test-only intelligence foundation
**Status:** Implemented; Phase 4 final audit written
(`docs/research/phase-4-final-audit.md`). Independent sign-off and developer acceptance
pending. Phase 3 acceptance and live provider integration remain pending.

## Completed

| Area | Artefacts |
| --- | --- |
| Root instructions | `AGENTS.md` (Phase 3 boundaries) |
| Overview and status | `README.md`, `PROJECT_STATUS.md` |
| Agents / skills / commands | `.opencode/` — 9 agents, 12 skills, 6 commands |
| Architecture docs | `docs/architecture/` — 10 documents plus `deployment-preparation.md` |
| Data docs | `docs/data/` — provider integration, ingestion, normalization, identity, sync, coverage |
| Guides | `docs/guides/` — setup, configuration, migrations, provider, sync, testing, troubleshooting |
| ADRs | `docs/decisions/` — ADR-0001 … ADR-0009 |
| Research | `docs/research/2026-11-13-football-data-org-api.md`, `docs/research/phase-4-final-audit.md` |
| Backend | `apps/backend/app/` — FastAPI, SQLAlchemy, ingestion, sync, CLI, worker |
| Schema | 17 tables; Alembic revision `0001`; no metadata drift |
| Intelligence | `apps/backend/app/intelligence/` — pure offline calculations, no I/O |
| Tests | `apps/backend/tests/` — 208 passing locally (58 Phase 3 unit, 66 integration, 84 Phase 4) |
| Memory | 5 files in `memory/` |
| Rules | 6 binding documents in `rules/` |

## Implemented capabilities

- SQLite database with `foreign_keys=ON`, WAL for file databases, busy timeout, and a
  fail-closed guard for any non-SQLite URL.
- Provider-neutral adapter contract and one reference adapter for football-data.org v4, built
  from publicly documented shapes.
- HTTP client with timeout, bounded retries, exponential backoff, `Retry-After`, token bucket,
  response-size cap, and typed errors.
- Raw payload archive: content-addressed files plus `raw_payloads` rows, committed before parsing.
- Exact-match identity resolution through provider mapping tables; ambiguity and conflicting
  second ids are quarantined, never merged.
- Idempotent ingestion for competitions, seasons, teams, fixtures, results, and statistics.
- Statistics stored one row per `(match, team, metric)`; absent metric has no row, measured zero
  is `0`.
- Sync engine with run lifecycle, counts, item errors, quarantine, and stale-run sweep.
- APScheduler worker (single thread) and operator CLI (`migrate`, `status`, `check-provider`,
  `sweep-runs`, `sync <job>`).
- Read-only `/api/v1` API over stored data, with pagination limits, filters, UTC timestamps, and
  one error envelope.
- Structured JSON logging with credential redaction.
- Immutable synthetic observation/request/dataset contracts with canonical input and
  configuration digests.
- Team form, explicit venue splits, H2H and competition-context calculations that exclude
  neutral fixtures from home/away baselines.
- Versioned point-in-time feature registry (version 2), explicit missing values and
  sample-quality abstention.
- Supplied-parameter Poisson (explicit overflow categories), Dixon-Coles (mass-conserving) and
  Elo mathematical primitives.
- 1X2 bounds with unresolved mass, double chance, over/under, BTTS, and correct-score output.
- Proper scores, one-vs-rest reliability summaries, rolling-origin folds and an explicit
  train/calibration/test/final-holdout partition.

## Latest local verification (2026-11-14 session)

- `python -m pytest`: 208 passed, 1 third-party Starlette deprecation warning.
- Phase 3: 58 unit + 66 integration = 124 tests, unchanged.
- Phase 4: 84 tests covering contracts, metrics, features, quality, reports, Poisson,
  Dixon-Coles, Elo, market invariants, evaluation, and the no-I/O boundary.
- Compilation: application, migrations and tests, exit 0.
- `python -m app.cli migrate` on a scratch database: 17 tables plus `alembic_version`.
- `alembic check`: no drift between models and migrated schema.
- CLI `status` and `sweep-runs`: JSON output, exit 0.
- CLI `check-provider` without a token: exit 2 with an explicit message, no request sent.
- API exercised through `TestClient`; no load, soak, or long-running server test.
- **No live provider call was made.** No token or account exists.
- No Phase 4 database write, migration, or schema change exists.

## Structure

```text
AGENTS.md  README.md  PROJECT_STATUS.md  pyproject.toml  requirements.lock  alembic.ini
.opencode/{agents,skills,commands}/
apps/backend/{app,migrations,tests}/
docs/{product,architecture,football,data,design,security,research,decisions,guides}/
memory/  rules/
```

## Not implemented (deliberately)

- Goal-rate/rho/Elo parameter fitting, calibration, real backtests, prediction persistence.
- Real-world prediction generation or performance claims.
- ML training, LLM analysis, explanation generation.
- Frontend, UI, branding.
- Authentication, authorisation, subscriptions, payments, betting.
- Docker, CI/CD, monitoring, alerting, public deployment.
- PostgreSQL support; non-SQLite URLs are rejected.
- Backup automation, restore rehearsal, migration rollback procedure.
- Coverage guarantee for any competition or season.

## Current blockers

- Provider credentials: none configured; live verification is **BLOCKED**.
- Provider selection, plan, competition coverage, and licence: pending developer decisions.
- Public display of provider-derived data: unresolved (`LIM-006`).
- Independent Phase 4 sign-off: the final audit is written by the implementing agent;
  delegated reviews were partial. Self-review is not acceptance.
- Remaining integrity/transport gaps: `memory/known-limitations.md`, GAP-013 onward.

## Next

Obtain developer review of `docs/research/phase-4-final-audit.md`, then independent sign-off
and explicit Phase 4 acceptance. Phase 5 remains unapproved. See `memory/next-steps.md`.
