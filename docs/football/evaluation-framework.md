# Offline Evaluation Framework

**Status:** Arithmetic and split mechanics implemented; no historical evaluation executed.

Implemented functions calculate:

- binary Brier score;
- unnormalized multiclass Brier score;
- binary log loss, returning infinity for a confident impossible true outcome;
- fixed-width reliability-bin summaries, preserving empty bins as unavailable;
- rolling-origin train/validation ID folds with observation-time checks.

The framework does not fit preprocessing, calibrators, or models. It does not create a final
holdout, confidence intervals, baselines, segmented reports, or experiment persistence.
These require an approved historical dataset and a frozen protocol.

## Real validation gate

Before any performance claim:

1. verify licensed competition and season coverage;
2. freeze target, population, feature set, baselines, folds, calibration period, final
   holdout, and abstention rules;
3. reconstruct only information available before each kickoff;
4. fit only on each training window;
5. evaluate every eligible stored forecast, including failures;
6. report sample size, abstention coverage, Brier score, log loss, calibration, uncertainty,
   competition/market scope, and model version.

Synthetic scores in tests prove arithmetic only. They are not historical experiments.
