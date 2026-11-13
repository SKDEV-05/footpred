# Decisions

Recorded decisions, rejected approaches, and their reasons. Detailed decisions live in
`docs/decisions/`; this is an index with rationale. Never delete an entry — supersede it.

---

## Recorded decisions

Status values: **Instructed** (required by the developer's phase brief), **Proposed**
(recommended by the foundation work, awaiting developer review), **Approved** (explicitly
accepted by the developer).

### DEC-001 — Phase 1 is foundation only

**Status:** Superseded by DEC-009 (Phase 3 completed).

**Date:** 2026-11-13
**Decision:** Phase 1 produces instructions, agents, skills, commands, documentation, memory,
and rules. No application code, dependencies, database, or provider integration.
**Reason:** Establish governance and clarity before implementation; avoid rework and invented
requirements.
**ADR:** `docs/decisions/ADR-0001-project-foundation.md`

### DEC-002 — Project root is the repository root

**Date:** 2026-11-13
**Status:** Proposed — pending developer review
**Decision:** Build the structure directly in the working directory rather than creating a
nested `football-intelligence/` folder.
**Reason:** OpenCode discovers `AGENTS.md` and `.opencode/` relative to the project root. A
nested folder would prevent instructions and agents from applying at the root. The working
directory was empty.
**Consequence:** The requested tree is rooted here; all paths in documents are relative to
this directory.

### DEC-003 — Modular monolith first

**Date:** 2026-11-13
**Status:** Proposed — pending developer review
**Decision:** The future system starts as one application plus one background worker and one
relational database.
**Reason:** Small team, unmeasured scale, strong need for reproducibility and simple
operations. Microservices would add failure modes without a requirement.
**Revisit when:** measured load, independent scaling needs, or team topology justify
distribution — with an ADR.

### DEC-004 — No LLM in the numerical prediction path

**Date:** 2026-11-13
**Status:** Proposed — pending developer review
**Decision:** Probabilities come from deterministic statistical/ML procedures. LLMs may only
explain verified outputs.
**Reason:** Reproducibility, calibration, evaluation, and auditability. An LLM cannot provide
stable, testable probabilities.
**ADR:** recorded in `docs/architecture/architecture-principles.md` and
`rules/ai-usage-rules.md`.

### DEC-005 — Data provenance is mandatory

**Date:** 2026-11-13
**Status:** Proposed — pending developer review
**Decision:** Every derived value must be traceable to raw payload, fetch time, parser version,
and source record.
**Reason:** Without provenance, predictions cannot be audited, reproduced, or defended.
**Reference:** `docs/data/data-provenance.md`, `rules/data-rules.md`.

### DEC-006 — No technology selected in Phase 1

**Date:** 2026-11-13
**Status:** Superseded by DEC-010 (Phase 2 stack selection).
**Decision:** Python, FastAPI, PostgreSQL, and the rest remain under evaluation. Nothing was
installed or pinned.
**Reason:** Selection without requirements evidence would anchor the design prematurely.
**Reference:** `docs/architecture/technology-decisions.md`.

### DEC-007 — No project-level `opencode.jsonc` in Phase 1

**Date:** 2026-11-13
**Status:** Proposed — pending developer review
**Decision:** Rely on OpenCode defaults and file-based definitions; do not set a
`default_agent` or global permissions in project config.
**Reason:** Avoid changing the developer's session behaviour and avoid inventing configuration
that is not required. Agents carry their own permissions.
**Revisit when:** a project-wide permission policy or default agent is explicitly wanted.

### DEC-008 — Documentation and rules are separate

**Date:** 2026-11-13
**Status:** Proposed — pending developer review
**Decision:** `rules/` holds binding constraints; `docs/` holds explanation and design;
`memory/` holds current summary. One topic, one home.
**Reason:** Prevents drift and duplicated, contradictory rules.

### DEC-009 — Phase 2 and Phase 3 scope

**Date:** 2026-11-13
**Status:** Instructed by the developer's Phase 2/3 brief; implemented.
**Decision:** Phase 2 records the system architecture. Phase 3 implements a Python backend with
SQLite, a provider adapter, normalization and identity, a sync engine, a read-only REST API,
tests, observability, and documentation. Phase 4 (prediction, ML, frontend, auth, deployment) is
excluded and not approved.
**Reason:** Build a trustworthy data foundation before any probability model. A prediction
without traceable data is a defect.
**Consequence:** The repository now contains application code and a database schema, unlike
Phase 1.

### DEC-010 — Python backend stack

**Date:** 2026-11-13
**Status:** Proposed — implemented, pending review.
**Decision:** Python 3.11+ (verified on 3.15.2), FastAPI, Pydantic v2, pydantic-settings,
SQLAlchemy 2.x, Alembic, HTTPX, APScheduler, pytest, Uvicorn. Versions are pinned in
`requirements.lock` and `pyproject.toml`.
**Reason:** Synchronous, small, well-documented stack for one API process and one worker. No
broker or distributed system is justified by the requirement.
**ADR:** `docs/decisions/ADR-0002-python-backend-stack.md`.

### DEC-011 — SQLite is the Phase 3 primary database

**Date:** 2026-11-13
**Status:** Proposed — implemented, pending review.
**Decision:** SQLite is the only supported database. `foreign_keys=ON`, WAL for file databases,
and a busy timeout are applied per connection. A non-SQLite URL fails closed.
**Reason:** Developer instruction, single-operator deployment, no server to operate, adequate
for the data volume in scope.
**Consequence:** PostgreSQL is a future option only. It is not installed, tested, or claimed
compatible. Any switch requires a migration plan and verification.
**ADR:** `docs/decisions/ADR-0003-sqlite-primary-database.md`.

### DEC-012 — Provider abstraction with one reference adapter

**Date:** 2026-11-13
**Status:** Proposed — implemented, live-unverified.
**Decision:** Ingestion depends on a provider-neutral contract with explicit capability flags.
The first adapter targets football-data.org API v4 because its documentation is publicly
verifiable. Vendor JSON never crosses the adapter boundary.
**Reason:** Avoid coupling canonical data and ingestion to one vendor; make unsupported
datasets explicit instead of empty.
**Consequence:** Provider selection remains provisional (PD-002). Credentials, coverage,
pricing, quota, history depth, and licence are **UNVERIFIED**. No live call has been made.
**ADR:** `docs/decisions/ADR-0004-provider-abstraction.md`.

### DEC-013 — Read-only API, manual sync through the CLI

**Date:** 2026-11-13
**Status:** Proposed — implemented, pending review.
**Decision:** `/api/v1` is read-only. There is no write endpoint, no authentication, and no
sync trigger over HTTP. Manual sync and migrations are CLI operations; scheduled sync runs in
one worker.
**Reason:** Without authentication, any write surface would be an unauthenticated mutation
path. The API never calls a provider during a request.
**Consequence:** Host access control is the Phase 3 security boundary. Public exposure is
blocked until auth, rate limiting, and TLS exist.
**ADR:** `docs/decisions/ADR-0005-api-contract.md`, `ADR-0007-synchronisation.md`.

### DEC-014 — Identity and provenance model

**Date:** 2026-11-13
**Status:** Proposed — implemented, pending review.
**Decision:** Internal surrogate ids; provider ids in mapping tables unique per
`(provider, external_id)` and per `(provider, internal entity)`. Resolution order: mapping →
exact natural key → create. Ambiguity and a second external id for an already-mapped entity are
quarantined, never fuzzy-merged. Raw payloads are archived before parsing.
**Reason:** Stable history across provider changes, auditability, and no accidental merges.
**Consequence:** Every canonical write carries a sync run and, where applicable, a raw payload
reference. Corrections append to `match_change_log`.
**ADR:** `docs/decisions/ADR-0006-identity-and-provenance.md`.

### DEC-015 — Statistics stored as metric rows

**Date:** 2026-11-13
**Status:** Proposed — implemented, pending review.
**Decision:** One row per `(match_id, team_id, metric)` with a numeric value. Absence of a row
means unavailable; `value=0` means a measured zero.
**Reason:** Makes "missing is not zero" a schema-level property and avoids a migration for every
new provider metric.
**Consequence:** The API returns an empty metric map rather than zeros. Statistics corrections
currently have no change-log entry (known gap).
**ADR:** `docs/decisions/ADR-0006-identity-and-provenance.md`.

### DEC-016 — Synchronisation with per-item transactions

**Date:** 2026-11-13
**Status:** Proposed — implemented, pending review.
**Decision:** One `data_sync_runs` row per job; provider I/O outside database transactions; each
item persisted in its own short transaction; failures recorded per item; rejected records
quarantined; stale `running` runs marked failed at worker start.
**Reason:** One malformed provider record must not discard a successful batch, and a crash must
not leave invisible work.
**Consequence:** A run is not atomic end to end. Re-running a window is safe because ingestion is
idempotent. One worker only, because the rate limit is per process and SQLite has one writer.
**ADR:** `docs/decisions/ADR-0007-synchronisation.md`.

---

## Rejected approaches

Recorded rationale for options the foundation recommends against. These recommendations are
subject to the same developer review as the ADR.

### REJ-001 — Microservices from day one

**Rejected because:** no measured scaling need; adds network failure modes, deployment
complexity, and data consistency problems for a small team.

### REJ-002 — LLM as the prediction engine

**Rejected because:** no calibration, no reproducibility, no auditability, and a high risk of
fabricated inputs.

### REJ-003 — Scraping providers without a licensing review

**Rejected because:** terms-of-service and redistribution risk; technical fragility; no SLA.

### REJ-004 — Estimating provider prices and quotas from memory

**Rejected because:** plans change and wrong numbers mislead planning. All such values must be
verified from official documentation and dated.

### REJ-005 — Committing mock football data to seed development

**Rejected because:** fabricated data is easily mistaken for real data and corrupts evaluation
habits. Test fixtures, if needed later, must be clearly labelled and isolated.

### REJ-006 — Choosing a brand palette in Phase 1

**Rejected because:** visual identity is premature; the product must first earn trust through
data and analysis. Design rules prohibit it.

---

## Superseded

| Decision | Superseded by | Reason |
| --- | --- | --- |
| DEC-001 — Phase 1 is foundation only | DEC-009 | Phases 2 and 3 were instructed and completed |
| DEC-006 — No technology selected in Phase 1 | DEC-010, DEC-011 | Stack and database selected in Phase 2 |

No other decision has been reversed. DEC-003 (modular monolith) and DEC-004 (no LLM in the
prediction path) remain in force.

---

## Related documents

- `docs/decisions/ADR-0001-project-foundation.md`
- `memory/known-limitations.md`
- `AGENTS.md`

## Close-out record — 2026-11-14

No new architecture is approved by this close-out. Report A and Report B are in `docs/reports/`.
Local verification is 124 passing tests plus a scratch migration/no-drift check. Independent
QA/security attempts both failed at the tool usage limit; acceptance is still pending. Remaining
transport/data-integrity gaps are not approved exceptions (see `memory/known-limitations.md`).
