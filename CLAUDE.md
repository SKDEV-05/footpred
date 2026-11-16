# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read first

`AGENTS.md` is binding for every agent. It defines the project's phase boundaries, engineering
philosophy, and approval gates. `PROJECT_STATUS.md` and `memory/current-state.md` track what is
actually implemented. Check both before starting work — the phase boundary (currently Phase 4)
is hard, and crossing it without developer approval is a defect even if the next step seems obvious.

The project is a football intelligence platform. Its goal is *explainable, reproducible, evaluated*
predictions, not more predictions. Data first, mathematics first, reliability first.

## Commands

Everything runs from the repo root with `PYTHONPATH=apps/backend` because the package lives under
`apps/backend/app/` (configured in `pyproject.toml` via `[tool.setuptools.packages.find]` and
`[tool.pytest.ini_options].pythonpath`). Omitting `PYTHONPATH` is the most common failure.

```bash
# Setup (once)
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
cp .env.example .env

# Apply Alembic migrations to head (creates data/football.db)
PYTHONPATH=apps/backend .venv/bin/python -m app.cli migrate

# Run the read-only API (binds loopback only; no auth exists in Phase 3)
PYTHONPATH=apps/backend .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Whole test suite (synthetic data only; no network)
PYTHONPATH=apps/backend .venv/bin/python -m pytest

# One file / one test
PYTHONPATH=apps/backend .venv/bin/python -m pytest apps/backend/tests/integration/test_api.py
PYTHONPATH=apps/backend .venv/bin/python -m pytest -k "statistics" -vv

# CLI operator commands (JSON output)
PYTHONPATH=apps/backend .venv/bin/python -m app.cli status          # recent sync runs
PYTHONPATH=apps/backend .venv/bin/python -m app.cli check-provider   # verify provider creds
PYTHONPATH=apps/backend .venv/bin/python -m app.cli sync fixtures    # run one sync job
PYTHONPATH=apps/backend .venv/bin/python -m app.cli sweep-runs       # mark stale runs failed

# Migration workflow (from repo root)
PYTHONPATH=apps/backend .venv/bin/alembic upgrade head
PYTHONPATH=apps/backend .venv/bin/alembic check          # fails on model/schema drift
PYTHONPATH=apps/backend .venv/bin/alembic revision --autogenerate -m "describe change"

# Verify no metadata drift after a model change
.venv/bin/python -m compileall apps/backend/app apps/backend/migrations apps/backend/tests
```

`pyproject.toml` treats deprecation warnings raised by `app.*` as errors, so a new deprecation in
app code will fail the suite. A `live` marker is registered for future live-provider tests, but
no test carries it yet — do not assume `-m "not live"` skips anything today.

## Architecture

### Two layers, one boundary

The backend has two deliberately separated layers that share a codebase but not a dependency path:

1. **Phase 3 data layer** (`app/ingestion`, `app/providers`, `app/sync`, `app/models`,
   `app/repositories`, `app/api`) — ingests provider data into SQLite and serves it through a
   read-only API. This layer does I/O.
2. **Phase 4 intelligence layer** (`app/intelligence/`) — pure computation. No I/O. It does not
   import any Phase 3 module (database, provider, ingestion, repository, API, sync, worker) and
   performs no reads, writes, clock access, environment lookup, or randomness. It accepts
   immutable values and returns immutable reports. Inputs (rates, policies, cutoffs) are
   *supplied by the caller* — nothing is fitted, estimated, or calibrated.

The intelligence layer is synthetic-test-only: its tests prove the math is correct, not that it
predicts real football. Crossing into fitting/calibration/persistence is Phase 5 and unapproved.

### Dependency direction (enforced by review and tests)

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

Hard rules: `api` never imports `providers` or `ingestion`. `providers` never imports `models`,
`repositories`, or `api`. `models` never imports `providers`. Ingestion owns all writes;
repositories own all reads. The API never contacts a provider during a request.

### Ingestion pipeline (provider → canonical store)

`docs/architecture/data-flow.md` is the authoritative description. The order matters:

provider HTTP client (timeouts, bounded retries, backoff, token bucket) → **raw archive**
(content-addressed file + `raw_payloads` row, written *before* parsing) → adapter (vendor JSON →
internal DTOs; only documented fields read) → normalization → validation → identity resolution →
persistence (one short transaction per record; rejected items don't roll back committed ones).

Key invariants:
- The raw archive is committed before parsing. If archiving fails, the item fails — nothing is
  parsed from unarchived bytes.
- Identity resolution is exact-match only: provider mapping → natural key → create. Ambiguity is
  quarantined, never merged by fuzzy name. A provider presenting a second external id for an
  already-mapped entity is a conflict, not a second mapping.
- Missing data is stored as **absence** (no row), never zero. A measured zero is stored as `0`.
  The API returns `available: false` for missing statistics, not a 404 or zero.
- Sync runs end `success` / `partial` / `failed`; stale `running` runs are swept to `failed` on
  next worker startup.

### Database

SQLite only (ADR-0003). `app/database/session.py` rejects any non-SQLite URL with an explicit
message — PostgreSQL is a future option, not a verified one. Engine pragmas set
`foreign_keys=ON`, WAL for file databases, and a configurable busy timeout. The engine is created
lazily so importing the app doesn't require a database.

Migrations: `apps/backend/migrations/env.py` pulls the URL from app settings (not `alembic.ini`),
so migrations and the app can never target different databases. `render_as_batch=True` is set for
SQLite's ALTER limitations. Adding a model requires importing it in `app/models/__init__.py`
(`env.py` imports `app.models` to register all tables for autogenerate). `alembic check` is the
gate that prevents a model change shipping without a revision. Never edit an applied revision.

### Testing

`apps/backend/tests/conftest.py` gives every test an isolated temporary SQLite file and raw dir
via monkeypatched env vars, then `get_settings.cache_clear()` and `reset_engine()`. The
`database` fixture creates tables from models (not migrations) for the ordinary suite; the
migration test runs Alembic in-process against its own temp DB. All payloads are synthetic and
labelled `SYNTHETIC TEST DATA` (`tests/factories.py`). No test contacts a provider.

A passing suite is evidence about the code under synthetic inputs — not live-provider behaviour,
load, PostgreSQL, or football accuracy.

## Hard constraints (from AGENTS.md and rules/)

These are the ones most likely to bite during normal work; they override convenience:

- **Phase boundary:** Until Phase 5 is explicitly approved, do not fit/train/calibrate/validate a
  model on real data, make a real prediction or performance claim, persist features/predictions,
  modify the SQLite schema for predictions, add ML/LLM paths, create a frontend, add auth/payments,
  add Docker/CI/deployment, or call a live provider without approval and credentials. Ask first.
- **No invented data, ever:** Never fabricate stats, fixtures, lineups, injuries, xG, provider
  pricing, quotas, or citations. Missing stays missing; unknown is `UNVERIFIED`, never a plausible
  guess.
- **Fail visibly (E8):** Never swallow an exception and continue with plausible-looking data, and
  never return a default that could be mistaken for a real measurement. Prefer a visible failure
  or explicit abstention over a confident wrong answer.
- **Reproducibility (E9):** Predictions must be reconstructable from stored inputs, code version,
  and parameters. The intelligence package computes a SHA-256 digest over canonical sorted JSON
  with explicit nulls and UTC timestamps.
- **No live provider call has been made.** `FOOTBALL_DATA_ORG_TOKEN` is empty by design; the CLI
  refuses provider calls rather than faking them. Coverage/pricing/quota/licence are all
  `UNVERIFIED`.

## Working in this repo

- Decisions become ADRs in `docs/decisions/`; research goes to `docs/research/` dated. Update
  affected docs/memory in the same change as the behaviour they describe. Never document an
  unimplemented capability as complete.
- `memory/` is a concise current-state index, not a copy of docs. Update `memory/current-state.md`,
  `memory/decisions.md`, `memory/known-limitations.md`, `memory/next-steps.md` when phase, state,
  decisions, limitations, or next steps change. Supersede, don't rewrite, history.
- `.opencode/` defines nine specialist agents (orchestrator coordinates; specialists are
  delegated by domain — one responsibility per agent). `.opencode/skills/` holds domain skills;
  `.opencode/commands/` holds `/research`, `/plan-phase`, `/architecture-review`,
  `/data-source-review`, `/quality-check`, `/update-memory`. Prefer these over improvising a
  process.
- An author does not approve their own work; independent review is required (E4).

## Documentation map

- Product: `docs/product/` · Architecture: `docs/architecture/` (see `components.md`,
  `data-flow.md`, `phase-4-architecture.md`) · Data: `docs/data/`
- Guides: `docs/guides/setup.md`, `configuration.md`, `migrations.md`, `provider-configuration.md`,
  `running-sync.md`, `testing.md`, `troubleshooting.md`
- Rules: `rules/` (engineering, system-design, data, ai-usage, design, security)
- Current gaps: `memory/known-limitations.md` · Next steps: `memory/next-steps.md`
