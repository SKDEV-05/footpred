# System Overview

## Purpose and status

This document fixes the architecture of the Football Intelligence Platform after Phase 2 and
the Phase 3 data foundation.

**Implemented in Phase 3:** a Python modular monolith with a read-only REST API, a SQLite
database, Alembic migrations, a provider adapter with a raw-payload archive, normalisation,
identity resolution, validation, a synchronisation engine, and automated tests.

**Not implemented:** prediction or feature engines, ML models, explanations, a frontend,
authentication, subscriptions, production deployment, PostgreSQL, Celery/Redis, and Docker.

Live integration with a real provider is **not verified**: no account or credentials exist.
The adapter is implemented against documented API v4 shapes and tested with synthetic
payloads. See `docs/decisions/ADR-0004-provider-abstraction.md`.

Technology adoption is recorded in ADR-0002; SQLite in ADR-0003. Long-term intelligence stages
remain design intent and are labelled as such.

## System context

| Actor | Interaction | Structural consequence |
| --- | --- | --- |
| Developer/operator | Runs migrations, synchronisation, inspections, tests; owns correctness | One host, CLI-driven operations, no admin UI |
| Future end user | Reads fixtures, results, statistics, and later probabilities | Read-only HTTP surface, explicit uncertainty |
| Data provider | Licensed HTTP API, rate-limited, schema-drifting input | Adapter boundary, archive before parse, quarantine |
| Background worker | Scheduled and manual provider synchronisation | Separate process, same codebase, single instance |
| Upstream reference data | Countries, competitions, seasons, teams, fixtures | Internal identity separate from provider IDs |

External dependencies: provider availability and licensing, Python runtime, host clock and
timezone database, SQLite file durability.

## Constraints

- **Data first.** Stored history and provenance outrank feature count.
- **No invented data.** Missing remains missing; unknown remains unknown.
- **Small team.** One operator must be able to run and recover the system.
- **One host, one database, one worker.** No premature distribution.
- **Reproducibility.** Every canonical row traces to a raw payload and a sync run.
- **Provider independence.** Domain code never imports a vendor module.

## Logical layers (Phase 3)

```
 External provider
        │
        ▼
 Provider adapter ──► raw archive (content-addressed files + raw_payloads)
        │
        ▼
 Normalisation ──► validation ──► identity resolution ──► quarantine
        │
        ▼
 Persistence (SQLite via SQLAlchemy) ──► change log + sync runs/errors
        │
        ▼
 Read-only REST API (/api/v1)
```

The worker and the API are two processes from one codebase. They share the database, not
memory. The API never contacts the provider.

## Implemented runtime components

| Component | Responsibility | Status |
| --- | --- | --- |
| FastAPI application (`app.main`) | HTTP routing, validation, error envelope, OpenAPI | Implemented |
| Configuration (`app.core.config`) | Environment-based settings, secret handling | Implemented |
| Structured logging (`app.core.logging`) | JSON logs, request IDs, redaction | Implemented |
| Database layer (`app.database`) | Engine, SQLite pragmas, sessions, unit of work | Implemented |
| ORM models (`app.models`) | 17 canonical/operational tables | Implemented |
| Repositories (`app.repositories`) | Read queries and pagination | Implemented |
| Provider contract (`app.providers.base`) | Capability-declaring adapter interface | Implemented |
| Reference adapter (`providers.adapters.football_data_org`) | API v4 parsing and endpoints | Implemented, live-unverified |
| HTTP client (`providers.http`) | Timeouts, retries, backoff, rate limiting | Implemented |
| Raw archive (`ingestion.raw_archive`) | Content-addressed payload storage | Implemented |
| Normalisation (`app.normalization`) | Names, enums, UTC, season labels, metrics | Implemented |
| Validation (`app.validation`) | Field, range, and consistency checks | Implemented |
| Identity resolution (`app.ingestion.identity`) | Mapping → natural key → create; ambiguity quarantine | Implemented |
| Ingestion (`app.ingestion.*`) | Competitions, teams, fixtures, results, statistics | Implemented |
| Sync engine (`app.sync.engine`) | Run records, counts, status, error capture | Implemented |
| Scheduler (`app.sync.scheduler`) | APScheduler single-worker periodic jobs | Implemented |
| CLI (`app.cli`) | Manual sync, status, provider check | Implemented |
| Tests (`apps/backend/tests`) | Unit, integration, data-quality, failure | Implemented, locally run |

## Deployment view (Phase 3)

One Linux host:

- one Python virtual environment;
- one SQLite database file (configurable path);
- one API process (`uvicorn app.main:app`);
- one optional worker process (`python -m app.worker`);
- a local directory for raw payloads.

No reverse proxy, container, managed database, or message broker is required for local
operation. The deployment document states the missing production controls.

## Trust boundaries

| Boundary | Crossing | Control |
| --- | --- | --- |
| Provider → HTTP client | Untrusted bytes, credentials | TLS, timeout, size limits, header-only token, redacted logs |
| HTTP client → archive | Untrusted body persisted | Content hash, path confinement, no execution |
| Archive → adapter | Untrusted JSON | Structural validation, typed DTOs, unknown enum rejection |
| Adapter → domain | Normalised data | Explicit translation, no vendor objects |
| Domain → database | Internal writes | Constraints, transactions, single writer |
| API → client | Untrusted requests | Read-only, validated parameters, bounded pages, generic errors |
| Operator → system | Privileged actions | Host access, CLI, no unauthenticated write API |

## Data flow (one fixture)

1. The scheduler or CLI starts a run; a `data_sync_runs` row is committed as `running`.
2. The HTTP client requests a match list within a bounded date range, respecting the rate limiter.
3. The body is written to the raw archive and a `raw_payloads` row records the observation.
4. The adapter parses documented fields into internal DTOs.
5. Normalisation maps statuses, stages, names, times, and metric keys.
6. Validation rejects malformed or inconsistent records.
7. Identity resolution finds the internal competition, season, teams, and match, or creates them.
8. Persistence upserts the fixture and, for final statuses, the result; changed fields append to
   `match_change_log`.
9. The run finalises with counts and status; errors and quarantined records stay visible.
10. The API serves the stored fixture, result, and available statistics with timestamps.

## What remains future work

- Feature construction and point-in-time feature tables.
- Team/match strength models, statistical prediction, calibration, evaluation.
- Explanations and any LLM-assisted wording over verified outputs.
- Frontend, authentication, subscriptions, public deployment.
- PostgreSQL migration, multi-worker scheduling, caching.
- Lineups, events, players, injuries, odds.

These are not claimed as implemented anywhere in the repository.
