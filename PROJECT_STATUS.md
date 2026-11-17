# Project Status

**Project:** Football Intelligence Platform
**Current phase:** Phase 7 — Model selection, comparison and evaluation (self-reviewed, not
independently accepted)
**Phase 8:** **Not approved.** Betting/odds/paper-betting proposals are frozen; see
`docs/research/phase-8-betting-proposals-rejected.md`.
**Last updated:** 2026-11-17

Phase history: Phase 4 was accepted by the developer on 2026-11-14 as an offline,
synthetic-test-only foundation. Phase 5 (private real-data analysis) was approved under
ADR-0010 and is implemented on loopback. Phase 6 was the provider capability audit. Phase 7
added explicit model selection, a model-comparison endpoint, multi-competition evaluation
coverage, tests, an evaluation dashboard and corrected documentation. No independent external
review exists for any phase.

## Current private analysis slice (2026-11-17)

Private, loopback-only, read-only ingestion from football-data.org is running.
`data/football.db` holds 70 countries, 13 competitions, 22 seasons, 334 teams, **5,322
matches**, **4,905 finished results**, and 417 upcoming fixtures. Of the finished results,
**4,892 are regulation results** usable by the models and 13 are extra-time/shootout records
that are excluded. Results were backfilled in one retrieval window on 2026-11-16; every
stored match is linked to an archived raw payload. Eleven competitions have stored matches;
EC and WC have competition rows but no matches.

The Next.js app lists stored fixtures with crests, competition emblems, countries, status and
score; offers Today / Tomorrow / 7 / 14 / 30-day windows, server-side search, a team combobox
and country/competition filters; and shows a match detail view with honest "Not supplied"
markers plus an **Analyze Match** panel.

The analysis panel calls `POST /api/v1/analysis/matches/{id}?model=…` and renders:

- a model selector: Poisson (default, permanent baseline), Dixon-Coles, Elo (Davidson);
- 1X2 probabilities that sum to 100%, expected goals, secondary markets and top scorelines
  for the score-based models;
- a comparison table from `POST /api/v1/analysis/matches/{id}/comparison`, with one persisted
  report per model on the same point-in-time dataset;
- sample size, competition baseline, historical record, head-to-head and model parameters;
- for Poisson only, the embedded 50-match rolling-origin block; DC and Elo return
  `evaluation: null` rather than borrowing a Poisson measurement;
- dataset provenance, explicit limitations, the four statuses (`READY`,
  `INSUFFICIENT_DATA`, `DATA_UNAVAILABLE`, `ANALYSIS_FAILED`) and prior reports.

Model outputs are labelled with `model_id` and `model_version`. An unknown model returns HTTP
422 `unknown_model`; nothing is persisted and there is no silent fallback.

The `/evaluation` dashboard renders **stored** evaluation runs only: provenance, model
overview, paired differences, per-outcome calibration, per-competition, per-season, timeline
and the run list. It never computes a metric in the browser.

## Measured evaluation (persisted run 2)

Protocol `phase7-v1`, evaluation version `evaluation-v1.2.0`, dataset
`ds_corpus_61252c4622bbc0db`, digest `48bc547bf6a88850…`, **970 matches**, 11 competitions,
2026-02-25T20:00Z → 2026-11-14T23:30Z.

| Model | Brier | Log loss | Skill vs uniform | ECE | Top-pick |
|---|---:|---:|---:|---:|---:|
| Poisson `poisson-v1.1.0` | 0.5831 | 0.9828 | 0.1253 | 0.0254 | 51.55% |
| Dixon-Coles `dixon-coles-v1.0.0` | 0.5829 | 0.9821 | 0.1256 | 0.0258 | 51.34% |
| Elo + Davidson `elo-v1.0.0` | 0.5911 | 0.9916 | 0.1133 | 0.0375 | 51.55% |
| Competition frequency | 0.6405 | 1.0592 | 0.0393 | 0.0143 | 45.36% |
| Uniform 1/3 | 0.6667 | 1.0986 | 0.0000 | 0.0802 | 45.36% |

Paired Brier difference vs Poisson (positive = Poisson worse): Dixon-Coles **+0.0002**
[−0.0009, +0.0013]; Elo **−0.0080** [−0.0195, +0.0040]; uniform **−0.0835**
[−0.1051, −0.0619]; frequency **−0.0573** [−0.0755, −0.0388].

Reading: Poisson is conclusively better than both trivial baselines, Dixon-Coles is
indistinguishable from Poisson, and Elo is directionally worse but not proven different. No
model change is justified by this evidence. The intervals are a lower bound on uncertainty
because matches are correlated (competition, season, matchday, team).

The live report for Real Madrid vs Celta (match 410, kickoff 2026-11-21) is `READY`:
Poisson 60.9% / 23.2% / 15.9% with xG 1.74 / 0.76; Dixon-Coles 60.2% / 24.7% / 15.1%;
Elo 68.4% / 19.8% / 11.9% and no xG. All three share dataset
`ds_match_410_61252c4622bbc0db`.

There is no paid plan, no public deployment, no in-match statistics, no lineup or injury data,
and no performance guarantee. These are measurements on one corpus from one provider in one
window, not a claim of general accuracy.

## Phase summary

| Phase | Scope | Status |
| --- | --- | --- |
| 1 | Foundation: instructions, agents, skills, commands, docs, rules, memory | Complete |
| 2 | System architecture: stack, database, provider abstraction, API, identity, sync | Complete |
| 3 | Python backend, SQLite schema, ingestion, read-only API, tests, guides | **Remediation implemented; final acceptance rejected pending re-audit** |
| 4 | Offline intelligence, mathematical primitives, evaluation mechanics | **Accepted by developer (synthetic-only)** |
| 5 | Real historical ingestion, fitted analysis, persistence/API, frontend | **Implemented privately; licence and review gates open** |
| 6 | Provider capability audit (two providers, bounded live probes) | Complete as research; entitlements unverified |
| 7 | Model selection, comparison, multi-competition evaluation, dashboard, tests | **Implemented, self-reviewed; independent review pending** |
| 8 | Betting analytics (odds/EV, paper betting, best bets) | **Not approved, not implemented** |

Status vocabulary for deliverables: **VERIFIED**, **IMPLEMENTED BUT NOT LIVE-VERIFIED**,
**PARTIALLY IMPLEMENTED**, **NOT IMPLEMENTED**, **BLOCKED**.

## Phase 7 deliverables

| Area | Deliverable | Evidence | Status |
| --- | --- | --- | --- |
| Model dispatch | Single key→model map, no fallback | `app/intelligence/model_selection.py`, 26 unit tests | VERIFIED |
| Analysis selection | `?model=` on `POST /analysis/matches/{id}` | `app/api/v1/endpoints/analysis.py`, integration tests | VERIFIED |
| Comparison | `POST /analysis/matches/{id}/comparison`, one report per model, same digest | endpoint + 20 analysis integration tests | VERIFIED |
| Error semantics | Unknown model 422 `unknown_model`; unknown match 404; missing report 404 | integration tests | VERIFIED |
| Dixon-Coles | Fitted `rho`, leakage guard, bounded/clipped | `models/dixon_coles.py`, unit tests | VERIFIED (mathematically); no proven gain |
| Elo + Davidson | Chronological replay, pre-kickoff ratings, frozen mapping | `models/elo_fitted.py`, `model_selection.py` | VERIFIED (mathematically); no proven gain |
| Evaluation engine | Chronological, identical match set, fixed-seed bootstrap, persisted | `backtest.py`, unit + integration tests | VERIFIED |
| Evaluation API | run/latest/runs/{id} | `endpoints/evaluation.py`, 5 new integration tests | VERIFIED (loopback) |
| Evaluation dashboard | `/evaluation`, persisted runs only | `apps/web/src/app/evaluation/page.tsx` | VERIFIED (build + 7 widths) |
| Match panel | Model selector, comparison table, model-aware copy | `MatchAnalysisPanel.tsx` | VERIFIED (build + 7 widths) |
| Documentation | Audit, review, DC note, backtest, comparison, readiness, final report | `docs/research/phase-7-*.md` | VERIFIED as written; self-produced |
| False Phase 8 docs | Replaced by one frozen-proposal record | `phase-8-betting-proposals-rejected.md` | CORRECTED |
| Orphan modules | `validation.py`, `calibration.py` deleted (unreferenced, untested) | git diff | CORRECTED |

## Verification evidence

Latest local verification: 2026-11-17.

| Check | Result |
| --- | --- |
| `PYTHONPATH=apps/backend .venv/bin/python -m pytest` | **321 passed**, 0 failed, 0 skipped, 1 third-party deprecation warning |
| `alembic current` | `0006 (head)` |
| `alembic check` | No new upgrade operations detected |
| `tsc --noEmit` | Clean |
| `npm run build` | Passes, including `/evaluation` |
| Evaluation reproducibility | Recomputed on the current corpus → identical metrics and intervals; persisted run reused (idempotent) |
| Lifecycle comparison, match 410 | 3 models, one dataset digest, 3 persisted reports, stable ids on repeat |
| Responsive check | 375/390/430/768/1024/1280/1440 px: no page overflow; wide tables scroll internally |
| Provenance | `VERIFIED_REAL` requires provider, archived payload ids, windows, digest; incomplete evidence fails closed |

The suite mixes synthetic fixtures with real-corpus evaluation tests. A passing suite is not
evidence of provider compatibility or football predictive usefulness.

## Architecture decisions

| ADR | Decision | Status |
| --- | --- | --- |
| ADR-0001 | Project foundation | Proposed — per its recorded status |
| ADR-0002 | Python backend stack | Proposed — implemented |
| ADR-0003 | SQLite primary database | Proposed — implemented |
| ADR-0004 | Provider abstraction | Proposed — implemented, live-verified for fixtures/results/media |
| ADR-0005 | Read-only API contract | Proposed — implemented (analysis/evaluation POSTs are documented exceptions that persist derived reports) |
| ADR-0006 | Identity and provenance | Proposed — implemented |
| ADR-0007 | Synchronisation model | Proposed — implemented |
| ADR-0008 | Phase 4/5 entry gates | Approved — gates partly unmet |
| ADR-0009 | Pure offline intelligence boundary | Approved — implemented, amended after review |
| ADR-0010 | Verified real dataset contract | Approved by developer — implemented |

Phase 7 did not change an approved architecture. It added a dispatch module, two endpoints, an
evaluation integration test file, a schema-level permissive `model_parameters` type and a
frontend route. The decision to keep `poisson-v1.1.0` as the permanent baseline is recorded in
`memory/decisions.md` (DEC-028).

## Deliberately not built

- Public deployment, shared-network exposure, public data display.
- Authentication, authorisation, subscriptions, payments, betting or odds features.
- Live-score push, news, notifications.
- Machine-learning training, an LLM numerical engine, generated analysis text.
- In-match statistics, lineups, injuries, or paid-tier xG.
- Docker, CI/CD, monitoring stack, PostgreSQL, broker, cache, multi-worker execution.
- Any coverage or accuracy guarantee.

## Blockers and pending decisions

| ID | Item | Impact |
| --- | --- | --- |
| PD-002 | Final provider selection | Adapter is a reference implementation, not a commitment |
| PD-003 | Competition and season coverage | No coverage guarantee; eleven competitions stored |
| PD-004 | Data budget / plan | Pricing, quota and statistics depth remain unverified |
| LIM-006 | Display/redistribution licence | Public data display blocked; loopback only |
| LIM-019 | Independent review | All reviews so far are self-produced |
| — | Phase 3 independent QA | Prior FAIL; final exact-tree re-audit pending |
| — | Phase 3 security conditions | S-01…S-19; public exposure rejected until addressed |
| — | Provider statistics | Free tier has none; models abstain instead of inventing zeros |
| MR-03 | Clustered uncertainty | Bootstrap CIs are likely too narrow |
| MR-04 | No untouched holdout | Small optimistic bias cannot be excluded |
| MR-05 | Retrospective observation times | 3 h horizon is a proxy, not a replay of live knowledge |
| MR-11 | Frozen evaluation vs live refit | The evaluated DC/Elo parameters are frozen; the live path refits per request |

No paid subscription was purchased, no provider account was created, and no provider terms were
accepted on the developer's behalf.

## Next

1. Obtain independent QA/ML review of the exact analysis tree, the three models and the
   measured evaluation. Self-review is not acceptance.
2. Decide whether the stored corpus (11 competitions, 59–100 evaluation matches each) is
   sufficient for the intended product; extend coverage only with explicit approval.
3. Resolve LIM-006 (public-display/redistribution licence) and LIM-020 (hot-linked crests and
   emblems) before any shared display.
4. Decide whether to reconcile the frozen evaluation cadence with the live refit (MR-11).
5. Consider a clustered bootstrap and a genuine out-of-time holdout before quoting intervals
   as precise.
6. Do not start Phase 8 without an explicit developer decision and an ADR.

Reports: [Phase 7 final report](docs/research/phase-7-final-report.md),
[baseline audit](docs/research/phase-7-baseline-audit.md),
[independent model review](docs/research/phase-7-independent-model-review.md),
[multi-competition backtest](docs/research/phase-7-multi-competition-backtest.md),
[model comparison](docs/research/phase-7-model-comparison.md),
[commercial readiness](docs/research/phase-7-commercial-readiness.md),
[Phase 8 proposals (rejected)](docs/research/phase-8-betting-proposals-rejected.md),
[Phase 3 QA review](docs/research/phase-3-independent-qa-review.md),
[historical coverage](docs/research/2026-11-16-historical-coverage-report.md).

See [`memory/current-state.md`](memory/current-state.md),
[`memory/next-steps.md`](memory/next-steps.md) and
[`memory/known-limitations.md`](memory/known-limitations.md).
