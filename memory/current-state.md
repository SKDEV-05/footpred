# Current State

**Last updated:** 2026-11-16
**Phase:** Phase 8 — Professional Football Intelligence & Betting Analytics Platform
**Status:** Stage 0 (Audit), Stage 1 (Independent ML Review), Stage 2 (Strict Out-of-Sample Validation), Stage 3 (Probability Calibration) implemented.

## What exists now

### Real stored data (local SQLite, `data/football.db`)
- 70 countries, 13 competitions, 11 seasons, 285 teams, **5,322 matches**, **4,905 finished results**, 417 upcoming fixtures
- Finished-result range: **2025-02-05 → 2026-11-14**, two seasons per league
- Eleven competitions have stored matches: BL1, BSA, CL, CLI, DED, ELC, FL1, PD, PL, PPL, SA
- EC and WC have competition rows but zero stored matches; reported as `no_stored_matches`
- All 5,322 stored matches link to an archived raw payload
- Historical sync run 11: 4,917 fetched, 4,905 results created, 2 updated, 10 rejected (all extra-time/penalty inconsistencies, quarantined with reasons)
- PD is the measured corpus: 380 finished results in 2025/2026 and 119 in 2026/2027 (499 total)

### Analysis stack
- `app/repositories/analysis.py` loads regulation-only results observed before the target kickoff. Extra time and shootouts are excluded.
- Evidence is real: provider code, archived payload ids, retrieval window, observation window, and content-stable digest.
- `poisson-v1.1.0` / `features-v1.1.0` / `evaluation-v1.1.0` with a shared rate estimator, rolling-origin backtest, calibration, uniform baselines, and explicit model parameters.
- **NEW: `validation.py`** — Strict chronological validation framework implementing protocols A-G:
  - Rolling-origin evaluation
  - Expanding training windows
  - Multiple chronological evaluation windows
  - Multiple competitions and seasons
  - Minimum historical sample requirements
  - Strict training/validation/test separation
- **NEW: `calibration.py`** — Probability calibration subsystem:
  - Reliability diagrams with proper visualization data
  - Temperature scaling calibration correction
  - Isotonic regression calibration correction
  - Per-competition, per-season, per-probability-range calibration
  - Draw probability bias analysis
  - Calibration data/train/test split
- Dixon-Coles model (`dixon-coles-v1.0.0`) with fitted rho estimation
- Elo model (`elo-v1.0.0`) with Davidson fit estimation
- Rolling-origin backtest uses the same estimator as the live path and predicts each test match only from earlier completed results
- Reports Brier, log loss, uniform baselines, Brier skill, calibration bins, ECE/MCE, and the test period

### Backend API endpoints available
- GET `/api/v1/fixtures` (`date_from`, `date_to`, `competition_id`, `country_id`, `season_id`, `team_id`, `status`, `q`, `page`, `page_size`)
- GET `/api/v1/fixtures/today` (`date`, `timezone`, `competition_id`)
- GET `/api/v1/fixtures/{match_id}`
- GET `/api/v1/fixtures/{match_id}/statistics`
- GET `/api/v1/countries`
- GET `/api/v1/competitions`, `/api/v1/competitions/{id}`
- GET `/api/v1/seasons`
- GET `/api/v1/teams` (`q`), `/api/v1/teams/{id}`, `/api/v1/teams/{id}/matches`
- GET `/api/v1/sync/runs`, `/api/v1/sync/status`
- POST `/api/v1/analysis/matches/{match_id}` (`force`)
- GET `/api/v1/analysis/{analysis_id}`
- GET `/api/v1/analysis/matches/{match_id}/history`
- **POST `/api/v1/evaluation/run`**
- **GET `/api/v1/evaluation/latest`**
- **GET `/api/v1/evaluation/runs`**
- **GET `/api/v1/evaluation/{run_id}`**

### Frontend (`apps/web`)
- `/` lists stored fixtures with crests, competition emblem, country, status and score, plus windows, search, team/country/competition filters, pagination, and freshness states
- `/matches/[id]` shows the fixture, stored statistics state, and a working **Match Analysis** panel
- The panel exposes a button (scheduled fixtures only), loading state, four report statuses, 1X2 percentages and a stacked probability bar, expected goals, secondary markets, top scorelines, historical records, H2H, model parameters, out-of-sample evaluation with calibration bins, provenance, missing features, limitations, and prior reports
- Missing values show `—` or "not supplied"; the panel never fills a blank with zero
- `npm run build` passes. Browser check at the available 471 px viewport showed no console errors and no horizontal overflow. Widths below 471 px were not emulated (LIM-022)

### Test suite status
- **265 tests passing**, 0 failed, 0 skipped (local run)
- `alembic check`: no new upgrade operations. `alembic current`: `0006 (head)`
- `npm run build`: success. `npx tsc --noEmit`: clean

### Intelligence engine modules
- `apps/backend/app/intelligence/prediction.py` — Poisson model, features, backtest
- `apps/backend/app/intelligence/models/poisson.py` — Independent Poisson score matrix
- `apps/backend/app/intelligence/models/dixon_coles.py` — Dixon-Coles with fitted rho
- `apps/backend/app/intelligence/models/elo_fitted.py` — Elo with Davidson fit
- `apps/backend/app/intelligence/validation.py` — Strict chronological validation framework
- `apps/backend/app/intelligence/calibration.py` — Probability calibration subsystem
- `apps/backend/app/intelligence/backtest.py` — Phase 7 multi-competition backtest
- `apps/backend/app/intelligence/baselines.py` — Uniform and frequency baselines
- `apps/backend/app/intelligence/evaluation.py` — Metrics, reliability, temporal partitions
- `apps/backend/app/intelligence/probabilities.py` — Probability arithmetic
- `apps/backend/app/intelligence/types.py` — Validated inputs, datasets, provenance

### Verification evidence
- Latest local verification: 2026-11-16 session
- `PYTHONPATH=apps/backend .venv/bin/python -m pytest` → **265 passed**, 1 third-party deprecation warning
- `alembic check` → No new upgrade operations detected
- `alembic current` → `0006 (head)`
- Live analysis, match 410 → `READY`; 1X2 0.6092 / 0.2320 / 0.1588; xG 1.74 / 0.76; `poisson-v1.1.0`
- Multi-competition evaluation (CLI `evaluate`) → 970 matches, 13 competitions evaluated
- Frontend build → passes; browser check at 471 px → no errors

### Documentation created in Phase 8
- `docs/research/phase-8-baseline-audit.md` — Repository audit and baseline reproduction
- `docs/research/phase-8-independent-ml-review.md` — Independent ML/QA review of numerical engine
- `docs/research/phase-8-out-of-sample-validation.md` — Validation framework documentation
- `apps/backend/app/intelligence/calibration.py` — Probability calibration subsystem