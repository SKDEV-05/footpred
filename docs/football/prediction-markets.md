# Prediction Markets

## Purpose

Defines the markets under consideration, how each is derived, what data it requires, and how it will be evaluated. All markets are planned. None is implemented, exposed, or validated. This document is analysis scope, not betting content.

## Common basis: the scoreline matrix

Let `M[i][j]` be the estimated probability that the home team scores `i` goals and the away team scores `j` goals in regulation time, including stoppage time but excluding extra time and penalties. `M` is a proper probability distribution: all cells are non-negative and sum to one, with a documented tail treatment for scores beyond the modelled range.

Every market below is a sum over regions of this single matrix. Deriving all markets from one object makes inconsistencies detectable and prevents unrelated models from publishing contradictory numbers. The matrix is produced from estimated attack and defence strengths, a competition baseline, and a home-advantage term; the family of distribution and its assumptions must be recorded with each prediction.

## Market catalogue

| Market | Definition | Derivation from `M` | Typical data requirement | Reliability tier |
| --- | --- | --- | --- | --- |
| 1X2 | Home win, draw, away win in regulation | Sum cells where `i>j`, `i=j`, `i<j` | Multi-season results by competition and venue | High |
| Double chance | Two of three 1X2 outcomes occur | Sum of the corresponding two 1X2 probabilities | Same as 1X2 | High |
| Over/under total goals | Total goals above or below a stated line | Sum cells where `i+j` exceeds or falls below the line | Goal totals, venue splits, scoring distribution | Medium |
| Both teams to score | Each team scores at least once | Sum cells where `i>=1` and `j>=1` | Goal totals by team and venue | Medium |
| Correct score | Exact final score in regulation | Individual cell `M[i][j]`, or grouped score bands | Large result samples; stable matrix | Low |
| First-half goals | Goals, result or totals in the first half | Same operations on a first-half matrix `M_H` | Half-time scores and half-specific scoring rates | Low to medium |

Tier meaning: **high** means the market is a sum over a large region and tolerates modest cell-level error; **medium** means it depends on distribution shape, tails, or zero probabilities; **low** means it rests on single cells or sparse half-specific data. Tier is a modelling judgement, not a measured result.

### 1X2

`P(home) = Σ_{i>j} M[i][j]`, `P(draw) = Σ_{i=j} M[i][j]`, `P(away) = Σ_{i<j} M[i][j]`. The three probabilities sum to one. Only regulation time counts. A cup tie decided in extra time or on penalties is a draw for this market. Data must distinguish regulation from extra-time scores; otherwise the market definition is corrupted.

### Double chance

`1X = P(home) + P(draw)`, `12 = P(home) + P(away)`, `X2 = P(draw) + P(away)`. Double chance is a deterministic function of 1X2, not independent evidence. The three selections overlap and sum to two, so they cannot be treated as a three-way probability distribution. It is normally presented as three separate two-outcome views; labelling must make the overlap explicit.

### Over/under total goals

`Over(L) = Σ_{i+j>L} M[i][j]`, `Under(L) = Σ_{i+j<L} M[i][j]`. For an integer line, `Σ_{i+j=L} M[i][j]` is the push probability and is neither over nor under; half-integer lines avoid this. Lines are nested: for `L1 < L2`, `P(Over L1) >= P(Over L2)`. Any published set of lines must satisfy that ordering. Accuracy depends on the assumed goal distribution and its dispersion, not only on the mean.

### Both teams to score

`P(Yes) = Σ_{i>=1, j>=1} M[i][j] = 1 - P(i=0) - P(j=0) + M[0][0]`. `P(No)` is the complement. The result is sensitive to the modelled probability of a shutout for each side, so a matrix that fits totals well can still misstate BTTS. BTTS Yes implies at least two total goals, which gives a testable consistency bound against the over/under market.

### Correct score

Each scoreline is a single cell. The market is high-variance by construction: many cells, most with small probabilities, and the most likely score is frequently not the observed one even when the matrix is well calibrated. It requires a large evaluation sample before any claim about performance is meaningful. Grouped outcomes such as "home win by two or more" are sums over regions and are more stable than an exact score. Presentation must not imply that the modal score is expected to occur.

### First-half goals

First-half markets require a separate matrix `M_H` built from first-half scoring rates, not from halving full-time expectations. `P(1H over 0.5) = 1 - M_H[0][0]`; first-half 1X2 and double chance use the same regional sums as their full-time counterparts. Half-time scores are mandatory input. First-half scoring rates differ from second-half rates and are affected by lineups, game state and competition. Coverage of half-time data is typically worse than full-time coverage, so the reliability tier is lower.

## Interdependencies between markets

- Correct-score marginals must reproduce 1X2 and total-goal probabilities within a documented tolerance.
- Over/under lines must be monotonic in the line; BTTS Yes must not exceed the probability of over 1.5 goals.
- Double chance must equal the sum of its two 1X2 components; it must never be published as if independently modelled.
- First-half markets constrain, but do not determine, full-time markets. A full-time estimate must not be derived from first-half output alone.
- Consistency checks are numerical, with a stated tolerance, and run before publication. A failed check blocks the output rather than silently adjusting one market.

## Minimum evidence thresholds

Proposal only. No numeric threshold is set; any value used later is tunable and must be recorded as UNVERIFIED until validated.

| Gate | Question | Evidence |
| --- | --- | --- |
| G1 Legality and coverage | Is the source permitted and does it cover the competition and seasons? | Licence record and coverage report |
| G2 Sample | Are there enough matches per team, competition and venue split? | Counts with missing-data breakdown; `N_min` TBD |
| G3 Calibration | Has the market been calibrated on held-out seasons? | Reliability curve and proper score versus baseline |
| G4 Stability | Does the result survive plausible model choices? | Sensitivity across matrix families and windows |
| G5 Completeness | Are half-time, lineup and status fields adequate for this market? | Field-level completeness report |
| G6 Review | Has a human accepted the limits? | Recorded decision and stated caveats |

Exposure should be staged: internal evaluation only, then a research preview with visible uncertainty, then public display. A market that fails any gate is not exposed, regardless of user demand.

## Evaluation metric per market

| Market | Primary metric | Secondary checks | Caveat |
| --- | --- | --- | --- |
| 1X2 | Multiclass Brier score and log loss | Calibration by outcome and confidence band | Compare against league base rates; draws are systematically hard |
| Double chance | Binary Brier/log loss per selection | Agreement with 1X2 components | Selections overlap; do not average as if independent |
| Over/under | Binary Brier/log loss per line | Calibration and monotonicity across lines | Each line is a separate series with its own sample |
| BTTS | Binary Brier/log loss | Calibration and consistency with totals | Sensitive to shutout probabilities |
| Correct score | Multiclass log loss with smoothing | Top-k calibration; grouped-score calibration | Sparse cells; raw accuracy is misleading |
| First-half goals | Binary or multiclass Brier/log loss | Calibration; coverage-adjusted reporting | Smaller effective sample; half-time data gaps |

All evaluation uses predictions timestamped before kickoff and a temporal split with no future leakage. Scores are reported with sample sizes and uncertainty intervals, broken down by competition and model version. Accuracy alone is not accepted as evidence of quality.

## No betting advice

The platform provides analysis of football matches. It does not provide betting advice, selections, staking guidance, or odds, and it does not claim any guaranteed outcome. Any market terminology is used to define analytical outputs, not to facilitate wagering.

## Markets deliberately excluded for now

| Market | Reason for exclusion |
| --- | --- |
| Asian handicap and alternative lines | Requires line-specific modelling and liquidity assumptions; not needed to prove the core approach |
| Corners, cards, fouls | Different count processes and weaker data coverage; separate modelling problem |
| Player props and goalscorer markets | Depend on lineup confirmation and player-level rates that are not yet reliable |
| In-play and next-goal markets | Need low-latency data and dynamic recalibration; out of current phase |
| VAR, injury and transfer outcomes | Not football scoring markets; data and verification are inadequate |
| Any market lacking sufficient reliable data | Excluded by the evidence gates above, regardless of popularity |

## Open questions

- Which over/under lines are supportable per competition, given goal distributions and sample sizes?
- Is half-time score coverage sufficient for first-half markets outside top competitions? UNVERIFIED.
- Which matrix family and tail treatment best fits observed scorelines without overfitting?
- Should double chance be exposed as a market or only as a derived view of 1X2?
- What calibration window and recalibration cadence are appropriate per competition?
- How should correct score be presented without implying that the modal score is likely?
- What tolerance should consistency checks use before blocking publication?

## Related documents

- [Football domain model](./football-domain.md)
- [Performance metrics](./performance-metrics.md)
- [Requirements](../product/requirements.md)
- [Non-goals](../product/non-goals.md)
