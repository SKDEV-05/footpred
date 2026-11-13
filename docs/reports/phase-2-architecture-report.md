# Report A — Phase 2 System Architecture

**Date:** 2026-11-13; close-out updated 2026-11-14
**Scope:** architecture design only, followed by Phase 3 implementation of the data foundation.
**Outcome:** architecture recorded and implemented for the data layer. Prediction, ML, frontend,
authentication, and deployment remain out of scope.
**Review status:** independent QA/security review attempts were blocked by the tool usage
limit. No findings or approval were returned; developer sign-off remains pending.

## 1. Objective

Define a system that can store trustworthy football history with provenance, resolve provider
identity without guessing, expose stored data read-only, and remain simple enough for a small
team to operate — before any probability model is considered.

## 2. Decisions recorded

| ADR | Decision | Status |
| --- | --- | --- |
| ADR-0001 | Project foundation | Proposed, as recorded; Phase 2/3 brief advances scope, not blanket ADR acceptance |
| ADR-0002 | Python backend stack | Proposed — implemented |
| ADR-0003 | SQLite primary database | Proposed — implemented |
| ADR-0004 | Provider abstraction | Proposed — implemented, live-unverified |
| ADR-0005 | Read-only API contract | Proposed — implemented |
| ADR-0006 | Identity, provenance, and statistics model | Proposed — implemented |
| ADR-0007 | Synchronisation and scheduling | Proposed — implemented |

"Proposed" is deliberate: implementation is not approval. Developer sign-off is still required.

## 3. Architecture delivered

```text
Provider HTTP API
      │  (one client: auth, timeout, retries, rate limit)
      ▼
Raw archive ── content-addressed bytes + raw_payloads row, committed before parsing
      │
      ▼
Adapter ── vendor JSON → provider-neutral DTOs; unsupported datasets raise
      │
      ▼
Normalisation → Validation → Identity resolution
      │
      ▼
SQLite (17 tables, FK enforced, WAL)
      │
      ├── Read-only FastAPI /api/v1
      └── Sync history, errors, quarantine, change log
```

Structural choices:

- **Modular monolith.** One API process, one worker, one database. No broker, cache, container,
  or microservice.
- **Synchronous code.** No async database layer; the workload does not justify it.
- **Provider-neutral boundary.** Vendor JSON never reaches canonical models.
- **Evidence-first storage.** Raw payloads are archived before parsing; canonical rows reference
  their run and, where meaningful, their raw payload.
- **No prediction in the data layer.** No feature or prediction tables exist.

## 4. Phase 2 validation gate

| Check | Result | Evidence |
| --- | --- | --- |
| Technology choices justified against requirements | Pass | ADR-0002, ADR-0003 |
| Database entities coherent and normalised | Pass | `docs/architecture/database-design.md`, 17 tables |
| Provider strategy realistic | Pass with caveat | ADR-0004; reference adapter documented; entitlement unverified |
| Provider ids separated from internal ids | Pass | Mapping tables, surrogate keys, ADR-0006 |
| API contracts defined | Pass | `docs/architecture/api-design.md`, generated OpenAPI |
| Synchronisation strategy documented | Pass | ADR-0007, `docs/data/synchronization.md` |
| Security requirements addressed for scope | Pass with caveat | `docs/architecture/security-architecture.md`; no auth, so no public exposure |
| Testing strategy exists and is executed | Locally checked; independent review blocked | `docs/guides/testing.md`, 124 tests passing |
| No unnecessary complexity | Pass with caveat | APScheduler instead of a broker; no cache |
| Consistent with Phase 0/1 research | Pass | SQLite supersedes the earlier PostgreSQL hypothesis by developer instruction |

## 5. Deviations and supersessions

| Earlier position | Current position | Reason |
| --- | --- | --- |
| PostgreSQL was the leading candidate | SQLite is the Phase 3 database | Developer instruction; simpler operations for one host |
| Provider selection deferred entirely | One reference adapter implemented | A contract needs a concrete parser to be credible; selection remains provisional |
| No application code in Phase 1 | Application code exists | Phase 3 was instructed after Phase 1 review |
| Statistics change log implied | Only fixture/result change entries exist | Scope control; the gap is recorded rather than hidden |

## 6. Risks accepted

- The reference adapter may need rework after a live payload is seen. Accepted because it is
  isolated behind a contract and covered by parser tests.
- SQLite limits concurrent writers. Accepted for a single-operator deployment; not suitable for
  a high-concurrency public service.
- No authentication means the API is not public. Accepted; the host is the security boundary in
  Phase 3.
- Provider licence and coverage are unresolved. Accepted only because no data is displayed
  publicly and no live call has been made.

## 7. Phase 2 status

**VERIFIED:** architecture documents and ADRs exist, and local boundary tests pass.
These are implementer checks, not independent approval.

**PARTIALLY IMPLEMENTED:** end-to-end provenance, dataset freshness and some ingestion/transport
controls. Remaining gaps are indexed in `memory/known-limitations.md` (GAP-013 onward).

**IMPLEMENTED BUT NOT LIVE-VERIFIED:** the provider integration.

**BLOCKED:** independent review and live provider acceptance.

**NOT IMPLEMENTED (by scope):** prediction, ML, frontend, auth, deployment.

**Open:** developer approval of ADR-0002 … ADR-0007, provider selection (PD-002), coverage
(PD-003), budget (PD-004), licence (LIM-006).

## 8. What would make this architecture wrong

- A requirement for multi-worker ingestion at a request rate above one process's budget.
- A requirement to serve concurrent public traffic with write-heavy sync.
- A provider whose licence forbids storing raw payloads.
- A decision to support PostgreSQL as a first-class target without a migration and test plan.
- A requirement for near-real-time event data that the chosen provider does not offer.

None of these is established today. If one becomes established, it requires a new ADR, not a
silent architecture drift.
