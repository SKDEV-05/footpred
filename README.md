# Football Intelligence Platform

A global football intelligence and match-analysis platform. The goal is not to publish more
predictions, but to publish *explainable, reproducible, evaluated* ones: reliable statistics,
historical performance, mathematically grounded probability estimates, and an honest statement
of uncertainty.

> **Status: Phase 4 offline intelligence accepted; Phase 5 entry gates remain blocked.** The
> Phase 3 backend remains unaccepted pending independent QA; security review permits private
> loopback-only use but rejects public exposure in its current state. Phase 4 adds synthetic-test-only descriptive intelligence,
> probability mathematics, and evaluation mechanics. It is not a fitted model and makes no
> real prediction or accuracy claim. Phase 5, frontend, authentication, and deployment do not
> exist. No live provider call has been made.
> See [`PROJECT_STATUS.md`](PROJECT_STATUS.md) and the
> [Phase 4 audit](docs/research/phase-4-final-audit.md).

## What this repository contains

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Root instructions for every AI agent working here |
| `.opencode/` | Nine agents, twelve skills, six project commands |
| `apps/backend/app/` | FastAPI data backend plus pure offline `intelligence` package |
| `apps/backend/migrations/` | Alembic environment and the initial schema revision |
| `apps/backend/tests/` | Unit and integration suite (synthetic data only) |
| `docs/architecture/` | System overview, components, database, API, data flow, deployment prep |
| `docs/data/` | Provider integration, ingestion, normalisation, identity, sync, coverage matrix |
| `docs/guides/` | Setup, configuration, migrations, provider setup, sync, testing, troubleshooting |
| `docs/decisions/` | Architecture Decision Records (ADR-0001 … ADR-0009) |
| `docs/research/` | Dated research notes with verified facts and open questions |
| `docs/product/`, `docs/football/`, `docs/design/`, `docs/security/` | Product, domain, design, security |
| `memory/` | Concise current-state memory for humans and agents |
| `rules/` | Binding engineering, design, data, AI-usage, and security rules |

## Quick start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
cp .env.example .env
PYTHONPATH=apps/backend .venv/bin/python -m app.cli migrate
PYTHONPATH=apps/backend .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Tests:

```bash
PYTHONPATH=apps/backend .venv/bin/python -m pytest
```

Full instructions: [`docs/guides/setup.md`](docs/guides/setup.md).

## What works

- SQLite schema with 17 tables, foreign keys enforced, WAL where applicable, and Alembic
  migrations verified against the models.
- Provider-neutral adapter contract plus one reference adapter for football-data.org v4.
- Raw payload archive written before parsing, addressed by SHA-256.
- Exact-match identity resolution with provider mappings; ambiguity is quarantined, never merged.
- Idempotent ingestion for competitions, seasons, teams, fixtures, results, and metric statistics.
- Missing data is represented as absence, never zero. Measured zero is stored as zero.
- Sync runs, item errors, quarantine, and stale-run recovery.
- Read-only `/api/v1` API with UTC timestamps, pagination limits, and one error envelope.
- Offline team/match metrics, point-in-time feature construction, quality/abstention,
  Poisson, Dixon-Coles, Elo, market arithmetic, and evaluation mechanics.
- 208 unit and integration tests passing locally (2026-11-14 session).

## What does not exist

- Fitted prediction engine, trained model, calibration, or real historical backtest.
- Machine learning, LLM analysis, or explanations.
- Frontend, authentication, authorisation, subscriptions, betting, or user accounts.
- Live provider verification. No account or token is configured, and coverage, pricing, quota,
  history depth, and licence terms are **UNVERIFIED**.
- PostgreSQL support. A non-SQLite URL is rejected by design.
- Docker, CI/CD, monitoring, backup automation, or production deployment.
- No coverage guarantee. The matrix starts empty: [`docs/data/coverage-matrix.md`](docs/data/coverage-matrix.md).

## Principles

**Data first. Mathematics first. Reliability first. Prediction quality first.
User experience second. Visual decoration last.**

- Evidence before implementation; official sources before opinion.
- The simplest architecture that satisfies the requirement.
- Missing data is reported as missing — never invented, never silently imputed.
- Every prediction must be reproducible, timestamped before kickoff, and evaluated.
- A percentage means a calibrated probability estimate, not a confidence score.
- Language models may explain verified results; they never generate the numbers.

## How to work in this repository

1. Read [`AGENTS.md`](AGENTS.md) — it is binding.
2. Check [`PROJECT_STATUS.md`](PROJECT_STATUS.md) and
   [`memory/current-state.md`](memory/current-state.md) before starting work.
3. Read the rules relevant to your task in [`rules/`](rules/).
4. Use the OpenCode agents and skills rather than improvising a process.
5. Record decisions as ADRs and research as dated reports.

## Documentation map

- Product: [`docs/product/vision.md`](docs/product/vision.md) →
  [`requirements.md`](docs/product/requirements.md) → [`scope.md`](docs/product/scope.md) →
  [`non-goals.md`](docs/product/non-goals.md)
- Architecture: [`docs/architecture/system-overview.md`](docs/architecture/system-overview.md) →
  [`database-design.md`](docs/architecture/database-design.md) →
  [`api-design.md`](docs/architecture/api-design.md) →
  [`data-flow.md`](docs/architecture/data-flow.md)
- Data: [`docs/data/provider-integration.md`](docs/data/provider-integration.md) →
  [`ingestion.md`](docs/data/ingestion.md) →
  [`identity-resolution.md`](docs/data/identity-resolution.md) →
  [`synchronization.md`](docs/data/synchronization.md)
- Operations: [`docs/guides/setup.md`](docs/guides/setup.md) →
  [`configuration.md`](docs/guides/configuration.md) →
  [`running-sync.md`](docs/guides/running-sync.md) →
  [`troubleshooting.md`](docs/guides/troubleshooting.md)
- Decisions: [`docs/decisions/`](docs/decisions/) (ADR-0001 … ADR-0009)
- Current gaps: [`memory/known-limitations.md`](memory/known-limitations.md)
- Report A: [`Phase 2 architecture`](docs/reports/phase-2-architecture-report.md)
- Report B: [`Phase 3 implementation`](docs/reports/phase-3-implementation-report.md)
- Report C: [`Phase 4 final audit`](docs/research/phase-4-final-audit.md)
- Phase 3 security review: [`security review`](docs/reports/phase-3-security-review.md)
- Provider evaluation: [`2026-11-14 provider evaluation`](docs/research/2026-11-14-provider-evaluation.md)
- Next steps: [`memory/next-steps.md`](memory/next-steps.md)

## Phase boundaries

Phase 4 is limited to the pure offline boundary in ADR-0009. It does not authorise model
fitting, real predictions, persistence, API endpoints, ML training, frontend,
authentication, or deployment. Phase 5 requires explicit developer approval.
