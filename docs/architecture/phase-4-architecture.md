# Phase 4 Offline Intelligence Architecture

**Status:** Implemented for synthetic-test-only use. Real-data validation is blocked.
**Date:** 2026-11-14

## Boundary

`apps/backend/app/intelligence/` is a pure computation package. It accepts immutable values
and returns immutable reports. It performs no I/O and imports no Phase 3 database, provider,
ingestion, repository, API, sync, or worker module.

```text
explicit synthetic dataset
        |
        v
validated observation contracts
        |
        +--> descriptive metrics --> quality/abstention --> feature snapshot
        |
        +--> supplied model parameters --> score matrix --> market arithmetic
        |
        +--> supplied observations/predictions --> evaluation mechanics
```

The descriptive intelligence engine and mathematical primitives are deliberately separate.
Features do not automatically become model inputs, and a quality classification is not a
probability or confidence score.

## Modules

| Module | Responsibility |
| --- | --- |
| `types.py` | UTC, immutable historical match/request/dataset contracts and input digest |
| `metrics.py` | Team form, listed-side/neutral splits, competition context, H2H |
| `quality.py` | Explicit versioned sample policy and abstention |
| `features.py` | Versioned feature registry and point-in-time values |
| `reports.py` | Structured intelligence report |
| `engine.py` | Synthetic-only orchestration |
| `models/poisson.py` | PMF and unconditional finite joint matrix with explicit overflow |
| `models/dixon_coles.py` | Supplied-parameter low-score adjustment with mass conservation |
| `models/elo.py` | Supplied-policy sequential rating transitions |
| `probabilities.py` | 1X2 bounds, double chance, totals, BTTS, top scorelines |
| `evaluation.py` | Proper scores, reliability summaries, chronological folds/partitions |

## Failure behavior

- Invalid timestamps, identities, scores, rates, probabilities, or policies raise
  `ValueError`; no partial report is returned.
- Empty valid history yields unavailable rates (`None`), never a fabricated zero.
- Insufficient samples produce a structured ineligible assessment.
- Future or not-yet-observed results are excluded; the cutoff is strict.
- A target fixture present in its own history dataset is rejected.
- Duplicate dataset or Elo fixture IDs are rejected.
- Rates that need a goal range above the supported maximum cannot produce a matrix.
- Dixon-Coles `rho` outside its admissible interval, or mass drift beyond tolerance, is
  rejected rather than renormalized.

## Reproducibility

The dataset SHA-256 digest covers canonical, sorted JSON with explicit nulls and UTC
timestamps. A separate configuration digest covers the target kickoff, season, neutral
state, analysis cutoff, form and H2H windows, both policy values, protocol version, and
feature versions. Neither digest is a signature or tamper-proof store. The package reads no
clock, environment, database, or random state; `generated_at` is supplied by the caller.

## Deferred boundaries

The following require new approval:

- ORM/repository adapters and schema migrations;
- model fitting, parameter estimation, calibration fitting, or real backtests;
- immutable prediction/feature persistence;
- API endpoints, analysis jobs, rate limiting, or authentication;
- frontend or public display.
