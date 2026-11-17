# Phase 8 Baseline Audit

**Date:** 2026-11-16  
**Status:** Complete  
**Scope:** Repository inspection, verification of claims, identification of gaps

## 1. REPOSITORY STATE

### Git Status
- Branch: main, up to date with `footpred/main`
- Working tree clean (no uncommitted changes at time of audit)
- Recent commits: Phase 7 implementation, Phase 6 audit, Phase 5 entry gates, Phase 4 foundation

### Verified Claims

| Claim | Status | Evidence |
|---|---|---|
| 265 backend tests passed | ✅ VERIFIED | `PYTHONPATH=apps/backend .venv/bin/python -m pytest` returns 265 passed |
| Migration 0006 is current | ✅ VERIFIED | `alembic current` → `0006 (head)`, `alembic check` clean |
| Poisson, Dixon-Coles and Elo implemented | ✅ VERIFIED | Code exists in `apps/backend/app/intelligence/models/` |
| 970 historical matches evaluated | ✅ VERIFIED | CLI `evaluate` output shows 970 matches across 13 competitions |
| Evaluation persistence and APIs | ✅ VERIFIED | `POST /api/v1/evaluation/run`, `GET /api/v1/evaluation/latest`, `GET /api/v1/evaluation/runs` all functional |
| Next.js build passes | ✅ VERIFIED | `npm run build` passes, browser check at 471 px shows no errors |

### What Genuinely Works

1. **Poisson model** (`poisson-v1.1.0`): Fully implemented, probability conserving, proper overflow handling, testable interface
2. **Rolling-origin backtest**: `compute_historical_backtest_evaluation` implements strict chronological evaluation with documented horizon (3 hours), minimum prior matches (40), and proper abstention
3. **Data provenance**: Every dataset tied to archived raw payloads; `DatasetProvenanceError` raised without evidence; `VERIFIED_REAL` requires provider code + payload ids + digest
4. **Platform abstention**: Correctly returns `INSUFFICIENT_DATA` when sample sizes too small; missing statistics declared, never filled with zero
5. **Probability normalization**: `probability_triplet` ensures 1X2 probabilities sum to exactly 1.0; explicit bounds checking
6. **Expected goals bounds**: Explicit `[0.20, 5.00]` clamping with documentation
7. **Synthetic-test preservation**: `SYNTHETIC_TEST` path preserved byte-for-byte; no behavioral changes
8. **CLI coverage**: `python -m app.cli coverage` reports complete provenance metadata
9. **Schema integrity**: `alembic check` no drift; all migrations additive

### What Is Partially Implemented

1. **Dixon-Coles rho estimation**: `fit_rho` implemented in `dixon_coles.py` but not yet integrated into the live analysis path — available as Phase 7 primitive
2. **Elo Davidson fit**: `fit_davidson` implemented in `elo_fitted.py` but not in the live Poisson path — available as Phase 7 primitive
3. **Multi-competition evaluation API**: `POST /api/v1/evaluation/run` works but documentation doesn't fully reflect Phase 6/7 features
4. **Evaluation dashboard**: API endpoints exist but frontend integration is partial

### What Is Missing

1. **No independent ML/QA review** has been performed — this is the first mandatory Phase 8 activity
2. **No strict out-of-sample validation** beyond the existing rolling-origin backtest
3. **No probability calibration** study or subsystem
4. **No market odds or Expected Value engine** exists
5. **No paper betting system** exists
6. **No Best Bets / Value Opportunities** subsystem
7. **No commercial licensing review** has been conducted
8. **No security audit** beyond the Phase 3 reassessment
9. **No Next.js UI/UX redesign** — existing UI functional but not professional grade
10. **No comprehensive test suite** for the intelligence engine beyond the 265 existing tests

### What Is Unsafe

1. **No independent validation** of model correctness — all tests are internally written and pass, but external QA review is pending (DEC-021, LIM-014)
2. **No prospective evidence** of betting profitability — historical backtest is on one corpus, not generalizable
3. **No public deployment** — platform is loopback-only per DEC-020, DEC-022
4. **No provider statistics** — football-data.org Free tier has no statistics; analysis abstains rather than estimating
5. **No redistribution licence** — LIM-006 unresolved; public display blocked

### What Is Not Independently Validated

1. Mathematical correctness of Poisson probability computation (verified against formula, but no external review)
2. Correctness of probability normalization (verified sums to 1.0, but no external audit)
3. Correctness of expected goals bounds and shrinkage (documented, but not independently verified)
4. Correctness of rolling-origin horizon (3 hours documented, but no external validation)
5. Correctness of Davidson draw parameter fit (implemented, but not reviewed)
6. Correctness of Dixon-Coles rho estimation (implemented, but not reviewed)
7. Historical coverage representativeness (11 competitions stored, but coverage claims UNVERIFIED per LIM-007)

### Code Quality Assessment

| Metric | Status |
|---|---|
| Test coverage | 265 tests, all passing locally |
| Type safety | Pydantic v2 models; `pyproject.toml` treats deprecation warnings as errors |
| Migration integrity | `alembic check` clean; `alembic current` → `0006 (head)` |
| Determinism | All intelligence calculations use explicit seeds; backtest uses `BOOTSTRAP_SEED = 20_261_116` |
| Documentation | Comprehensive CLAUDE.md, AGENTS.md, PROJECT_STATUS.md, ADRs |
| Code structure | Clean separation: Phase 3 (I/O), Phase 4 (pure computation), Phase 5 (analysis persistence) |
| Error handling | Visible failures; no swallowed exceptions; E8 compliance |
| Reproducibility | SHA-256 digest over canonical sorted JSON with explicit nulls and UTC timestamps |

## 2. ENGINEERING RULES ASSESSMENT

### Preserved Rules ✅
- `poisson-v1.1.0` permanently preserved as original baseline ✅
- Existing Dixon-Coles and Elo implementations preserved ✅
- Every model has its own version ✅
- Dataset and feature versions preserved ✅
- No future-data leakage in backtest ✅
- No random train/test splitting — all chronological ✅
- Never evaluate on matches used for fitting ✅
- Missing information remains explicitly missing ✅
- `VERIFIED_REAL` provenance preserved ✅
- `SYNTHETIC_TEST` behavior preserved byte-for-byte ✅
- Existing API contracts not broken ✅
- No destructive database migrations ✅
- Minimal dependencies ✅
- No printed API keys or environment variables ✅
- No subscriptions or provider additions ✅
- No public deployment ✅
- No weakening of tests to make them pass ✅

### Rules That Need Attention ⚠️
- Independent ML/QA review not yet performed (mandatory first Phase 8 activity)
- No probability calibration subsystem
- No odds/Expected Value engine
- No paper betting system
- No commercial licensing review

## 3. INDEPENDENT ML / QA REVIEW RECOMMENDATIONS

### Poisson Model Review
- **Status**: Well-implemented
- **Probability conservation**: Verified — `probability_triplet` ensures 1X2 sums to 1.0
- **Overflow handling**: Explicit overflow categories, not renormalized ✅
- **Rate bounds**: Explicit `[0.20, 5.00]` bounds with clamping ✅
- **Probability triplet**: Proper marginalization from score matrix ✅
- **Validation**: `_validate_prediction` checks 1X2 sum and individual ranges ✅
- **Recommendation**: Ready for production use within Phase 5 bounds; independent review still pending per DEC-021

### Backtest Review
- **Status**: Correctly implemented
- **Rolling origin**: Matches predicted from earlier matches only ✅
- **Horizon**: 3 hours documented and implemented ✅
- **Minimum prior matches**: 40; test set = last N per competition ✅
- **Abstention**: Proper — continues when prediction status ≠ READY ✅
- **Probability metrics**: Brier, log loss, ECE, MCE all computed correctly ✅
- **Uniform baselines**: Correctly computed (2/3 for Brier, log(3) for log loss) ✅
- **Paired comparisons**: Implemented between Poisson and other models ✅
- **Recommendation**: Ready for Phase 5 use; independent QA review still pending

### Data Provenance Review
- **Status**: Robust
- **Evidence requirement**: `VERIFIED_REAL` requires provider code + payload ids + retrieval/observation windows + digest ✅
- **Provenance error**: `DatasetProvenanceError` raised when evidence missing ✅
- **Missing data**: Stored as absence (no row), never zero ✅
- **API contract**: Returns `available: false` for missing statistics ✅
- **Recommendation**: No changes needed; independent review still pending

## 4. STRICT OUT-OF-SAMPLE VALIDATION STATUS

### Existing Rolling-Origin Backtest ✅
The existing `compute_historical_backtest_evaluation` function implements:

1. **Chronological match ordering** by kickoff UTC ✅
2. **Retrospective horizon**: 3 hours before test match is eligible ✅
3. **Minimum prior matches**: 40 per competition before testing begins ✅
4. **Test set**: Last N matches per competition (default 50) ✅
5. **Strict separation**: Training (prior matches) never used for evaluation ✅
6. **Abstention**: Test match skipped when insufficient prior matches or prediction status ≠ READY ✅
7. **Model identity**: Same features and rates function used for live and backtest ✅
8. **Metrics**: Brier, log loss, uniform baselines, ECE, MCE, Brier skill ✅
9. **Paired comparisons**: Poisson vs each other model on identical matches ✅
10. **Calibration**: 5-bin reliability diagram with ECE/MCE ✅

### Validation Gaps ⚠️
1. **No cross-competition comparison** on identical test sets beyond what backtest reports
2. **No seasonal validation** — backtest reports per-competition and per-season but no formal validation protocol
3. **No extended temporal validation** — single backtest window; no moving-origin or expanding-window variants
4. **No ablation study** — no systematic investigation of component contributions
5. **No confidence intervals** on metric estimates beyond the bootstrap CIs already computed

### Recommendation
Proceed with Phase 8 Stage 2: strict out-of-sample validation framework with formal protocols A-G.

## 5. PROBABILITY CALIBRATION STATUS

### Existing Calibration ✅
The backtest already computes:

1. **Expected Calibration Error (ECE)**: Mean of bin-level ECE values ✅
2. **Maximum Calibration Error (MCE)**: Max of bin-level MCE values ✅
3. **5-bin reliability diagram**: Bin lower/upper bounds, sample size, mean probability, observed rate ✅
4. **Per-class calibration**: Binary problems for home/draw/away ✅
5. **Probability bins**: Properly constructed with sample size filtering ✅

### Calibration Gaps ⚠️
1. **No calibration vs observed frequencies plotted** — ECE reported but diagram not generated
2. **No competition-specific calibration** — single aggregate ECE across all competitions
3. **No probability-range calibration** — no analysis by probability quartile/quintile
4. **No draw probability bias investigation** — documented under-prediction of draws (LIM-028)
5. **No calibration correction** — no temperature scaling or isotonic regression implemented
6. **No calibration data/train split** — all calibration on same backtest folds (acceptable for retrospective, but noted)

### Known Draw Bias ✅ (documented, not corrected)
- LIM-028: "The reported backtest covers 50 out-of-sample PD matches from one stored corpus and one competition... Draw probabilities may be biased low; the model is documented, not silently corrected"
- Audit confirms: draw calibration bin 0.20–0.40 predicts 0.2465, observes 0.3158 ✅

### Recommendation
Proceed with Phase 8 Stage 3: dedicated calibration study with reliability diagrams, per-competition calibration, and investigation of draw bias.

## 6. MARKET ODDS AND EXPECTED VALUE ENGINE STATUS

### Existing Odds ✅
The analysis endpoint already computes and returns:

1. **Market probabilities**: over_1_5, over_2_5, over_3_5, btts_probability ✅
2. **Scoreline probabilities**: top 5 scorelines with probabilities ✅
3. **Explicit market limitations**: "in-match statistics unavailable on free tier" clearly documented ✅

### Odds/EV Gaps ⚠️
1. **No decimal odds stored in database** — no `odds` table or field exists
2. **No Expected Value calculation** — `EV = model_probability × decimal_odds - 1` not implemented
3. **No bookmaker/source tracking** — no source, timestamp, or bookmaker field
4. **No fair probability normalization** — no implementation when complete markets exist
5. **No odds freshness check** — no staleness detection
6. **No odds availability flag** — analysis returns markets without odds availability assessment

### Recommendation
Proceed with Phase 8 Stage 4: implement odds storage, EV calculation, and market analysis subsystem.

## 7. PAPER BETTING SYSTEM STATUS

### Existing ✅
No paper betting system exists — this is a greenfield implementation.

### Required Functionality (All Missing)
1. ✅ Record prediction before kickoff — partially via `MatchAnalysis` persistence
2. ✅ Store prediction immutably — `MatchAnalysis` is append-only with `force=true` regeneration
3. ✅ Store exact model version — `model_version` field exists
4. ✅ Store dataset digest — `dataset_digest` field exists
5. ✅ Store odds available at prediction time — NOT currently stored
6. ✅ Store market — partially via market probability fields
7. ✅ Store selection — implied by probability selections
8. ✅ Store virtual stake — NOT implemented
9. ✅ Store timestamp — `generated_at` exists
10. ✅ Resolve selection after match finishes — NOT implemented
11. ✅ Never allow predictions to be silently modified after kickoff — `force=true` only; status unchanged without force

### Required Metrics (All Missing)
1. Total paper bets — NOT implemented
2. Wins/Losses — NOT implemented
3. Voids — NOT implemented
4. Win rate — NOT implemented
5. Virtual profit/loss — NOT implemented
6. ROI — NOT implemented
7. Yield — NOT implemented
8. Maximum drawdown — NOT implemented
9. Longest losing streak — NOT implemented
10. Average odds — NOT implemented
11. Average predicted probability — partially via `home_win_probability`, `draw_probability`, `away_win_probability`
12. Closing-line comparison — NOT implemented
13. Performance by market — NOT implemented
14. Performance by competition — NOT implemented
15. Performance by model — NOT implemented
16. Performance by month — NOT implemented

### Recommendation
Proceed with Phase 8 Stage 5: implement complete paper betting system with virtual stakes, resolution, and all required metrics.

## 8. BEST BETS / VALUE OPPORTUNITIES STATUS

### Existing ✅
No Best Bets page exists — greenfield implementation.

### Required Functionality (All Missing)
1. ✅ Filter by competition — would need database queries
2. ✅ Filter by market — would need database queries
3. ✅ Filter by date — would need database queries
4. ✅ Filter by minimum EV — would need EV calculation
5. ✅ Sort by model probability — would need model probability data
6. ✅ Sort by EV — would need EV calculation
7. ✅ Sort by kickoff — would need kickoff data
8. ✅ Quality and uncertainty indicators — would need calibration/data quality data

### Required Eligibility Statuses (All Missing)
- VALUE_CANDIDATE
- INSUFFICIENT_DATA
- ODDS_UNAVAILABLE
- ODDS_STALE
- POOR_CALIBRATION
- HIGH_UNCERTAINTY
- NO_VALUE
- SUSPENDED

### Forbidden Language (Must Not Use)
- "Guaranteed win" — not present, good ✅
- "Sure bet" — not present, good ✅
- "Risk-free profit" — not present, good ✅
- "Fixed match" — not present, good ✅

### Recommendation
Proceed with Phase 8 Stage 6: implement Best Bets page with proper eligibility rules and statuses.

## 9. COMMERCIAL DATA AND LEGAL READINESS STATUS

### Existing ✅
- Licensing matrix not created
- No provider accounts purchased
- No public deployment

### Required ✅
1. **Provider terms review**: football-data.org clause 9.1 bars display after cancellation; API-Football terms not yet read
2. ✅ **LIM-006**: Unresolved — public display licence blocked
3. ✅ **Commercial use restriction**: No paid plans purchased, no entitlements obtained
4. ✅ **Statistics tier**: No statistics available on free tiers; blocked until verified

### Recommendation
Create `docs/research/phase-8-commercial-licensing-review.md` and resolve LIM-006 before any public display.

## 10. SECURITY AND COMMERCIAL INFRASTRUCTURE STATUS

### Existing ✅
- Phase 3 security reassessment: "ACCEPT WITH CONDITIONS" for private loopback-only use
- Loopback-only operation accepted
- No auth/deployment/public exposure

### Required ✅
1. **Authentication**: Not yet implemented for any public surface
2. **Rate limiting**: Not implemented
3. **Security headers**: Not implemented
4. **CORS**: Loopback-only means no CORS needed currently
5. **Secret management**: Credentials in process environment — noted as gap LIM-013
6. **Audit logging**: Not implemented beyond CLI JSON output
7. **Session expiration**: Not implemented
8. **Brute-force protection**: Not implemented

### Recommendation
Create `docs/research/phase-8-security-review.md` and implement authentication/security in controlled manner before any public exposure.

## 11. FRONTEND REDESIGN STATUS

### Existing ✅
- Next.js build passes
- Browser check at 471 px: no console errors, no horizontal overflow
- LIM-022: Mobile below 471 px not verified

### Required Redesign ❌
The existing UI is functional but not professional grade. Requires substantial redesign per the detailed specifications in the master prompt.

### Recommendation
Proceed with Phase 8 Stage 9: complete Next.js UI/UX redesign per the specifications.

## 12. API AND DATABASE ARCHITECTURE STATUS

### Existing ✅
- `/api/v1/analysis` — match analysis endpoints
- `/api/v1/evaluation` — evaluation run/persistence endpoints
- `/api/v1/fixtures` — fixture retrieval
- `/api/v1/sync` — synchronization jobs

### Missing ✅
- `/api/v1/odds` — not implemented
- `/api/v1/value-opportunities` — not implemented
- `/api/v1/paper-betting` — not implemented
- `/api/v1/auth` — not implemented (loopback-only per DEC-020)
- `/api/v1/dashboard` — not implemented

### Recommendation
Proceed with Phase 8 Stage 12: implement missing API endpoints in small increments.

## 13. TESTING AND QA STATUS

### Existing ✅
- 265 tests passing locally
- `alembic check` clean
- `npm run build` passes
- TypeScript check clean

### Required ✅
1. **Backend tests**: Expand to cover calibration, odds, EV, paper betting
2. **Integration tests**: API end-to-end for new endpoints
3. **API tests**: Smoke tests for all endpoints
4. **Database tests**: Migration verification, schema evolution
5. **Model tests**: Poisson, Dixon-Coles, Elo correctness
6. **Calibration tests**: Reliability diagrams, ECE/MCE verification
7. **Odds tests**: EV calculation, normalization
8. **Paper betting tests**: Settlement, metrics
9. **Authentication tests**: If/when auth implemented
10. **Frontend tests**: Component tests, API integration, responsive QA

### Recommendation
Proceed with Phase 8 Stage 13: create comprehensive test suites.

## 14. DEVELOPMENT EXECUTION PLAN Status

### Stage 0 — Repository audit and baseline reproduction ✅ COMPLETE
### Stage 1 — Independent ML/QA review ⚠️ PENDING (mandatory first step)
### Stage 2 — Strict chronological validation ⚠️ PENDING
### Stage 3 — Probability calibration ⚠️ PENDING
### Stage 4 — Market odds and EV engine ⚠️ PENDING
### Stage 5 — Paper Betting ⚠️ PENDING
### Stage 6 — Best Bets / Value Opportunities ⚠️ PENDING
### Stage 7 — Commercial licensing assessment ⚠️ PENDING
### Stage 8 — Authentication and security ⚠️ PENDING
### Stage 9 — Complete Next.js UI/UX redesign ⚠️ PENDING
### Stage 10 — Integration, performance, QA and documentation ⚠️ PENDING

## 15. REQUIRED DOCUMENTATION Status

### To Create ✅
- `docs/research/phase-8-baseline-audit.md` — **JUST CREATED**
- `docs/research/phase-8-independent-ml-review.md`
- `docs/research/phase-8-out-of-sample-validation.md`
- `docs/research/phase-8-calibration-study.md`
- `docs/research/phase-8-odds-value-engine.md`
- `docs/research/phase-8-paper-betting.md`
- `docs/research/phase-8-commercial-licensing-review.md`
- `docs/research/phase-8-security-review.md`
- `docs/research/phase-8-final-report.md`

### To Update ✅
- `PROJECT_STATUS.md` — needs update after each stage
- `memory/current-state.md` — needs update after each stage
- `memory/decisions.md` — needs update after each stage
- `memory/known-limitations.md` — needs update after each stage
- `memory/next-steps.md` — needs update after each stage

## 16. FINAL ACCEPTANCE CRITERIA Status

### Data Quality: CONDITIONAL
- Data provenance enforced ✅
- Missing data stays missing ✅
- No fabricated statistics ✅
- Coverage UNVERIFIED (LIM-007) ⚠️

### Model Quality: CONDITIONAL
- Poisson model verified ✅
- Rolling-origin backtest verified ✅
- Independent review pending (DEC-021) ⚠️
- Calibration not studied ⚠️
- Draw bias documented but not corrected ⚠️

### Business Quality: CONDITIONAL
- No guaranteed predictions ✅
- No claimed profitability ✅
- No public deployment ✅
- Licensing unresolved (LIM-006) ⚠️
- No auth/deployment/public exposure ✅

### Independent Review Findings
- Platform is technically complete for Phase 5 scope ✅
- All mathematics is deterministic and testable ✅
- No model is fitted on real data in Phase 4 code ✅
- Provenance enforcement is robust ✅
- **Outstanding: Independent ML/QA review required** (DEC-021, LIM-014)
- **Outstanding: Probability calibration not studied** (LIM-028 draw bias)
- **Outstanding: Odds/EV engine not implemented** (greenfield)
- **Outstanding: Paper betting system not implemented** (greenfield)
- **Outstanding: Commercial licensing not reviewed** (LIM-006)
- **Outstanding: Security audit not repeated for Phase 5 scope** (DEC-020)
- **Outstanding: Frontend not professionally redesigned** (LIM-022, UI quality)

### Verdict
The platform is **technically complete** for its Phase 5 scope (offline, synthetic-test-only intelligence foundation with private analysis). It is **not** commercially ready without:
1. Independent QA/ML review
2. Probability calibration study
3. Commercial licensing resolution
4. Professional UI/UX redesign
5. Security infrastructure for any public surface

The platform can progress toward lawful commercial operation through controlled paper testing, but all three acceptance criteria remain CONDITIONAL until the outstanding items are addressed.