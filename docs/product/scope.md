# Scope

## Purpose

Defines what work is permitted now, what is a candidate for the next phase, and what is excluded. Scope is a control, not a forecast: inclusion here does not authorise implementation.

## Phase model

| Phase | Content | Status | Gate to enter |
| --- | --- | --- | --- |
| 1. Foundation | Instructions, agents, skills, rules, product and domain documentation | Artefacts delivered | Developer review |
| 2. System architecture | Stack, SQLite schema design, provider boundary, read-only API contract, identity, sync | Documents delivered; ADR sign-off pending | Developer's Phase 2/3 brief |
| 3. Data foundation backend | Python backend, SQLite migrations, adapter, ingestion, sync, read-only API, tests, guides | Implemented locally; independent reviews blocked | Developer's Phase 2/3 brief |
| 4. Future work | Prediction, modelling and evaluation; product-surface work requires separately bounded approval | Not started or approved | Review of Phases 2/3, verified data, licensing and explicit developer approval |

The Phase 1 candidate roadmap below was superseded by the developer's Phase 2/3 brief.
Phase 3 permits the data backend, not predictions, ML, frontend, authentication or deployment.
Live provider access still requires approval and credentials. See
[`PROJECT_STATUS.md`](../../PROJECT_STATUS.md) for verification and outstanding gates.

## Historical Phase 1 candidate (superseded, not authorisation)

The following was the original Phase 2 proposal. It remains here as historical context;
it does not authorise a provider trial or expand the current implementation.

| Candidate work item | Deliverable | Decision it enables |
| --- | --- | --- |
| Data source verification spike | Written assessment of candidate sources: coverage, definitions, update behaviour, licensing constraints, known gaps | Whether a lawful, sufficient data foundation exists |
| Data model design | Conceptual and logical model for competitions, fixtures, results, events, lineups and provenance | How historical data is represented without ambiguity |
| Ingestion prototype | A bounded, non-production pipeline for one competition and season, with validation and provenance | Whether ingestion is feasible at acceptable quality and effort |

The spike is research, not procurement. It must not commit to a provider, store provider data beyond what the licence permits, or produce football statistics as if verified. Findings go to `docs/research/` with sources and access dates.

## Out of scope until later

| Item | Earliest phase | Reason |
| --- | --- | --- |
| Frontend or mobile application | 4 | Depends on a stable API and validated analysis |
| ML models in production | Unscheduled; not Phase 3 | Requires verified data, evaluation and explicit approval |
| Monetisation, pricing, subscriptions | Not scheduled | No validated product or cost model |
| User accounts and personalisation | Not scheduled | Adds security and privacy scope without validated need |
| Public API | Unscheduled | No authentication, rate limiting or licensing clearance |
| Live or in-play analysis | Not scheduled | Latency and data quality requirements are unmet |
| Additional sports | Not scheduled | Football domain assumptions are unvalidated |

## Phase entry and exit criteria template

Every phase proposal uses this template. Criteria must be observable and evidenced, not assertions of effort.

| Field | Content |
| --- | --- |
| Phase name and number | |
| Objective | One sentence stating the decision or capability the phase delivers |
| Entry criteria | Prior phase exit met; required approvals recorded; dependencies available |
| Deliverables | Concrete artefacts with locations |
| Exit criteria | Verifiable conditions, including quality and documentation checks |
| Explicit exclusions | Work that must not be started within the phase |
| Risks and unknowns | Known blockers with owners |
| Evidence of completion | Links to artefacts, review notes and recorded limitations |

A phase is not complete because its deliverables exist. Exit requires review against the criteria and a recorded decision.

## Change control

- Scope changes require explicit human approval and an ADR in `docs/decisions/`.
- A change proposal states the current scope, the proposed addition or removal, the reason, the affected requirements and the cost of deferral.
- Urgent defects may be fixed within the current phase only if the fix does not add a new capability.
- Approved scope is not expanded by implication. A document describing a future capability does not authorise building it.
- Rejected changes are recorded with their rationale to prevent repeated proposals.

## Relationship to non-goals

Scope states what may be done and when. [Non-goals](./non-goals.md) state what the product will not become. A proposal that conflicts with a non-goal is rejected unless the non-goal is formally revisited. A proposal that is merely absent from scope needs approval, not a non-goal amendment.

## Related documents

- [Vision](./vision.md)
- [Requirements](./requirements.md)
- [Non-goals](./non-goals.md)
- [Prediction markets](../football/prediction-markets.md)
- Root phase rules: `../../AGENTS.md`
