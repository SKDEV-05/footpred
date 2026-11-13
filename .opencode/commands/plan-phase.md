---
description: Prepare the next development phase with objective, scope, non-goals, dependencies, agents, steps, acceptance criteria, risks, testing, and deliverables. Does not begin implementation.
---

# /plan-phase

Prepare a plan for: **$ARGUMENTS**

This command produces a plan only. It does **not** authorise implementation, dependency
installation, data integration, or starting a new phase. The developer must approve the plan
first.

## Read before planning

- `AGENTS.md`, `PROJECT_STATUS.md`, `memory/current-state.md`, `memory/next-steps.md`
- `docs/product/scope.md`, `requirements.md`, `non-goals.md`
- Relevant architecture, data, football, security, and design docs
- `rules/engineering-rules.md` and the rules specific to the phase

## Produce

1. **Phase objective** — one paragraph, outcome-oriented, measurable.
2. **Scope** — concrete deliverables, each with an owner agent and a definition of done.
3. **Non-goals** — what this phase explicitly will not do, to prevent drift.
4. **Entry criteria** — what must already be true (approvals, decisions, data access, docs).
5. **Dependencies** — technical, data, licensing, and human. Mark unknowns `TBD`.
6. **Required agents** — which specialists own which work, with no overlapping ownership.
7. **Required skills** — the skills each agent must load.
8. **Implementation steps** — ordered, each independently verifiable. Include a first step
   that reduces the biggest uncertainty (e.g. a bounded provider verification spike).
9. **Acceptance criteria** — testable statements, not activity descriptions.
10. **Testing requirements** — unit, contract, data-quality, regression, backtest, and
    reproducibility expectations for this phase.
11. **Risks and mitigations** — technical, data-quality, licensing, schedule, and model risk.
    Include the risk of shipping a plausible but unvalidated number.
12. **Deliverables** — files, documents, and artefacts with paths.
13. **Exit criteria and stop conditions** — when to stop and ask the developer.

## Rules

- Do not invent effort estimates, prices, quotas, or performance numbers. Use `TBD` with the
  measurement that would resolve it.
- Do not propose scope that requires unverified data or unapproved licensing.
- Prefer the smallest phase that produces a verifiable increment.
- Do not include application code in a foundation-phase plan.
- Do not silently expand the product scope; flag it for approval.
- Identify which decisions require an ADR before work starts.

## Output

Write the plan to `docs/product/phase-<n>-plan.md` (or update the existing plan) and update
`memory/next-steps.md`. Report a summary with: objective, scope, top three risks, decisions
needed from the developer, and the file path. Do not start the work.
