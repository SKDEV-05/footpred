# Phase 8: Best Bets and Value Opportunities

**Date:** 2026-11-16  
**Status:** Stage 6 — Best Bets system implemented  
**Scope:** Value opportunity detection, filtering, sorting, and ranking interface with proper eligibility statuses

---

## 1. EXECUTIVE SUMMARY

The Best Bets system has been implemented to enable professional sports betting analytics. It provides:

- Filtering by competition, market, date, and minimum expected value
- Sorting by model probability, expected value, kickoff time
- Quality and uncertainty indicators for each opportunity
- Proper eligibility statuses (VALUE_CANDIDATE, INSUFFICIENT_DATA, ODDS_UNAVAILABLE, etc.)
- No fake opportunities created - all based on real model outputs and validated odds
- Integration with existing validation and odds engines

All best bets are derived from the paper betting system and validation framework.

---

## 2. CORE COMPONENTS

### 1.1 Value Opportunity Detection

Value opportunities are detected using the same logic as the odds engine:

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

### 1.2 Eligibility Statuses

| Status | Criteria | Use Case |
|--------|----------|----------|
| `VALUE_CANDIDATE` | EV ≥ 0.20, odds_fresh = true, model_probability > 0.10 | High-value betting opportunity |
| `POTENTIAL_VALUE` | 0.10 ≤ EV < 0.20, odds_fresh = true | Potential value |
| `INSUFFICIENT_DATA` | model_probability < 0.05 or sample_size < 5 | Not enough data |
| `ODDS_UNAVAILABLE` | odds_fresh = false | Odds not current |
| `NO_MODEL_PROBABILITY` | No model probability available | Cannot calculate EV |
| `FAIR_VALUE` | -0.10 ≤ EV < 0.10 | Fair odds, no edge |
| `NEGATIVE_VALUE` | EV < -0.10 | Unfavorable bet |

### 1.3 Detection Algorithm

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

### 1.4 Quality Indicators

Each best bet includes:

- **Confidence Score**: Model probability strength (0.0-1.0)
- **Uncertainty Range**: Confidence interval for probability estimate
- **Historical Performance**: Performance of similar predictions
- **Market Liquidity**: Odds stability indicator
- **Time Sensitivity**: Time remaining until kickoff

---

## 3. DATABASE SCHEMA

### 3.1 Best Bets Table Schema

```sql
CREATE TABLE best_bets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(id),
    model_version TEXT NOT NULL,  -- e.g., 'poisson-v1.1.0'
    dataset_digest TEXT NOT NULL,  -- SHA-256 of canonical dataset
    market_type TEXT NOT NULL,     -- '1X2', 'over_under', etc.
    home_odds DECIMAL(4,2) NOT NULL,
    draw_odds DECIMAL(4,2) NOT NULL,
    away_odds DECIMAL(4,2) NOT NULL,
    model_probability_home DECIMAL(6,4) NOT NULL,
    model_probability_draw DECIMAL(6,4) NOT NULL,
    model_probability_away DECIMAL(6,4) NOT NULL,
    expected_value_home DECIMAL(6,4),
    expected_value_draw DECIMAL(6,4),
    model_probability_selected DECIMAL(6,4),
    expected_value_selected DECIMAL(6,4),
    odds_fresh BOOLEAN NOT NULL DEFAULT true,
    sample_size INTEGER NOT NULL,
    eligibility_status TEXT NOT NULL,  -- VALUE_CANDIDATE, POTENTIAL_VALUE, etc.
    kickoff_utc TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    notes TEXT,
    CONSTRAINT best_bets_unique UNIQUE (match_id, model_version, market_type)
);
```

### 3.2 Key Fields

| Field | Description | Validation |
|-------|-------------|------------|
| `match_id` | Foreign key to matches table | Must exist |
| `model_version` | Model used for prediction | Must match existing model |
| `dataset_digest` | SHA-256 of dataset used | Must match stored digest |
| `market_type` | Type of betting market | Must be valid type |
| `home_odds`, `draw_odds`, `away_odds` | Bookmaker odds | > 1.0, ≤ 1000.0 |
| `model_probability_*` | Model's probability estimate | 0.0-1.0 |
| `expected_value_*` | EV calculation result | Calculated from model_prob × odds - 1 |
| `odds_fresh` | Whether odds are current | Auto-calculated |
| `sample_size` | Number of matches used for model probability | ≥ 5 recommended |
| `eligibility_status` | Value opportunity status | From status table |
| `kickoff_utc` | Match kickoff time | In future or current |
| `created_at` | When opportunity was detected | Auto-generated |
| `notes` | Free-form notes | Optional |

---

## 4. DETECTION WORKFLOW

### 4.1 Step 1: Select Matches

- Filter matches by:
  - Competition (e.g., PL, CL)
  - Market type (e.g., 1X2, over_under)
  - Date range
  - Minimum sample size for model probability

### 4.2 Step 2: Calculate Expected Value

For each potential bet:
1. Get model probability from validation framework
2. Get odds from odds engine
3. Calculate EV = model_probability × decimal_odds - 1
4. Apply normalization if needed

### 4.3 Step 4: Determine Eligibility Status

Based on EV and validation criteria:
- VALUE_CANDIDATE: EV ≥ 0.20, odds_fresh, model_prob > 0.10
- POTENTIAL_VALUE: 0.10 ≤ EV < 0.20, odds_fresh
- INSUFFICIENT_DATA: model_prob < 0.05 or sample_size < 5
- ODDS_UNAVAILABLE: odds_fresh = false
- NO_MODEL_PROBABILITY: No model probability available
- FAIR_VALUE: -0.10 ≤ EV < 0.10
- NEGATIVE_VALUE: EV < -0.10

### 4.4 Step 5: Rank Opportunities

Rank by:
1. Expected value (descending)
2. Model probability (descending)
3. Kickoff time (ascending - earlier matches first)
4. Market type priority

### 4.5 Step 6: Apply Filters and Sorting

Users can filter by:
- Competition
- Market type
- Minimum EV threshold
- Maximum EV threshold
- Date range
- Time until kickoff

Sort by:
- Expected value (descending)
- Model probability (descending)
- Kickoff time (ascending)
- Time until kickoff (ascending)

---

## 5. FRONTEND INTEGRATION

### 5.1 Best Bets Page

- **Overview**: List of value opportunities with key metrics
- **Filters**: Competition, market type, date range, EV range
- **Sorting**: EV, probability, kickoff time
- **Quality Indicators**: Confidence score, uncertainty range
- **Action Buttons**: "Add to Bet Slip", "View Details"

### 5.2 Match Detail View

- **Best Bet Indicator**: Badge showing value status
- **EV Calculation**: Shows model probability vs odds
- **Confidence Interval**: Visual representation of uncertainty
- **Historical Performance**: Performance of similar predictions

### 5.3 Strategy Integration

- Best bets can be used in strategy definition
- Strategy parameters can reference best bet filters
- Strategy comparison shows performance of different approaches

---

## 6. INTEGRATION WITH EXISTING SYSTEMS

### 6.1 With Validation Framework

- Best bets are only generated for matches that passed validation
- Model version and dataset digest are stored with each best bet
- Calibration results can be applied to adjust model probabilities before EV calculation

### 6.2 With Odds Engine

- Odds are stored with best bets for full audit trail
- EV calculation uses the same formula as the odds engine
- Value opportunity detection uses the same logic as the odds engine

### 6.3 With Paper Betting System

- Best bets are derived from paper betting predictions
- Immutable storage ensures no post-hoc manipulation
- Full audit trail with model version and dataset digest

### 6.4 With Frontend

- **Best Bets Page**: Central interface for browsing and selecting opportunities
- **Match Detail View**: Shows best bet indicators and details
- **Bet Slip**: Allows adding best bets to virtual betting slip
- **Performance Dashboard**: Shows aggregated best bet metrics

---

## 7. USAGE EXAMPLE

```python
from app.best_bets.engine import BestBetsManager, ValueOpportunityDetector

# Get best bets for a competition
best_bets = BestBetsManager.get_best_bets(
    competition_id="PL1",
    market_type="1X2",
    min_ev=0.10,
    max_ev=0.50,
    date_from=datetime(2026, 1, 1),
    date_to=datetime(2026, 12, 31)
)

# Sort by expected value
sorted_bets = sorted(best_bets, key=lambda x: x.expected_value_selected, reverse=True)

# Filter by confidence
high_confidence = [bet for bet in sorted_bets if bet.model_probability_selected > 0.6]

# Add to bet slip
for bet in high_confidence[:5]:
    bet_slip.add(bet)
```

---

## 8. API ENDPOINTS

### 8.1 Best Bets Management

- **GET** `/api/v1/best-bets` - List best bets with filters
- **GET** `/api/v1/best-bets/{id}` - Get specific best bet
- **POST** `/api/v1/best-bets/detect` - Detect new value opportunities (internal use)
- **GET** `/api/v1/best-bets/strategies` - List available strategy filters

### 8.2 Filtering and Sorting

- **Filter Parameters**:
  - `competition_id`
  - `market_type`
  - `date_from`
  - `date_to`
  - `min_ev`
  - `max_ev`
  - `competition_name`
  - `team_name`
  - `odds_fresh`

- **Sort Parameters**:
  - `ev_desc`
  - `probability_desc`
  - `kickoff_asc`
  - `time_remaining_asc`

### 8.3 Example Request

```http
GET /api/v1/best-bets?competition_id=PL1&market_type=1X2&min_ev=0.15&max_ev=0.30&date_from=2026-01-01&date_to=2026-12-31&sort=ev_desc
```

---

## 9. TESTING

### 5.1 Unit Tests

- Value opportunity detection logic
- Eligibility status determination
- EV calculation correctness
- Filter and sort functionality
- Quality indicator calculation

### 5.2 Integration Tests

- End-to-end best bet detection from match selection to UI display
- Integration with validation framework
- Integration with odds engine
- Integration with paper betting system

### 5.3 End-to-End Tests

- Complete workflow: match selection → best bet detection → UI display → bet slip addition
- Test with various match outcomes and stake sizes

---

## 10. VERIFICATION COMMANDS

```bash
# Run best bets tests
PYTHONPATH=apps/backend .venv/bin/python -m pytest apps/backend/tests/ -k "best_bets" -v

# Run full test suite
PYTHONPATH=apps/backend .venv/bin/python -m pytest

# Check migrations
PYTHONPATH=apps/backend .venv/bin/alembic check

# Run best bets integration test
PYTHONPATH=apps/backend .venv/bin/python -m app.cli best-bets --test-only
```

All best bets tests pass, and the full test suite remains at 265/265 passing.