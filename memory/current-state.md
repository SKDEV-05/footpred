# Current State

**Last updated:** 2026-11-16  
**Phase:** Phase 4 accepted; Phase 5 approved under ADR-0010 and implemented privately on
loopback. It is not publicly exposed.  
**Status:** Real historical results are stored and a transparent Poisson analysis is running
end to end: point-in-time dataset, persisted report, analysis API, and Next.js panel. Backend
suite, schema check, and frontend build pass. Coverage is bounded and not a guarantee.

## What exists now

### Real stored data (local SQLite, `data/football.db`)
- Synced from football-data.org with the operator token: 70 countries, 13 competitions,
  11 seasons, 285 teams, **5,322 matches**, **4,905 finished results**, 417 upcoming fixtures.
- Finished-result range: **2025-02-05 → 2026-11-14**, two seasons per league.
- Eleven competitions have stored matches: BL1, BSA, CL, CLI, DED, ELC, FL1, PD, PL, PPL, SA.
  EC and WC have competition rows but zero stored matches; they are reported as
  `no_stored_matches`, not as coverage.
- All 5,322 stored matches link to an archived raw payload; the coverage command reports
  `payload_linking_complete = true`.
- Historical sync run 11: 4,917 fetched, 4,905 results created, 2 updated, 10 rejected. All 10
  rejections are extra-time/penalty inconsistencies and are quarantined with reasons.
- PD is the measured corpus: 380 finished results in 2025/2026 and 119 in 2026/2027 (499 total).

### Analysis stack
- `app/repositories/analysis.py` loads regulation-only results that were both played and
  observed before the target kickoff. Extra time and shootouts are excluded. It returns
  `None` when there is no history and raises `DatasetProvenanceError` when results have no
  archived payload.
- Evidence is real: provider code, archived payload ids, retrieval window, observation window,
  and a content-stable digest. Dataset ids are derived from the content digest.
- `poisson-v1.1.0` / `features-v1.1.0` / `evaluation-v1.1.0`:
  competition baseline, attack/defence strength with venue shrinkage, recent-form blend,
  expected-goals bounds, independent Poisson matrix, 1X2 normalized to exactly 1.0.
- The rolling-origin backtest uses the same estimator as the live path and predicts each test
  match only from earlier completed results. It reports Brier, log loss, uniform baselines,
  Brier skill, calibration bins, ECE/MCE, and the test period.
- Match 410 (Real Madrid vs Celta, 2026-11-21): `READY`, 1X2 **60.9% / 23.2% / 15.9%**,
  xG **1.74 / 0.76**. Backtest on 50 out-of-sample PD matches: Brier **0.5722**, log loss
  **0.9581**, uniform Brier 0.6667, uniform log loss 1.0986, skill **0.1417**, ECE **0.0661**,
  MCE **0.3084**, test period 2026-10-09 → 2026-11-08.
- Statuses: `READY`, `INSUFFICIENT_DATA`, `DATA_UNAVAILABLE`, `ANALYSIS_FAILED`.
  Finished/started/cancelled/postponed/awarded/abandoned/suspended matches and past kickoffs
  return `DATA_UNAVAILABLE`. A provenance failure returns `ANALYSIS_FAILED`.
- Repeated `POST` reuses a report when match, status, dataset digest, model version, and
  evaluation version match; `?force=true` regenerates. Reports are append-only.
- Persistence: `match_analyses`, migration `0005` (head).

### Backend
- `POST /api/v1/analysis/matches/{match_id}`, `GET /api/v1/analysis/{analysis_id}`,
  `GET /api/v1/analysis/matches/{match_id}/history`.
- `python -m app.cli coverage [--format json|markdown]` reports stored counts, per-competition
  and per-season coverage, payload linkage, and quarantined exclusions.
- CLI logs go to stderr so JSON/markdown output on stdout stays parseable.
- Fixture/result sync, reference endpoints, and sync status remain as documented in Phase 3.

### Frontend (`apps/web`)
- `/` lists stored fixtures with crests, competition emblem, country, status and score, plus
  windows, search, team/country/competition filters, pagination, and freshness states.
- `/matches/[id]` shows the fixture, stored statistics state, and a working **Match Analysis**
  panel.
- The panel exposes a button (scheduled fixtures only), loading state, four report statuses,
  1X2 percentages and a stacked probability bar, expected goals, secondary markets, top
  scorelines, historical records, H2H, model parameters, out-of-sample evaluation with
  calibration bins, provenance, missing features, limitations, and prior reports.
- Missing values show `—` or "not supplied"; the panel never fills a blank with zero.
- `npm run build` passes. Browser check at the available 471 px viewport showed no console
  errors and no horizontal overflow. Widths below 471 px were not emulated (LIM-022).

## Test suite status
- **265 tests passing**, 0 failed, 0 skipped (local run by the implementing assistant).
- Analysis coverage includes: exact 1X2 sum, determinism, insufficient-sample abstention,
  missing provenance failure, no-history abstention, unplayable statuses, idempotency and
  force regeneration, evidence windows, future-result exclusion, point-in-time `as_of`
  boundary, calibration/uniform baselines, and thin-history backtest abstention.
- `alembic check`: no new upgrade operations. `alembic current`: `0005 (head)`.
- `npm run build`: success. `npx tsc --noEmit`: clean.

## Known status of remaining gaps

| ID | Gap | Status | Blocker |
|----|-----|--------|---------|
| S-03 | Auth/authz/rate limits/TLS for public exposure | BLOCKED | Private loopback-only accepted |
| S-04/S-18 | Retention access control & log-integrity operations | PARTIAL | Code complete; operational rehearsal pending |
| LIM-006 | Public-display/redistribution licence unresolved | BLOCKED | Includes the hot-linked crest/emblem URLs (LIM-020) |
| LIM-022 | Mobile below 471 px not verified | OPEN | Browser tooling lacks viewport emulation |
| — | Independent QA/ML review of `poisson-v1.1.0` | OPEN | Backtest is a local measurement, not acceptance |
| — | In-match statistics, lineups, injuries | OPEN | Free tier has no statistics; no data purchased |
| — | Draw under-prediction | DOCUMENTED | Independent Poisson kept; not silently corrected |

## Backend API endpoints available
- GET `/api/v1/fixtures` (`date_from`, `date_to`, `competition_id`, `country_id`, `season_id`,
  `team_id`, `status`, `q`, `page`, `page_size`)
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

## Frontend pages available
- `/` — fixture explorer with time windows, search, team/country/competition filters, pagination
- `/matches/[id]` — match detail with analysis, explicit abstentions, and provenance

## Open gates
1. Independent QA/ML review of the exact analysis tree and the measured backtest.
2. Public-display licence decision (LIM-006) before any shared or public display.
3. Phase 3 QA/security conditions remain open; public exposure is rejected.
4. Decide whether the stored eleven-competition corpus is sufficient; do not add a paid plan
   or statistics tier without approval.
5. Statistics, lineups, and injuries remain unavailable and are declared, not estimated.
