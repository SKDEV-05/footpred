# Intelligence Data Reliability

**Status:** Configurable synthetic-test mechanics implemented; real thresholds unvalidated.

## Separate concepts

- **Sample coverage** describes the number of eligible observations.
- **Eligibility** applies an explicit minimum-sample policy.
- **Predictive reliability** would require real out-of-sample evaluation and is unavailable.
- **Probability** is a model output and is not inferred from coverage.

`CoveragePolicy` requires a policy ID and ordered minimum, moderate, and high match counts.
There are no hidden numeric defaults. The returned classes are:

- `insufficient_data`;
- `low_data_coverage`;
- `moderate_data_coverage`;
- `high_data_coverage`.

The current synthetic tests use arbitrary boundary values to verify classification logic.
Those values are not recommendations for real football.

## Missing safeguards before real use

- verified competition/season coverage;
- reconstructable point-in-time result and statistic versions;
- explicit regulation, extra-time, and shootout scores;
- neutral-venue support in stored data;
- provider metric contracts and correction history;
- empirically justified sample and freshness policies.
