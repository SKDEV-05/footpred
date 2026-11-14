# ADR-0008 — Entry gates for intelligence, predictions, and frontend

**Status:** Proposed — developer decision required; no implementation authorised by this ADR.
**Date:** 2026-11-14
**Owners:** developer, product-architect, backend-architect, data-engineer, ml-researcher
**Related:** [Project status](../../PROJECT_STATUS.md),
[next steps](../../memory/next-steps.md),
[coverage matrix](../data/coverage-matrix.md)

## Context

The developer's Phase 4 + Phase 5 brief requests team and match intelligence, a validated
probability engine, and a Next.js frontend in sequence. It also requires a stop and developer
approval when historical data is insufficient, a prediction method cannot be validated,
provider licensing is unclear, or an architectural change is required.

The Phase 3 backend is delivered but not accepted. Its 124 local tests passed in the
2026-11-14 audit, but no live provider call or independent Phase 3 sign-off exists. The
coverage matrix contains no verified competition, season, result, or statistic history.
Licensing and the provider plan are undecided. The existing read-only API has no protection
for a public or expensive analysis endpoint. These facts do not establish that any model can
be fitted or validated.

## Proposed decision

Treat the master brief as approval to **audit and propose** Phase 4/5 scope, not as a waiver
of its stop conditions or of unresolved Phase 3 acceptance. Obtain an explicit developer
go/no-go before implementing a model, adding a write endpoint, installing Next.js, or making
a destructive migration.

Proposed sequence, subject to that decision:

1. Accept or amend Phase 3 after independent QA/security review; triage the open data
   integrity and provenance gaps in
   [known limitations](../../memory/known-limitations.md).
2. Choose provider, plan, competitions/seasons, permitted uses, and historical coverage.
   Authorise a bounded live verification separately; do not purchase or accept terms on the
   developer's behalf.
3. Specify point-in-time input contracts, regulation-time score and venue semantics,
   metric formulas, minimum-data/abstention rules, and a frozen temporal evaluation protocol.
4. Implement and independently review Phase 4 intelligence against those contracts, with
   synthetic fixtures confined to tests and no claim of real-world coverage.
5. Proceed to Phase 5 fitting and performance claims only with verified, adequate historical
   data and out-of-sample evidence. Mathematical primitives alone do not constitute a
   validated prediction service.
6. Design the frontend against stable backend contracts; public display additionally
   requires rights to show provider-derived data and an approved exposure/security boundary.

The developer must approve any change to the Phase 4/5 ordering or these entry gates in a
subsequent decision; this proposal does not supersede ADR-0002 through ADR-0007.

## Alternatives considered

- **Implement both phases immediately with synthetic data.** Rejected: synthetic tests can
  verify formulas but cannot establish coverage, fit parameters, or validate predictions.
- **Implement an uncalibrated public model and label it experimental.** Rejected: an
  unprotected write API, unclear data rights, and absent point-in-time evidence are not
  cured by a disclaimer.
- **Stop all activity without an audit.** Safe, but would leave the developer without a
  bounded list of decisions and evidence needed to proceed.

## Consequences

- Phase 4 and Phase 5 remain **not implemented** while the entry decisions are pending.
- Descriptive calculations and probability mathematics may later be implemented and tested
  separately from claims about predictive validity; the latter require historical evidence.
- No frontend dependency or migration is added by this decision. The sequence is reversible
  until an implementation decision is accepted.

## Risks

- Provider coverage or licensing may make the proposed scope infeasible or expensive.
- Current mutable statistics and incomplete historical reconstruction may prevent honest
  pre-kickoff backtesting even after live data arrives.
- Independent reviewers may discover further Phase 3 defects. Their findings must be
  addressed, not treated as implied approval.

## Open decisions

- Does the developer accept or amend Phase 3 and ADR-0002 through ADR-0007?
- Which provider, plan, competition/seasons, and data/display licence are approved?
- Is an offline, synthetic-only Phase 4 intelligence implementation permitted before live
  verification, explicitly without model fitting or predictive claims?
- What evidence and review gate should permit Phase 5 model fitting, analysis API, and UI?
