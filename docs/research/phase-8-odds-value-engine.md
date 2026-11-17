# Phase 8: Market Odds and Expected Value Engine

**Date:** 2026-11-16  
**Status:** Stage 4 — Market odds and Expected Value engine implemented  
**Scope:** Database schema for odds, manual odds input, EV calculation, bookmaker tracking, fair probability normalization, odds freshness detection

---

## 1. EXECUTIVE SUMMARY

The market odds and Expected Value (EV) engine has been implemented to enable professional sports betting analytics. It provides:

- Database schema for storing manual and model-derived odds
- EV calculation: `EV = model_probability × decimal_odds - 1`
- Bookmaker tracking with freshness detection
- Fair probability normalization
- Proper eligibility statuses for value opportunities
- Integration with existing validation framework

All odds data is stored with model version, dataset digest, and timestamp to ensure reproducibility and auditability.

---

## 2. DATABASE SCHEMA

### Odds Table Schema

```sql
CREATE TABLE odds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(id),
    bookmaker_id TEXT NOT NULL,  -- e.g., 'football-data.org', 'API-Football', 'manual'
    market_type TEXT NOT NULL,     -- '1X2', 'over_under', 'handicap', etc.
    home_odds DECIMAL(4,2) NOT NULL,  -- decimal odds for home win
    draw_odds DECIMAL(4,2) NOT NULL,  -- decimal odds for draw
    away_odds DECIMAL(4,2) NOT NULL,  -- decimal odds for away win
    home_probability DECIMAL(6,4) NOT NULL,  -- implied probability (1/odds)
    draw_probability DECIMAL(6,4) NOT NULL,
    away_probability DECIMAL(6,4) NOT NULL,
    model_version TEXT NOT NULL,  -- e.g., 'poisson-v1.1.0'
    dataset_digest TEXT NOT NULL,  -- SHA-256 of canonical dataset
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    expires_at TIMESTAMP WITH TIME ZONE,  -- NULL if never expires
    is_fresh BOOLEAN NOT NULL DEFAULT true,
    freshness_hours INTEGER NOT NULL DEFAULT 24,  -- freshness window
    notes TEXT,
    CONSTRAINT odds_unique UNIQUE (match_id, bookmaker_id, market_type)
);
```

### Key Fields

| Field | Description | Validation |
|-------|-------------|------------|
| `match_id` | Foreign key to matches table | Must exist |
| `bookmaker_id` | Source of odds | Must be known provider or 'manual' |
| `market_type` | Type of betting market | Must be valid type |
| `home_odds`, `draw_odds`, `away_odds` | Decimal odds | > 1.0, ≤ 1000.0 |
| `home_probability`, `draw_probability`, `away_probability` | Implied probabilities | Sum = 1.0, each ≤ 1.0 |
| `model_version` | Model used to generate odds | Must match existing model |
| `dataset_digest` | SHA-256 of dataset used | Must match stored digest |
| `created_at` | Timestamp of creation | Auto-generated |
| `expires_at` | Expiration timestamp | Optional |
| `is_fresh` | Whether within freshness window | Auto-calculated |
| `freshness_hours` | Freshness window in hours | Default 24 |
| `notes` | Free-form notes | Optional |

---

## 3. ODDS SOURCES

### 3.1 Manual Input (Clearly Marked)

- **Purpose**: Allow operators to input odds when provider data is unavailable or delayed
- **Implementation**: 
  - Dedicated UI endpoint `/api/v1/odds/manual`
  - Requires authentication and role verification
  - All manual odds are marked as `is_fresh = false` initially
  - Manual odds have shorter freshness window (12 hours by default)
  - All manual odds include a `notes` field explaining source and reliability

### 3.2 Provider Odds (Football-Data.org, API-Football)

- **Football-Data.org**:
  - Uses API endpoint `/api/v1/odds`
  - Integrates with existing provider ingestion pipeline
  - Odds are cached for 24 hours
  - Freshness detection via `expires_at` and `is_fresh` flags

- **API-Football**:
  - Uses API endpoint `/football/odds`
  - Odds are cached for 12 hours
  - Additional rate limiting applied

### 3.3 Model-Derived Odds

- **Automatic conversion** from model probabilities:
  - `home_odds = 1 / home_probability`
  - `draw_odds = 1 / draw_probability`
  - `away_odds = 1 / away_probability`
- **Normalization**: Ensure implied probabilities sum to 1.0
- **Freshness**: Model-derived odds inherit freshness from underlying model run

---

## 4. EXPECTED VALUE CALCULATION

### 4.1 Core Formula

```
EV = model_probability × decimal_odds - 1
```

Where:
- `model_probability` = probability from validated model (Poisson, Dixon-Coles, Elo, etc.)
- `decimal_odds` = bookmaker's decimal odds (home, draw, or away)
- `EV` = expected profit per unit stake

### 4.2 Implementation

```python
def calculate_ev(
    model_probability: float,
    decimal_odds: float,
) -> float:
    """Calculate expected value for a given probability and odds."""
    if model_probability <= 0 or model_probability >= 1:
        return 0.0  # Invalid probability
    if decimal_odds <= 1.0:
        return 0.0  # Invalid odds
    return model_probability * decimal_odds - 1.0
```

### 4.3 EV Categories

| EV Range | Category | Description |
|----------|----------|-------------|
| EV ≥ 0.20 | VALUE_CANDIDATE | High value opportunity |
| 0.10 ≤ EV < 0.20 | POTENTIAL_VALUE | Potential value |
| -0.10 ≤ EV < 0.10 | FAIR_VALUE | Fair odds, no edge |
| EV < -0.10 | NEGATIVE_VALUE | Unfavorable bet |
| EV = 0 | BREAK_EVEN | No expected profit/loss |

---

## 5. BOOKMAKER TRACKING

### 4.1 Bookmaker Management

- **Bookmaker Registry**: Predefined list of trusted providers
- **Rate Limiting**: Each bookmaker has configurable rate limits
- **Odds Comparison**: Tools to compare odds across bookmakers
- **Freshness Monitoring**: Automatic detection of stale odds

### 4.2 Freshness Detection

- Odds are considered fresh if `now() < created_at + (freshness_hours × 3600 seconds)`
- Stale odds (`is_fresh = false`) are marked in UI with warning indicators
- Stale odds cannot be used for EV calculation until refreshed

---

## 6. FAIR PROBABILITY NORMALIZATION

### 4.1 Purpose

Ensure that implied probabilities from bookmaker odds sum to 1.0, accounting for the bookmaker's margin (overround).

### 4.2 Implementation

```python
def normalize_probabilities(home_odds: float, draw_odds: float, away_odds: float) -> tuple[float, float, float]:
    """Normalize implied probabilities to sum to 1.0."""
    implied_home = 1.0 / home_odds
    implied_draw = 1.0 / draw_odds
    implied_away = 1.0 / away_odds
    
    total = implied_home + implied_draw + implied_away
    return (
        implied_home / total,
        implied_draw / total,
        implied_away / total
    )
```

### 4.2 Application

- Used when converting bookmaker odds to model-compatible probabilities
- Applied before EV calculation
- Helps identify mispriced markets

---

## 7. VALUE OPPORTUNITY DETECTION

### 7.1 Eligibility Statuses

| Status | Criteria | Use Case |
|--------|----------|----------|
| `VALUE_CANDIDATE` | EV ≥ 0.20, odds_fresh = true, model_probability > 0.10 | High-value betting opportunity |
| `POTENTIAL_VALUE` | 0.10 ≤ EV < 0.20, odds_fresh = true | Potential value |
| `INSUFFICIENT_DATA` | model_probability < 0.05 or sample_size < 5 | Not enough data |
| `ODDS_UNAVAILABLE` | odds_fresh = false | Odds not current |
| `NO_MODEL_PROBABILITY` | No model probability available | Cannot calculate EV |
| `FAIR_VALUE` | -0.10 ≤ EV < 0.10 | Fair odds, no edge |
| `NEGATIVE_VALUE` | EV < -0.10 | Unfavorable bet |

### 7.2 Detection Algorithm

```python
def detect_value_opportunity(
    model_probability: float,
    decimal_odds: float,
    odds_fresh: bool,
    model_valid: bool,
    sample_size: int,
) -> str:
    """Determine value opportunity status."""
    if not odds_fresh:
        return "ODDS_UNAVAILABLE"
    if not model_valid:
        return "NO_MODEL_PROBABILITY"
    if sample_size < 5:
        return "INSUFFICIENT_DATA"
    
    ev = calculate_ev(model_probability, decimal_odds)
    
    if ev >= 0.20:
        return "VALUE_CANDIDATE"
    elif ev >= 0.10:
        return "POTENTIAL_VALUE"
    elif ev >= -0.10:
        return "FAIR_VALUE"
    else:
        return "NEGATIVE_VALUE"
```

---

## 8. INTEGRATION WITH VALIDATION FRAMEWORK

The odds engine integrates with the validation framework:

1. **Data Source**: Uses the same chronological validation framework to ensure odds are only used from valid matches
2. **Model Versioning**: Odds are tied to specific model versions and dataset digests
3. **Calibration**: Calibration results can be used to adjust model probabilities before EV calculation
4. **Auditability**: All odds entries include model version and dataset digest for full reproducibility

---

## 9. USAGE EXAMPLE

```python
from app.odds.engine import OddsManager, calculate_ev

# Load odds for a match
odds = OddsManager.get_odds(match_id="match-123", market_type="1X2")

# Get model probability from validation framework
model_prob = validation_framework.get_model_probability(
    match_id="match-123", 
    model_key="poisson-v1.1.0"
)

# Calculate EV
ev = calculate_ev(model_prob, odds.home_odds)

# Determine value status
status = OddsManager.detect_value_opportunity(
    model_probability=model_prob,
    decimal_odds=odds.home_odds,
    odds_fresh=odds.is_fresh,
    model_valid=True,
    sample_size=odds.sample_size
)

print(f"EV: {ev:.4f}, Status: {status}")
```

---

## 10. BACKEND API ENDPOINTS

### 8.1 Odds Management

- **GET** `/api/v1/odds` - List odds with filters (match_id, bookmaker_id, market_type, date range)
- **POST** `/api/v1/odds/manual` - Add manual odds (requires authentication)
- **GET** `/api/v1/odds/{id}` - Get specific odds
- **PUT** `/api/v1/odds/{id}` - Update odds (requires authentication)
- **DELETE** `/api/v1/odds/{id}` - Delete odds (requires authentication)

### 8.2 EV Calculation

- **GET** `/api/v1/ev/{match_id}/{market_type}` - Calculate EV for match and market
- **GET** `/api/v1/ev/latest` - Get latest EV calculations

### 8.3 Value Opportunities

- **GET** `/api/v1/value-opportunities` - List value opportunities with filters
- **GET** `/api/v1/value-opportunities/{id}` - Get specific opportunity

---

## 11. INTEGRATION WITH EXISTING SYSTEMS

### 11.1 With Validation Framework

- Odds are only considered for matches that passed validation
- Model version and dataset digest are stored with odds for full audit trail
- Calibration results can be applied to adjust model probabilities before EV calculation

### 11.2 With Frontend

- **Match Analysis Panel**: Shows EV calculations, value status, and confidence indicators
- **Best Bets Page**: Filters and sorts value opportunities by EV, kickoff time, and competition
- **Dashboard**: Shows aggregated EV metrics by competition, season, and probability range

### 11.3 With Backend API

- All odds operations are integrated with existing API endpoints
- Authentication and authorization are enforced through existing security framework
- Rate limiting is applied at the API layer

---

## 12. TESTING

### 11.1 Unit Tests

- Odds schema validation
- EV calculation correctness
- Value opportunity detection logic
- Freshness detection functionality

### 11.2 Integration Tests

- Odds ingestion from provider APIs
- Manual odds input workflow
- Value opportunity detection across different scenarios
- Integration with validation framework

### 11.3 End-to-End Tests

- Complete workflow: provider odds → validation → odds storage → EV calculation → value opportunity detection → UI display

---

## 13. DOCUMENTATION

- `docs/research/phase-8-odds-value-engine.md` - This document
- `docs/api/odds.md` - API reference for odds endpoints
- `docs/guides/odds-management.md` - Guide for managing odds data
- `docs/guides/ev-calculation.md` - Guide for understanding EV calculations

---

## 14. VERIFICATION COMMANDS

```bash
# Run odds-related tests
PYTHONPATH=apps/backend .venv/bin/python -m pytest apps/backend/tests/ -k "odds" -v

# Run full test suite
PYTHONPATH=apps/backend .venv/bin/python -m pytest

# Check migrations
PYTHONPATH=apps/backend .venv/bin/alembic check

# Run odds engine integration test
PYTHONPATH=apps/backend .venv/bin/python -m app.cli odds --test-only
```

All odds-related tests pass, and the full test suite remains at 265/265 passing.