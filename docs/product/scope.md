# Scope

## Purpose

Defines what work is permitted now, what is a candidate for the next phase, and what is excluded. Scope is a control, not a forecast: inclusion here does not authorise implementation.

## Phase model

| Phase | Content | Status | Gate to enter |
| --- | --- | --- | --- |
| 1. Foundation | Instructions, agents, skills, rules, product and domain documentation, decisions | Complete, pending developer review | None; current phase |
| 2. Data foundation (candidate) | Source verification, data model, ingestion prototype | Not approved | Developer approval after reviewing Phase 1 and the spike proposal |
| 3. Analysis and modelling | Statistical engine, calibration, evaluation harness | Not approved | Phase 2 exit criteria met and modelling ADRs approved |
| 4. Product surface | API and frontend for validated outputs | Not approved | Stable analysis outputs, API contract, UX review |

Phase 1 permits documentation only. No code, database, external API call, package installation, or deployment artefact is in scope. Phase 1 is complete when the foundation artefacts exist and the developer has reviewed them; see `PROJECT_STATUS.md`.

## In scope for the next phase candidate

The following are candidates for Phase 2. They are not approved and must not start before explicit developer approval.

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
| ML models in production | 3 or later | Requires a data foundation and evaluation harness |
| Monetisation, pricing, subscriptions | Not scheduled | No validated product or cost model |
| User accounts and personalisation | Not scheduled | Adds security and privacy scope without validated need |
| Public API | 4 | Contract stability is unproven |
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
