# PROJECT STATUS RECONCILIATION — PHASE 7

**Date:** 2026-11-16

**Objective:** Understand the exact current state of the football intelligence platform and identify what is completed, partially completed, missing, broken, or unverified.

**Scope:** This audit verifies the actual implementation, not the documented state. No new features are implemented, no models are created, no database schemas are modified, and no data is altered or deleted.

## Summary of Findings

The platform is **functionally complete for the defined scope**: offline, synthetic-test-only intelligence foundation with Phase 5 analysis capabilities implemented privately on loopback. All tests pass except two migration tests that expect Phase 6 models (`model_evaluations`). The evaluation engine and API work end-to-end, but the current implementation includes Phase 6 and Phase 7 model evaluation features that were not in the documented Phase 5 scope.

---

## A. Completed

### Backend Core
- **Database**: SQLite with WAL, foreign keys, busy timeout, fail-closed non-SQLite enforcement
- **Schema**: Complete with all models defined in `app/models/`; migrations `0001`–`0006` applied
- **Migration system**: Alembic working; `alembic check` passes; migrations include `model_evaluations` (Phase 6)
- **Ingestion pipeline**: Raw archive, identity resolution, normalization, validation, provider adapters
- **Phase 3 read-only API**: Complete with `/api/v1/` endpoints for fixtures, teams, competitions, sync
- **Phase 5 analysis**: `POST /api/v1/analysis/matches/{id}` works end-to-end with Poisson model
- **Evaluation persistence**: `model_evaluations` table stores `match_analyses` and evaluation reports

### Intelligence Engine
- **Poisson model**: `poisson-v1.1.0` with supplied rates (Phase 4)
- **Dixon-Coles model**: Baseline Phase 4 implementation plus Phase 7 `dixon-coles-v1.0.0` with fitted `rho` estimation
- **Elo baseline**: `elo-v1.0.0` with Davidson fit estimation (Phase 7)
- **Evaluation engine**: `run_multi_competition_backtest` implements Phase 7 protocol `phase7-v1`
- **Backtesting**: Rolling-origin, multi-competition, multi-model evaluation with bootstrapped CIs

### Analysis & API
- **Analysis API**: `/api/v1/analysis/matches/{id}` produces Poisson-based reports
- **Evaluation API**: `/api/evaluation/run`, `/api/evaluation/latest`, `/api/evaluation/runs`
- **Backend CLI**: `coverage`, `migrate`, `status`, `check-provider`, `sync`, `sweep-runs`
- **Frontend**: Next.js app with fixture explorer and Match Analysis panel

### Real Historical Data
- **Storage**: `data/football.db` contains 5,322 matches, 4,905 results, 417 fixtures across 13 competitions
- **Scope**: PD (La Liga) is the evaluated corpus with 380 finished results in 2025/2026
- **Provenance**: Every match links to an archived raw payload from football-data.org
- **Analysis window**: PD matches 2025-02-05 → 2026-11-14 for evaluation

### Verification
- **Tests**: 265 tests passing (2 failures in migration tests due to missing Phase 6 expectations)
- **Live analysis**: Match 410 (Real Madrid vs Celta) returns `READY` with Poisson-based probabilities
- **Backtest**: 50 out-of-sample PD matches evaluated with Brier 0.5722, skill 0.1417
- **Persistence**: Evaluation runs stored in `model_evaluations` table

---

## B. Partially Completed

### Phase 3 (Documentation vs. Implementation)
- **Phase 3.1 remediation**: Some issues addressed but conditions remain open
- **Provider evaluation**: Live verification performed but statistics/H2H UNVERIFIED
- **Security conditions**: Public exposure rejected but private loopback accepted

### Phase 4/5 (Documentation vs. Implementation)
- **Documentation scope**: PROJECT_STATUS.md states Phase 5 analysis only, but implementation includes Phase 6 & 7
- **Model coverage**: Phase 6 (`model_evaluations`) and Phase 7 (`dixon_coles-v1.0.0`, `elo-v1.0.0`, `phase7-v1`) features exist but are undocumented
- **Frontend scope**: Project documented as Phase 5 only, but includes evaluation dashboard features

### Integration
- **Phase 6 model persistence**: `model_evaluations` table works but tests fail due to expected tables mismatch
- **Phase 7 evaluation**: Protocol `phase7-v1` implemented but not documented as scope
- **Provider statistics**: Not verified (free tier has no statistics)

---

## C. Not Implemented

### Deliberately Not Built (Documented)
- **Public deployment**: No shared-network exposure
- **Authentication**: No auth/authz/rate limits/TLS for public exposure
- **Live statistics**: No in-match statistics, lineups, injuries (free tier limitation)
- **Paid features**: No subscriptions, payments, or provider tiers
- **Frontend limitations**: Mobile below 471px not verified (LIM-022)

### Current Unverified Capabilities
- **Provider statistics**: Neither football-data.org nor API-Football statistics endpoints verified
- **H2H data**: No head-to-head records verified from either provider
- **Multi-season depth**: Only 9-day window (football-data.org) or yesterday (API-Football) verified
- **Real-time data**: No in-match statistics, events, players
- **Redistribution licence**: LIM-006 unresolved (no public display rights)

---

## D. Broken

### Tests
- **test_initial_migration_builds_every_table**: Fails because `model_evaluations` table not created by migration `0005`
- **test_upgrade_is_idempotent**: Same failure - migration mismatch

### Implementation Status
- **Phase 6/7 documentation gap**: Code implements features not in documented scope
- **Test expectations**: Migration tests expect Phase 6 tables from migration `0005` but they're actually in `0006`

---

## E. Unverified

### Business Capabilities
- **Coverage guarantee**: No proven coverage of any competition or season beyond documented
- **Provider selection**: football-data.org adapter exists, API-Football verified but statistics UNVERIFIED
- **Public deployment ready**: License unresolved (LIM-006)
- **Mobile below 486px**: Not verified (browser tooling lacks viewport emulation)
- **Independent QA/ML review**: Open requirement for `poisson-v1.1.0` review

### Provider Capabilities
- **Statistics**: Not called on either provider during Phase 6 audit
- **H2H**: Not called on either provider during Phase  doubling 06 audit
- **Season depth**: Only recent window probed, not multi-season
- **Lineups/players**: Not called during audit

---

## F. Model Evaluation (Measured Results)

### Actual Evaluation Run (CLI: `python -m app.cli evaluate --summary-only`, 2026-11-16)
- **Evaluation ID**: 1
- **Protocol**: `phase7-v1`
- **Evaluation version**: `evaluation-v1.2.0`
- **Dataset**: `ds_corpus_a9dff46f14c9b473` (digest: `bde93c2d1684d7133cb40c4fd928075b447b1006e13c0d229bb0142b0a1ad42c`)
- **Sample size**: **970 matches** (not 50)
- **Window**: 2026-02-25 → 2026-11-14 (9 months across all 13 competitions)
- **Generated**: 2026-11-16T19:49:29.766189Z

### Model Metrics (all scored on identical 970 matches)

| Model | Key | Version | Brier | Log Loss | Brier Skill vs Uniform | ECE |
|-------|-----|---------|-------|----------|------------------------|-----|
| Poisson | `poisson` | `poisson-v1.1.0` | **0.5831** | 0.9828 | **0.1253** | 0.0254 |
| Dixon-Coles | `dixon_coles` | `dixon-coles-v1.0.0` | 0.5829 | 0.9821 | 0.1256 | 0.0258 |
| Elo (Davidson) | `elo` | `elo-v1.0.0` | 0.5911 | 0.9916 | 0.1133 | 0.0375 |
| Uniform (baseline) | `uniform` | `uniform-v1.0.0` | 0.6667 | 1.0986 | 0.0000 | 0.0802 |
| Competition frequency | `competition_frequency` | `frequency-v1.0.0` | 0.6405 | 1.0592 | 0.0393 | **0.0143** |

### Key Observations
- **All models beat uniform baseline** on Brier skill (positive = better than 1/3 guessing)
- **Dixon-Coles slightly edges Poisson** (0.1256 vs 0.1253 Brier skill, 0.5829 vs 0.5831 Brier)
- **Elo lags** other models on both Brier (0.5911) and log loss (0.9916)
- **Competition frequency** has best calibration (ECE 0.0143) but worst discrimination (Brier 0.6405)
- **Sample size**: 970 is meaningful; covers all 13 competitions with stored finished results

### Per-Competition Evaluation
- **Competitions evaluated**: All 13 with sufficient history (BL1, BSA, CL, CLI, DED, ELC, FL1, PD, PL, PPL, SA, EC, WC)
- **EC/WC**: `no_stored_matches` in corpus, marked `INSUFFICIENT_DATA` 
- **Phase 7 protocol**: Models fitted per competition before first test match, frozen for window

### Phase 5 Single-Competition Backtest (from docs)
- **Model**: `poisson-v1.1.0` only
- **Competition**: PD only
- **Sample**: 50 out-of-sample matches (2026-10-09 → 2026-11-08)
- **Brier**: 0.5722, **Log loss**: 0.9581, **Skill**: 0.1417
- **ECE**: 0.0661, **MCE**: 0.3084
- **Note**: Phase 5 backtest differs from Phase 7 multi-competition protocol

---

## G. Business Readiness

### Data Quality
- **Storage**: Real historical results (4,905 finished) with archived payloads
- **Provenance**: Every match linked to provider raw archive
- **Completeness**: Missing data stays missing, never filled with zeros
- **Quality**: Extra-time/penalty defects quarantined (10 rejections)

### Model Quality
- **Reproducibility**: Predictions reconstructable from stored inputs, code version, parameters
- **Synthetic testing**: All intelligence tests pass (265/267)
- **Evaluation evidence**: Backtest results measured but only on one corpus (PD)
- **Calibration**: Measurable but indicates room for improvement (ECE 0.0661)

### Commercial Data Licensing
- **football-data.org**: Free tier verified, statistics UNVERIFIED, public display licence UNVERIFIED
- **API-Football**: Free tier verified (100 requests/day), per-date only, statistics UNVERIFIED
- **No paid plans**: None purchased, no entitlements obtained
- **Statistics tier**: No statistics available on free tiers, blocked until verified

### Security
- **Phase 3 security**: ACCEPTED WITH CONDITIONS (private loopback only)
- **Public exposure**: REJECTED (LIM-006 unresolved)
- **Loopback only**: All real data and analysis runs on localhost only
- **No auth**: No authentication, authorization, rate limiting implemented

### Authentication / Rate Limiting / TLS
- **Not implemented**: No auth system, no rate limits, no TLS for public exposure
- **Scope**: Explicitly documented as deliberately not built
- **Private loopback**: Accepted as current operational mode

### Operational Readiness
- **Database**: SQLite only, migrations working, schema locked (Phase 5 scope)
- **Frontend**: TypeScript build passes, Next.js app functions locally
- **Monitoring**: No CI/CD, monitoring stack, or operational tooling
- **Deployment**: Deliberately not built (Docker, CI/CD, PostgreSQL)
- **API documentation**: Complete but doesn't reflect actual implementation (Phase 6/7 features)

---

## H. Next Development Roadmap

### Priority 1: Scope Alignment (Must)
1. **Resolve scope documentation**: Update PROJECT_STATUS.md, CLAUDE.md to reflect actual implementation
   - **Priority**: Critical
   - **Files affected**: PROJECT_STATUS.md, CLAUDE.md, memory/* files
   - **Dependencies**: Developer approval for Phase 6/7 scope
   - **Acceptance criteria**: Documentation matches implemented features
   - **Tests required**: Updated migration test expectations (Phase 6 tables from migration `0006`)

### Priority 2: Data Capabilities (Blocker)
2. **Verify provider statistics**: Bounded verification of football-data.org and API-Football statistics endpoints
   - **Priority**: High (blocks Phase 6 statistics)
   - **Files affected**: Phase 6 audit, provider evaluation docs
   - **Dependencies**: football-data.org API v4, API-Football documentation
   - **Acceptance criteria**: Statistics endpoints work and return usable data
   - **Tests required**: Live provider tests with synthetic validation

3. **Verify multi-season depth**: Test historical season access on Free plans
   - **Priority**: High (blocks historical backfill)
   - **Files affected**: Coverage matrix, ingestion pipeline
   - **Dependencies**: Provider authentication, API rate limits
   - **Acceptance criteria**: Can fetch 3-5 completed seasons per competition
   - **Tests required**: Historical backfill tests for each provider

### Priority 3: Business Blockers (Must)
4. **Resolve public display license**: Obtain or verify redistribution rights for PD match results
   - **Priority**: High (LIM-6) 
   - **Files affected**: LIM-6 tracking, provider evaluation
   - **Dependencies**: Provider terms review, legal approval
   - **Acceptance criteria**: Valid licence for public data display
   - **Tests required**: No tests - legal requirement

5. **Independent QA/ML review**: External review of `poisson-v1.1.0` and fitted models
   - **Priority**: High (mandated by developer)
   - **Files affected**: Research documentation, evaluation reports
   - **Dependencies**: ML reviewer availability
   - **Acceptance criteria**: Signed off on accuracy, calibration, limitations
   - **Tests required**: None - qualitative review

### Priority 4: Infrastructure (Phase 5/6)
6. **Implement proper Phase 5/6 boundaries**: Separate intelligence from ingestion in code structure
   - **Priority**: Medium
   - **Files affected**: Architecture, dependency direction, review gates
   - **Dependencies**: AGENTS.md phase boundaries, ADR-0008 entry gates
   - **Acceptance criteria**: Clear separation with import enforcement
   - **Tests required**: Architecture review, boundary tests

7. **Add missing infrastructure**: Monitoring, logging, backup, PostgreSQL option
   - **Priority**: Low (deliberately not built scope)
   - **Files affected**: Architecture decisions, deployment guides
   - **Dependencies**: Business case for production operations
   - **Acceptance criteria**: Production-ready operations capabilities
   - **Tests required**: Operational testing, load testing

---

## Verification Evidence

### Tests Executed
- **Full pytest suite**: 265 passed, 2 failed (migration table expectations)
- **Alembic check**: No drift (migration `0006` applied)
- **Live analysis**: Match 410 analyzed successfully via API (Real Madrid vs Celta, READY)
- **Backtest**: 50 out-of-sample PD matches evaluated (Phase 5), 970 matches evaluated (Phase 7)
- **Frontend build**: `npm run build` passes
- **Database schema**: All tables created except Phase 6 mismatch
- **CLI evaluate**: Works end-to-end, stores run in `model_evaluations` table

### Code Inspection
- **Phase 4 models**: Poisson, Dixon-Coles (baseline), Elo (baseline) - all implemented
- **Phase 5 analysis**: Analysis API, match_analyses table, persistence working
- **Phase 6 models**: Dixon-Coles fitted (`dixon-coles-v1.0.0`), Elo fitted (`elo-v1.0.0`), evaluation persistence (`model_evaluations`)
- **Phase 7 evaluation**: `phase7-v1` protocol, multi-competition backtest, fitted parameter estimation

### Runtime Verification (2026-11-16 session)
- **API endpoints**: All documented endpoints functional (`/api/v1/analysis/matches/{id}`, `/api/evaluation/run`, `/api/evaluation/latest`, `/api/evaluation/runs`)
- **Database records**: 5,322 matches, 4,905 finished results, 417 upcoming fixtures across 13 competitions
- **Evaluation persistence**: 1 run stored in `model_evaluations` table (ID=1, protocol `phase7-v1`, 970 matches)
- **Model comparison**: All 5 models (Poisson, Dixon-Coles, Elo, Uniform, Competition Frequency) evaluated on identical 970-match test set
- **Frontend integration**: Analyze Match panel displays Poisson-based analysis with calibration, provenance, and history
- **Coverage report**: `python -m app.cli coverage` returns complete provenance metadata
- **Provider verification**: `python -m app.cli check-provider` verifies football-data.org auth

---

## Conclusion

The platform is **technically complete** for its intended Phase 5 scope (offline, synthetic-test-only intelligence foundation with private analysis). However, the implementation **exceeds documented scope** by including Phase 6 model persistence and Phase 7 fitted model evaluation.

**Critical issues**:
1. **Scope misalignment**: Documentation claims Phase 5 only, but implementation includes Phase 6/7
2. **Migration test failures**: Expected Phase 6 tables in wrong migration
3. **Provider statistics unverified**: Critical for Phase 6 statistics capability

**Recommendations**:
1. **Immediate**: Align documentation with implementation or remove Phase 6/7 features
2. **Before production**: Obtain public display license (LIM-6) and verify provider statistics
3. **Before expansion**: Obtain independent QA/ML review of fitted models
4. **Before scaling**: Implement proper Phase 5/6 boundaries if keeping Phase 6

The platform is ready for **Phase 5 operations** (private, loopback-only) but has **unresolved blockers** for Phase 6 production deployment and scope clarity.