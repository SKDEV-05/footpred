# Implementation Plan

**Status as of 2026-11-14:** Phase 2 documents and Phase 3 data foundation are delivered.
Acceptance remains pending: independent QA/security review attempts hit a usage limit.
Phase 4 is not started and requires explicit developer approval.

## 1. What was delivered

| Step | Deliverable | Status |
| --- | --- | --- |
| 1 | Technology selection recorded (ADR-0002, ADR-0003) | Done |
| 2 | Database design and migrations (17 tables) | Done |
| 3 | Provider contract, HTTP client, reference adapter | Done; live-unverified |
| 4 | Raw archive, normalisation, validation, identity resolution | Done |
| 5 | Ingestion for competitions, teams, fixtures, results, statistics | Done |
| 6 | Sync engine, run records, errors, quarantine, scheduler, CLI | Done |
| 7 | Read-only API with pagination, filters, error envelope, OpenAPI | Done |
| 8 | Unit, integration, data-quality, and failure tests (124 passed) | Done; locally run |
| 9 | Documentation, ADRs, guides, memory, status | Done |

Status vocabulary used in the final report: **VERIFIED**, **IMPLEMENTED BUT NOT LIVE-VERIFIED**,
**PARTIALLY IMPLEMENTED**, **NOT IMPLEMENTED**, **BLOCKED**.

## 2. Phase 2 validation gate

| Check | Result |
| --- | --- |
| Technology choices justified against actual requirements | Pass — ADR-0002, ADR-0003 |
| Database entities coherent and normalised | Pass — 17 tables, explicit keys and constraints |
| Provider strategy realistic | Pass with caveat — reference adapter documented; live entitlement unverified |
| Provider IDs separated from internal IDs | Pass — mapping tables, surrogate keys |
| API contracts defined | Pass — `docs/architecture/api-design.md`, generated OpenAPI |
| Synchronisation strategy documented | Pass — ADR-0007, `docs/data/synchronization.md`, `docs/guides/running-sync.md` |
| Security requirements addressed | Pass for Phase 3 scope; public exposure blocked — `docs/architecture/deployment-preparation.md` |
| Testing strategy exists | Locally checked — `docs/guides/testing.md`, executed suite (124 passed); independent review blocked |
| No unnecessary complexity | Pass with caveat — APScheduler, no broker, no cache |
| Consistent with Phase 0/1 research | Pass — no contradiction; SQLite supersedes the PostgreSQL hypothesis by developer instruction |

## 3. Sequence used

1. Read Phase 0/1 context and rules.
2. Fix the decisions that block implementation: stack, database, provider abstraction, API
   contract, identity/provenance model, synchronisation.
3. Design the schema and write the design document before code.
4. Implement configuration, database session, models, and the first migration.
5. Implement the provider contract, HTTP controls, adapter, archive, normalisation, validation,
   and identity resolution.
6. Implement ingestion and the sync engine.
7. Implement the read-only API over repositories.
8. Implement tests, run them, fix defects, and record actual results.
9. Update documentation, memory, and status; produce the final reports.

## 4. Gates and stop conditions

| Condition | Response |
| --- | --- |
| Missing Phase 0 decision | Stop and request approval |
| Paid subscription required to proceed | Stop; do not purchase |
| Destructive migration or data loss | Stop and request approval |
| Provider licence unclear for intended use | Do not publish data; record as blocking |
| New major service required | Stop and request approval |
| Scope expands into prediction, ML, frontend, auth, deployment | Do not proceed |

No paid account was needed, no existing database was destroyed, and no external service was
added. Live verification/publication remain blocked by missing credentials and unclear licensing.
Independent acceptance is also blocked: both review attempts failed at the tool usage limit.

## 5. Phase 4 prerequisites (not started)

- Developer approval of Phase 2/3 outputs and of the provider/licence decision.
- A live provider verification with recorded evidence (access date, plan, competition, season).
- A point-in-time feature table design and leakage test protocol.
- A baseline model and an evaluation protocol fixed before results are inspected.
- A prediction store with immutability and tamper-evidence.
- A decision on competition coverage and calibration segments.
- A decision on whether any live data is in scope.

## 6. Operational runbook to write before production

- Backup and restore rehearsal for the SQLite file and raw archive.
- Log rotation and retention.
- Credential rotation.
- Provider outage and rate-limit escalation.
- Corrupt/ambiguous identity review procedure.
- Migration rollback procedure (where SQLite permits).
- Incident response and data-correction announcement.

## 7. Known gaps carried forward

- Live provider integration and entitlement are unverified.
- Provider pricing, quota, coverage, history depth, and licence are unverified.
- No PostgreSQL compatibility testing.
- No automated backup, monitoring, alerting, or deployment pipeline.
- No API authentication or rate limiting.
- No player, lineup, event, injury, or odds model.
- No coverage guarantee for any competition; the coverage matrix starts empty by design.
