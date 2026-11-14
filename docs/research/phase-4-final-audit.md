# Phase 4 Final Audit — Offline Intelligence and Mathematical Primitives

**Date:** 2026-11-14
**Author:** orchestrator (implementing agent). Specialist reviews were delegated but only
partially completed; this is a self-audit, not independent acceptance.
**Confidence:** high for software and mathematical behaviour under synthetic tests; none for
real-football validity
**Decision affected:** whether Phase 4 may be accepted as an offline, synthetic-test-only
foundation, and whether Phase 5 entry gates are met (they are not).

> Path requested by the developer. This intentionally deviates from the
> `YYYY-MM-DD-<topic>.md` naming convention in `docs/research/README.md`.

## Question

Is the Phase 4 offline intelligence package correct, reproducible, free of temporal leakage,
and honest about the limits of synthetic testing — and what remains blocked before Phase 5?

## Context

- Phase 3 backend is delivered but not accepted; live provider use is unverified and
  unlicensed (`LIM-001`, `LIM-006`, `LIM-007`, `LIM-008`).
- Phase 4 was approved as **offline, synthetic-test-only** by the developer on 2026-11-14,
  under twelve explicit conditions, recorded in
  [`ADR-0009`](../decisions/ADR-0009-pure-offline-intelligence-boundary.md).
- No database write, migration, provider call, API endpoint, frontend, model fitting, or real
  prediction was permitted.

## Method

1. Inspected Phase 3 models, ingestion, validation, API, and the memory/rules registers.
2. Delegated independent reviews: football domain, statistical, backend architecture, QA, and
   security. Findings were treated as blocking by default.
3. Implemented the package, then corrected every blocking finding raised, including two
   mathematical defects and one leaking baseline.
4. Re-ran the complete suite and compilation after each change.
5. Verified the package has no I/O surface by static AST inspection in a test.

## Verified facts

Each is reproducible from the repository at this date.

1. The complete backend suite passes: **208 passed**, one third-party Starlette deprecation
   warning, no failures. Phase 3 integration tests: 66. Phase 3 unit tests: 58.
   Phase 4 tests: 84. (Source: local `pytest` run, 2026-11-14.)
2. `app/intelligence` imports no database, provider, ingestion, repository, API, sync, worker,
   FastAPI, SQLAlchemy, HTTPX, or APScheduler module; this is asserted by
   `tests/unit/test_intelligence_boundary.py`. (Source: AST scan in tests.)
3. The package reads no wall clock, environment variable, filesystem, network, or random
   state; `generated_at` is a caller-supplied argument. (Source: same test file.)
4. A dataset digest and a separate configuration digest are computed over canonical JSON with
   `allow_nan=False`; the configuration digest covers kickoff, season, neutral state, cutoff,
   windows, both policies, protocol version, and feature versions.
5. Results observed at or after the analysis cutoff, and fixtures at or after it, are
   excluded; the target fixture cannot appear in its own history. (Tests:
   `test_observation_at_cutoff_is_strictly_excluded`,
   `test_target_fixture_cannot_contribute_to_its_own_history`,
   `test_elo_excludes_result_observed_at_or_after_cutoff`.)
6. Neutral fixtures are excluded from competition home/away baselines and are never counted
   as home or away form. (Tests: `test_team_form_separates_listed_venue_and_neutral_matches`,
   competition-context tests.)
7. The Poisson matrix contains exact cells `0..K` plus one marginal overflow category per
   team, totals 1 within `1e-12`, and does not renormalize truncated exact-cell mass. 1X2 is
   returned as bounds with explicit unresolved probability. (Tests over a 6×6 rate grid.)
8. Dixon-Coles applies the four standard `tau` factors, rejects `rho` outside the admissible
   interval, rejects negative factors, and requires mass conservation within `1e-12` instead
   of renormalizing.
9. Rolling-origin folds reject overlapping validation windows (`step < validation_size`) and
   reject a training label unavailable before the next partition. An explicit
   train/calibration/test/final-holdout partition is available.
10. Binary Brier, binary log loss, unnormalized multiclass Brier, multiclass log loss, and
    one-vs-rest reliability summaries produce hand-checked reference values; a confident
    impossible true outcome returns infinity rather than being clipped.
11. Benchmark-and-insight claims about real football are absent: no fitted rate, `rho`, Elo
    policy, calibration map, or performance number exists anywhere in the package.

## Analysis

### Implemented components

| Component | Status | Evidence |
| --- | --- | --- |
| Immutable UTC contracts, dataset digest, research context | VERIFIED | unit tests; strict timezone rejection |
| Team form, listed-side and neutral splits | VERIFIED | reference-value tests |
| Competition context excluding neutral fixtures | VERIFIED | neutral and non-standard points tests |
| Head-to-head, orientation-normalised, context only | VERIFIED | mixed-orientation test |
| Versioned point-in-time features with evidence timestamps | VERIFIED | per-feature source audit test |
| Sample coverage classification and abstention | VERIFIED | boundary tests at `N-1`, `N` |
| Structured report with reproducible configuration | VERIFIED | config-digest divergence test |
| Poisson score matrix with overflow | VERIFIED | 36-case rate grid invariants |
| Dixon-Coles low-score adjustment | VERIFIED | mass conservation, admissible bounds |
| Sequential Elo | VERIFIED | zero-sum, same-kickoff batching, cutoff exclusion |
| 1X2, double chance, over/under, BTTS, correct score | VERIFIED | bounds and monotonicity invariants |
| Brier, log loss, reliability, temporal folds | VERIFIED | arithmetic and leakage tests |
| No-I/O boundary | VERIFIED | AST-based boundary tests |

### Statistical methodology

- **Poisson**: caller-supplied rates only, recurrence PMF, `K` chosen adaptively until the
  overflow-overflow cell is below tolerance. The model is a primitive, not an estimator.
- **Dixon-Coles**: supplied `rho`; standard four-cell adjustment; admissibility interval
  `rho >= max(-1/lambda)` and `rho <= min(1, 1/(lambda_home*lambda_away))`.
- **Elo**: supplied `K`, scale, initial rating, home offset; chronological replay; same-kickoff
  batches computed from one pre-batch state; neutral venues use no home offset; only
  pre-cutoff observations eligible.
- **Uncertainty**: no confidence intervals, calibration fits, or significance claims are made;
  the unresolved score mass is exposed rather than hidden.

### Probability methodology

All markets derive from one matrix. 1X2 and double chance return lower/upper bounds because
the overflow-overflow cell cannot determine a winner; over/under and BTTS use overflow cells
where the outcome is logically determined; correct-score output excludes overflow categories
and therefore does not claim to preserve total mass.

### Synthetic-only restrictions

Enforced in three layers:

1. A dataset must be constructed with `DataClassification.SYNTHETIC_TEST`; the engine rejects
   anything else.
2. Every mathematical and evaluation entry point requires a validated `ResearchContext`
   carrying that classification, a SHA-256 dataset digest, and a protocol version.
3. Outputs and reports carry the classification and limitations, including
   `offline_synthetic_test_only` and `descriptive_metrics_not_validated_predictors`.

Residual risk: classification is caller-asserted. A deliberately mislabelled real dataset
cannot be detected. This is documented, not solved.

### Security review

Delegated review of the offline boundary and the implementing agent's checks found no secrets,
logging, network, filesystem, or database access in the package. Three blocking issues were
found, all now fixed: bypassable synthetic enforcement, non-finite/loose numeric acceptance,
and unbounded inputs. Current
controls: exact `int` checks for goals and points, `isfinite` checks on rates/metrics/feature
values, explicit size caps (dataset 100 000 matches; PMF 1 000; Elo 100 000 results; folds
10 000; reliability bins 1 000), and `allow_nan=False` serialization.

### Test results (executed 2026-11-14)

| Suite | Result |
| --- | --- |
| Complete backend suite | 208 passed |
| Phase 3 integration tests | 66 passed |
| Phase 3 unit tests | 58 passed |
| Phase 4 intelligence tests | 84 passed |
| `compileall` over app and tests | exit 0 |
| Live provider calls | none attempted |
| Database writes / migrations | none |

## Recommendation

Accept Phase 4 as an **offline, synthetic-test-only mathematical and descriptive foundation**,
with the explicit understanding that it provides **no evidence of predictive value,
calibration, or football coverage**. Do not treat any output as a match prediction.

## Assumptions

- The developer's approval covers only the boundary in ADR-0009.
- Synthetic fixtures are adequate for testing arithmetic and leakage guards.
- Callers of low-level primitives behave honestly; classification cannot be cryptographically
  enforced in-process.

## Limitations

- Every metric is descriptive, opponent-strength unadjusted, and not shrunk.
- Sample-coverage thresholds are caller policy, not empirically justified values.
- No first-half, xG, lineup, injury, standings, tie-state, or competition-strength features.
- No calibration fitting, confidence intervals, holdout execution, or persisted experiments.
- Elo produces a two-outcome rating expectation, not a three-way probability.
- Poisson/Dixon-Coles parameters are supplied, never estimated.
- Digests detect change; they are not signatures or tamper-proof storage.
- The 208-test figure is a local run by the implementing agent, not an independent CI result.

## Open questions

| ID | Question | Owner | Resolution path |
| --- | --- | --- | --- |
| Q1 | Which provider, plan, competitions, seasons, and display licence apply? | Developer | PD-002/PD-003/PD-004, LIM-006 |
| Q2 | How will regulation, extra-time, and shootout scores be separated in storage? | data-engineer | GAP-018; provider semantics verified live |
| Q3 | How will neutral venues be represented in canonical data? | backend-architect | schema decision, requires approval |
| Q4 | What point-in-time snapshot or bitemporal model is acceptable? | backend-architect | ADR plus migration approval |
| Q5 | Which sample thresholds and shrinkage are empirically justified? | ml-researcher | frozen out-of-sample evaluation |
| Q6 | Is xG licensed and comparable, or omitted? | football-analyst | PD-005 |

## Phase 5 prerequisites

1. Developer acceptance of Phase 4 and of Phase 3 as its input.
2. Independent QA/security sign-off on the Phase 4 audit (the current review is specialist
   delegation, not final acceptance).
3. Verified, licensed competition coverage with recorded evidence.
4. Trustworthy regulation-time, neutral-venue, and point-in-time source contracts.
5. Approved snapshot/migration design if any persistence is required.
6. A frozen evaluation protocol: baselines, temporal splits, calibration window, untouched
   holdout, abstention rules, metrics, and uncertainty reporting.
7. Explicit Phase 5 approval covering model fitting, persistence, API, and any frontend.

## Sources

- Repository: `apps/backend/app/intelligence/`, `apps/backend/tests/unit/`
- Decisions: `docs/decisions/ADR-0009-pure-offline-intelligence-boundary.md`,
  `ADR-0008-phase-4-5-entry-gates.md`
- Registers: `memory/known-limitations.md`, `PROJECT_STATUS.md`
- Access date for all repository claims: 2026-11-14.
- No external source is cited because no external fact is asserted.
