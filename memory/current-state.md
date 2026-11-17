# Current State

**Last updated:** 2026-11-17
**Phase:** Phase 7 — model selection, comparison and multi-competition evaluation, implemented
and self-reviewed. **Phase 8 is not approved.** Phase 5 analysis remains private and
loopback-only. No independent external review exists for any phase.

## What exists now

### Real stored data (local SQLite, `data/football.db`)
- 70 countries, 13 competitions, 22 seasons, 334 teams, **5,322 matches**, **4,905 finished
  results**, 417 upcoming fixtures
- **4,892 regulation-time results** are usable by the models; 13 extra-time/shootout records
  are excluded
- Eleven competitions have stored matches: BL1, BSA, CL, CLI, DED, ELC, FL1, PD, PL, PPL, SA
- EC and WC have competition rows but zero stored matches; they do not appear in any evaluation
- All 5,322 stored matches link to an archived raw payload (64 archived payload files)
- Results span 2025-02-05 → 2026-11-14; the entire corpus was backfilled in one retrieval
  window on 2026-11-16, so every historical observation is a reconstruction (LIM-030)
- 10 extra-time/penalty records were quarantined during ingestion with recorded reasons
- 37 persisted analysis reports and 2 persisted evaluation runs exist

### Intelligence and evaluation
- `poisson-v1.1.0` — **permanent baseline and default**. Live path and backtest share the same
  rate estimator. Live reports embed the 50-match Poisson rolling-origin block.
- `dixon-coles-v1.0.0` — reuses Poisson rates, fits `rho` on prior matches (two-stage, not joint
  MLE), clips `rho` to the admissible interval. Populated on request, never the default.
- `elo-v1.0.0` — chronological replay (K=20, initial 1500, scale 400), pre-kickoff ratings,
  Davidson `home_advantage`/`draw_nu` fitted on pre-window matches and frozen. 1X2 only: no xG,
  scorelines, BTTS or over/under.
- `uniform-v1.0.0` and `frequency-v1.0.0` — comparison baselines.
- `app/intelligence/model_selection.py` — the only public-key→implementation map. Unknown keys
  raise before computation; no fallback.
- `app/intelligence/backtest.py` — protocol `phase7-v1`, evaluation `evaluation-v1.2.0`,
  chronological, identical match set, `kickoff + 3 h` eligibility, fixed-seed bootstrap.
- `app/models/evaluation.py` + `app/repositories/evaluation.py` — persisted runs, unique on
  `(protocol_version, evaluation_version, dataset_digest)`; append-only on digest change.

### API (prefix `/api/v1`)
- GET `/fixtures`, `/fixtures/today`, `/fixtures/{id}`, `/fixtures/{id}/statistics`
- GET `/countries`, `/competitions`, `/competitions/{id}`, `/seasons`, `/teams`, `/teams/{id}`,
  `/teams/{id}/matches`
- GET `/sync/runs`, `/sync/status`
- POST `/analysis/matches/{match_id}?model={poisson|dixon_coles|elo}&force=`
- POST `/analysis/matches/{match_id}/comparison`
- GET `/analysis/{analysis_id}`, GET `/analysis/matches/{match_id}/history`
- POST `/evaluation/run`; GET `/evaluation/latest`, `/evaluation/runs`, `/evaluation/{run_id}`
- Unknown model → 422 `unknown_model`, nothing persisted. Unknown match or missing report → 404.

### Frontend (`apps/web`)
- `/` lists stored fixtures with crests, emblems, countries, status and score, with windows,
  search, team/country/competition filters, pagination and freshness states
- `/matches/[id]` shows the fixture, statistics state and an **Analyze Match** panel with a
  model selector, "Analyze with …", "Compare all models", a comparison table, model-aware copy
  (Elo says it produces no xG/markets), generic parameter rendering, provenance and history
- `/evaluation` renders persisted evaluation runs only: provenance, overview, paired
  differences, per-outcome calibration, per-competition, per-season, timeline, run list
- Missing values show `—` or "not supplied"; the UI never fills a blank with zero and never
  computes a metric in the browser
- `npm run build` passes; `tsc --noEmit` clean; responsive behaviour executed at
  375/390/430/768/1024/1280/1440 px with no page-level overflow

### Measured evaluation (persisted run 2)
- Dataset `ds_corpus_61252c4622bbc0db`, digest `48bc547bf6a88850…`, **970 matches**,
  11 competitions, 2026-02-25T20:00Z → 2026-11-14T23:30Z
- Poisson 0.5831 Brier / 0.9828 log loss / 0.1253 skill / 0.0254 ECE
- Dixon-Coles 0.5829 / 0.9821 / 0.1256 / 0.0258
- Elo 0.5911 / 0.9916 / 0.1133 / 0.0375
- Competition frequency 0.6405 / 1.0592 / 0.0393 / 0.0143
- Uniform 0.6667 / 1.0986 / 0 / 0.0802
- Paired Brier vs Poisson: DC +0.0002 [−0.0009, +0.0013]; Elo −0.0080 [−0.0195, +0.0040];
  uniform −0.0835 [−0.1051, −0.0619]; frequency −0.0573 [−0.0755, −0.0388]
- Run 1 (`bde93c2d…`) has identical metrics; its digest differs because matches 1 and 2 were
  re-resolved after it was written. This is input sensitivity, not engine non-determinism.

### Verification evidence (2026-11-17)
- `PYTHONPATH=apps/backend .venv/bin/python -m pytest` → **321 passed**, 0 failed, 0 skipped,
  1 third-party Starlette/httpx deprecation warning
- `alembic current` → `0006 (head)`; `alembic check` → no new upgrade operations
- `npx tsc --noEmit` clean; `npm run build` passes including `/evaluation`
- Evaluation recomputed on the current corpus → identical metrics and intervals; repeat run
  reuses the persisted row (idempotent)
- Match 410 comparison → 3 models, one digest `2e2120e17f474329…`, reports #37/#28/#27

### Module map
- `app/intelligence/prediction.py` — Poisson live prediction and embedded backtest
- `app/intelligence/model_selection.py` — model dispatch and DC/Elo on-demand prediction
- `app/intelligence/models/poisson.py`, `dixon_coles.py`, `elo_fitted.py`
- `app/intelligence/backtest.py` — multi-competition chronological evaluation
- `app/intelligence/baselines.py`, `evaluation.py`, `probabilities.py`, `types.py`
- `app/intelligence/validation.py` and `calibration.py` were **deleted** in Phase 7: they were
  untracked, unreferenced, untested duplicates of `backtest.py` labelled Phase 8

### Tests added in Phase 7
- `tests/phase7_support.py` — shared fixtures
- `tests/unit/test_phase7_models.py` — 26 tests (dispatch, rho fitting/leakage/clipping,
  Elo replay, Davidson bounds, normalisation)
- `tests/unit/test_phase7_backtest.py` — 16 tests (eligibility horizon, identical sets,
  abstention, determinism, persistence semantics)
- `tests/integration/test_evaluation_api.py` — 5 tests
- `tests/integration/test_analysis_api.py` — extended from 11 to 20 tests

### Documentation
- `docs/research/phase-7-baseline-audit.md`
- `docs/research/phase-7-independent-model-review.md` (internal, not independent)
- `docs/research/phase-7-dixon-coles-research.md`
- `docs/research/phase-7-multi-competition-backtest.md`
- `docs/research/phase-7-model-comparison.md`
- `docs/research/phase-7-commercial-readiness.md`
- `docs/research/phase-7-actual-project-status.md`
- `docs/research/phase-7-final-report.md`
- `docs/research/phase-8-betting-proposals-rejected.md` — the six false Phase 8 status
  documents were deleted; their content survives only as frozen proposals here and in git
  history at `4aed17d`

## What is not true

- There is no odds, expected-value, paper-betting or best-bets feature. None was built.
- There is no evaluation dashboard computing numbers in the browser.
- There is no evidence that Dixon-Coles or Elo is better than Poisson.
- There is no public display right, no authentication, no deployment, and no accuracy claim.
