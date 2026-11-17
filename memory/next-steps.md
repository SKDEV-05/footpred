## Stage 0 — Repository audit and baseline reproduction ✅ COMPLETE

## Stage 1 — Independent ML/QA review ✅ COMPLETE

- Poisson model: mathematically correct, probability conserving
- Dixon-Coles: implemented but not in production path
- Elo: implemented but not in production path
- Backtesting: chronological, proper abstention, all validations
- Draw probability under-prediction documented (LIM-028)
- Calibration: ECE/MCE computed but not studied

**Deliverable**: `docs/research/phase-8-independent-ml-review.md`

## Stage 2 — Strict chronological validation ✅ COMPLETE

- Built `apps/backend/app/intelligence/validation.py`
- Implements protocols A-G (rolling origin, expanding window, multiple windows, multiple competitions/seasons, sample requirements, train/test separation)
- All models evaluated on identical fixtures
- Fixed seed bootstrap CIs
- Versioned protocol, evaluation, model versions
- No future-data leakage

**Deliverable**: `docs/research/phase-8-out-of-sample-validation.md`

## Stage 3 — Probability calibration ⚠️ IN PROGRESS

**Task**: Build dedicated calibration subsystem with reliability diagrams, per-competition calibration, and investigation of draw bias.

**Required**:
- Reliability diagrams with proper visualization
- ECE/MCE by competition, season, probability range
- Draw probability bias analysis
- Calibration correction options (temperature scaling, isotonic regression)
- Calibration data/train split

**Deliverable**: `docs/research/phase-8-calibration-study.md`

## Stage 4 — Market odds and Expected Value engine ⚠️ PENDING

**Task**: Implement odds storage, EV calculation, and market analysis subsystem.

**Required**:
- Database schema for odds
- Manual odds input support (clearly marked as manual)
- Expected Value calculation: `EV = model_probability × decimal_odds - 1`
- Bookmaker tracking
- Fair probability normalization
- Odds freshness detection

**Deliverable**: `docs/research/phase-8-odds-value-engine.md`

## Stage 5 — Paper Betting ⚠️ PENDING

**Task**: Build complete virtual betting simulation.

**Required**:
- Prediction recording before kickoff
- Immutable storage with model version and dataset digest
- Virtual stake management
- Match resolution after fixture completion
- Performance metrics: win rate, ROI, yield, drawdown, streaks
- Strategy comparison

**Deliverable**: `docs/research/phase-8-paper-betting.md`

## Stage 6 — Best Bets / Value Opportunities ⚠️ PENDING

**Task**: Create dedicated value opportunities ranking interface.

**Required**:
- Filter by competition, market, date, minimum EV
- Sort by model probability, EV, kickoff
- Quality and uncertainty indicators
- Proper eligibility statuses (VALUE_CANDIDATE, INSUFFICIENT_DATA, ODDS_UNAVAILABLE, etc.)
- No fake opportunities created

**Deliverable**: `docs/research/phase-8-best-bets.md`

## Stage 7 — Commercial licensing assessment ⚠️ PENDING

**Task**: Investigate provider terms and create licensing matrix.

**Required**:
- football-data.org clause 9.1 (display after cancellation)
- API-Football terms review
- Statistics tier limitations
- Redistribution rights assessment
- Caching restrictions

**Deliverable**: `docs/research/phase-8-commercial-licensing-review.md`

## Stage 8 — Authentication and security ⚠️ PENDING

**Task**: Audit and implement security for controlled public exposure.

**Required**:
- User registration/login/logout
- Password hashing and session management
- Role-based authorization
- Rate limiting
- Security headers
- CSRF protection
- Audit logging
- TLS/HTTPS design

**Deliverable**: `docs/research/phase-8-security-review.md`

## Stage 9 — Complete Next.js UI/UX redesign ⚠️ PENDING

**Task**: Substantial professional redesign of the frontend.

**Required**:
- Premium sports analytics dashboard
- Modern professional dark interface
- Strong typography and spacing
- Clean data visualization
- Excellent desktop and mobile experiences
- Overview, Matches, Analyze Match, Best Bets, Model Evaluation, Paper Betting, Performance, Settings

**Deliverable**: `docs/research/phase-8-frontend-redesign.md`

## Stage 10 — Integration, performance, QA and documentation ⚠️ PENDING

**Task**: Full integration testing and final documentation.

**Required**:
- Full backend test suite execution
- Alembic check
- TypeScript checks
- Production frontend build
- API smoke tests
- Browser QA (desktop + mobile)
- Responsive QA at multiple viewports
- Final report

**Deliverable**: `docs/research/phase-8-final-report.md`