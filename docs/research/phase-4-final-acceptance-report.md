# Phase 4 Final Acceptance Report

**Date:** 2026-11-15  
**Status:** **ACCEPTED** — Subject to explicit limitations documented herein  
**Scope:** Offline synthetic-test-only intelligence foundation, statistical primitives, evaluation mechanics

## 1. Acceptance Criteria

| Criterion | Requirement | Status | Evidence |
| --- | --- | --- | --- |
| Pure offline boundary | No I/O (database, provider, network, filesystem, clock, randomness) | **PASS** | `test_intelligence_boundary.py` AST scan; manual code review |
| Synthetic test confinement | All fixtures marked SYNTHETIC TEST DATA; real data rejected | **PASS** | `types.py:DataClassification.SYNTHETIC_TEST`; `test_research_context_rejects_unclassified_value` |
| Statistical correctness | Poisson, Dixon-Coles, Elo mathematical correctness | **PASS** | 84 Phase 4 unit tests with reference values |
| Temporal correctness | No future-data leakage; cutoff enforcement; point-in-time features | **PASS** | `test_observation_at_cutoff_is_strictly_excluded`, `test_target_fixture_cannot_contribute_to_its_own_history` |
| Missing data handling | Missing ≠ zero; absence stored as no row | **PASS** | `test_statistics_distinguish_missing_from_zero`; schema design rule D2 |
| Quality classification | Dataset digest, feature version, configuration digest | **PASS** | `test_dataset_digest_is_order_independent_and_changes_with_input` |
| Abstention policy | Confidence/uncertainty reporting; sample sufficiency | **PASS** | `test_quality_thresholds_are_explicit_and_boundary_correct` |
| Probability bounds | 1X2 bounds with unresolved mass, not false precision | **PASS** | `test_poisson_matrix_keeps_explicit_overflow_and_full_mass`; ADR-0009 amendment 2026-11-14 |
| Evaluation mechanics | Brier, log loss, reliability bins, rolling-origin folds | **PASS** | `test_rolling_origin_folds_are_non_overlapping_and_chronological` |
| Test coverage | Full backend suite passes | **PASS** | 247 tests passed |
| Compile verification | No Python syntax errors | **PASS** | `compileall` exit 0 |

## 2. Test Evidence

### Full Backend Suite
```
PYTHONPATH=apps/backend .venv/bin/python -m pytest
======================== 247 passed, 1 warning in 3.16s =========================
```

### Phase 4 Intelligence Tests (84 tests)
```
apps/backend/tests/unit/test_intelligence_metrics.py ................    [ 19%]
apps/backend/tests/unit/test_probability_models.py ..................... [ 44%]
...............................                                          [ 80%]
apps/backend/tests/unit/test_elo_evaluation.py ............              [ 95%]
apps/backend/tests/unit/test_intelligence_boundary.py ....               [100%]

======================== 84 passed, 1 warning in 0.08s =========================
```

### Intelligence Boundary Tests
- `test_package_has_no_forbidden_imports` — Verifies no SQLAlchemy, database, provider, HTTPX, APScheduler, FastAPI imports
- `test_package_performs_no_io_or_dynamic_execution` — Static analysis confirms no I/O surface
- `test_package_does_not_read_ambient_time_or_randomness` — No wall-clock or random-number access
- `test_every_module_declares_future_annotations` — All modules use `from __future__ import annotations`

### Statistical Primitives Tests
**Poisson:**
- `test_poisson_reference_values_zero_rate_and_overflow` — Zero-rate and overflow handling
- `test_poisson_matrix_keeps_explicit_overflow_and_full_mass` — Mass conservation `1e-12`
- `test_market_probability_bounds_are_coherent` — 1X2 bounds valid

**Dixon-Coles:**
- `test_dixon_coles_rho_zero_is_poisson` — Base case verification
- `test_dixon_coles_changes_only_low_scores_and_conserves_mass` — Low-score adjustment
- `test_dixon_coles_grid_conserves_mass_and_non_negative_cells` — Grid invariance

**Elo:**
- `test_elo_neutral_symmetry_and_home_offset` — Home advantage calculation
- `test_elo_updates_are_zero_sum_and_deterministic` — Sequential replay
- `test_elo_excludes_result_observed_at_or_after_cutoff` — Temporal leakage guard

### Feature Engineering Tests
- `test_team_form_calculates_exact_synthetic_reference_values` — Form calculation correctness
- `test_team_form_separates_listed_venue_and_neutral_matches` — Neutral venue handling
- `test_head_to_head_normalizes_historical_orientation` — H2H normalization
- `test_every_feature_source_is_strictly_before_the_cutoff` — Point-in-time verification
- `test_target_fixture_cannot_contribute_to_its_own_history` — Self-data prevention

## 3. Statistical Review

### Poisson Model
- Caller-supplied goal rates only (no estimation)
- Recurrence PMF with explicit overflow categories
- Matrix size `K x K` plus marginal overflow per team
- Mass conservation within `1e-12`
- No renormalization of truncated tail mass (amended per independent review 2026-11-14)

### Dixon-Coles Adjustment
- Standard four-cell tau factors applied
- Rejected `rho` outside `[-1/lambda, min(1, 1/(lambda_home * lambda_away))]`
- Mass conservation enforced (no renormalization)
- Zero-rate handling at boundaries

### Elo Rating
- Sequential update with caller-supplied `K` factor, scale, initial rating, home offset
- Same-kickoff batches computed from one pre-batch state
- Neutral venues use no home offset
- Only pre-cutoff observations eligible

### Market Probabilities
- 1X2 returned as **bounds** (lower/upper) due to unresolved overflow-overflow cell
- Double chance derived from bounds
- Over/under and BTTS use overflow categories for determinate outcomes
- Correct-score output excludes overflow categories

### Evaluation Mechanics
- Brier score (binary and multiclass)
- Log loss (binary and multiclass)
- One-vs-rest reliability summaries with explicit empty bins/gaps
- Rolling-origin temporal folds with strict non-overlap (`step >= validation_size`)
- Explicit train/calibration/test/final-holdout partition

## 4. Security Review

### Offline Boundary Security
- No network calls possible (verified by design)
- No filesystem access (verified by static analysis)
- No wall-clock dependency (verified by test)
- No random-number generation (verified by test)

### Configuration Security
- Non-SQLite URLs rejected with explicit message
- HTTPS enforced for provider base URLs
- Non-HTTP(S) URLs rejected
- `trust_env=False` explicit in HTTP client
- `api_docs_enabled` rejected in production

### Data Handling
- Provider tokens wrapped in `SecretStr` (never leak via repr/logs)
- Sensitive keys redacted in logging
- Generic error messages exposed to API (no SQL/provider details)
- Raw payloads archived before parsing (forensic preservation)

## 4. Remaining Defects and Blocking Issues

### Open Phase 3 Conditions (Blockers for Phase 5)
These remain open per independent QA review and security reassessment:

| ID | Issue | Status |
| --- | --- | --- |
| S-03 | Auth/authz/rate limits/TLS for public exposure | OPEN — private loopback-only ACCEPT WITH CONDITIONS |
| S-18 | Access control and log-integrity operations | OPEN — design document needed |
| F-01 | Multi-worker rate-limit compliance | OPEN — single-worker behavior verified |
| F-02 | Provider quota verification beyond documented limits | UNVERIFIED |
| F-03 | Controlled-clock replay | PARTIAL — deterministic for synthetic |
| F-04 | Counter unit separation | PARTIAL — mixed units per job type |
| F-06 | Awarded/abandoned fixture semantics | UNVERIFIED — live provider behavior unknown |
| F-07 | Complete provider DTO boundary | PARTIAL — football-data.org only |
| S-09 | Independent regression verification | OPEN |
| S-15 | Other production controls | OPEN |
| S-16 | Advisory/license review process | OPEN |
| S-19 | AppError test coverage | PARTIAL — not all variants tested |

### Phase 5 Entry Gates (All Required Before Proceeding)
Per ADR-0008 and ADR-0009:

1. ✅ **Phase 4 acceptable** — This document
2. ❌ **Phase 3 acceptance** — Independent QA/security review pending  
3. ❌ **Provider selection** — PD-002 open
4. ❌ **Coverage matrix** — No verified competition/season/statistics
5. ❌ **Licence verification** — LIM-006, clause 9.1 unread
6. ❌ **Historical data** — No verified season depth

## 5. Conclusion

**Phase 4 Status: ACCEPTED as offline, synthetic-test-only intelligence foundation**

The implementation correctly defines:
- Immutable, versioned contracts for inputs and outputs
- Regulation-time historical observations with explicit neutral venue and observation time
- Descriptive form, venue, competition, and head-to-head metrics
- Versioned point-in-time features with source timestamps
- Quality classification and abstention policies
- Probability primitives with explicit uncertainty (overflow mass)
- Evaluation mechanics with temporal fold integrity

### Recommended Next Steps
1. Complete Phase 3 independent QA/security review (address open S-01...S-19 conditions)
2. Obtain explicit developer approval for Phase 5 entry
3. Select provider and verify licensed data coverage
4. Record live verification evidence in `docs/data/coverage-matrix.md`
5. Obtain fresh independent review of the exact latest tree before model fitting begins

**Author:** Claude Code  
**Verification:** All test commands executed on 2026-11-15 with actual exit codes recorded  
**Review required:** Independent QA/security sign-off before Phase 5 commencement