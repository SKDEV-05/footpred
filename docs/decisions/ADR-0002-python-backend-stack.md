# ADR-0002 — Python backend stack for Phase 3

**Status:** Proposed — implemented under the developer's Phase 2/3 brief; final approval pending.
**Date:** 2026-11-13
**Owners:** backend-architect, data-engineer
**Supersedes:** the "under evaluation" status of the Python/FastAPI/SQLAlchemy rows in
`docs/architecture/technology-decisions.md` for Phase 3 only.

## Context

Phase 1 selected no technology. The developer's Phase 2/3 brief fixes Python as the
implementation language, requires a REST API, SQLAlchemy ORM, Alembic migrations, SQLite for
Phase 3, background synchronisation, and a test suite. The system is a single-operator modular
monolith with one database and one worker. Nothing has been measured at scale.

## Decision

Use the following stack for Phase 3:

| Layer | Choice | Version verified in this environment |
| --- | --- | --- |
| Language | Python (3.11+ declared; 3.15.2 used to verify) | 3.15.2 |
| API | FastAPI | 0.162.7 |
| Validation | Pydantic v2 + pydantic-settings | 2.14.3 |
| Persistence | SQLAlchemy 2.x ORM | 2.1.8 |
| Migrations | Alembic | 1.20.1 |
| HTTP client | HTTPX (sync) | 0.28.1 |
| Scheduling | APScheduler (in-process, single worker) | 3.11.3 |
| Tests | pytest (+ FastAPI TestClient via HTTPX) | 9.2.0 |
| Database | SQLite via the standard `sqlite3` driver | see ADR-0003 |

The application is synchronous. FastAPI runs synchronous endpoints in its thread pool. There is
no async database driver, no Celery, no Redis, no Docker requirement, and no frontend
dependency.

## Alternatives considered

1. **Async stack (async SQLAlchemy, async HTTPX, async endpoints).** Rejected for Phase 3:
   concurrency is bounded by one SQLite writer and a low-volume scheduler, so async adds
   complexity without a measured benefit. Revisit if request concurrency or provider fan-out is
   measured as a bottleneck.
2. **Flask + SQLAlchemy.** Viable, but loses the typed request/response contract and generated
   OpenAPI document that the brief requires.
3. **Django + DRF.** A larger framework with admin and ORM conventions that pull in components
   the project does not need; the modular boundaries are easier to keep explicit in FastAPI.
4. **Celery + Redis for background jobs.** Rejected because there is one worker and no measured
   queue pressure. APScheduler plus persisted sync-run records covers the requirement; Celery
   remains a documented upgrade trigger.
5. **Pandas/Polars in the ingestion path.** Not needed: ingestion is per-record validation and
   upsert, not bulk dataframe transformation. Adding a dataframe dependency now would violate
   the "no unnecessary dependency" rule.

## Reasons

- One language covers API, ingestion, and the future statistical engine.
- Pydantic gives one validation mechanism at the provider and API boundaries.
- SQLAlchemy keeps the persistence layer database-independent enough to move to PostgreSQL
  later without rewriting business logic (ADR-0003).
- Alembic makes schema changes reviewable and reversible where SQLite permits.
- HTTPX supports injectable transports, which is what makes provider tests runnable without a
  paid API or credentials.
- APScheduler is the smallest scheduler that satisfies "periodic sync in one worker".

## Consequences

- Dependencies are pinned in `pyproject.toml` and recorded in `requirements.lock`
  (`pip freeze`), per engineering rule E6.
- The API is read-only in Phase 3. Any write endpoint would need authentication and CSRF/abuse
  design first.
- Synchronous code keeps debugging simple but caps throughput; this is acceptable until
  measured.
- APScheduler state is in-process, so a restart loses only the next tick, not data. Sync runs
  are persisted in the database and are the source of truth for what happened.

## Risks

- Version drift: the declared floor (3.11) is not exercised in CI in this phase; only 3.15.2
  was verified locally. **UNVERIFIED for 3.11–3.14.**
- SQLite's single-writer model constrains concurrent sync jobs. See ADR-0003.
- FastAPI/Pydantic major-version changes can alter validation error shapes; the error envelope
  is normalised by an explicit handler and tested.

## Revisit conditions

Measured API latency, scheduler contention, or a need for multiple concurrent workers; a
second deployable; or a requirement for async provider fan-out.
