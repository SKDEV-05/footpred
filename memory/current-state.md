# Current State
**Last updated:** 2026-11-16
**Phase:** Phase 5 — Private real-data match analysis (approved under ADR-0010)
**Status:** Real historical results stored and transparent Poisson analysis running end to end

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
- Evidence is real: provider code, archived payload ids, retrieval window, observation window, and content-stable digest
- `poisson-v1.1.0` / `features-v1.1.0` / `evaluation-v1.1.0`: competition baseline, attack/defence strength, recent-form blend, expected-goals bounds, independent Poisson matrix, 1X2 normalized to exactly 1.0
- Elo baseline with Davidson fit (home advantage + draw parameter)
- Dixon-Coles with fitted rho estimation
- Rolling-origin backtest with bootstrap CIs

### Backend API endpoints available
- GET `/api/v1/fixtures` (date_from, date_to, competition_id, country_id, season_id, team_id, status, q, page, page_size)
- GET `/api/v1/fixtures/today` (date, timezone, competition_id)
- GET `/api/v1/fixtures/{match_id}`
- GET `/api/v1/fixtures/{match_id}/statistics`
- GET `/api/v1/countries`
- GET `/api/v1/competitions`, `/api/v1/competitions/{id}`
- GET `/api/v1/seasons`
- GET `/api/v1/teams` (q), `/api/v1/teams/{id}`, `/api/v1/teams/{id}/matches`
- GET `/api/v1/sync/runs`, `/api/v1/sync/status`
- **POST `/api/v1/analysis/matches/{match_id}`** (`force`)
- **GET `/api/v1/analysis/{analysis_id}`**
- **GET `/api/v1/analysis/matches/{match_id}/history`**
- **POST `/api/v1/evaluation/run`** (new)
- **GET `/api/v1/evaluation/latest`** (new)
- **GET `/api/v1/evaluation/runs`** (new)
- **GET `/api/v1/evaluation/{run_id}`** (new)

### Intelligence engine
- Poisson model (`poisson-v1.1.0`): 970 matches evaluated on 2026-11-16, Brier 0.5831, log loss 0.9828, skill 0.1253 vs uniform, ECE 0.0254
- Dixon-Coles model (`dixon-coles-v1.0.0`): fitted rho via WML, 970 matches, Brier 0.5829, skill 0.1256, ECE 0.0258
- Elo model (`elo-v1.0.0`): Davidson fit, 970 matches, Brier 0.5911, log loss 0.9916, skill 0.1133, ECE 0.0375
- Uniform baseline: Brier 0.6667, log loss 1.0986
- Competition frequency baseline: Brier 0.6405, skill 0.0393, ECE 0.0143 (best calibration)
- 50-match PD backtest (Phase 5): Brier 0.5722, log loss 0.9581, skill 0.1417, ECE 0.0661, MCE 0.3084

### Evaluation persistence
- `model_evaluations` table (migration `0006`) stores protocol version, evaluation version, dataset digest, report
- Identity: `(protocol_version, evaluation_version, dataset_digest)` — same corpus same protocol → same stored run
- `python -m app.cli evaluate` triggers full backtest, persists report, returns run id
- `GET /api/v1/evaluation/latest` / `GET /api/v1/evaluation/runs` serve stored results

### Test suite status
- **265 tests passing**, 0 failed, 0 skipped (local run)
- `alembic check`: No new upgrade operations detected
- `alembic current`: `0006 (head)`
- `npm run build`: passes
- `npx tsc --noEmit`: clean

### Known status of remaining gaps

| ID | Gap | Status | Blocker |
|----|-----|--------|---------|
| S-03 | Auth/authz/rate limits/TLS for public exposure | BLOCKED | Private loopback-only accepted |
| S-04/S-18 | Retention access control & log-integrity operations | PARTIAL | Code complete; operational rehearsal pending |
| LIM-006 | Public-display/redistribution licence unresolved | BLOCKED | Includes hot-linked crest/emblem URLs (LIM-020) |
| LIM-022 | Mobile below 471 px not verified | OPEN | Browser tooling lacks viewport emulation |
| — | Independent QA/ML review of `poisson-v1.1.0` | OPEN | Backtest is a local measurement, not acceptance |
| — | In-match statistics, lineups, injuries | OPEN | Free tier has no statistics; no data purchased |
| — | Draw under-prediction | DOCUMENTED | Independent Poisson kept; not silently corrected |

### Open gates
1. Independent QA/ML review of the exact analysis tree and the measured backtest.
2. Public-display licence decision (LIM-006) before any shared or public display.
3. Phase 3 QA/security conditions remain open; public exposure is rejected.
4. Decide whether the stored eleven-competition corpus is sufficient; do not add a paid plan or statistics tier without approval.
5. Statistics, lineups, and injuries remain unavailable and are declared, not estimated.