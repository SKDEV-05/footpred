# Phase 8 Independent ML Review

**Date:** 2026-11-16  
**Status:** Complete  
**Scope:** Mathematical correctness review of Poisson, Dixon-Coles, Elo, backtesting, calibration, and validation methodology  
**Type:** Independent review (not yet externally audited — this is self-produced review per DEC-021 requirements)

---

## 1. EXECUTIVE SUMMARY

| Overall Assessment | Status |
|---|---|
| Poisson model | **HIGH** — mathematically sound |
| Dixon-Coles | **MEDIUM** — not integrated into production path |
| Elo rating | **MEDIUM** — not integrated into production path |
| Backtesting | **HIGH** — chronological but single-window |
| Calibration | **MEDIUM** — incomplete |
| Validation | **MEDIUM** — needs formal protocol |
| Independence | **MEDIUM** — no external validation |

## 2. POISSON MODEL REVIEW

### Implementation Location
- `apps/backend/app/intelligence/prediction.py`
- Version: `poisson-v1.1.0` (MODEL_VERSION)
- Protocol: `phase5-v1` (PROTOCOL_VERSION)
- Feature version: `features-v1.1.0` (FEATURE_VERSION)

### Mathematical Correctness Review

#### Probability Conservation ✅ VERIFIED
- `probability_triplet()` ensures home/draw/away probabilities sum to exactly 1.0
- `_validate_prediction()` checks 1X2 sum = 1.0 and individual ranges [0,1]
- Score matrix probabilities must sum to 1.0 (enforced in `ScoreMatrix.__post_init__`)
- Overflow categories preserved, not renormalized ✅

#### Probability Triplet ✅ VERIFIED
- Derived correctly from score matrix via `probability_triplet(matrix)`
- Home/win and draw probabilities computed from matrix outcomes
- Away probability = 1.0 - home - draw (guarantees sum to 1.0)
- Rounding applied to 4 decimal places ✅

#### Probability Bounds ✅ VERIFIED
- Expected goals clamped to `[0.20, 5.00]` with explicit validation
- Individual probabilities bounded to [0,1] with validation ✅

#### Rate Estimation ✅ VERIFIED
- Competition baseline: average home/away goals from competition matches
- Attack/defence strengths: team goal rates relative to baseline
- Venue shrinkage: sample-size-weighted blend toward competition average
- Recent form: up to 10 most recent matches with weight ≤ 0.20
- All rates derived only from matches before target kickoff ✅

#### Sample Thresholds ✅ VERIFIED
- `MIN_TEAM_SAMPLE_SIZE = 5` (per team)
- `MIN_COMPETITION_SAMPLE_SIZE = 20` (for baseline)
- `MIN_H2H_SAMPLE = 3`
- `FORM_MATCHES = 10`
- `FORM_WEIGHT = 0.20` ✅

#### Validation ✅ VERIFIED
- `_validate_prediction()` checks:
  - 1X2 probabilities sum to 1.0
  - Individual probabilities in [0,1]
  - Expected goals in [0.20, 5.00]
- Raises ValueError on invalid values ✅

### Finding #1 — POISSON MODEL MATHEMATICAL CORRECTNESS
- **Severity**: HIGH (pass)
- **Finding**: Poisson model implementation is mathematically correct and matches its documented description
- **Recommendation**: Ready for production use within Phase 5 bounds; independent QA review still pending per DEC-021

---

## 3. DIXON-COLES MODEL REVIEW

### Implementation Location
- `apps/backend/app/intelligence/models/dixon_coles.py`
- Version: `dixon-coles-v1.0.0` (DC_MODEL_VERSION)
- Parameter version: `rho-v1.0` (DC_PARAMETER_VERSION)

### Mathematical Review

#### Rho Estimation ✅ VERIFIED
- `fit_rho()` implements time-weighted maximum likelihood estimation
- Only low-score cells (0-0, 0-1, 1-0, 1-1) contribute to likelihood ✅
- Time-weighted by `reference_kickoff` with half-life `RHO_HALF_LIFE_DAYS = 180.0` ✅
- Grid search with refinement rounds (`RHO_REFINE_ROUNDS = 4`) ✅

#### Admissible Interval ✅ VERIFIED
- Intersects per-match bounds with global [-0.30, 0.30] limits ✅
- `_rho_bounds()` computes per-match admissible interval ✅
- `_admissible_rho_interval()` intersects across all observations ✅

#### Probability Conservation ✅ VERIFIED
- `dixon_coles_score_matrix()` ensures mass conservation ✅
- Base `dixon_coles_matrix()` applies tau correction with validation ✅

#### Integration Status ⚠️ PARTIAL
- Not yet integrated into live analysis path (Phase 4 only)
- Available for Phase 6/7 evaluation ✅

### Finding #2 — DIXON-COLES NOT INTEGRATED INTO PRODUCTION
- **Severity**: MEDIUM
- **Finding**: Dixon-Coles rho estimation is implemented but not integrated into the live analysis path
- **Evidence**: `apps/backend/app/intelligence/prediction.py` only uses independent Poisson (`poisson_score_matrix`); no Dixon-Coles in live path
- **Impact**: Model under-predicts draws (documented in LIM-028); Dixon-Coles could mitigate but is unavailable for production predictions
- **Recommendation**: Integrate Dixon-Coles into production path with proper versioning; requires independent review before use

---

## 4. ELO RATING REVIEW

### Implementation Location
- `apps/backend/app/intelligence/models/elo_fitted.py`
- Version: `elo-v1.0.0` (ELO_MODEL_VERSION)

### Mathematical Review

#### Home Advantage ✅ VERIFIED
- Estimated via grid search on training data ✅
- Estimated on training matches only ✅
- Frozen for evaluation window ✅

#### Draw Parameter ✅ VERIFIED
- `draw_nu` estimated via grid search on training data ✅
- Estimated on training matches only ✅
- Frozen for evaluation window ✅

#### Outcome Probabilities ✅ VERIFIED
- `elo_outcome_probabilities()` correctly implements Bradley-Terry/Davidson model ✅
- Probabilities sum to 1.0 ✅

#### Training Data Separation ✅ VERIFIED
- Only matches before evaluation window used for fitting ✅
- Test matches never used ✅

#### Integration Status ⚠️ PARTIAL
- Not yet integrated into live analysis path ✅
- Available for Phase 6/7 evaluation ✅

### Finding #3 — ELO NOT INTEGRATED INTO PRODUCTION
- **Severity**: MEDIUM
- **Finding**: Elo/Davidson model is implemented but not integrated into the live analysis path
- **Recommendation**: Integrate into Phase 6/7 evaluation framework for model comparison

---

## 5. BACKTESTING METHODOLOGY REVIEW

### Backtest Protocol ✅ VERIFIED

The `compute_historical_backtest_evaluation()` function in `prediction.py` implements:

1. **Rolling-origin evaluation** ✅
2. **Chronological match ordering** by kickoff UTC ✅
3. **Test set selection**: Last N matches per competition (default 50) ✅
4. **Minimum prior matches**: 40 matches before test match ✅
5. **Match horizon**: 3 hours before kickoff ✅
6. **Abstention**: Matches with prediction status ≠ READY are skipped ✅
7. **Model identity**: Same features/rates function used for live and backtest ✅
8. **Metrics**: Brier, log loss, uniform baselines, ECE, MCE, Brier skill ✅
9. **Paired comparisons**: Poisson vs each other model on identical matches ✅
10. **Calibration**: 5-bin reliability diagram with ECE/MCE ✅
11. **Bootstrap CIs**: 1000 resamples with fixed seed (20_261_116) ✅

### Validation Gaps ⚠️ IDENTIFIED

| Gap | Status |
|---|---|
| No formal validation protocol | Missing |
| No cross-competition comparison | Partial (reported but not formal) |
| No seasonal validation | Partial (reported but not formal) |
| No ablation study | Missing |
| No extended temporal validation | Missing |

### Finding #4 — BACKTEST IS SINGLE-WINDOW ONLY
- **Severity**: MEDIUM
- **Finding**: Backtest covers single evaluation window; no formal validation protocol A-G as required by master prompt
- **Impact**: Results are valid for measured corpus but cannot establish general model performance
- **Recommendation**: Implement Stage 2: strict out-of-sample validation framework with formal protocols

### Finding #5 — NO CLOSING-LINE COMPARISON
- **Severity**: MEDIUM
- **Finding**: Backtest does not compare predictions against closing market odds
- **Impact**: Cannot determine if model provides value vs market
- **Recommendation**: Implement Stage 4: market odds and EV engine

---

## 6. CALIBRATION REVIEW

### Existing Calibration ✅ VERIFIED

The backtest computes:

| Metric | Implementation | Status |
|---|---|---|
| ECE | Mean of bin-level ECE values | ✅ |
| MCE | Max of bin-level MCE values | ✅ |
| 5-bin reliability diagram | Bin lower/upper, sample size, mean probability, observed rate | ✅ |
| Per-class calibration | Binary problems for home/draw/away | ✅ |
| Probability bins | Properly constructed with sample size filtering | ✅ |

### Calibration Gaps ⚠️ IDENTIFIED

| Gap | Severity | Status |
|---|---|---|
| No reliability diagram visualization | MEDIUM | Missing |
| No competition-specific calibration | MEDIUM | Missing |
| No probability-range calibration | MEDIUM | Missing |
| No draw probability bias investigation | HIGH | Partially documented |
| No calibration correction | MEDIUM | Missing |
| No calibration data/train split | LOW | Noted |

### Finding #6 — DRAW PROBABILITY UNDER-PREDICTION DOCUMENTED BUT NOT ANALYZED
- **Severity**: HIGH
- **Finding**: LIM-028 documents draw calibration bin 0.20–0.40 predicts 0.2465, observes 0.3158
- **Impact**: Systematic under-prediction of draws; independent Poisson model may need Dixon-Coles correction
- **Recommendation**: Proceed with Stage 3: dedicated calibration study with reliability diagrams and bias investigation

---

## 7. CLASSIFICATION OF FINDINGS

| Finding ID | Severity | Category | Description | Status |
|---|---|---|---|---|
| F-001 | HIGH | POISSON_MODEL | Poisson model mathematically correct; production ready | PASS |
| F-002 | MEDIUM | DIXON_COLES | Not integrated into production path | PENDING |
| F-003 | MEDIUM | ELO | Not integrated into production path | PENDING |
| F-004 | MEDIUM | BACKTEST | Single-window only; no formal protocol A-G | PENDING |
| F-005 | HIGH | CALIBRATION | Draw under-prediction documented but not analyzed | PENDING |
| F-006 | MEDIUM | CALIBRATION | No calibration correction implemented | PENDING |
| F-007 | MEDIUM | VALIDATION | No cross-competition/seasonal validation | PENDING |
| F-008 | MEDIUM | CLOSING_LINE | No closing-line comparison | PENDING |

---

## 8. SEVERITY CLASSIFICATION SUMMARY

| Severity | Count | Findings |
|---|---|---|
| CRITICAL | 0 | — |
| HIGH | 2 | F-001 (pass), F-005 (draw under-prediction) |
| MEDIUM | 6 | F-002, F-003, F-004, F-006, F-007, F-008 |
| LOW | 0 | — |

---

## 9. NEXT STEPS

1. **Stage 2 — Strict chronological validation**: Implement formal validation protocols A-G (rolling-origin, expanding windows, multiple competitions/seasons, minimum samples, training/validation/test separation)
2. **Stage 3 — Probability calibration**: Build calibration subsystem with reliability diagrams, per-competition calibration, and investigation of draw bias (F-005, F-006)
3. **Stage 4 — Market odds and EV engine**: Implement odds storage, EV calculation, and closing-line comparison (F-008)
4. **Stage 5 — Paper betting**: Build complete virtual betting simulation
5. **Stage 6 — Best Bets**: Implement value opportunities ranking
6. **Integration**: Integrate Dixon-Coles and Elo into production path (F-002, F-003) — requires independent review before use