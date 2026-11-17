# Phase 7 — Baseline Audit

**Date:** 2026-11-17
**Status:** Complete — audit executed against the working tree, database, API and test suite
**Scope:** Verify what actually exists before adding model selection, comparison, tests and
documentation. No model, schema or data was changed by this audit.
**Auditor:** implementing agent. This is a self-produced audit, not independent external QA.

## 1. Method

The audit did not trust any status document. Each claim was checked against one or more of:

- the source tree at git HEAD and the uncommitted working tree;
- the live SQLite store (`data/football.db`), read directly through SQLAlchemy;
- the running API on `127.0.0.1:8000`, exercised with `curl`;
- the full pytest suite;
- Alembic (`current`, `check`);
- the Next.js build and a browser.

Where a document and the code disagreed, the code and the database were treated as the
evidence, and the disagreement is recorded in §5.

## 2. Repository state at audit start

| Item | Verified value |
|---|---|
| Git HEAD | `4aed17d` — "phase 7 audit" (on top of `d3a9490` — "pahse 7") |
| Working tree | Modified `memory/*`, untracked `validation.py`, `calibration.py`, six `docs/research/phase-8-*.md` |
| Python | 3.15 in `.venv`; pure-Python maths (no numpy/scipy/pandas/sklearn) |
| Backend tests | 265 passed before this phase's changes |
| Alembic | `0006 (head)`; `alembic check` reports no new upgrade operations |
| Frontend | Next.js 16.4.6 App Router, React 19, TypeScript 5, Tailwind 4 |

## 3. Data state

Read directly from `data/football.db`:

| Item | Value |
|---|---:|
| Tables | 20 |
| Countries | 70 |
| Competitions | 13 (11 with stored matches) |
| Seasons | 22 |
| Teams | 334 |
| Matches | 5,322 |
| Finished results | 4,905 |
| Regulation-time results usable by the models | 4,892 |
| Extra-time / shootout results excluded | 13 |
| Upcoming fixtures | 417 |
| Matches linked to an archived raw payload | 5,322 / 5,322 |
| Persisted evaluation runs at audit start | 1 |

Integrity checks executed during the audit found no duplicate natural key
`(competition, season, kickoff, home, away)`, no `home_team == away_team`, no null scores,
and no `resolved_at < kickoff`.

### 3.1 The observation-time limitation is real

The entire corpus was backfilled in one retrieval window on 2026-11-16.
`MatchResult.resolved_at` therefore records when this platform first stored the score, not
when the provider published it. Every observation is a reconstruction. The evaluation uses
a documented `kickoff + 3 h` eligibility horizon and labels itself retrospective; it must
never be described as a replay of what was known live.

## 4. Intelligence layer as found

| Component | State |
|---|---|
| Independent Poisson `poisson-v1.1.0` | Live analysis path, fitted competition-baselined rates, normalised 1X2 |
| Dixon-Coles `dixon-coles-v1.0.0` | Fitted `rho`, two-stage (rates then rho), used only by the evaluation engine |
| Elo `elo-v1.0.0` | Chronological replay plus grid-fitted Davidson mapping, evaluation only |
| Uniform `uniform-v1.0.0` | Baseline |
| Competition frequency `frequency-v1.0.0` | Baseline |
| Evaluation engine | `run_multi_competition_backtest`, protocol `phase7-v1`, evaluation `evaluation-v1.2.0` |
| Persistence | `model_evaluations`, unique on `(protocol_version, evaluation_version, dataset_digest)` |
| Evaluation API | `POST /api/v1/evaluation/run`, `GET .../latest`, `GET .../runs`, `GET .../{id}` |

The evaluation engine was already correct and reproducible. What did **not** exist:

- any way to request a non-Poisson model from the analysis API;
- any model-comparison endpoint or UI;
- any evaluation dashboard in the Next.js app;
- any tests for rho fitting, the Davidson mapping, the multi-model engine, evaluation
  persistence or the comparison path.

## 5. Contradictions found between documents and reality

| Document claim | Reality |
|---|---|
| "970 matches across all 13 competitions evaluated" (`phase-7-actual-project-status.md`, `phase-8-baseline-audit.md`) | 11 competitions contribute matches. EC and WC have competition rows but no stored matches and do not appear in the sample. 970 is correct. |
| "All 13 with sufficient history … EC/WC marked `INSUFFICIENT_DATA`" | No competition is marked insufficient in the persisted run: EC/WC are absent from the corpus, and the run's `insufficient_competitions` list is empty. |
| "265 passed, 2 failed (migration table expectations)" (`phase-7-actual-project-status.md`) | The suite was green at 265 before this work. The migration tests do not fail. |
| "Evaluation API at `/api/evaluation/...`" | The prefix is `/api/v1/evaluation`. |
| "Frontend includes evaluation dashboard" (`phase-7-actual-project-status.md`) | No `/evaluation` route existed; only `/` and `/matches/[id]`. |
| "`validation.py` implements protocols A–G", "`calibration.py` implements calibration subsystem" (`memory/current-state.md`) | Both files existed untracked, were imported by nothing (app, API, CLI, tests), and duplicated `backtest.py`. |
| Odds / EV engine, paper betting and best bets "implemented" (`docs/research/phase-8-*.md`) | No odds table, endpoint, component, test or UI exists. |
| `PROJECT_STATUS.md`: "265 tests", "Alembic `0005 (head)`", Phase 5 only | Tests were 265, migration head was `0006`, and Phase 7 code existed. |
| `AGENTS.md`: "Current phase 4" | Phase 5 analysis and Phase 7 evaluation were already implemented. |

The pattern is consistent: status documents lagged the code, and the newest documents
over-claimed features that were never built. Documentation, not code, was the main source
of risk.

## 6. Baseline reproduction

### 6.1 Phase 5 single-competition backtest

Reproduced exactly from match 410's checkpoint (PD, 50 out-of-sample matches,
2026-10-09 → 2026-11-08): Brier **0.5722**, log loss **0.9581**, uniform Brier 0.6667,
Brier skill **0.1417**, ECE **0.0661**, MCE **0.3084**. These match the figures recorded in
`PROJECT_STATUS.md`.

### 6.2 Phase 7 persisted run (run id 1)

| Field | Value |
|---|---|
| Protocol | `phase7-v1` |
| Evaluation version | `evaluation-v1.2.0` |
| Dataset | `ds_corpus_a9dff46f14c9b473` |
| Digest | `bde93c2d1684d7133cb40c4fd928075b447b1006e13c0d229bb0142b0a1ad42c` |
| Matches in corpus | 4,892 regulation results |
| Sample | 970 matches, 11 competitions |
| Window | 2026-02-25T20:00Z → 2026-11-14T23:30Z |
| Generated | 2026-11-16T19:49:29Z |

Recomputing the metrics from the corpus reproduced every model figure exactly (Brier, log
loss, skill, ECE, MCE, top-pick accuracy, bootstrap intervals) **on the current corpus**.

### 6.3 The digest drift incident (important, resolved)

Recomputing at run 1's `observed_to` checkpoint produced a corpus of 4,890 matches and a
different digest, and small metric differences appeared. Cause, verified in the database:
results for internal matches **1** and **2** had `resolved_at` updated to
`2026-11-16T21:16:16Z` — after run 1 was generated — because the rows were re-resolved.
The checkpoint filter is `resolved_at <= observed_to`, so those two rows dropped out
retroactively.

This is not non-determinism in the engine. Recomputing on the corpus as it exists now gives
4,892 matches, sample 970, and metrics identical to run 1 in every field; a new run
(id 2, digest `48bc547bf6a88850…`) was persisted for the current corpus and repeated
evaluation returned the same row (idempotent).

**Consequence for the record:** the digest identifies the materialised corpus rows, not
just the matches. A later correction to `resolved_at` changes the digest, which is the
intended behaviour: an evaluation that silently keeps old numbers after the input changed
would be worse. The cost is that run 1 cannot be byte-reproduced from today's store without
the two original observation timestamps.

## 7. What this audit establishes

Verified:

- the corpus, provenance and point-in-time loader are real and consistent;
- the Poisson baseline reproduces exactly;
- the persisted Phase 7 run reproduces on the corpus that now exists;
- persistence is idempotent on identity and append-only on digest change;
- the missing Phase 7 deliverables are exactly those listed in `§4`.

Not established:

- provider-side correctness of the stored scores;
- true publication times of results;
- any general accuracy claim for any model;
- independent external review;
- licence for public display.

## 8. Actions taken in this phase because of the audit

1. Added `model` selection to the analysis API and a comparison endpoint, with an explicit
   `unknown_model` error and no fallback.
2. Added `app/intelligence/model_selection.py` as the only key→implementation map.
3. Deleted `validation.py` and `calibration.py`: unreferenced, untested, Phase 8-labelled
   duplicates of the tested `backtest.py`. Their useful ideas are recorded as proposals, not
   code.
4. Added 56 tests: 42 new model/backtest unit tests, 5 evaluation-API integration
   tests, and 9 added analysis-API cases (265 → 321 passing).
5. Built the `/evaluation` dashboard from persisted runs only.
6. Corrected the Phase 8 documents and the memory files.

## 9. Related documents

- `phase-7-independent-model-review.md`
- `phase-7-multi-competition-backtest.md`
- `phase-7-model-comparison.md`
- `phase-7-final-report.md`
- `memory/known-limitations.md`
