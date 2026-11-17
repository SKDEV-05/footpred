# Phase 7 — Dixon-Coles Research Note

**Date:** 2026-11-17
**Status:** Model implemented and evaluated; **no proven gain over Poisson** on the stored corpus
**Model version:** `dixon-coles-v1.0.0`, parameter version `rho-v1.0`
**Scope:** Low-score dependence in association-football scorelines, the implementation used
here, and the measured effect.

## 1. Why a low-score correction exists

An independent Poisson model treats home and away goals as unrelated Poisson variables. That
implies the probability of a 0-0 is the product of the two zero-goal probabilities, and
similarly for 1-0, 0-1 and 1-1. In real league football those four cells are systematically
misestimated: goalless and 1-1 draws occur more often, and 1-0/0-1 less often, than
independence predicts (Dixon & Coles, 1997).

Dixon-Coles multiplies only those four cells by a factor `tau`, leaving every other score
cell untouched, then renormalises the finite matrix. One parameter, `rho`, controls the
direction and size of the adjustment.

## 2. The correction as implemented

For home rate `λ`, away rate `μ`, and cells `(home_goals, away_goals)`:

```
tau(0,0) = 1 - λ·μ·ρ
tau(0,1) = 1 + λ·ρ
tau(1,0) = 1 + μ·ρ
tau(1,1) = 1 - ρ
tau(x,y) = 1            otherwise
```

All four factors must stay strictly positive. Solving the four inequalities gives the
admissible interval for a given pair of rates:

```
lower = max(-1/λ, -1/μ) = -1 / max(λ, μ)
upper = min(1/(λ·μ), 1)
```

The implementation clips `rho` into that interval per match, so a fitted value can never
produce a negative cell probability. The global fit is additionally bounded to
`[-0.30, +0.30]` as a guard against a degenerate likelihood; that bound is a numerical
guard, not a prior.

Sign reading:

- **positive rho** raises 0-0 and 1-1 and lowers 1-0/0-1 (more draws, fewer 1-0 wins);
- **negative rho** does the opposite (fewer draws, more 1-0/0-1).

## 3. Fitting procedure

| Element | Value |
|---|---|
| Estimator | Weighted maximum likelihood on training matches only |
| Time weighting | Exponential, half-life 180 days |
| Search | Grid step 0.0025 over ±0.30, then 4 refinement rounds |
| Minimum sample | 30 matches, else `IDENTITY_NO_TRAINING_DATA` and rho = 0 |
| Training boundary | `kickoff_utc < reference_kickoff`, enforced inside `fit_rho` |
| Rates | Reused from the shared Poisson estimator (two-stage fit) |

Two properties matter for honesty:

1. **The fit is two-stage, not joint.** A full Dixon-Coles model estimates attack, defence
   and `rho` together. Here the rates are fixed first and only `rho` is fitted. The model
   can therefore adjust draw mass but cannot correct a rate error. The API reports
   `two_stage_rate_and_rho_estimation_not_joint_mle` as a limitation on every DC report.
2. **The training boundary is enforced in the fit itself**, not only by the caller. A
   future observation passed by mistake is filtered out before the likelihood is computed.
   A unit test duplicates future observations to prove the estimate does not change.

## 4. Evaluation versus live behaviour (important)

The two code paths fit at different cadences:

| Path | When rho is fitted | Data used |
|---|---|---|
| Evaluation (`phase7-v1`) | Once, at the competition's first target kickoff, then frozen for the window | Prior matches up to that kickoff |
| Live match report | On each request | All point-in-time matches before the target kickoff |

So the evaluated DC is a **frozen-parameter** version, while the live report uses a
refreshed parameter. The evaluation is the more conservative test (no parameter updates),
but it is not literally the live configuration. This is recorded as finding MR-11 and
should be resolved before anyone quotes a live DC number as "the evaluated model".

## 5. Measured effect

Persisted run 2 (`48bc547bf6a88850…`), 970 matches, 11 competitions:

| Metric | Poisson | Dixon-Coles |
|---|---:|---:|
| Brier | 0.5831 | 0.5829 |
| Log loss | 0.9828 | 0.9821 |
| Brier skill vs uniform | 0.1253 | 0.1256 |
| ECE | 0.0254 | 0.0258 |
| MCE | 0.4497 | 0.4457 |
| Top-pick accuracy | 51.55% | 51.34% |
| Draw calibration gap | +0.0004 | +0.0046 |

Paired bootstrap, candidate − Poisson:

| Metric | Mean | 95% CI | Reading |
|---|---:|---|---|
| Brier | +0.0002 | [−0.0009, +0.0013] | no difference |
| Log loss | +0.0006 | [−0.0015, +0.0027] | no difference |

The interval is narrow enough to exclude any practically meaningful improvement. DC is
neither better nor worse on this corpus.

### 5.1 Fitted rho by competition

| Competition id | Training matches | rho | Sign |
|---:|---:|---:|---|
| 1 | 619 | −0.0688 | negative |
| 2 | 286 | −0.0405 | negative |
| 3 | 295 | −0.0023 | ≈ zero |
| 4 | 398 | +0.0056 | ≈ zero |
| 5 | 456 | −0.0313 | negative |
| 6 | 380 | −0.0958 | negative |
| 7 | 156 | −0.0453 | negative |
| 9 | 390 | +0.0603 | positive |
| 10 | 312 | −0.1189 | negative |
| 11 | 299 | +0.0594 | positive |
| 12 | 187 | +0.0923 | positive |

The sign is not stable. That is consistent with a small, competition-specific effect, and
with fitting noise on 156–619 matches. A single global rho would average incompatible
signs; the implementation deliberately fits per competition.

### 5.2 Where the correction helps and hurts

Per-competition Brier (Poisson → DC):

| Competition | Poisson | DC | Direction |
|---|---:|---:|---|
| 1 | 0.5368 | 0.5378 | slightly worse |
| 2 | 0.5588 | 0.5593 | slightly worse |
| 3 | 0.6077 | 0.6077 | unchanged |
| 4 | 0.5539 | 0.5540 | unchanged |
| 5 | 0.6611 | 0.6596 | better |
| 6 | 0.6436 | 0.6415 | better |
| 7 | 0.5814 | 0.5849 | worse |
| 9 | 0.5127 | 0.5119 | better |
| 10 | 0.6290 | 0.6249 | better |
| 11 | 0.5228 | 0.5222 | better |
| 12 | 0.6035 | 0.6065 | worse |

Five competitions improve, four worsen, two are unchanged; the magnitudes are 0.0001–0.004
in each direction. This is noise-level, not a systematic gain.

## 6. Why the model is kept

- It is a genuine football model with a published basis, not a cosmetic variant.
- It is a permanent comparison partner for the Poisson baseline: removing it would make
  the "does low-score dependence help?" question unanswerable.
- It is evaluation-only. `poisson` remains the default and the live baseline; DC is never
  substituted silently.

## 7. When to revisit

Revisit only with new evidence, not to chase a headline:

1. Implement a genuine **joint** MLE (rates and rho together) and compare that, not the
   two-stage approximation.
2. Evaluate on more seasons per competition, so per-competition rho is estimated on
   materially more than 156–619 matches.
3. Consider a hierarchical/partial-pooling rho if the sign instability persists.
4. Evaluate the live cadence (refit per fixture) rather than a frozen window parameter.
5. Only then decide via ADR whether DC should influence any user-facing default.

## 8. Related documents

- `phase-7-independent-model-review.md`
- `phase-7-multi-competition-backtest.md`
- `apps/backend/app/intelligence/models/dixon_coles.py`
- `apps/backend/tests/unit/test_phase7_models.py`
