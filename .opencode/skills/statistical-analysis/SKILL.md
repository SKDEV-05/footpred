---
name: Statistical Analysis
description: Reason correctly about football probability models — Poisson and Dixon-Coles goal models, Elo, home advantage, calibration, sample size, uncertainty, and model assumptions. Use when defining, reviewing, or interpreting a probability estimate.
---

# Statistical Analysis

## Objective

Ensure probability estimates are derived from stated assumptions, estimated on adequate
samples, calibrated, and reported with uncertainty. Statistics describe evidence; they do not
guarantee outcomes.

## Activation

Use for goal-rate estimation, scoreline distributions, market probabilities, team ratings,
calibration, uncertainty statements, or when interpreting a model result.

## Required context

- Target quantity (match outcome, goals, scoreline) and its definition.
- Population and sample (competition, seasons, matches, inclusion rules).
- Data availability at prediction time.
- Evaluation metric and the baseline to beat.
- Known confounders and missing data.

## Workflow

1. **Define the target** as a random variable with a sample space.
2. **State the model and its assumptions** in plain language and mathematics.
3. **Estimate parameters** from data available before the prediction time.
4. **Check assumptions** and sensitivity to violations.
5. **Quantify uncertainty** (standard errors, intervals, or posterior spread).
6. **Calibrate** the output probabilities against observed frequencies.
7. **Evaluate** with proper scoring rules and compare to baselines.
8. **Report** the estimate with uncertainty and limitations.

## Detailed procedures

### The Poisson goal model

If home and away goals are modelled as independent Poisson variables with rates
λ_home and λ_away:

P(X = k) = e^(−λ) · λ^k / k!

The scoreline probability is the product of the two marginal probabilities. Summing cells of
the scoreline matrix produces 1X2, over/under, and BTTS probabilities consistently. This
internal consistency is a major advantage over estimating each market separately.

Limitations:
- Goals are not perfectly independent; match state affects behaviour.
- Rates are not constant across the match (late-game effects, red cards).
- Low-scoring results are systematically misestimated by independent Poisson.
- Team strength and home advantage must be estimated, not assumed.

### Dixon-Coles adjustment

Dixon-Coles (1997) modifies the joint probability of low scorelines (0-0, 1-0, 0-1, 1-1) with
a dependence parameter ρ, improving fit for the low-score region. It also typically applies
exponential time decay to historical matches so recent form matters more. The decay rate is a
tunable parameter and should be selected by out-of-sample evaluation, not intuition.

Do not claim Dixon-Coles is universally superior; it is a refinement with its own
assumptions and estimation cost.

### Estimating goal rates

Common approaches:
- League average goals multiplied by attack/defence strength parameters.
- Team-specific rates with shrinkage toward the league mean (empirical Bayes).
- Time-decayed rates.
- Ratings (Elo-style) converted to expected goals.

Every approach needs:
- a defined home-advantage term (league- and possibly team-specific);
- promotion/relegation handling;
- a minimum sample rule or shrinkage for teams with few matches;
- separation of competition types (league vs cup).

### Elo-style ratings

Expected score for player/team A against B is often written
E_A = 1 / (1 + 10^(−(R_A − R_B + H)/400)), where H is a home-advantage term in rating points.
Updates use a K-factor scaled by result and margin. For football, margin-of-victory
adjustments and competition weighting are common.

Limitations: Elo is ordinal, not a goal model; it does not directly give scoreline
probabilities; K-factor and home term are choices that must be validated; cross-league
comparisons are unreliable without calibration.

### Home advantage

Estimate it; do not hardcode it. It can be modelled as a multiplicative factor on home/away
goal rates, a rating offset, or a team-specific effect. Check whether it is stable over the
evaluation window. Neutral venues must be explicit.

### Sample size and uncertainty

- For a proportion p with n observations, the standard error is approximately
  sqrt(p(1−p)/n).
- A team with 8 home matches provides very little evidence about its true home scoring rate.
- Shrink estimates toward a league prior when samples are small; state the prior.
- Report intervals, not just point estimates.
- Multiple comparisons inflate false discoveries; pre-register the metrics you will evaluate.

### Calibration

A model is calibrated if, among predictions of probability p, the observed frequency is
approximately p. Check with reliability diagrams and by binning predicted probabilities.
Calibration is separate from discrimination: a model can rank well and still be badly
calibrated.

Calibration methods: Platt scaling (logistic fit on held-out scores), isotonic regression
(non-parametric, needs enough data), beta calibration. Fit calibration on data not used to fit
the model, and re-check after any distribution shift.

### Proper scoring rules

- Brier score: mean squared error between predicted probability and outcome indicator
  (0/1). Lower is better.
- Log loss: −mean[y·ln(p) + (1−y)·ln(1−p)]. Penalises confident errors heavily.
- Both are proper: they are optimised by reporting the true probability.
- Accuracy alone is a poor metric: it ignores confidence and is sensitive to class balance.
- Always report the base rate and a naive baseline.

### Correlation and dependence

- Home and away goals are weakly negatively correlated in some models; ignoring dependence
  affects correct-score and low-score markets.
- Market probabilities derived from the same scoreline matrix are dependent; do not treat
  them as independent signals.
- Team performance observations are autocorrelated over time; standard i.i.d. standard errors
  understate uncertainty.

### Assumption audit

For each model, list: independence, stationarity, distributional family, parameter stability,
home-advantage form, sample inclusion, and missing-data handling. State which violations are
likely and how sensitive the output is.

## Quality checklist

- [ ] Target and sample space are defined.
- [ ] The model's assumptions are written down, not implied.
- [ ] Parameters are estimated only from pre-kickoff information.
- [ ] Sample size and shrinkage are addressed.
- [ ] Uncertainty is reported with the estimate.
- [ ] Probabilities are calibrated on held-out data.
- [ ] Proper scoring rules and a baseline are reported.
- [ ] Derived markets are internally consistent.
- [ ] No claim that a probability guarantees an outcome.

## Common failure patterns

- Presenting a point probability without uncertainty.
- Treating 5-10 matches as a reliable rate estimate.
- Hardcoding a universal home-advantage multiplier.
- Evaluating with accuracy only, on a balanced-looking sample.
- Fitting calibration on the training data.
- Mixing Poisson marginals with separately estimated markets, producing inconsistent prices.
- Confusing discrimination (ranking) with calibration.
- Ignoring competition and era differences when pooling data.

## Expected outputs

- Model specification with equations and assumptions.
- Parameter estimation and shrinkage rules.
- Calibration and evaluation protocol.
- Uncertainty reporting format.
- Assumption/limitation register.

## Sources and references

- `docs/football/performance-metrics.md`
- `docs/football/prediction-markets.md`
- Maher (1982), modelling football scores with Poisson; Dixon & Coles (1997), association
  football scores and inefficiencies in the football betting market. Consult original papers
  before relying on specific parameterisations.
- `rules/data-rules.md`

## Limitations

All football models are approximations of a low-scoring, dependent, non-stationary process.
Historical relationships may not persist. This skill does not authorise implementation,
data access, or performance claims without an executed evaluation.
