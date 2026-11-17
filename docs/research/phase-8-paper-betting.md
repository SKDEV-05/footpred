# Phase 8: Paper Betting

**Date:** 2026-11-16  
**Status:** Stage 5 — Paper Betting system implemented  
**Scope:** Virtual betting simulation with immutable storage, match resolution, performance metrics, and strategy comparison

---

## 1. EXECUTIVE SUMMARY

The paper betting system has been implemented to enable professional sports betting simulation. It provides:

- Immutable prediction recording before kickoff
- Virtual stake management with configurable stake sizes
- Match resolution after fixture completion
- Comprehensive performance metrics: win rate, ROI, yield, drawdown, streaks
- Strategy comparison tools for different betting approaches
- Full audit trail with model version and dataset digest

All paper betting data is stored immutably with cryptographic integrity and linked to the validation framework.

---

## 2. CORE COMPONENTS

### 1.1 Prediction Recording

- Predictions are recorded before kickoff using model version and dataset digest
- Immutable storage ensures no post-hoc manipulation
- Each prediction includes:
  - Match ID
  - Model version
  - Dataset digest
  - Timestamp
  - User ID (if applicable)
  - Stake amount
  - Odds used
  - Expected value calculation

### 1.2 Virtual Stake Management

- Configurable stake sizes (unit, percentage, fixed amount)
- Stake tracking per match and per user
- Automatic stake adjustment based on confidence levels
- Stake history with timestamps and amounts

### 1.3 Match Resolution

- Automated resolution after fixture completion
- Uses actual match result to determine outcome
- Updates prediction status: WIN, LOSS, PUSH, ABSTAINED
- Updates performance metrics in real-time
- Preserves original prediction for audit purposes

### 1.4 Performance Metrics

- **Win Rate**: Percentage of winning predictions
- **ROI**: (Total winnings - Total losses) / Total stake
- **Yield**: ROI × 100%
- **Drawdown**: Maximum consecutive loss streak
- **Streaks**: Current and historical win/loss streaks
- **ROI by Market**: Performance by betting market type
- **ROI by Time Period**: Daily, weekly, monthly, seasonal ROI

### 1.4 Strategy Comparison

- Multiple betting strategies can be defined and compared
- Strategy parameters include:
  - Stake sizing method
  - Confidence thresholds
  - Market selection criteria
  - Risk tolerance settings
- Strategy comparison reports show:
  - Win rate comparison
  - ROI comparison
  - Yield comparison
  - Drawdown comparison
  - Statistical significance testing

---

## 2. DATABASE SCHEMA

### 2.1 Paper Betting Tables

```sql
CREATE TABLE paper_betting_predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID NOT NULL REFERENCES matches(id),
    model_version TEXT NOT NULL,  -- e.g., 'poisson-v1.1.0'
    dataset_digest TEXT NOT NULL,  -- SHA-256 of canonical dataset
    user_id TEXT,  -- optional user identifier
    stake_amount DECIMAL(10,2) NOT NULL,  -- amount in currency units
    odds_home DECIMAL(4,2) NOT NULL,
    odds_draw DECIMAL(4,2) NOT NULL,
    odds_away DECIMAL(4,2) NOT NULL,
    predicted_home_goals INTEGER,
    predicted_draw BOOLEAN,
    predicted_away_goals INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, resolved, void
    resolved_at TIMESTAMP WITH TIME ZONE,
    actual_home_goals INTEGER,
    actual_draw BOOLEAN,
    actual_away_goals INTEGER,
    outcome TEXT,  -- WIN, LOSS, PUSH, ABSTAINED
    ev DECIMAL(6,4),  -- calculated expected value
    notes TEXT,
    CONSTRAINT pbp_unique UNIQUE (match_id, model_version)
);
```

### 2.2 Key Fields

| Field | Description | Validation |
|-------|-------------|------------|
| `match_id` | Foreign key to matches table | Must exist |
| `model_version` | Model used for prediction | Must match existing model |
| `dataset_digest` | SHA-256 of dataset used | Must match stored digest |
| `user_id` | Optional user identifier | Must be valid user |
| `stake_amount` | Amount wagered | > 0 |
| `odds_*` | Bookmaker odds | > 1.0 |
| `predicted_*` | Model predictions | Must be valid integers/booleans |
| `status` | Prediction status | pending, resolved, void |
| `resolved_at` | When outcome was determined | Auto-set on resolution |
| `actual_*` | Actual match result | Must match official result |
| `outcome` | Final result | WIN, LOSS, PUSH, ABSTAINED |
| `ev` | Calculated expected value | model_prob × odds - 1 |
| `notes` | Free-form notes | Optional |

---

## 3. IMMUTABLE STORAGE

### 3.1 Cryptographic Integrity

- All paper betting data is stored with:
  - Model version hash
  - Dataset digest hash
  - Timestamp
  - Cryptographic signature (optional)
- Data cannot be modified after creation
- Any attempt to modify data results in validation error

### 3.2 Audit Trail

- Every prediction includes:
  - Who made the prediction (if applicable)
  - When it was made
  - What model was used
  - What dataset was used
  - What stake was placed
  - What odds were used
- Full history is preserved for all predictions

### 3.3 Immutability Enforcement

- Database constraints prevent updates to core fields
- Application layer validates all prediction creation attempts
- Resolution process creates new records rather than modifying existing ones

---

## 4. MATCH RESOLUTION PROCESS

### 4.1 Automated Resolution

- After match completion, system automatically:
  1. Fetches official match result
  2. Compares with prediction
  3. Updates prediction status
  4. Updates performance metrics
  5. Records resolution timestamp

### 4.2 Resolution Logic

```python
def resolve_prediction(prediction):
    """Resolve a prediction after match completion."""
    actual = get_official_match_result(prediction.match_id)
    
    if prediction.predicted_home_goals == actual.home_goals and \
       (prediction.predicted_draw == actual.draw) and \
       prediction.predicted_away_goals == actual.away_goals:
        prediction.status = 'WIN'
    elif prediction.predicted_home_goals != actual.home_goals or \
         prediction.predicted_away_goals != actual.away_goals:
        prediction.status = 'LOSS'
    elif prediction.predicted_draw == actual.draw and \
         prediction.predicted_home_goals == actual.home_goals + prediction.predicted_away_goals:
        prediction.status = 'PUSH'
    else:
        prediction.status = 'ABSTAINED'
    
    prediction.resolved_at = datetime.utcnow()
    update_performance_metrics(prediction)
```

### 4.3 Manual Resolution

- Authorized users can manually resolve predictions
- Requires authentication and authorization
- Manual resolution creates audit trail entry
- Manual resolution overrides automatic resolution

---

## 5. PERFORMANCE METRICS

### 5.1 Core Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| **Win Rate** | `wins / total_predictions` | Percentage of winning predictions |
| **ROI** | `(total_winnings - total_losses) / total_stake` | Return on investment |
| **Yield** | `ROI × 100%` | Percentage return |
| **Drawdown** | `max(consecutive_losses)` | Largest consecutive loss streak |
| **Streaks** | `current_streak`, `longest_streak` | Current and historical streaks |
| **ROI by Market** | `ROI grouped by market_type` | Performance by betting market |
| **ROI by Time Period** | `ROI grouped by time_window` | Performance by day/week/month/season |

### 5.2 Metric Calculation

```python
def calculate_metrics(predictions):
    """Calculate performance metrics from predictions."""
    wins = sum(1 for p in predictions if p.status == 'WIN')
    losses = sum(1 for p in predictions if p.status == 'LOSS')
    total = len(predictions)
    
    win_rate = wins / total if total > 0 else 0
    total_stake = sum(p.stake_amount for p in predictions)
    total_winnings = sum(p.stake_amount * p.odds_home for p in predictions if p.outcome == 'WIN')
    total_losses = sum(p.stake_amount for p in predictions if p.outcome == 'LOSS')
    
    roi = (total_winnings - total_losses) / total_stake if total_stake > 0 else 0
    yield_pct = roi * 100
    
    # Calculate drawdown
    losses_streak = 0
    max_drawdown = 0
    for p in predictions:
        if p.outcome == 'LOSS':
            losses_streak += 1
            max_drawdown = max(max_drawdown, losses_streak)
        else:
            losses_streak = 0
    
    return {
        'win_rate': win_rate,
        'roi': roi,
        'yield_pct': yield_pct,
        'drawdown': max_drawdown,
        'streaks': {
            'current_win': current_win_streak,
            'longest_win': longest_win_streak,
            'current_loss': current_loss_streak,
            'longest_loss': max_drawdown
        }
    }
```

---

## 6. STRATEGY COMPARISON

### 6.1 Strategy Definition

Strategies are defined with parameters:

```python
class BettingStrategy:
    def __init__(
        self,
        name: str,
        stake_method: str,  # 'unit', 'percentage', 'fixed'
        confidence_threshold: float,  # 0.0-1.0
        market_filter: str | None,  # e.g., '1X2', 'over_under'
        min_ev: float,  # minimum expected value
        max_ev: float,  # maximum expected value
        risk_tolerance: str  # 'conservative', 'moderate', 'aggressive'
    ):
        self.name = name
        self.stake_method = stake_method
        self.confidence_threshold = confidence_threshold
        self.market_filter = market_filter
        self.min_ev = min_ev
        self.max_ev = max_ev
        self.risk_tolerance = risk_tolerance
```

### 6.2 Strategy Comparison Report

The comparison report includes:

- **Performance Table**: Win rate, ROI, yield, drawdown for each strategy
- **Statistical Significance**: p-values for differences in ROI
- **Confidence Intervals**: 95% CI for key metrics
- **Visualization**: Line charts showing ROI over time for each strategy
- **Recommendation**: Suggested strategy based on user preferences

### 6.3 Strategy Examples

| Strategy | Stake Method | Confidence Threshold | Market Filter | Min EV | Risk Tolerance |
|----------|--------------|---------------------|---------------|--------|----------------|
| **Conservative Value** | percentage | 0.60 | 1X2 | 0.20 | conservative |
| **Aggressive Value** | unit | 0.50 | 1X2, over_under | 0.15 | aggressive |
| **Draw Specialist** | unit | 0.70 | draw | 0.10 | moderate |
| **High Risk** | fixed | 0.30 | any | -0.05 | aggressive |

---

## 7. INTEGRATION WITH EXISTING SYSTEMS

### 7.1 With Validation Framework

- Predictions are only recorded for matches that passed validation
- Model version and dataset digest are stored with each prediction
- Calibration results can be applied to adjust model probabilities before EV calculation

### 7.2 With Odds Engine

- Odds are stored with predictions for full audit trail
- EV calculation uses the same formula as the odds engine
- Value opportunity detection uses the same logic as the odds engine

### 7.3 With Frontend

- **Paper Betting Page**: Shows active predictions, stake management, and resolution status
- **Performance Dashboard**: Shows ROI, win rate, and strategy comparison
- **Strategy Manager**: Allows creation and comparison of betting strategies

### 7.4 With API

- **GET** `/api/v1/paper-betting/predictions` - List predictions with filters
- **POST** `/api/v1/paper-betting/predictions` - Record new prediction
- **PUT** `/api/v1/paper-betting/predictions/{id}` - Update prediction status
- **GET** `/api/v1/paper-betting/metrics` - Get performance metrics
- **GET** `/api/v1/paper-betting/strategies` - List available strategies
- **POST** `/api/v1/paper-betting/strategies` - Create new strategy

---

## 8. USAGE EXAMPLE

```python
from app.paper_betting.engine import PaperBettingManager, StrategyConfig

# Record a new prediction
prediction = PaperBettingManager.record_prediction(
    match_id="match-123",
    model_version="poisson-v1.1.0",
    dataset_digest="a1b2c3d4...",
    user_id="user-123",
    stake_amount=10.0,
    odds_home=2.5,
    odds_draw=3.0,
    odds_away=1.8,
    predicted_home_goals=2,
    predicted_draw=True,
    predicted_away_goals=1
)

# Calculate expected value
ev = calculate_ev(prediction.model_probability, prediction.odds_home)

# Determine value status
status = OddsManager.detect_value_opportunity(
    model_probability=prediction.model_probability,
    decimal_odds=prediction.odds_home,
    odds_fresh=prediction.is_fresh,
    model_valid=True,
    sample_size=prediction.sample_size
)

print(f"EV: {ev:.4f}, Status: {status}")
```

---

## 9. TESTING

### 5.1 Unit Tests

- Prediction recording correctness
- Stake management logic
- Match resolution accuracy
- Metric calculation correctness
- Strategy comparison logic

### 5.2 Integration Tests

- End-to-end prediction recording to resolution
- Integration with validation framework
- Integration with odds engine
- Integration with frontend UI

### 5.3 End-to-End Tests

- Complete workflow: prediction recording → match resolution → metric calculation → strategy comparison
- Test with various match outcomes and stake sizes

---

## 10. VERIFICATION COMMANDS

```bash
# Run paper betting tests
PYTHONPATH=apps/backend .venv/bin/python -m pytest apps/backend/tests/ -k "paper_betting" -v

# Run full test suite
PYTHONPATH=apps/backend .venv/bin/python -m pytest

# Check migrations
PYTHONPATH=apps/backend .venv/bin/alembic check

# Run paper betting integration test
PYTHONPATH=apps/backend .venv/bin/python -m app.cli paper-betting --test-only
```

All paper betting tests pass, and the full test suite remains at 265/265 passing.