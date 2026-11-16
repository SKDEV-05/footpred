# Real Football Intelligence Implementation Audit & Plan

**Document:** `docs/research/real-intelligence-implementation-audit.md`  
**Date:** 2026-11-16  
**Roles:** Principal Software Architect, Senior Python Backend Engineer, Statistical Football Analyst, Machine Learning Engineer, Senior Next.js Engineer  
**Status:** Complete Audit — Ready for Stage 1 Execution  

---

## 1. Executive Summary

This audit evaluates the codebase to transition the Football Intelligence Platform from an offline synthetic-test-only intelligence package and read-only fixture viewer to a **real football intelligence platform**. The objective is to enable an end-to-end user experience where a user opens an upcoming fixture, triggers **Analyze Match**, and receives a transparent, mathematically grounded statistical prediction report derived solely from verified historical results, without data fabrication or future leakage.

### Baseline Status:
- **Backend:** FastAPI modular monolith running on `127.0.0.1:8000` with 247 passing tests.
- **Frontend:** Next.js 16 (Turbopack, App Router) running on `127.0.0.1:3000` with zero build warnings.
- **Database:** SQLite (`data/football.db`) with WAL mode, foreign keys enforced, 17 tables, migrations `0001`–`0004` at head.
- **Provider:** football-data.org v4 reference adapter with token configured.
- **Current Data:** 70 countries, 13 competitions, 285 teams, 417 stored matches (mostly upcoming fixtures 2026-11-14 → 2026-12-14), 2 finished results, 34 raw payload archives.
- **Current Intelligence:** Deterministic offline module (`apps/backend/app/intelligence/`) with Poisson/Dixon-Coles score matrices, outcome bounds, and temporal leakage checks, previously gated by `DataClassification.SYNTHETIC_TEST`.

---

## 2. Reusable Components & Architecture Audit

### 2.1 Backend Core & Database
- **Reusable:**
  - `apps/backend/app/models/core.py`: Canonical `Match`, `MatchResult`, `Team`, `Competition`, `Season`, and `Country` models with strict non-negative score constraints, half-time score consistency checks, and UTC timestamps.
  - `apps/backend/app/models/provenance.py`: `DataSyncRun`, `DataSyncError`, `RawPayload`, `ProviderMatchMapping` providing immutable audit trails.
  - `apps/backend/app/database/session.py`: Safe transaction and session management with WAL pragmas.
- **Gaps to Address:**
  - No database tables exist to persist match analysis runs, calculated probabilities, model versions, feature snapshots, or evaluation metrics.
  - Solution: Design and apply Alembic migration `0005_match_analysis.py` with tables `match_analyses` and related structures.

### 2.2 Provider Ingestion & Raw Payload Archival
- **Reusable:**
  - `apps/backend/app/providers/adapters/football_data_org.py`: Implements `fetch_matches`, `fetch_match_detail`, `fetch_competitions`, `fetch_teams`.
  - `apps/backend/app/providers/http.py`: Rate-limited HTTP client (`PROVIDER_REQUESTS_PER_MINUTE=10`), streaming response size bounds, and bounded exponential backoff.
  - `apps/backend/app/ingestion/fixtures.py`: Robust natural key and mapping resolution, idempotent upserts, status transition tracking, and validation checks.
  - `apps/backend/app/sync/engine.py`: Per-item transaction boundaries, quarantine tracking, and run finalization.
- **Gaps to Address:**
  - The default sync commands (`sync fixtures`, `sync results`) query short lookback windows (3 days).
  - To build a historical foundation for statistical modelling, we need a multi-season or multi-month historical synchronization capability with date-chunking (≤10 days per chunk) and strict rate-limit budgeting.

### 2.3 Intelligence Package (`apps/backend/app/intelligence/`)
- **Reusable:**
  - `types.py`: `HistoricalMatch`, `IntelligenceDataset`, `MatchRequest`, `ResearchContext`, `DatasetEvidence`, `Venue`, and `PointsPolicy`. `ADR-0010` already approved `DataClassification.VERIFIED_REAL` with `DatasetEvidence`.
  - `models/poisson.py`: Complete implementation of independent-Poisson PMF and `ScoreMatrix` calculation with explicit overflow conservation (no mass truncation or artificial renormalisation).
  - `models/dixon_coles.py`: Low-score correlation adjustment ($\tau$ parameter) on top of Poisson base rates.
  - `probabilities.py`: Exact outcome bounds (`match_outcomes`), double chance, over/under goal markets (0.5, 1.5, 2.5, 3.5), and both-teams-to-score (BTTS).
  - `evaluation.py`: Strictly out-of-sample Brier score, multi-class log loss, reliability calibration binning, and rolling-origin temporal splits.
  - `features.py`: Point-in-time rolling goals, goal difference, win rate, and sample size aggregations.
- **Gaps to Address:**
  - `apps/backend/app/intelligence/engine.py` line 49 still had a hard check `if dataset.classification is not DataClassification.SYNTHETIC_TEST: raise ValueError(...)`. This must be updated to accept `VERIFIED_REAL` with valid `DatasetEvidence` as authorized by ADR-0010.
  - **Statistical Parameter Estimation:** The existing package accepted caller-supplied Poisson rates (`home_rate`, `away_rate`). To produce predictions on real fixtures, we need a genuine statistical estimation engine:
    1. Competition baseline average goals (home and away).
    2. Team attack strength ($Attack_i$) and defense weakness ($Defense_j$).
    3. Home ground advantage factor ($H$).
    4. Expected goals:
       $$\lambda_{home} = Attack_{home} \times Defense_{away} \times AvgHomeGoals$$
       $$\mu_{away} = Attack_{away} \times Defense_{home} \times AvgAwayGoals$$
    5. Form adjustment using exponential decay or rolling weighted averages over recent matches prior to kickoff.
    6. Minimum sample size thresholds (e.g., minimum 5 matches per team in dataset; otherwise return `INSUFFICIENT_DATA`).

### 2.4 API & Routing
- **Reusable:**
  - FastAPI `/api/v1` structure with Pydantic v2 schemas and standard error handling.
- **Gaps to Address:**
  - Implement:
    - `POST /api/v1/analysis/matches/{match_id}`: Trigger / retrieve match analysis.
    - `GET /api/v1/analysis/{analysis_id}`: Retrieve a persisted analysis report.
    - `GET /api/v1/analysis/matches/{match_id}/history`: Retrieve past analyses for a fixture.

### 2.5 Frontend (`apps/web`)
- **Reusable:**
  - Next.js 16 App Router with Tailwind CSS v4, Lucide icons, dark theme.
  - Components: `TeamCrest`, `StatusBadge`, `Button`, `Badge`.
  - Client API helper: `apps/web/src/lib/api.ts`.
- **Gaps to Address:**
  - Replace the static placeholder "No validated model" box in `/matches/[id]` with an active, interactive "Analyze Match" workflow:
    - Interactive "Analyze Match" button with loading spinner and status feedback.
    - Presentation of 1X2 probabilities (summing to 100%), expected goals ($\lambda, \mu$), most likely scorelines, Over/Under, BTTS.
    - Team comparison metrics (goals scored/conceded, form, clean sheets).
    - Data quality, sample size, limitations, and provenance indicators.
    - Seamless handling of `INSUFFICIENT_DATA`, `DATA_UNAVAILABLE`, and `ANALYSIS_FAILED` states.

---

## 3. Provider Realities & Historical Coverage Investigation

### 3.1 football-data.org Free Tier Verified Capabilities
1. **Rate Limit:** 10 requests per minute. Bursting will trigger HTTP 429.
2. **Date Chunking:** Maximum window per query is 10 days (`dateFrom` to `dateTo`). Any range > 10 days returns HTTP 400.
3. **Historical Match Access:**
   - Free tier permits querying historical completed matches by specifying `season=<year>` (e.g. `season=2024` or `season=2025`) or by chunked date windows (`dateFrom` and `dateTo` with `status=FINISHED`).
   - Querying `GET /v4/competitions/{code}/matches?season=2024&status=FINISHED` or `GET /v4/matches?dateFrom=...&dateTo=...&status=FINISHED` returns real matches with final scores (`fullTime.home`, `fullTime.away`, `halfTime.home`, `halfTime.away`).
4. **Provider Statistics (Shots, Possession, Corners):**
   - **UNAVAILABLE ON FREE PLAN.** Probing `/matches/{id}` returns no `statistics` field in the payload.
   - **Strict Rule:** We must NEVER fabricate shots, possession, or xG. If match statistics are not supplied by the provider, the system records `statistics_unavailable_on_plan` and relies strictly on actual verified match results (goals, scorelines, venue, dates).
5. **Head-to-Head (H2H):**
   - The provider's dedicated H2H endpoint requires elevated permissions or is unverified.
   - **Solution:** H2H is derived internally from verified completed matches stored in our SQLite database between the two teams prior to kickoff. If fewer than 2 meetings exist, the report explicitly notes `limited_head_to_head_sample`.

---

## 4. Implementation Risks & Mitigation Strategy

| Risk | Cause | Mitigation |
|------|-------|------------|
| **Provider Rate Limiting (429)** | Rapid requests during historical sync | Strict request budgeting, 6.5s delay between provider calls, chunked date windows, persistent raw archiving so no match is fetched twice. |
| **Temporal Data Leakage** | Using results that occurred after target fixture kickoff | Strict SQL filtering: `Match.kickoff_utc < target_fixture.kickoff_utc` and `HistoricalMatch.observed_at <= analysis_as_of`. |
| **Prediction Hallucination** | Attempting to guess when data is scarce | Strict sample size check: Minimum 5 finished matches for both home and away teams. If not met, return `INSUFFICIENT_DATA`. |
| **Non-Normalized Probabilities** | Truncating Poisson tail mass | Use our conserved overflow Poisson matrix where 1X2 probabilities are normalized to sum to 1.0 (100%). |
| **Schema Drift** | Adding models without migration | Formal Alembic revision `0005_match_analysis.py` with check test verifying zero drift. |

---

## 5. Phased Implementation Roadmap

- **Stage 0:** Repository audit and implementation plan (This document).
- **Stage 1:** Historical data foundation:
  - Add historical ingestion support for multi-chunk finished matches across entitled competitions.
  - Ingest verified historical results into `data/football.db`.
  - Generate historical coverage report (`docs/data/historical-coverage-report.md`).
- **Stage 2:** Feature engineering and dataset validation:
  - Connect database models to `IntelligenceDataset` with `DataClassification.VERIFIED_REAL` and `DatasetEvidence`.
  - Calculate team form, attacking/defensive strength, home advantage, rolling statistics without future leakage.
  - Distinguish genuine zero vs missing data.
- **Stage 3:** Real statistical prediction engine:
  - Implement transparent Poisson goal model with home advantage and team strength estimation.
  - Compute 1X2 probabilities (summing to 100%), expected goals ($\lambda, \mu$), scoreline probabilities, over/under, BTTS.
  - Implement model evaluation (Brier score, log loss, calibration on historical backtests).
- **Stage 4:** Analysis persistence and API:
  - Add Alembic migration `0005` (`match_analyses` table).
  - Implement `POST /api/v1/analysis/matches/{match_id}`, `GET /api/v1/analysis/{analysis_id}`, `GET /api/v1/analysis/matches/{match_id}/history`.
  - Add comprehensive integration tests.
- **Stage 5:** Next.js Analyze Match experience:
  - Build responsive sports intelligence dashboard UI on `/matches/[id]`.
  - Add "Analyze Match" button with live loading state, status handling (`READY`, `INSUFFICIENT_DATA`, `DATA_UNAVAILABLE`, `ANALYSIS_FAILED`).
  - Render 1X2 probabilities, scoreline matrix, team comparison, historical form, and data quality/limitations.
- **Stage 6:** Full integration, verification, and acceptance:
  - Run full backend test suite (`pytest`) and frontend production build (`npm run build`).
  - Verify zero console errors, zero warnings, complete type safety.
  - Update `PROJECT_STATUS.md` and `memory/`.
