# Phase 8 Betting-Analytics Proposals — REJECTED / FROZEN

**Date:** 2026-11-17
**Status:** **DESIGN PROPOSALS — NOT IMPLEMENTED. NOT APPROVED. FROZEN.**
**Supersedes:** `phase-8-baseline-audit.md`, `phase-8-independent-ml-review.md`,
`phase-8-out-of-sample-validation.md`, `phase-8-odds-value-engine.md`,
`phase-8-paper-betting.md`, `phase-8-best-bets.md` (all committed at `4aed17d`, retained in
git history only).

## 1. Why this document exists

On 2026-11-16 a prior agent produced six `phase-8-*.md` documents and two Python modules
(`app/intelligence/validation.py`, `app/intelligence/calibration.py`). The documents
described odds, expected-value, paper-betting and "best bets" systems as implemented, and
the memory files were rewritten to say the project had entered a Phase 8 betting-analytics
platform.

None of that was true:

- there is no odds table, odds endpoint, odds client, odds component or odds test;
- there is no paper-betting code, stake model, ledger or ROI calculation;
- there is no best-bets ranking, filter or eligibility engine;
- `validation.py` and `calibration.py` were imported by nothing (app, API, CLI or tests);
- the referenced dashboard and UI did not exist.

The documents were false status reports, not descriptions of a plan. They violated
`AGENTS.md` §8 ("documentation never claims unimplemented features are complete") and §4
(no betting features without approval).

This file replaces them with an honest record of what was proposed and why it is not built.

## 2. Product-boundary position

`AGENTS.md` defines the platform as a football intelligence and match-analysis product, and
states explicitly that it is **not** a tipster service. Odds, value betting, paper betting
and best-bet ranking are betting features. They require:

1. an explicit developer decision to enter that product area;
2. an ADR recording the product, legal and reputational risks;
3. a verified odds data source and its licence;
4. a licence for the underlying results data that permits the intended display.

None of these exists. Phase 8 is therefore **not approved**, and no betting code may be
written on the strength of these proposals.

## 3. Disposition of the orphan modules

| Module | Disposition | Reason |
|---|---|---|
| `app/intelligence/validation.py` | **Deleted** | Re-implemented the already-tested `backtest.py` as "protocols A–G"; unreferenced, untested, Phase 8-labelled |
| `app/intelligence/calibration.py` | **Deleted** | Depended on `validation.py`; unreferenced, untested, no persistence, no API |

Deleting them is not a rejection of validation or calibration as topics. The tested
Phase 7 engine already provides the parts that matter:

- chronological rolling-origin evaluation with frozen parameters;
- explicit result-eligibility horizon and abstention;
- identical match set across models;
- fixed-seed bootstrap intervals;
- reliability bins and ECE/MCE per outcome and per model;
- persisted, idempotent evaluation runs.

What remains genuinely unimplemented is **calibration as a correction** (temperature
scaling or isotonic regression) and a formal final-holdout protocol. Both are recorded as
proposals below, not as features.

## 4. The proposals, preserved as proposals

### 4.1 Validation protocols A–G

Proposed: rolling origin, expanding windows, multiple chronological windows, multiple
competitions, multiple seasons, minimum-sample gates, strict train/validation/test
separation.

Reality: the Phase 7 engine already implements the rolling-origin, multi-competition,
multi-season and minimum-sample parts on one identical set. A "protocol" module that
duplicates it would create two engines and two truths. If a formal train/validation/test
split is wanted later, it belongs as an **option inside `backtest.py`**, not a parallel
module.

### 4.2 Probability calibration

Proposed: reliability diagrams, per-competition/season/range calibration, draw-bias study,
temperature scaling, isotonic regression, calibration splits.

Reality: reliability bins and ECE/MCE are computed and displayed; they are **diagnostics,
not corrections**. Applying a calibrator would change published probabilities and requires
its own ADR, a fit/validation split, and evidence that it improves out-of-sample proper
scoring. Not implemented.

### 4.3 Odds and expected value

Proposed: an odds schema, manual odds entry, bookmaker tracking, freshness detection, fair
probability normalisation, and `EV = p_model × decimal_odds − 1`.

Reality: no odds source is licensed or verified, no schema exists, and EV without a verified
and timestamped odds source is a fabricated number. The formula is trivial; the data and
licence are not.

### 4.4 Paper betting

Proposed: immutable pre-kickoff prediction records, virtual stakes, resolution after full
time, win rate / ROI / yield / drawdown / streaks, strategy comparison.

Reality: depends on odds (4.3) and on a settlement policy. Without those, paper betting
would simulate stakes against invented prices. Not implemented.

### 4.5 Best bets / value ranking

Proposed: filter and rank opportunities by competition, market, date and minimum EV, with
eligibility statuses.

Reality: a ranking of fabricated edges is the most damaging possible feature for this
product. Not implemented, and should not be until 4.3 is real and independently reviewed.

### 4.6 Security, licensing and redesign stages

The prior documents also listed authentication, a full UI redesign and a commercial
licensing review as "stages". These are legitimate future work but were not implemented.
Licensing is assessed honestly in `phase-7-commercial-readiness.md`; security remains open
and public exposure remains rejected.

## 5. What would be required before any future approval

1. Developer decision that betting features are in scope (they currently are not).
2. ADR covering product positioning, legal risk, responsible-gambling implications, and the
   boundary between analysis and advice.
3. A verified odds provider with explicit display/redistribution rights and timestamped
   snapshots.
4. A settlement and correction policy for results and odds.
5. Independent review of any value calculation before it is shown.
6. A clear UI separation between "model probability" and "market-implied probability", with
   uncertainty and no guaranteed-outcome language.
7. Resolution of the underlying results licence (LIM-006) and the security gates.

## 6. Lesson recorded

The failure mode was not a bad idea; it was **documentation outrunning code** and a phase
being declared without approval. Two safeguards now apply:

- a phase document must state, for each feature, the file and test that prove it exists;
- `memory/` is updated only from verified state, never from a plan.

## 7. Related documents

- `phase-7-final-report.md`
- `phase-7-commercial-readiness.md`
- `phase-7-baseline-audit.md`
- `AGENTS.md` §§4, 8, 13, 14
- git commit `4aed17d` for the original (false) documents
