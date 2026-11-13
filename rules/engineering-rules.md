# Engineering Rules

Binding for all agents and future contributors. These rules govern **how work is done**.
Domain-specific rules live in the sibling documents; root context is in `AGENTS.md`.

Violations are defects. If a rule must be broken, obtain developer approval and record the
exception in an ADR.

---

## E1 — Evidence before implementation

Do not make an important architectural, data, or modelling decision from assumption alone.

- Framework and API capabilities: check official documentation.
- Data-provider behaviour: check official docs or a bounded, authorised trial.
- Model behaviour: check an executed evaluation, not intuition.
- Record the source and access date in the relevant research note.

If evidence is unavailable, the decision is a hypothesis. Label it, state what would confirm
it, and keep the design reversible.

## E2 — No unnecessary complexity

Choose the simplest design that satisfies the actual requirement.

MUST NOT introduce:
- microservices or a message broker without a measured need;
- abstraction layers with one implementation and no foreseeable second;
- design patterns used for decoration;
- redundant dependencies or duplicate implementations;
- caching treated as a source of truth;
- configuration options nobody needs.

Before adding a moving part, state the requirement it serves and the cost of operating it.

## E3 — One owner per responsibility

Every responsibility has exactly one owning agent or module. Shared ownership produces
conflicting rules and silent divergence.

- Requirements: `product-architect`.
- System design: `backend-architect`.
- Data pipeline and providers: `data-engineer`.
- Football domain validity: `football-analyst`.
- Models and evaluation: `ml-researcher`.
- Verification: `qa-engineer`.
- Security: `security-reviewer`.
- Interface and accessibility: `ux-designer`.
- Coordination and phase boundaries: `orchestrator`.

Review by another agent is expected; competing ownership is not.

## E4 — Reviews are independent

- An author does not approve their own work.
- A reviewer checks evidence, scope, correctness, and limitations — not style preferences.
- Review findings are classified by severity; blockers must be resolved, not deferred
  silently.
- "Looks good" is not a review.

## E5 — Phase discipline

- Work stops at the approved phase boundary.
- Starting a new phase, installing dependencies, or adding a major technology requires
  explicit developer approval.
- Do not perform "preparatory" implementation that the phase forbids.
- Do not start Phase 2 as a convenience while finishing Phase 1.

## E6 — Dependencies are decisions

- Every dependency must have a stated purpose and an owner.
- Prefer the standard library and existing dependencies.
- Review licence, maintenance status, and security posture before adoption.
- Pin versions and commit lockfiles once implementation begins.
- Do not install anything during a restricted phase.

## E7 — Behaviour must be verifiable

A change is complete when:
1. it matches approved scope;
2. its behaviour is verified by a test, measurement, or explicit manual check;
3. its limitations are documented;
4. relevant docs and memory are updated;
5. an independent reviewer accepted it.

"A script ran without error" is not verification.

## E8 — Fail visibly

- Never swallow an exception and continue with plausible-looking data.
- Never return a default value that could be mistaken for a real measurement.
- Surface stale, partial, or missing data at the point of use.
- Prefer a visible failure or an explicit abstention over a confident wrong answer.

## E9 — Reproducibility is a requirement

- A prediction must be reconstructable from stored inputs, code version, and parameters.
- Record data snapshot, feature version, model version, and timestamp.
- Seed randomness where it affects output; record nondeterminism otherwise.
- Do not mutate historical records to make a later result look better.

## E10 — Documentation is part of the deliverable

- Decisions go in ADRs, research in dated notes, stable reference in `docs/`.
- Do not duplicate rules; link to the authoritative document.
- Never document an unimplemented capability as complete.
- Update documentation in the same change as the behaviour it describes.

## E11 — No invented data, sources, prices, or quotas

- Never fabricate statistics, fixtures, lineups, injuries, xG, citations, provider pricing,
  rate limits, or benchmarks.
- Missing values are missing; zero is zero; unknown is unknown.
- If a number cannot be verified, write `UNVERIFIED` and state how to verify it.
- Hypothetical examples must be clearly labelled as illustrative.

## E12 — Human approval gates

Explicit developer approval is required before:

- starting a new phase;
- changing approved architecture;
- adding a major technology or dependency set;
- installing anything in a restricted phase;
- destructive operations (deleting data, rewriting history, force-pushing);
- expanding product scope or competition coverage;
- publishing or redistributing licensed data;
- accepting a known correctness or security defect.

## E13 — Errors are designed, not patched

- Define expected failure modes before implementation.
- External calls have timeouts, bounded retries with backoff, and a failure path.
- Partial success is represented explicitly, not rounded up to success.
- Every fixed defect gets a regression test.

## E14 — Simplicity in interfaces

- Public interfaces are small, documented, and stable.
- Prefer explicit parameters over implicit global state.
- Do not expose internal representations as contracts.
- Version contracts before breaking them.

## Enforcement

- The orchestrator checks these rules before accepting a deliverable.
- The QA engineer checks verifiability and test coverage.
- The security reviewer checks secrets, input handling, and prediction integrity.
- Repeated violations are recorded in `memory/known-limitations.md` and addressed by a rule
  or process change, not by reminder alone.

## Related documents

- `rules/system-design-rules.md`
- `rules/data-rules.md`
- `rules/ai-usage-rules.md`
- `rules/security-rules.md`
- `rules/design-rules.md`
- `AGENTS.md`
