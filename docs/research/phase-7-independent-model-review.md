# Phase 7 — Independent Model Review (internal)

**Date:** 2026-11-17
**Status:** Complete — internal review, **not** independent external review
**Reviewer:** implementing agent (self-review; the reviewer wrote part of the code under review)
**Scope:** Poisson, Dixon-Coles, Elo + Davidson, the evaluation protocol, and the claims the
Phase 7 report is allowed to make.

## 0. Independence statement

This review was performed by the same agent that implemented the model-selection layer and
the tests. It is therefore **not** independent in the sense required by `AGENTS.md` §7 and
`memory/known-limitations.md` LIM-019. It is a structured technical self-review, and every
claim below is tied to a measurable output or a code location. External sign-off remains an
open gate.

## 1. What was reviewed

| Item | Location |
|---|---|
| Poisson live path | `app/intelligence/prediction.py` |
| Poisson score matrix | `app/intelligence/models/poisson.py` |
| Dixon-Coles fit and matrix | `app/intelligence/models/dixon_coles.py` |
| Elo replay + Davidson fit | `app/intelligence/models/elo_fitted.py` |
| Baselines | `app/intelligence/baselines.py` |
| Evaluation engine | `app/intelligence/backtest.py` |
| Model dispatch | `app/intelligence/model_selection.py` |
| Metrics | `app/intelligence/evaluation.py` |

The review used the persisted report (run 2, digest `48bc547bf6a88850…`, 970 matches) and
the new unit/integration tests. Numbers below are from that stored report.

## 2. Poisson — assessed sound as a baseline

Verified properties:

- independent Poisson goal model with competition-baselined rates, attack/defence
  strengths, venue shrinkage and recent-form blending;
- expected goals are bounded, the score matrix is finite with explicit overflow
  categories, and 1X2 is normalised to 1.0;
- live path and backtest use the same estimator (`estimate_goal_rates`), so an evaluation
  number describes the code that serves users.

Measured on 970 matches:

| Metric | Value |
|---|---:|
| Brier | 0.5831 |
| Log loss | 0.9828 |
| Brier skill vs uniform | 0.1253 |
| ECE | 0.0254 |
| Brier 95% CI | [0.5620, 0.6046] |

Per-outcome calibration gap (mean probability − observed rate):

| Outcome | Gap |
|---|---:|
| Home | −0.0047 |
| Draw | +0.0004 |
| Away | +0.0043 |

**Draw bias is not present at the aggregate level on this window.** The earlier PD-only
finding (draw bin 0.20–0.40 predicted 0.2465, observed 0.3158 on 50 matches) does not
generalise. On 970 matches the draw bin 0.20–0.40 predicts 0.2493 and observes 0.2553, a
0.6 pp under-prediction. Both figures are real measurements of different windows; neither
may be quoted without its window.

Weakness found: the largest calibration error comes from a bin with **two** observations
(draw 0.40–0.60, predicted 0.4497, observed 0.0000). This single bin drives MCE = 0.4497
while ECE is 0.0254. MCE must not be read as a model-quality summary on this sample.

## 3. Dixon-Coles — correctly implemented, no proven gain

Implementation: the Poisson rate estimator is reused unchanged, then `rho` is fitted by
time-weighted maximum likelihood on training matches only, bounded to ±0.30 and refined on
a grid, and finally clipped per match so every low-score correction stays positive. This is
a **two-stage** fit: rates are not re-estimated jointly with rho. That is a documented
simplification, not a bug, but it means DC cannot repair a rate misspecification — it can
only move probability mass among 0-0, 1-0, 0-1 and 1-1.

Measured:

| Metric | Poisson | Dixon-Coles |
|---|---:|---:|
| Brier | 0.5831 | 0.5829 |
| Log loss | 0.9828 | 0.9821 |
| Brier skill | 0.1253 | 0.1256 |
| ECE | 0.0254 | 0.0258 |
| Draw gap | +0.0004 | +0.0046 |

Paired difference (candidate − Poisson on the same matches):

| Metric | Mean | 95% CI |
|---|---:|---|
| Brier | +0.0002 | [−0.0009, +0.0013] |
| Log loss | +0.0006 | [−0.0015, +0.0027] |

**Verdict: no proven improvement and no proven harm.** A 0.0002 Brier difference is far
below any practically meaningful effect, and the interval spans zero. DC slightly
over-corrects draws on this window (+0.0046 vs +0.0004). Anyone claiming "Dixon-Coles is
better" from this run would be misreading the evidence.

Fitted rho per competition ranged from −0.1189 to +0.0923, on per-competition training sets of
156 to 619 matches. The sign is not stable across competitions, which is expected for a small
per-competition effect and argues against a single global rho.

## 4. Elo + Davidson — defensible, but structurally weaker here

Implementation:

- pure chronological replay, K = 20, initial 1500, scale 400, no goal-margin weighting;
- pre-match ratings are captured before a kickoff group is applied, so simultaneous
  matches cannot influence each other;
- `home_advantage` and `draw_nu` are fitted by grid maximum likelihood on pre-window
  matches and frozen for the competition's evaluation window;
- output is 1X2 only: no expected goals, no scoreline distribution, no BTTS or over/under.

Measured:

| Metric | Elo |
|---|---:|
| Brier | 0.5911 |
| Log loss | 0.9916 |
| Brier skill | 0.1133 |
| ECE | 0.0375 |
| Draw gap | +0.0211 |

Paired difference vs Poisson: Brier −0.0080, 95% CI [−0.0195, +0.0040]. Elo is not proven
worse, nor better. Its own Brier interval [0.5759, 0.6055] lies entirely below the uniform
score of 0.6667, so it is a real improvement on guessing; that is a marginal interval, not
a paired test against uniform, and must be described as such.

Findings:

1. **Global rating pool.** Every result in the corpus updates the Elo state, including
   other competitions. A Champions League match therefore moves a league rating. This is a
   deliberate simplicity, but it means Elo's "competition" fitting is only for the outcome
   mapping, not for the ratings. It should be stated wherever Elo numbers are shown.
2. **Fitted home advantage is unstable across competitions** (15.6 to 129.4 Elo points) on
   156–619 training matches. With a coarse grid and small samples this is expected; it also
   means Elo's home edge can differ sharply from the Poisson baseline's.
3. **Draw over-prediction** (+0.0211) is the largest draw gap of the three models, despite
   the Davidson term. The mapping is fitted per competition on pre-window data, so this is
   a genuine out-of-sample bias, not leakage.
4. **MCE is dominated by tiny bins**: away 0.60–0.80 has n = 2 and home 0.20–0.40 has
   n = 306 with a 7 pp over-prediction. ECE (0.0375) is the usable summary.

## 5. Baselines

| Baseline | Brier | Log loss | Skill | ECE |
|---|---:|---:|---:|---:|
| Uniform 1/3 | 0.6667 | 1.0986 | 0.0000 | 0.0802 |
| Competition frequency | 0.6405 | 1.0592 | 0.0393 | 0.0143 |

The frequency baseline is better calibrated than every model (ECE 0.0143) and worse at
discrimination (Brier 0.6405). That is the expected signature of a marginal-rate forecast:
it gets the average right and cannot separate matches. It is a useful honesty check — a
model that cannot beat it has no demonstrated discrimination.

## 6. Protocol review

Sound:

- one chronological pass, all models scored on the identical match set;
- results eligible only at `kickoff + 3 h`; simultaneous kickoffs never inform each other;
- per-competition parameters fitted before the first target kickoff and frozen;
- deterministic percentile bootstrap (1,000 resamples, fixed seed);
- explicit abstention for insufficient history;
- leakage guards in both the engine and `fit_rho`.

Residual risks, in order of importance:

1. **Bootstrap ignores clustering.** Matches are resampled i.i.d., but they are clustered by
   competition, season, matchday and team. The reported intervals are therefore likely
   **too narrow**. The correct reading is "the interval is a lower bound on uncertainty",
   not "the effect is precise".
2. **No untouched final holdout.** The 970 matches are the only evaluation sample. Protocol
   and model choices were made with knowledge of this corpus, so a small optimistic bias
   cannot be excluded. Fixing it requires future matches, not a re-split.
3. **The 3 h horizon is a proxy.** If the provider published a result later than kickoff + 3 h,
   the evaluation used information slightly earlier than it truly existed. The size and
   direction of that error are unknown; the corpus is a backfill.
4. **No multiple-comparison correction.** Four pairwise comparisons are reported. With
   intervals that already cross zero, no correction changes the conclusion, but a future
   report with many markets would need one.
5. **MCE is unstable** at this sample size and should be presented as a diagnostic, not a
   headline.

## 7. Findings register

| ID | Finding | Severity | Action |
|---|---|---|---|
| MR-01 | DC shows no proven gain over Poisson; difference ≈ 0.0002 Brier | Informational | Report as "not proven"; keep Poisson default |
| MR-02 | Elo not proven different from Poisson, worse calibration on draws | Informational | Report honestly; no default change |
| MR-03 | Bootstrap treats clustered matches as independent; CIs likely narrow | Medium | Documented; future clustered bootstrap |
| MR-04 | No untouched holdout; protocol chosen with corpus knowledge | Medium | Documented; future out-of-time test |
| MR-05 | 3 h eligibility horizon is a retrospective proxy | Medium | Documented in report, dashboard and memory |
| MR-06 | MCE dominated by very small bins | Low | Dashboard shows ECE as primary; MCE secondary |
| MR-07 | Elo ratings pool across competitions | Low | Documented in model limitations |
| MR-08 | DC is a two-stage fit, not joint MLE | Low | Documented in API limitations and report |
| MR-09 | Draw bias is window-dependent (PD-only vs 970-match corpus) | Medium | Both windows recorded; no global claim |
| MR-10 | No external independent review of any model | High | Remains an open blocker |
| MR-11 | Evaluated DC/Elo fit is frozen at the competition's first target kickoff, while the live path refits before each fixture | Medium | Documented here and in the comparison doc; a future protocol should evaluate the live cadence or the live path should freeze |

## 8. What may and may not be claimed

May be claimed:

- every model beats a uniform 1/3 forecast with a paired interval excluding zero on this
  corpus;
- Poisson and Dixon-Coles are indistinguishable on this corpus;
- Elo is directionally worse but not proven different;
- the frequency baseline is better calibrated and worse at discrimination.

May **not** be claimed:

- that any model is "the best";
- any accuracy percentage, expected profit, or guaranteed outcome;
- that DC or Elo is production-ready;
- that these numbers generalise beyond the stored corpus, provider or window;
- that the evaluation reconstructs what was known live at each historical moment.

## 9. Related documents

- `phase-7-dixon-coles-research.md`
- `phase-7-multi-competition-backtest.md`
- `phase-7-model-comparison.md`
- `phase-7-final-report.md`
