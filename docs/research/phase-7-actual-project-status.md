# Project Status Reconciliation — Phase 7

**Date:** 2026-11-17
**Supersedes:** the 2026-11-16 version of this file, which contained several false claims
(see §6).
**Objective:** Record the verified state of the platform after the Phase 7 model-selection,
comparison, evaluation and documentation work.
**Scope:** Verification and correction. No model was re-fitted to change a result, no schema
was changed, and no stored data was edited or deleted.
**Method:** every figure below was read from the working tree, the live SQLite store, the
running API, an executed test suite, or Alembic. Nothing is copied from an earlier status
document without re-checking it.

---

## 1. Summary

The platform is a **private, loopback-only, real-data football analysis prototype** with:

- a provenance-complete historical corpus (one provider, one backfill);
- three statistical models (Poisson baseline, Dixon-Coles, Elo + Davidson) plus two
  trivial baselines;
- a chronological, identical-match-set evaluation that is persisted, idempotent and
  reproducible on the current corpus;
- a model selector and a model-comparison endpoint on the analysis API;
- next/image-free Next.js UI with fixture explorer, match analysis panel and an
  `/evaluation` dashboard that reads only persisted runs.

It is **not** production-ready, **not** publicly deployable, and makes **no accuracy claim**.
Phase 8 (betting analytics) is not approved; the documents that claimed it was implemented
were false and have been replaced by a frozen proposal record.

## 2. Repository state

| Item | Verified value |
|---|---|
| Git HEAD | `4aed17d` — "phase 7 audit" (parent `d3a9490`) |
| Working tree | Phase 7 changes uncommitted (see `phase-7-final-report.md` §4) |
| Python | 3.15 in `.venv`; pure-Python maths (no numpy/scipy/pandas/sklearn) |
| Backend tests | **321 passed**, 0 failed, 0 skipped |
| Alembic | `current` → `0006 (head)`; `check` → no new upgrade operations |
| Frontend | Next.js 16 App Router, React 19, TypeScript 5, Tailwind 4 |
| Type check | `tsc --noEmit` clean |
| Build | `npm run build` passes, including `/evaluation` |

## 3. Data state (`data/football.db`)

| Item | Value |
|---|---:|
| Countries | 70 |
| Competitions | 13 (11 with stored matches) |
| Seasons | 22 |
| Teams | 334 |
| Matches | 5,322 |
| Finished results | 4,905 |
| Regulation results usable by the models | 4,892 |
| Extra-time / shootout results excluded | 13 |
| Upcoming fixtures | 417 |
| Matches linked to an archived raw payload | 5,322 / 5,322 |
| Persisted analysis reports | 37 |
| Persisted evaluation runs | 2 |

Eleven competitions have stored matches: BL1, BSA, CL, CLI, DED, ELC, FL1, PD, PL, PPL, SA.
EC and WC have competition rows but **zero stored matches**, so they do not appear in the
evaluation at all. "13 competitions in the database" is **not** "13 competitions evaluated".

Every result was backfilled in one retrieval window on 2026-11-16. `resolved_at` records when
this platform stored the score, not when the provider published it, so every historical
observation is a reconstruction (LIM-030). The evaluation uses a documented
`kickoff + 3 h` eligibility horizon and labels itself retrospective.

## 4. What exists, verified

### 4.1 Intelligence

| Component | Version | State |
|---|---|---|
| Independent Poisson | `poisson-v1.1.0` | Live analysis path; shared rate estimator |
| Dixon-Coles | `dixon-coles-v1.0.0` | Two-stage fit (rates, then `rho`); evaluated; not the default |
| Elo + Davidson | `elo-v1.0.0` | Chronological replay and frozen 1X2 mapping; evaluation and on-demand |
| Uniform baseline | `uniform-v1.0.0` | Comparison baseline |
| Competition frequency baseline | `frequency-v1.0.0` | Comparison baseline |
| Evaluation engine | protocol `phase7-v1`, `evaluation-v1.2.0` | Chronological, identical match set, persisted |
| Model dispatch | `app/intelligence/model_selection.py` | Only key→implementation map; no fallback |

### 4.2 API

All under the `/api/v1` prefix (this is `/api/v1/...`, **not** `/api/...`):

| Method | Path | Writes? |
|---|---|---|
| POST | `/analysis/matches/{match_id}?model=&force=` | Yes — persists a report |
| POST | `/analysis/matches/{match_id}/comparison` | Yes — persists one report per model |
| GET | `/analysis/{analysis_id}` | No |
| GET | `/analysis/matches/{match_id}/history` | No |
| POST | `/evaluation/run` | Yes — persists an evaluation run |
| GET | `/evaluation/latest` | No |
| GET | `/evaluation/runs` | No |
| GET | `/evaluation/{run_id}` | No |

An unknown `model` value returns HTTP 422 with `code = "unknown_model"`; nothing is
persisted. An unknown match returns 404. There is no silent fallback to Poisson.

### 4.3 Frontend

| Route | State |
|---|---|
| `/` | Stored fixtures, crests, emblems, windows, search, filters, pagination |
| `/matches/[id]` | Fixture detail, honest "not supplied" markers, analysis panel |
| `/matches/[id]` analysis panel | Model selector, "Analyze with …", comparison table, model-aware copy, generic parameters, provenance, limitations, history |
| `/evaluation` | Persisted-run dashboard: provenance, overview, paired differences, per-outcome calibration, per-competition, per-season, timeline, run list |

`/evaluation` never computes a metric in the browser; it renders `GET /api/v1/evaluation/...`.
Responsive behaviour was executed at 375, 390, 430, 768, 1024, 1280 and 1440 px: no
page-level overflow, wide tables scroll inside their own container.

## 5. Measured evaluation

Persisted run 2, digest `48bc547bf6a88850…`, protocol `phase7-v1`, sample **970 matches**,
11 competitions, 2026-02-25T20:00Z → 2026-11-14T23:30Z.

| Model | Brier | Log loss | Skill vs uniform | ECE | Top-pick |
|---|---:|---:|---:|---:|---:|
| Poisson | 0.5831 | 0.9828 | 0.1253 | 0.0254 | 51.55% |
| Dixon-Coles | 0.5829 | 0.9821 | 0.1256 | 0.0258 | 51.34% |
| Elo (Davidson) | 0.5911 | 0.9916 | 0.1133 | 0.0375 | 51.55% |
| Competition frequency | 0.6405 | 1.0592 | 0.0393 | 0.0143 | 45.36% |
| Uniform 1/3 | 0.6667 | 1.0986 | 0.0000 | 0.0802 | 45.36% |

Paired difference vs Poisson (positive = Poisson worse on the same matches):

| Candidate | Brier mean | 95% CI | Reading |
|---|---:|---|---|
| Dixon-Coles | +0.0002 | [−0.0009, +0.0013] | indistinguishable |
| Elo | −0.0080 | [−0.0195, +0.0040] | directionally worse, not proven |
| Uniform | −0.0835 | [−0.1051, −0.0619] | Poisson significantly better |
| Competition frequency | −0.0573 | [−0.0755, −0.0388] | Poisson significantly better |

Run 1 (digest `bde93c2d1684d713…`) has identical metrics. It differs only in identity because
`resolved_at` for internal matches 1 and 2 was re-set after run 1 was written, which changed
the materialised corpus and its digest. This is digest sensitivity to input, not engine
non-determinism; the detail is recorded in `phase-7-baseline-audit.md` §6.3.

## 6. Corrections to the previous version of this document

| Previous claim | Verified reality |
|---|---|
| "970 matches across all 13 competitions" | 11 competitions contribute matches. EC and WC have no stored matches. |
| "EC/WC marked `INSUFFICIENT_DATA`" | No competition is marked insufficient in the persisted run; `insufficient_competitions` is empty. |
| "265 passed, 2 failed (migration expectations)" | 321 passed, 0 failed. The migration tests were green before Phase 7 too. |
| "Evaluation API `/api/evaluation/...`" | Prefix is `/api/v1/evaluation`. |
| "Frontend includes evaluation dashboard" | No `/evaluation` route existed before this phase; it was built in Phase 7. |
| "Poisson with supplied rates (Phase 4)" | The live Poisson path fits competition rates from prior results; it is not supplied-parameter. |
| "Dixon-Coles slightly edges Poisson" | The paired interval spans zero. DC is indistinguishable, not better. |
| "Implementation exceeds documented scope with Phase 6/7 features" | The features are Phase 7 and are now documented. Phase 6 was the provider capability audit. |
| "Mobile below 471 px not verified" | Executed at 375/390/430 px in this phase. |
| "265/267 synthetic tests" | 321 tests, all passing, with synthetic fixtures plus real-corpus evaluation tests. |

The failure mode was consistent: status text drifted ahead of, or behind, the code. The rule
that follows is applied from here on — a status claim must name the file/test that proves it.

## 7. Not implemented, deliberately

- Public deployment, containers, CI/CD, public hosting.
- Authentication, authorisation, rate limiting, TLS.
- Odds ingestion, expected value, paper betting, best bets (Phase 8, not approved).
- Subscriptions, payments, advertising, affiliate links.
- Machine-learning training, an LLM numerical engine, generated analysis text.
- In-match statistics, lineups, injuries, provider xG (free tier has none).
- Monitoring/alerting, backup automation, PostgreSQL support.
- Any coverage guarantee, accuracy promise or fixed-accuracy figure.

## 8. Unresolved and unverified

| Item | State |
|---|---|
| Independent external QA/ML review | **Open** — this phase's review is self-produced |
| Public-display / redistribution licence (LIM-006, LIM-020) | **Open** — public exposure rejected |
| Provider statistics / H2H | **Unavailable on free tier**; not purchased |
| True publication timestamps | **Unavailable**; 3 h horizon is a retrospective proxy |
| Untouched final holdout | **None**; the 970 matches informed protocol choices |
| Clustered uncertainty | Bootstrap treats clustered matches as independent; CIs likely narrow |
| Frozen evaluation parameters vs live refit | Differ (MR-11); documented, not reconciled |
| Second results source | **None**; provider-side correctness unverified |

## 9. Conclusion

Phase 7 delivered what it claimed: explicit model selection, a comparison path on one
point-in-time dataset, a persisted and reproducible multi-competition evaluation, tests for
all of it, an evaluation dashboard, and documentation that matches the code.

No evidence supports choosing a new default model. `poisson-v1.1.0` remains the baseline
because DC shows no proven gain and Elo is directionally worse with a wider interval. That is
a statement about this corpus and window only.

The correct posture remains: private, loopback-only, research prototype, no public claims,
no betting features, with licensing and independent review as the real gates.

## 10. Related documents

- `docs/research/phase-7-baseline-audit.md`
- `docs/research/phase-7-independent-model-review.md`
- `docs/research/phase-7-dixon-coles-research.md`
- `docs/research/phase-7-multi-competition-backtest.md`
- `docs/research/phase-7-model-comparison.md`
- `docs/research/phase-7-commercial-readiness.md`
- `docs/research/phase-7-final-report.md`
- `docs/research/phase-8-betting-proposals-rejected.md`
- `PROJECT_STATUS.md`, `memory/current-state.md`
