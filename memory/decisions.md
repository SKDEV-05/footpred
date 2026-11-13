# Decisions

Recorded decisions, rejected approaches, and their reasons. Detailed decisions live in
`docs/decisions/`; this is an index with rationale. Never delete an entry — supersede it.

---

## Recorded decisions

Status values: **Instructed** (required by the developer's phase brief), **Proposed**
(recommended by the foundation work, awaiting developer review), **Approved** (explicitly
accepted by the developer).

### DEC-001 — Phase 1 is foundation only

**Status:** Instructed by the developer's Phase 1 brief.

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
**Status:** Proposed — pending developer review
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

None.

---

## Related documents

- `docs/decisions/ADR-0001-project-foundation.md`
- `memory/known-limitations.md`
- `AGENTS.md`
