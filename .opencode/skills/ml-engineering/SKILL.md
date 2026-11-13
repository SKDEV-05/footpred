---
name: ML Engineering
description: Build responsible football ML practices — feature engineering, temporal validation, leakage prevention, calibration, proper scoring rules, versioning, reproducibility, and monitoring. Use for any model design, training plan, or evaluation protocol.
---

# ML Engineering

## Objective

Make models reproducible, honestly evaluated, and safe to deploy. The hard part is not
fitting a model; it is proving it generalises to matches it has never seen.

## Activation

Use for feature design, training/validation design, model selection, calibration, evaluation,
versioning, or monitoring. Mandatory before any claim that a model "works".

## Required context

- Prediction target and market.
- Data availability timestamps per feature.
- Evaluation population and period.
- Baseline to beat.
- Compute and operational constraints (mark `TBD` if unknown).

## Workflow

1. **Define the target and the decision** the prediction supports.
2. **Specify the evaluation protocol** before modelling: period, splits, metrics, baselines.
3. **Build features** with an explicit "available at" timestamp relative to kickoff.
4. **Split temporally**: train on the past, validate on the future, walk forward.
5. **Fit a simple baseline first** (base rates, home/away averages, Elo, Poisson).
6. **Add complexity only if it beats the baseline out-of-sample.**
7. **Calibrate** on held-out data; verify calibration per market and per competition.
8. **Stress-test**: different seasons, competitions, sample sizes, missing-data regimes.
9. **Version everything**: data snapshot, features, code, hyperparameters, model artefact.
10. **Document limitations and abstention rules.**

## Detailed procedures

### Temporal validation

- Football data is time-ordered and non-stationary. Random splits leak future information and
  inflate performance.
- Use rolling-origin (walk-forward) evaluation: train up to time t, predict t+1, advance.
- Keep a final holdout period untouched until the protocol is frozen.
- Ensure the same fixture never appears in both train and validation.
- Include a "cold start" test: newly promoted teams, new competitions, missing history.

### Leakage catalogue

| Leak | Example | Prevention |
| --- | --- | --- |
| Future aggregates | Season-long xG used to predict matches mid-season | Point-in-time features |
| Target leakage | Post-match shots or result-derived features | Feature availability audit |
| Preprocessing leak | Scaling/imputation fitted on all data | Fit on train fold only |
| Calibration leak | Calibrator fitted on training predictions | Calibrate on held-out fold |
| Selection leak | Choosing features after seeing holdout results | Freeze protocol first |
| Entity leak | Same team-season statistics shared across splits | Split by match time, not row |
| Label leak | Postponed match replaced after seeing outcome | Immutable prediction records |

### Feature engineering rules

- Every feature has: definition, source, computation window, availability time, missing-value
  policy, and owner.
- Prefer ratios and rates over raw counts where exposure differs (matches played, minutes).
- Encode home/away/neutral explicitly; do not let a single "home" boolean absorb neutral
  venues.
- Use shrinkage for small samples.
- Avoid features that encode the outcome or are only known after the match.
- Keep the feature set small enough to audit; a hundred opaque features is a liability.

### Baselines

Always report:
- global base rate for the market;
- league/competition base rate;
- a simple strength model (e.g. goal averages with home advantage);
- the proposed model.

If the proposed model does not beat the baseline on proper scoring rules with uncertainty
accounted for, do not ship it.

### Metrics

- Brier score and log loss for binary/multiclass probabilities.
- Calibration curves, expected calibration error (with bin-count caveats), and reliability
  diagrams.
- Ranked probability score for ordered outcomes where relevant.
- Accuracy and confusion matrices only as secondary diagnostics.
- Report confidence intervals via bootstrap over matches (respecting time blocks).

### Calibration

- Fit on a held-out temporal fold, never the training set.
- Prefer simple methods with few parameters (Platt scaling) unless data supports isotonic.
- Recalibrate after distribution shifts (new season, rule changes, competition changes).
- Calibration is market-specific and competition-specific; a global calibrator can hide
  failures.

### Model selection and complexity

- Start with Poisson/Dixon-Coles and logistic regression.
- Gradient boosting (XGBoost/LightGBM) can capture non-linearity but needs more data,
  careful regularisation, and explainability work.
- Neural networks are unjustified until simpler models plateau and data volume supports them.
- Ensemble only models that are individually calibrated and add diversity; otherwise it is
  complexity without benefit.

### Reproducibility

- Pin data snapshot (by ID/hash), code version, library versions, random seeds, and
  hyperparameters.
- Store the fitted artefact with its metadata; a prediction must be recomputable.
- Deterministic training where feasible; record nondeterminism otherwise.
- Keep an experiment log: hypothesis, configuration, metrics, decision.

### Monitoring (future)

- Track input distribution drift (goals per match, xG levels, competition mix).
- Track calibration drift on settled predictions.
- Track coverage: how often the model abstains.
- Alert on data-quality regressions before they reach predictions.
- Retrain on a schedule or trigger, with the same frozen evaluation protocol.

## Quality checklist

- [ ] Target, population, and evaluation period are defined.
- [ ] Protocol and metrics were fixed before results were seen.
- [ ] Splits are temporal; no fixture crosses train/validation.
- [ ] Every feature has an availability timestamp before kickoff.
- [ ] Baselines are reported alongside the model.
- [ ] Calibration is fitted out-of-sample and checked.
- [ ] Uncertainty is reported (bootstrap or intervals).
- [ ] Model, data, and code versions are recorded.
- [ ] Abstention conditions are defined.
- [ ] No invented performance numbers.

## Common failure patterns

- Random cross-validation on time-series data.
- Reporting accuracy without base rates.
- Tuning on the holdout set.
- Feature computed from end-of-season aggregates.
- Calibrating on training predictions.
- Adding a complex model without beating a simple baseline.
- Ignoring promoted/relegated teams and league transitions.
- Deploying without a reproducible artefact.

## Expected outputs

- Model specification and feature contract.
- Frozen evaluation protocol with baselines and metrics.
- Leakage audit.
- Calibration plan.
- Reproducibility and versioning requirements.
- Monitoring plan for later phases.

## Sources and references

- `rules/data-rules.md`, `rules/ai-usage-rules.md`
- `docs/architecture/components.md`
- `docs/research/` for model research notes
- Consult primary literature for specific methods (Poisson/Dixon-Coles, Elo, gradient
  boosting, calibration) rather than secondary summaries.

## Limitations

No protocol can prove a model will work in the future. Evaluation is always conditional on the
historical sample, the data source, and the competition mix. This skill does not authorise
training, data access, or dependency installation.
