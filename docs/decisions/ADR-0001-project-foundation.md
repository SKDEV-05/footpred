# ADR-0001 — Project Foundation

## Status

Proposed — pending developer review

This ADR becomes Accepted when the developer approves Phase 1. Amendments before approval
are edits to this document; amendments after approval require a superseding ADR.

## Date

2026-11-13

## Context

The project is a long-term football intelligence and match-analysis platform. Before any
implementation, it needs a shared engineering environment: instructions for AI agents,
specialised roles, reusable skills and commands, product and architecture documentation, a
memory system, and binding rules.

Without this foundation, agents would improvise scope, invent data, duplicate rules, and make
technology decisions without evidence. The developer supervises the work and approves
decisions; the environment must make that supervision efficient.

Constraints at the time of this decision:

- The repository was empty and is not yet a Git repository.
- No dependencies, application code, database, or provider access exists.
- The IDE/terminal agent is OpenCode; the coding model is DeepSeek V4.1.
- Phase 1 is explicitly foundation-only.

## Decision

1. **Adopt a documentation-and-rules foundation before implementation.** Phase 1 delivers
   `AGENTS.md`, agents, skills, commands, `docs/`, `memory/`, and `rules/`.
2. **Use the repository root as the project root.** Do not nest a `football-intelligence/`
   directory, so OpenCode discovers `AGENTS.md` and `.opencode/` at the root.
3. **Create nine agents**: one `orchestrator` (primary) and eight specialists (`subagent`):
   product-architect, backend-architect, data-engineer, football-analyst, ml-researcher,
   qa-engineer, security-reviewer, ux-designer.
4. **Create twelve skills** covering research, architecture, football domain, data sources,
   data engineering, statistics, ML, validation, testing, security, documentation, and
   anti-AI-slop design.
5. **Create six commands**: `/research`, `/plan-phase`, `/architecture-review`,
   `/data-source-review`, `/quality-check`, `/update-memory`.
6. **Separate concerns**: `rules/` is binding constraints, `docs/` is explanation and design,
   `memory/` is the current summary, `docs/decisions/` holds ADRs, `docs/research/` holds
   dated research notes.
7. **Default to a modular monolith** with one relational database and one background worker
   for the future system.
8. **Forbid LLMs in the numerical prediction path.** LLMs may explain verified outputs only.
9. **Select no technology in Phase 1.** All candidates remain under evaluation; nothing is
   installed or pinned.
10. **Require provenance for all derived data** and immutable, timestamped prediction records.

## Alternatives considered

### A. Start implementing immediately (backend skeleton + provider integration)

Rejected. It would force technology and data-model decisions before requirements and provider
verification, and would produce code that cannot be evaluated. Rework cost is high; governance
cost is low.

### B. Create only `AGENTS.md` and a folder skeleton

Rejected. Insufficient: agents would still lack domain procedures, phase boundaries, and
quality standards, and would duplicate or contradict each other.

### C. Adopt a full multi-service architecture and monorepo tooling up front

Rejected. No measured scaling need, a small team, and no application code. It adds operational
and consistency costs without evidence.

### D. Use a nested `football-intelligence/` directory as specified in the brief

Rejected in favour of the repository root. OpenCode loads `AGENTS.md` and discovers
`.opencode/` from the workspace/project root; nesting would silently disable the environment
for work at the root. The working directory was empty, so no existing work was displaced.

### E. Pin a model and project-wide permissions in `opencode.jsonc`

Rejected for Phase 1. It would change session behaviour and encode choices not yet justified.
Agents carry their own permissions; model selection remains with the session.

## Consequences

**Positive**

- Agents have explicit roles, boundaries, and procedures.
- Phase discipline is enforceable and documented.
- Decisions are traceable (ADRs, research notes, memory).
- Data integrity and anti-hallucination rules are stated before code exists.
- Future work can reuse skills and commands instead of re-deriving process.

**Negative / costs**

- Documentation must be maintained; stale docs are a real risk.
- The foundation is larger than a minimal skeleton and requires developer review time.
- Some documents contain `TBD`/`UNVERIFIED` values that must be resolved later.
- Agent definitions depend on OpenCode V2 conventions, which may evolve.

**Neutral**

- No technology is selected, so Phase 2 still faces open decisions.

## Risks

| Risk | Mitigation |
| --- | --- |
| Documentation drifts from reality | `/update-memory`, ADR discipline, review in every change |
| Agents ignore rules | Root `AGENTS.md`, least-privilege permissions, orchestrator review |
| Premature technology commitment | Explicit "under evaluation" status; ADR required |
| Provider facts invented under pressure | `UNVERIFIED` rule, dated sources, verification spike |
| Phase boundary erosion | Explicit stop conditions and human approval gates |
| Over-documentation slows delivery | Keep memory short; link instead of duplicating; review for usefulness |

## Related documents

- `AGENTS.md`
- `PROJECT_STATUS.md`
- `docs/product/vision.md`
- `docs/product/scope.md`
- `docs/architecture/architecture-principles.md`
- `docs/architecture/technology-decisions.md`
- `rules/engineering-rules.md`
- `memory/decisions.md`
