# Phase 3 Remediation Roadmap

**Date:** 2026-11-14
**Purpose:** Prioritized remediation plan from the independent QA review and security reassessment.
This document does not authorize implementation, live provider use, or public exposure.

## Critical

| ID | Required action | Components | Dependencies | Acceptance criteria | Verification |
| --- | --- | --- | --- | --- | --- |
| R-01 | Keep public/shared-network exposure rejected; implement an approved security boundary before reconsideration | `app/main.py`, API, deployment | Developer/security approval; auth design; TLS/edge decision | Non-loopback serving is refused or demonstrably protected by approved auth/authz, limits, TLS, headers and audit logging | Startup/network and authorization tests plus deployment review; maps S-03 |
| R-02 | Remove raw sync exception text from API-visible records | sync engine, sync schemas/mappers/API | Safe error-code contract | SQL, paths, URLs, provider values and credentials never appear in unauthenticated responses | Sentinel exception integration test; maps S-01/F-10 |
| R-03 | Stream provider responses and abort at the configured byte limit | provider HTTP client | Transport test strategy; provider policy | Bytes are bounded before full buffering; oversize responses close cleanly and produce bounded failure state | Chunked transport test; maps GAP-013/S-02/F-01 |
| R-04 | Validate statistics and fixture participant membership at ingestion | statistics ingestion, validation, sync quarantine | Agreed metric semantics and score/participant contract | Invalid values and non-participant teams are quarantined; valid records continue; no partial invalid writes | Integration tests for NaN/inf/negative/oversize/wrong team; maps GAP-019/F-07/F-08 |
| R-05 | Define regulation, extra-time, shootout, awarded and abandoned result semantics | provider DTOs, validation, models, ingestion | Provider contract and football-domain decision | Results preserve regulation and settlement meaning without false draw/winner values | Regression matrix for normal draw, shootout, extra-time, awarded and abandoned; maps GAP-018/F-06 |
| R-06 | Repair archive integrity and retention controls | raw archive, provenance, operations | Licence decision and retention owner | Existing files are re-hashed; equal-size tampering fails; retention/deletion and permission policy is explicit | Tamper, failure-response, retention and permission tests; maps GAP-020/S-04/F-09 |

## High

| ID | Required action | Components | Dependencies | Acceptance criteria | Verification |
| --- | --- | --- | --- | --- | --- |
| R-07 | Persist effective sync windows, configuration and raw payload linkage | sync engine/jobs, provenance models | Approved provenance contract; migration approval if schema changes | A run can be replayed from stored effective inputs and rejected records link to payload evidence | Controlled-clock repeat run and quarantine linkage test; maps GAP-015/F-03 |
| R-08 | Make freshness and counters dataset-specific and semantically stable | sync status API, sync engine/jobs | Freshness policy and counter definitions | Empty/reference/statistics jobs cannot falsely mark fixtures/results fresh; counters have named units | Matrix of stale/recent/empty/failed jobs and multi-metric counters; maps GAP-016/F-04 |
| R-09 | Stop competition area from becoming team identity country | fixture ingestion, identity resolution | Provider team-country semantics | International fixture teams retain correct country provenance and do not duplicate on competition area | Cross-country synthetic fixture test; maps GAP-017/F-05 |
| R-10 | Quarantine all provider-boundary validation failures | normalization, identity, statistics, sync jobs | Exception taxonomy and field limits | Malformed provider text/metrics never aborts a whole run; safe quarantine evidence is retained | Malformed-record continuation tests; maps GAP-019/S-05/F-07 |
| R-11 | Enforce HTTPS/host policy and disable ambient proxy/TLS environment influence by default | config, provider HTTP client | Chosen provider and approved development override policy | Credentials cannot be sent to an unexpected host or plain HTTP by default | Configuration and client tests; maps S-10/S-11 |
| R-12 | Define public-display licence and provider entitlement before live data | provider decision, legal/product docs, coverage matrix | Developer budget/contact approval; named competitions/seasons | Provider, plan, licence, named entitlement and coverage evidence are recorded; no fabricated coverage | Authenticated bounded verification and coverage-matrix evidence; maps LIM-006…008 |

## Medium

| ID | Required action | Components | Dependencies | Acceptance criteria | Verification |
| --- | --- | --- | --- | --- | --- |
| R-13 | Bound page, IDs, timezone, search and request IDs; escape LIKE wildcards | API dependencies, repositories, time/error handling | API compatibility decision | Oversized, malformed and wildcard inputs return bounded safe errors and cannot force unbounded scans | API contract tests; maps S-06…S-09 |
| R-14 | Wire `APP_ENV` to fail-closed docs and security defaults | config, app factory | Deployment environment policy | Production defaults disable docs and reject unsafe configuration unless explicitly approved | Settings/app-factory tests; maps S-15 |
| R-15 | Minimize health and logging disclosure; establish retention/access controls | health API, logging, operations | Private/public exposure decision and licence policy | Health exposes liveness only; logs are allowlisted, bounded, retained and access-controlled | Response/redaction/retention tests; maps S-17/S-18 |
| R-16 | Redact CLI database URLs and generic exception output | CLI | Stable operator error-code contract | CLI output cannot expose credentials, SQL, paths or provider payload details | CLI sentinel tests; maps S-19 |
| R-17 | Verify provider rate semantics and implement conservative multi-worker budgeting | provider client, worker/scheduler | Provider selection and quota terms | Initial burst, retries and concurrent workers remain within documented quota | Deterministic clock/concurrency tests; maps GAP-014/S-14/F-02 |

## Low / process

| ID | Required action | Components | Dependencies | Acceptance criteria | Verification |
| --- | --- | --- | --- | --- | --- |
| R-18 | Establish dependency hash/advisory/licence review | requirements/operations | CI or documented clean-environment procedure | Dependency versions, hashes where supported, licenses and advisory date are recorded | Clean installation and dated review; maps S-16 |
| R-19 | Add DST, duplicate/correction, database failure and scheduler long-run tests | test suites, sync/scheduler | Test fixtures and controlled clock | Failure scenarios are reproducible and recovery behavior is asserted | Integration/non-functional test runs |
| R-20 | Define backup/restore and SQLite file-permission rehearsal | operations, database | Retention and deployment owner | Restore is tested; database/archive/log permissions are verified on the target host | Non-destructive scratch rehearsal and permission audit |

## Ordering and gate

No item authorizes Phase 5. R-01 through R-06 are required before public/shared-network or live-
provider exposure. R-07 through R-12 are required before using provider-derived data as a
reproducible intelligence input. R-13 through R-20 are required before production-like operation.
Each item requires regression evidence and review; documentation alone does not close a defect.
