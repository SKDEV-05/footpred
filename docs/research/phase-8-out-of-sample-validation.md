# Phase 8 Out-of-Sample Validation Study

**Date:** 2026-11-16  
**Status:** Complete — Framework implemented and tested  
**Scope:** Strict chronological validation framework implementing protocols A-G

---

## 1. EXECUTIVE SUMMARY

The strict chronological validation framework has been implemented in `apps/backend/app/intelligence/validation.py`. It provides a formal, versioned validation protocol that:

- Implements rolling-origin evaluation (Protocol A)
- Supports expanding training windows (Protocol B)
- Enables multiple chronological evaluation windows (Protocol C)
- Evaluates across multiple competitions (Protocol D)
- Evaluates across multiple seasons (Protocol E)
- Enforces minimum historical sample requirements (Protocol F)
- Maintains strict training/validation/test separation (Protocol G)

All models are evaluated on identical eligible fixtures with proper chronological separation and no future-data leakage.

---

## 2. VALIDATION FRAMEWORK ARCHITECTURE

### Core Components

| Component | Purpose |
|---|---|
| `ValidationProtocol` | Configuration dataclass for protocol parameters |
| `ValidationResult` | Complete validation output with all metrics |
| `run_multi_competition_validation()` | Main entry point |
| `_evaluate_rows()` | Evaluates one model's predictions |
| `_paired_comparison()` | Paired bootstrap comparison between models |
| `_bootstrap_ci()` | Percentile bootstrap confidence intervals |

### Protocol Configuration

```python
@dataclass(frozen=True)
class ValidationProtocol:
    protocol_version: str = "phase8-v1"
    evaluation_version: str = "evaluation-v1.2.0"
    min_prior_matches: int = 40
    max_test_per_competition: int = 100
    match_horizon_hours: float = 3.0
    bootstrap_resamples: int = 1_000
    bootstrap_seed: int = 20_261_116
    calibration_bins: int = 5
    timeline_bucket_size: int = 25
    min_competition_matches: int = 50
    min_elo_training: int = 30
```

All parameters are versioned and explicit — no hidden defaults.

---

## 3. PROTOCOLS IMPLEMENTED

### Protocol A: Rolling-Origin Evaluation
**Status: ✅ IMPLEMENTED**

Matches are predicted in strict chronological order. Each test match is predicted using only matches that completed before the test match's kickoff (plus a 3-hour horizon for result availability).

```python
# In run_multi_competition_validation():
while cursor < len(matches):
    head_kickoff = matches[cursor].kickoff_utc
    if head_kickoff + MATCH_HORIZON > kickoff:
        break
    # Add completed results to available training data
    available.extend(batch)
    elo.apply_batch(batch)
```

Each fold uses a distinct training set that grows as more matches complete.

### Protocol B: Expanding Training Windows
**Status: ✅ IMPLEMENTED**

Training set expands monotonically:
- Initial: minimum 40 prior matches required
- Expands: each completed match added to training
- No fixed window size — uses all available history

### Protocol C: Multiple Chronological Evaluation Windows
**Status: ✅ IMPLEMENTED**

The framework supports configurable evaluation windows:
- `max_test_per_competition`: limits test matches per competition (default 100)
- `timeline_bucket_size`: groups matches into chronological buckets for timeline analysis (default 25)
- Can be called multiple times with different window parameters

### Protocol D: Multiple Competitions
**Status: ✅ IMPLEMENTED**

All competitions with sufficient history are evaluated:
- Minimum 50 competition matches required (`min_competition_matches`)
- Per-competition models fitted before first test match
- Models frozen for entire evaluation window per competition
- Results reported per competition and overall

### Protocol E: Multiple Seasons
**Status: ✅ IMPLEMENTED**

Season-level breakdown automatically generated:
- Matches grouped by `(competition_id, season_id)`
- All models evaluated per season
- Results include sample size and metrics per season

### Protocol F: Minimum Historical Sample Requirements
**Status: ✅ IMPLEMENTED**

| Requirement | Value | Purpose |
|---|---|---|
| `min_prior_matches` | 40 | Minimum training matches before testing |
| `min_competition_matches` | 50 | Minimum competition matches to participate |
| `min_elo_training` | 30 | Minimum Elo training matches |
| `MIN_TEAM_SAMPLE_SIZE` | 5 | Minimum team matches (from prediction) |
| `MIN_COMPETITION_SAMPLE_SIZE` | 20 | Minimum competition matches for baseline |

Competitions below thresholds are reported as `INSUFFICIENT_DATA` with explicit counts.

### Protocol G: Strict Training/Validation/Test Separation
**Status: ✅ IMPLEMENTED**

| Separation | Mechanism |
|---|---|
| Training → Validation | Time horizon (3h) + match ordering |
| Validation → Test | Chronological ordering by kickoff |
| Model fitting | Before competition's first test match |
| Parameters frozen | For entire competition evaluation window |
| No future data | All predictions use only earlier matches |

---

## 4. MODELS EVALUATED

All models are scored on **identical eligible fixtures**:

| Model | Key | Version | Role |
|---|---|---|---|
| Independent Poisson | `poisson` | `poisson-v1.1.0` | Primary |
| Dixon-Coles | `dixon_coles` | `dixon-coles-v1.0.0` | Model |
| Elo (Davidson) | `elo` | `elo-v1.0.0` | Model |
| Uniform 1/3 | `uniform` | `uniform-v1.0.0` | Baseline |
| Competition Frequency | `competition_frequency` | `frequency-v1.0.0` | Baseline |

---

## 5. METRICS REPORTED

### Overall Metrics (per model)
- **Brier Score**: Multiclass Brier score
- **Log Loss**: Multiclass log loss
- **Brier Skill Score**: vs Uniform baseline
- **Expected Calibration Error (ECE)**: Mean across classes
- **Maximum Calibration Error (MCE)**: Max across classes
- **Top-pick Accuracy**: Rate of correct most-likely outcome

### Per-Outcome Metrics (binary view)
- **Observed Rate**: Actual frequency of outcome
- **Mean Probability**: Model's average probability
- **Calibration Gap**: Mean probability − Observed rate
- **Binary Brier**: Brier for outcome vs not-outcome
- **Binary Log Loss**: Log loss for outcome vs not-outcome

### Calibration
- **Reliability Diagram**: 5 bins (configurable)
- **Per-bin**: Lower/upper bound, sample size, mean probability, observed rate
- **ECE/MCE**: Per-class and aggregate

### Confidence Intervals
- **Bootstrap**: 1000 resamples (configurable)
- **Percentile CI**: 2.5% / 97.5%
- **Fixed Seed**: 20_261_116 for reproducibility

### Paired Comparisons
- **Brier Difference**: Poisson vs each other model
- **Log Loss Difference**: Poisson vs each other model
- **Interpretation**: Positive = reference (Poisson) is worse

### Aggregations
- **Per Competition**: All metrics per competition
- **Per Season**: All metrics per competition×season
- **Timeline Buckets**: Brier score over chronological buckets
- **Diagnostics**: Evaluated count, abstention count, history skip count

---

## 6. USAGE

```python
from app.intelligence.validation import (
    run_multi_competition_validation,
    ValidationProtocol,
)
from app.repositories.analysis import load_corpus_dataset
from app.core.time import utc_now
from app.database.session import session_scope

# Load corpus as of checkpoint
with session_scope() as session:
    dataset, _ = load_corpus_dataset(session, as_of=utc_now())

# Run validation with default protocol
result = run_multi_competition_validation(dataset)

# Or customize protocol
protocol = ValidationProtocol(
    min_prior_matches=50,
    max_test_per_competition=75,
    bootstrap_resamples=2000,
)
result = run_multi_competition_validation(dataset, protocol=protocol)

# Access results
if result.evaluated:
    print(f"Sample size: {result.sample_size}")
    for model in result.models:
        if model["evaluated"]:
            print(f"{model['label']}: Brier={model['brier_score']}, "
                  f"Skill={model['brier_skill_score_vs_uniform']}, "
                  f"ECE={model['expected_calibration_error']}")
```

---

## 7. REPRODUCIBILITY

All validation results are reproducible from:
1. **Dataset digest** — SHA-256 of canonical match data
2. **Protocol version** — `phase8-v1`
3. **Evaluation version** — `evaluation-v1.2.0`
4. **Model versions** — Each model has fixed version
5. **Fixed seeds** — Bootstrap seed 20_261_116, no other randomness

Same inputs → identical results.

---

## 8. INTEGRATION WITH EXISTING BACKTEST

The new framework (`validation.py`) supersedes the Phase 7 backtest (`backtest.py`):

| Aspect | Phase 7 (`backtest.py`) | Phase 8 (`validation.py`) |
|---|---|---|
| Protocol version | `phase7-v1` | `phase8-v1` |
| Evaluation version | `evaluation-v1.2.0` | `evaluation-v1.2.0` |
| Configuration | Hard-coded constants | `ValidationProtocol` dataclass |
| Extensibility | Single function | Composable protocols |
| Versioning | Partial | Full (protocol, evaluation, model, feature) |
| Reproducibility | Via dataset digest | Via dataset digest + protocol + versions |

The Phase 7 function remains for backward compatibility; new evaluation should use `validation.py`.

---

## 9. TEST RESULTS

All 265 backend tests pass including:
- 4 boundary tests (no I/O, no forbidden imports, no ambient time/randomness, future annotations)
- Integration tests for analysis API, migrations, sync, etc.
- Unit tests for prediction engine, probability models, Elo evaluation, etc.

---

## 10. NEXT STEPS

The validation framework is complete and tested. Next stages:

| Stage | Document | Status |
|---|---|---|
| Stage 3: Probability Calibration | `docs/research/phase-8-calibration-study.md` | **PENDING** |
| Stage 4: Market Odds & EV Engine | `docs/research/phase-8-odds-value-engine.md` | **PENDING** |
| Stage 5: Paper Betting | `docs/research/phase-8-paper-betting.md` | **PENDING** |
| Stage 6: Best Bets | `docs/research/phase-8-best-bets.md` | **PENDING** |
| Stage 7: Commercial Licensing | `docs/research/phase-8-commercial-licensing-review.md` | **PENDING** |
| Stage 8: Security | `docs/research/phase-8-security-review.md` | **PENDING** |
| Stage 9: Frontend Redesign | `docs/research/phase-8-frontend-redesign.md` | **PENDING** |
| Stage 10: Integration & QA | `docs/research/phase-8-final-report.md` | **PENDING** |

---

## 11. VERIFICATION COMMANDS

```bash
# Run full test suite
PYTHONPATH=apps/backend .venv/bin/python -m pytest

# Check migrations
PYTHONPATH=apps/backend .venv/bin/alembic check

# Run validation on stored data
PYTHONPATH=apps/backend .venv/bin/python -m app.cli evaluate --summary-only

# Frontend build
cd apps/web && npm run build
```

All commands currently pass.