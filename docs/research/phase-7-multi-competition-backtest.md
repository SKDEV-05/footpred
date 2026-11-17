# Phase 7 — Multi-Competition Rolling-Origin Backtest

**Date:** 2026-11-17
**Protocol:** `phase7-v1`
**Evaluation version:** `evaluation-v1.2.0`
**Status:** Executed and persisted; reproduced on the current corpus; idempotent
**Scope:** How the evaluation works, what it produced, and what it cannot prove.

## 1. Purpose

One chronological pass predicts every eligible match once, with every model, from the same
information cutoff, and scores all models on the identical match set. This is what makes a
model comparison legitimate: no model sees more matches, later information, or a different
target set.

## 2. Protocol as implemented

### 2.1 Ordering and eligibility

1. Matches are ordered by kickoff (ties broken deterministically).
2. A result becomes usable only when `kickoff + 3 h <= target kickoff`. The horizon is a
   documented retrospective bound: the corpus was backfilled in one retrieval window, so the
   provider's original publication time cannot be reconstructed.
3. All matches sharing a kickoff are processed as one group. A simultaneous result can never
   inform another match at the same kickoff, and Elo applies a group as one batch.
4. Only regulation-time results participate. Extra time and shootouts are excluded upstream
   by the corpus loader.

The helper `result_is_available(result_kickoff, target_kickoff)` exists so the horizon is a
testable rule rather than an inline arithmetic expression. Tests pin the exact boundary
(+3 h is available, −1 s is not) and reject naive timestamps and negative horizons.

### 2.2 Target selection

Per competition:

- the **last 100 matches** are targets (`MAX_TEST_PER_COMPETITION = 100`);
- a competition needs at least **50 matches** to be evaluated and at least **40 prior**
  matches before its first target (`MIN_PRIOR_MATCHES = 40`);
- a competition below the threshold is reported with `status = INSUFFICIENT_DATA`, its
  sample size and the required count — never silently dropped and never scored.

### 2.3 Parameter fitting

For each competition, the first target kickoff is the fitting point:

- Poisson rates/form come from the shared estimator over available prior matches;
- DC `rho` is fitted on prior matches, then frozen for the competition's window;
- Elo ratings are replayed continuously; the Davidson `home_advantage` and `draw_nu` are
  fitted on pre-window Elo pairs, then frozen.

Frozen parameters are recorded in the report (`fitted_parameters` per competition), so a
reader can see exactly what the evaluation used. See
`phase-7-dixon-coles-research.md` §4 for the difference between this frozen cadence and the
live per-request refit.

### 2.4 Scoring

| Metric | Definition |
|---|---|
| Brier | mean squared error of the 3-vector, lower better; uniform = 0.6667 |
| Log loss | mean negative log probability of the observed outcome |
| Brier skill | `1 − model Brier / uniform Brier` |
| ECE | sample-weighted mean gap between predicted probability and observed rate across bins |
| MCE | worst bin gap |
| Top-pick accuracy | share of matches where the highest-probability outcome occurred |
| Per-outcome metrics | each class scored as its own binary problem |
| Paired differences | candidate − Poisson, on the same rows, with a paired bootstrap |

Calibration uses 5 fixed-width probability bins per class. Timeline uses consecutive
25-match buckets in kickoff order.

### 2.5 Uncertainty

- Percentile bootstrap, **1,000 resamples**, fixed seed `20261116`.
- The same seed is used for every model, so a rerun is byte-identical.
- Intervals are reported for Brier and log loss, and for each paired difference.

Caveat: the bootstrap resamples matches as independent units. Matches are clustered by
competition, season, matchday and team, so these intervals are likely **too narrow**. They
are a lower bound on uncertainty, not a precise statement.

## 3. Stored runs

| Run | Digest | Sample | Generated | Note |
|---:|---|---:|---|---|
| 1 | `bde93c2d1684d713…` | 970 | 2026-11-16T19:49Z | Original run |
| 2 | `48bc547bf6a88850…` | 970 | 2026-11-17T09:22Z | Current corpus |

Run 2 exists because two results (`match_id` 1 and 2) were re-resolved after run 1, changing
`resolved_at` and therefore the materialised corpus and its digest. Metrics are identical in
every field; only the identity changed. Repeated `evaluate_corpus` returns run 2, not a third
row. See `phase-7-baseline-audit.md` §6.3.

## 4. Result

**Sample:** 970 matches, 11 competitions, 2026-02-25T20:00Z → 2026-11-14T23:30Z.
**Corpus:** 4,892 regulation results, `verified_real_data`, provider `football_data_org`.

| Model | Brier | 95% CI | Log loss | 95% CI | Skill | ECE | MCE | Top-pick |
|---|---:|---|---:|---|---:|---:|---:|---:|
| Poisson | **0.5831** | [0.5620, 0.6046] | **0.9828** | [0.9481, 1.0124] | 0.1253 | 0.0254 | 0.4497 | 51.55% |
| Dixon-Coles | **0.5829** | [0.5620, 0.6037] | **0.9821** | [0.9480, 1.0117] | 0.1256 | 0.0258 | 0.4457 | 51.34% |
| Elo (Davidson) | 0.5911 | [0.5759, 0.6055] | 0.9916 | [0.9684, 1.0124] | 0.1133 | 0.0375 | 0.3638 | 51.55% |
| Competition frequency | 0.6405 | [0.6288, 0.6513] | 1.0592 | [1.0426, 1.0754] | 0.0393 | **0.0143** | 0.1206 | 45.36% |
| Uniform 1/3 | 0.6667 | — | 1.0986 | — | 0.0000 | 0.0802 | 0.1203 | 45.36% |

All five rows have `sample_size = 970`. That equality is enforced and tested.

### 4.1 Paired differences vs Poisson

Positive mean = Poisson had the higher loss on the same matches.

| Candidate | Brier mean | 95% CI | Log loss mean | 95% CI |
|---|---:|---|---:|---|
| Dixon-Coles | +0.0002 | [−0.0009, +0.0013] | +0.0006 | [−0.0015, +0.0027] |
| Elo | −0.0080 | [−0.0195, +0.0040] | −0.0088 | [−0.0279, +0.0100] |
| Uniform | −0.0835 | [−0.1051, −0.0619] | −0.1158 | [−0.1473, −0.0822] |
| Competition frequency | −0.0573 | [−0.0755, −0.0388] | −0.0764 | [−0.1041, −0.0492] |

Readings:

- Poisson is significantly better than both trivial baselines.
- DC is indistinguishable from Poisson.
- Elo is directionally worse but not proven different.

### 4.2 Per-outcome calibration gaps

Mean predicted probability − observed rate; positive = over-predicted.

| Model | Home | Draw | Away |
|---|---:|---:|---:|
| Poisson | −0.0047 | +0.0004 | +0.0043 |
| Dixon-Coles | −0.0068 | +0.0046 | +0.0022 |
| Elo | −0.0088 | +0.0211 | −0.0123 |
| Competition frequency | −0.0066 | +0.0215 | −0.0149 |
| Uniform | −0.1203 | +0.1045 | +0.0158 |

Observed rates are identical for every model: home 45.36%, draw 22.89%, away 31.75%.

### 4.3 Per competition

| Id | n | Poisson | DC | Elo | Skipped (abstain) |
|---:|---:|---:|---:|---:|---:|
| 1 | 100 | 0.5368 | 0.5378 | 0.5587 | 0 |
| 2 | 86 | 0.5588 | 0.5593 | 0.5769 | 14 |
| 3 | 90 | 0.6077 | 0.6077 | 0.6121 | 10 |
| 4 | 91 | 0.5539 | 0.5540 | 0.5855 | 9 |
| 5 | 100 | 0.6611 | 0.6596 | 0.6492 | 0 |
| 6 | 100 | 0.6436 | 0.6415 | 0.6360 | 0 |
| 7 | 76 | 0.5814 | 0.5849 | 0.5388 | 24 |
| 9 | 89 | 0.5127 | 0.5119 | 0.5611 | 11 |
| 10 | 88 | 0.6290 | 0.6249 | 0.6296 | 12 |
| 11 | 91 | 0.5228 | 0.5222 | 0.5500 | 9 |
| 12 | 59 | 0.6035 | 0.6065 | 0.5873 | 41 |

`skipped_history` is 0 everywhere: each competition had enough prior history. The
`skipped_model_abstention` column counts target matches where the shared feature/rate
estimator could not produce a ready prediction (typically a team without enough prior
matches). Those matches are excluded from **all** models, preserving the identical set.

No competition is labelled `INSUFFICIENT_DATA` in this run; every competition with stored
matches had at least 50 results. Two competitions (EC, WC) have no stored matches at all and
therefore do not appear. "13 competitions in the database" is not "13 evaluated".

### 4.4 Per season

15 competition/season blocks: sample sizes 2 to 100. The two-observation block
(competition 11, season 21) is a season-boundary fragment. Per-season metrics are
descriptive only; they are not used to claim a trend.

### 4.5 Timeline

39 consecutive buckets of 25 matches (last bucket 20). Brier moves between roughly 0.45 and
0.72 for Poisson across buckets, with no monotone trend. A bucket is a descriptive slice,
not a forecast. Publishing a "model improving over time" narrative from this would be
unsupported.

## 5. Reproducibility

- Same corpus + same protocol + same evaluation version → same row (unique constraint and
  tested idempotency).
- Same dataset object recomputed → identical metrics, intervals and report document.
- Across separate corpus loads, the report's `dataset.observed_to` records the load time, so
  two loads at different wall-clock moments differ in that one field while every metric and
  interval is identical. The stored row is reused by digest, so this does not create a new run.
- A changed corpus (including a changed `resolved_at`) produces a new digest and a new row;
  existing rows are never overwritten.

## 6. Threats to validity

1. **Clustered sample.** 970 matches are not 970 independent draws; bootstrap CIs are
   optimistic (see §2.5).
2. **No untouched holdout.** This corpus informed the protocol and model choices, so a
   small optimistic bias cannot be excluded.
3. **Retrospective observation times.** The 3 h horizon may admit a result earlier than the
   provider truly published it.
4. **One provider, one backfill.** Provider-side correctness and coverage are unverified.
5. **Small per-competition samples.** 59–100 matches per competition cannot establish a
   per-league ranking.
6. **Frozen evaluation parameters vs live refit** (MR-11).
7. **No multiplicity correction** across four comparisons, though no conclusion depends on
   a borderline interval.

## 7. What this run supports

- A reproducible, chronological, identical-set evaluation exists and is persisted.
- All three statistical models beat a uniform forecast in point estimate; only the
  baselines comparison is statistically conclusive.
- DC is not proven better than Poisson; Elo is not proven different.
- No claim about future accuracy, profit, or any competition ranking is supported.

## 8. Related documents

- `phase-7-baseline-audit.md`
- `phase-7-independent-model-review.md`
- `phase-7-model-comparison.md`
- `apps/backend/app/intelligence/backtest.py`
- `apps/backend/tests/unit/test_phase7_backtest.py`
- `apps/backend/tests/integration/test_evaluation_api.py`
