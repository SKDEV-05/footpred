# ADR-0003 — SQLite as the Phase 3 primary database

**Status:** Instructed by the developer (2026-11-13) and implemented for Phase 3.
**Date:** 2026-11-13
**Owners:** backend-architect, data-engineer
**Related:** ADR-0002, `docs/architecture/database-design.md`

## Context

Phase 1 named PostgreSQL as the leading candidate but selected nothing. The developer's Phase 3
brief fixes SQLite as the initial database and requires SQLAlchemy/Alembic, foreign keys,
centralised configuration, and a design that can later move to PostgreSQL with limited changes.
The expected Phase 3 workload is one writer (the sync worker) and a low-volume read API.

## Decision

- SQLite is the only database implemented and verified in Phase 3.
- The database is a local file whose path comes from `DATABASE_URL` (default
  `sqlite+pysqlite:///./data/football.db`).
- The SQLAlchemy engine enables `PRAGMA foreign_keys=ON`, `PRAGMA journal_mode=WAL` (configurable),
  `PRAGMA synchronous=NORMAL`, and a busy timeout on every connection.
- A single writer is assumed. Sync jobs run in one worker process with
  `max_instances=1`; API requests are read-only.
- Business logic uses SQLAlchemy constructs only. No raw SQLite SQL is used outside the
  connection-setup function and migration scripts.
- Alembic runs with `render_as_batch=True` so SQLite can perform table-altering migrations.
- PostgreSQL is **not installed, configured, or claimed compatible**. Portability is a design
  intention, not a verified property.

## Alternatives considered

1. **PostgreSQL now.** Rejected by the developer's explicit instruction for Phase 3. It also
   adds an external service to operate before any measured need.
2. **SQLite with aiosqlite and async sessions.** Rejected: one writer, no measured concurrency
   benefit; it would add an async driver and complicate transactions.
3. **DuckDB or an embedded analytical store.** Rejected: the Phase 3 workload is transactional
   upserts and point lookups, not columnar analytics.

## Reasons

- Zero operational cost, one file, trivial backup and test setup.
- Adequate for the verified workload shape: one sync writer and read-only API traffic.
- Forces the code to keep persistence behind SQLAlchemy rather than rely on PostgreSQL-specific
  features.

## Consequences

- **Concurrent writes serialise.** A long write transaction blocks other writers. Sync batches
  must be bounded and short; the worker is single-instance.
- **WAL improves reader/writer overlap** but does not make SQLite a multi-writer database.
- **No `JSONB`, range types, or window-function-heavy point-in-time queries** may be assumed.
  Point-in-time history is modelled explicitly with append-only change records.
- **Backups are file copies** and must be taken with SQLite's backup mechanism or while the
  database is quiescent; a raw copy during a write can be inconsistent.
- **Migration to PostgreSQL is not automatic.** It requires a data export/import, sequence
  resets, index review, and a new verification pass.

## When PostgreSQL becomes necessary

Measured evidence of any of the following:

- sustained write contention or `database is locked` errors under the intended workload;
- concurrent workers or multi-user write access;
- database size or query complexity that SQLite cannot serve within the freshness target;
- a requirement for replication, point-in-time recovery, or row-level access control.

A migration then requires a new ADR, a rehearsed export/import, and a full test-suite run
against PostgreSQL. Until that happens, no PostgreSQL compatibility claim may be made.

## Risks

- A single database file is a single point of failure; retention and backup are documented but
  not automated in Phase 3.
- Developers may wrongly treat SQLite as production-equivalent for a public multi-user service.
  The documentation states the limitation explicitly.
