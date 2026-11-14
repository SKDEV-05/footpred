# ADR-0009 — Pure offline intelligence boundary

**Status:** Accepted — explicitly approved by the developer.
**Date:** 2026-11-14
**Owners:** developer, backend-architect, football-analyst, ml-researcher
**Related:** [ADR-0008](ADR-0008-phase-4-5-entry-gates.md),
[Phase 4 architecture](../architecture/phase-4-architecture.md)

## Context

The repository has no verified football history, no approved provider licence, and no
point-in-time statistics store. The developer nevertheless approved a bounded Phase 4 that
uses only synthetic test data to establish software and mathematical correctness. It must not
fit a model, make real predictions, claim accuracy, change the SQLite schema, call a
provider, expose APIs, or begin Phase 5.

## Decision

Implement Phase 4 as a pure `app.intelligence` Python package:

- frozen input and output contracts;
- regulation-time historical observations with explicit neutral venue and observation time;
- descriptive form, venue, competition, and head-to-head metrics;
- versioned feature definitions, explicit missing values, source match IDs, and as-of time;
- caller-supplied, versioned points and sample-coverage policies;
- quality classification and abstention;
- independent-Poisson, Dixon-Coles low-score adjustment, and sequential Elo primitives;
- score-matrix market arithmetic;
- Brier score, log loss, fixed-bin reliability summaries, and rolling-origin fold mechanics.

The package has no database, repository, provider, API, scheduler, worker, environment,
network, wall-clock, or random-number dependency. Its top-level intelligence engine rejects
any dataset not classified `synthetic_test_data`. Mathematical model constructors label
their output synthetic-test data and accept supplied parameters only; they do not estimate
football parameters.

## Alternatives considered

- **Read current ORM rows directly.** Rejected because current statistics are mutable and
  regulation-score, neutral-venue, and exact point-in-time reconstruction are incomplete.
- **Add snapshot and prediction tables now.** Rejected because schema changes require
  separate approval and Phase 5 is prohibited.
- **Implement no model mathematics.** Rejected because the approved scope explicitly asks
  for statistical architecture, probability infrastructure, and evaluation mechanics.

## Consequences

- Synthetic tests can verify formulas, invariants, leakage guards, missing-data behavior,
  and deterministic replay.
- They cannot establish predictive validity, calibration, parameter suitability, provider
  coverage, or performance on any real competition.
- A future storage adapter may construct these contracts only after point-in-time data and
  migration designs receive separate approval.
- Poisson and Dixon-Coles consume supplied goal rates; Elo consumes supplied configuration.
  No defaults are represented as empirically suitable for football.

## Risks

- A future caller could misuse low-level mathematical functions with real values outside the
  approved application flow. Documentation and output classification reduce but cannot
  eliminate misuse.
- The default metric set is descriptive and not opponent-strength adjusted.
- Sample-policy values are caller policy, not evidence of predictive reliability.

## Amendment — 2026-11-14 (independent review)

The first implementation normalized a truncated finite matrix, which conditioned derived
markets on `home, away <= K` without saying so. Independent statistical and security review
found this unacceptable. The implementation now keeps one explicit marginal overflow
category per team, never renormalizes tail mass, excludes overflow cells from correct-score
output, and returns 1X2 lower/upper bounds plus unresolved mass. Dixon-Coles must conserve
mass rather than renormalize. This amendment changes the implementation, not the decision.

## Revisit when

- licensed historical coverage is verified;
- regulation-time, neutral-venue, and point-in-time source contracts are trustworthy;
- a schema migration or offline storage adapter is proposed;
- Phase 5 model fitting, persistence, API delivery, or frontend work is explicitly approved.
