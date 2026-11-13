# Next Steps

**Phase 2 is not approved.** Do not begin any work below without explicit developer approval.

## Immediate next action

Developer review of Phase 1:

1. Read `AGENTS.md`, `PROJECT_STATUS.md`, and `memory/current-state.md`.
2. Review the agent ecosystem and skills for overlap or missing ownership.
3. Review `docs/product/requirements.md` and `docs/product/scope.md`.
4. Decide whether to accept, amend, or reject the foundation.
5. If accepted, approve or amend the Phase 2 candidate scope.

## Phase 2 candidate (not approved)

**Working title:** Data foundation and provider verification.

**Objective:** Reduce the largest unknown — whether usable, legally obtainable football data
exists at the required quality — and produce a data model and ingestion design grounded in
observed payloads.

**Candidate scope:**

1. Bounded provider verification spike: 2-3 providers, fixed competitions and seasons,
   field-level checks, latency measurement, licence confirmation, time-boxed.
2. Update `docs/data/providers-research.md` with verified facts and a recommendation.
3. Data model design: entities, keys, point-in-time versioning, provenance records.
4. Ingestion design: idempotency, scheduling, failure handling, quarantine.
5. Baseline feasibility note: is there enough history to estimate goal rates and calibrate?
6. ADRs for provider choice, storage model, and ingestion approach.

**Explicit non-goals for Phase 2 candidate:** no production API, no frontend, no ML model, no
public deployment, no monetisation.

## Prerequisites

- [ ] Developer approval of Phase 1.
- [ ] Developer approval of Phase 2 scope and non-goals.
- [ ] Initialise version control with a `.gitignore` excluding `.env`, caches, build output,
      and large data artefacts (no repository exists yet).
- [ ] Decision on data budget and permitted licence types.
- [ ] Decision on first-release competition coverage.
- [ ] Authorisation to create provider accounts and run a time-boxed trial.
- [ ] Agreement on how derived statistics may be displayed.

## Pending decisions

| ID | Decision | Owner | Blocks |
| --- | --- | --- | --- |
| PD-001 | Phase 2 approval and scope | Developer | Everything below |
| PD-002 | Provider(s) after verification | Developer + data-engineer | Storage, ingestion |
| PD-003 | Competition/season coverage | Developer + product-architect | Data model, evaluation |
| PD-004 | Data budget | Developer | Provider choice |
| PD-005 | xG: licensed, computed, or omitted | Developer + football-analyst | Feature set |
| PD-006 | Storage stack confirmation (PostgreSQL leading candidate) | Developer + backend-architect | Implementation |
| PD-007 | Whether to support live data at all initially | Developer | Architecture |
| PD-008 | Uncertainty presentation approach | Developer + ux-designer | Interface design |

## Expected deliverables (if approved)

- Verified provider evaluation with dated sources.
- Data model document and ER-level design (no migrations yet unless approved).
- Ingestion design with failure modes and provenance.
- ADRs: provider, storage, ingestion.
- Updated requirements with approved statuses.
- Updated memory and status.

## Stop conditions

Stop and ask the developer if:

- a provider requires a paid commitment or legal agreement;
- licensing terms are ambiguous for the intended use;
- the required history is unavailable at usable quality;
- a design would require a technology not yet approved;
- work would cross into application implementation without explicit approval.

## Related documents

- `docs/product/scope.md`
- `memory/known-limitations.md`
- `memory/decisions.md`
- `docs/architecture/technology-decisions.md`
