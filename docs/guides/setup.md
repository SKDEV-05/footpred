# Setup Guide

**Scope:** run the Phase 3 backend locally from this repository.
**Verified:** 2026-11-13 on Linux with Python 3.15.2. Migration, CLI, and test commands below
were executed; the API was exercised through `TestClient`, not a long-running Uvicorn process.
**Read first:** `AGENTS.md`, `docs/architecture/technology-decisions.md`, `ADR-0002`, `ADR-0003`.

## 1. Prerequisites

| Requirement | Value |
| --- | --- |
| Python | 3.11 or newer (`pyproject.toml`); verified on 3.15.2 |
| Database | SQLite, bundled with Python; no server to install |
| Network | Only needed for a live provider call; tests and the API run offline |
| Provider account | Not required for setup; see `docs/guides/provider-configuration.md` |

No provider account, API key, or paid plan is needed to build, migrate, test, or serve stored
data. A live sync is the only operation that needs credentials.

## 2. Install

Run from the repository root.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.lock
```

`requirements.lock` pins runtime and test dependencies. Do not add packages for a Phase 3 task
without checking `rules/engineering-rules.md` and obtaining approval.

## 3. Configure

```bash
cp .env.example .env
```

The defaults are usable for local development:

- `DATABASE_URL=sqlite+pysqlite:///./data/football.db`
- `RAW_STORAGE_DIR=./data/raw`
- `FOOTBALL_DATA_ORG_TOKEN=` (empty: provider calls are refused, API still works)

Relative paths are resolved from the process working directory. Start commands from the
repository root, or use absolute paths in `.env`.

Every setting is documented in `docs/guides/configuration.md`. `.env` is ignored by
`.gitignore`; never commit it.

## 4. Create the schema

```bash
PYTHONPATH=apps/backend .venv/bin/python -m app.cli migrate
```

This applies Alembic migrations to `head` and prints a JSON result. The `data/` directory is
created by SQLite when the database file is first opened. See
`docs/guides/migrations.md` for the full migration workflow.

## 5. Run the API

```bash
PYTHONPATH=apps/backend .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Process liveness; does not touch the database |
| `GET /api/v1/health` | Readiness, database check, provider configuration, freshness |
| `GET /docs` | OpenAPI UI when `API_DOCS_ENABLED=true` |
| `GET /openapi.json` | Generated OpenAPI document |

There is no write endpoint. Manual synchronisation is a CLI operation. Binding to a public
interface is not approved: Phase 3 has no API authentication or rate limiting.

## 6. Run the tests

```bash
PYTHONPATH=apps/backend .venv/bin/python -m pytest
```

The suite uses temporary SQLite files and synthetic payloads. It makes no network call. See
`docs/guides/testing.md` for what is and is not covered.

## 7. Repository layout

```text
apps/backend/app/
  api/            FastAPI routers, error envelope, response mappers
  core/           settings, exceptions, logging, UTC helpers
  database/       declarative base, engine/session, pragmas
  ingestion/      archive, identity resolution, upserts
  models/         SQLAlchemy models (17 tables)
  normalization/  names, statuses, metric keys
  providers/      provider contract, HTTP client, football-data.org adapter
  repositories/   read queries for the API
  schemas/        Pydantic response models
  sync/           run lifecycle, jobs, scheduler
  validation/     record-level rules
apps/backend/migrations/   Alembic environment and revisions
apps/backend/tests/        unit and integration tests
docs/guides/               operator and contributor guides
```

To use the package without `PYTHONPATH`, install it in editable mode
(`.venv/bin/python -m pip install -e .`). This is optional and was not the verified path.

## 8. What setup does not include

- No Docker, container, or deployment configuration.
- No PostgreSQL service; the application rejects a non-SQLite URL.
- No frontend, authentication, scheduler daemon, or reverse proxy.
- No seed data. The database starts empty, and an empty database is reported as such.
