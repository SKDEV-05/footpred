# Technology Decisions

## Purpose and status

This document records candidate technologies and their adoption status. Phase 1 selected
nothing; Phase 3 adopted the stack below by developer instruction and ADR. Adoption means
"implemented and tested in this repository", not "proven at production scale".

Status values: **Adopted (Phase 3)**, **Deferred**, **Not adopted**, **Under evaluation**.
Version numbers are those actually installed and verified on 2026-11-13 in the development
environment; they are not a support-window claim.

## Selection criteria

Fit to the actual problem; maturity and maintenance activity; operational simplicity for one
operator; team familiarity; quality of the data/statistics ecosystem; licensing compatibility;
exit cost; performance only where it constrains a measured workload. Popularity is not a
criterion.

## Adopted for Phase 3

| Technology | Layer | Purpose | Version verified | Decision |
| --- | --- | --- | --- | --- |
| Python | Language/runtime | API, ingestion, future modelling | 3.15.2 | Adopted; declared floor 3.11 |
| FastAPI | API framework | HTTP API, validation, OpenAPI | 0.162.7 | Adopted (ADR-0002) |
| Pydantic v2 | Validation | Provider and API contracts | 2.14.3 | Adopted |
| pydantic-settings | Configuration | Environment-based settings | 2.16.3 | Adopted |
| SQLAlchemy 2 | Persistence | ORM, transactions, portable queries | 2.1.8 | Adopted |
| Alembic | Migrations | Versioned schema changes | 1.20.1 | Adopted |
| SQLite | Database | Phase 3 canonical store | stdlib `sqlite3` | Adopted (ADR-0003) |
| HTTPX | HTTP client | Provider transport, mockable tests | 0.28.1 | Adopted |
| APScheduler | Scheduling | Single-worker periodic sync | 3.11.3 | Adopted (ADR-0007) |
| pytest | Testing | Unit/integration/data tests | 9.2.0 | Adopted |
| Uvicorn | ASGI server | Local API process | 0.54.0 | Adopted for local run |

## Deferred or not adopted

| Technology | Status | Reason / trigger |
| --- | --- | --- |
| PostgreSQL | Deferred by developer instruction | Phase 3 uses SQLite. Revisit on measured write contention, concurrent workers, replication, or access-control needs. **Compatibility unverified.** |
| Redis | Not adopted | No cache or broker requirement; cache would not be authoritative |
| Celery | Not adopted | One worker; APScheduler plus persisted run records is sufficient. Revisit for durable queues/multiple workers |
| Pandas | Deferred | Not needed for per-record validation/upsert. Revisit for bulk feature construction |
| Polars | Deferred | Same; requires a measured volume benchmark |
| NumPy | Deferred | Phase 4 statistics dependency |
| scikit-learn | Deferred | Phase 4 baselines/calibration |
| XGBoost / LightGBM | Deferred | Phase 4, only after a baseline is beaten out-of-sample |
| PyTorch | Deferred | Evidence-gated, later |
| Docker | Deferred | No environment drift or second target yet; not required for one host |
| Next.js / TypeScript | Deferred | No frontend; contract not stable for a client |
| LLM runtime | Not adopted | Prohibited in the numerical prediction path; no explanation engine yet |

## Leading architecture choice

A modular monolith: one FastAPI application, one SQLite database, one optional scheduler process,
one codebase. This satisfies the Phase 3 workload without a broker, cache, container, or
distributed system. Boundaries are enforced by module imports and tested by review.

The choice fails if measured API latency, write contention, or multi-worker scheduling cannot be
met vertically. The first response is measurement, not a new service.

## Why SQLite now

The developer fixed SQLite for Phases 2–3. It is sufficient for one writer and read-only API
traffic, costs nothing to operate, and keeps backup and tests simple. It is **not** equivalent to
PostgreSQL for concurrent writes or multi-user production use. The migration trigger and the
required work are in ADR-0003 and `docs/architecture/deployment-preparation.md`.

## Why not Redis or Celery yet

Redis is a cache and broker; it must never hold canonical state. No measured latency or queue
pressure justifies it. Celery brings durable retries and multiple workers at the cost of a broker
and more operations. APScheduler plus `data_sync_runs` covers the current need; the upgrade
trigger is jobs that must survive restarts, multiple workers, or retry logic rewritten twice.

## Why not a dataframe library in ingestion

Ingestion is record-oriented: validate one match, resolve identity, upsert. Pulling a dataframe
library in now would add a dependency and a second data model without serving a requirement.
The feature builder in Phase 4 may adopt one library; the choice must be recorded in an ADR with
a benchmark on stored data.

## Decision triggers

| Candidate | Evidence that would justify adoption | Prerequisite |
| --- | --- | --- |
| PostgreSQL | Write contention, concurrent workers, replication, or row-level access control | New ADR, data export/import rehearsal, full test run on PostgreSQL |
| Redis | Measured read latency or queue throughput SQLite cannot meet | Invalidation design; never authoritative |
| Celery | Jobs outlive restarts, need multiple workers, or retry logic is reimplemented | Broker operations plan, idempotency audit |
| Pandas/Polars | Feature build or backfill exceeds memory/time budget on real data | Benchmark on the actual dataset; one primary library |
| XGBoost/LightGBM | A statistical baseline is beaten out-of-sample | Fixed split protocol, calibration comparison |
| PyTorch | Demonstrated gain on sequence/relational structure | Data volume, inference cost, explanation path |
| Docker | Environment drift or a second target host | Pinned image; no secrets baked in |
| Next.js/TypeScript | API contract stable and UX scheduled | Client types generated from OpenAPI |

## Evidence note

Framework versions above were observed by importing the installed packages, not copied from a
marketing page. Provider pricing, quotas, coverage, and licensing remain **UNVERIFIED**; see
`docs/data/providers-research.md` and the dated research note for the reference provider.

## Related documents

- ADR-0002 (stack), ADR-0003 (SQLite), ADR-0004 (provider), ADR-0007 (synchronisation)
- [system-overview.md](system-overview.md), [components.md](components.md),
  [database-design.md](database-design.md), [quality-attributes.md](quality-attributes.md)
