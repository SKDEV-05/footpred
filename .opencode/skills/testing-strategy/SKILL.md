---
name: Testing Strategy
description: Define unit, integration, contract, data-quality, regression, backtest, and reproducibility tests, including edge cases and failure scenarios. Use when planning verification or judging whether work is actually done.
---

# Testing Strategy

## Objective

Demonstrate correctness with tests that could fail for a meaningful reason. Coverage numbers
are not evidence; assertions about behaviour are.

## Activation

Use when defining acceptance criteria, planning a test suite, reviewing a change, or
investigating a defect. Mandatory before any claim that a component works.

## Required context

- The requirement or contract being verified.
- Inputs, outputs, and error semantics.
- Data dependencies and their variability.
- The cost of a false positive (wrong prediction) versus a false negative (missed detection).

## Workflow

1. **State the claim** to verify, in falsifiable terms.
2. **Choose the lowest test level** that can detect the failure.
3. **Define fixtures**: normal, boundary, empty, null, duplicated, out-of-order, adversarial.
4. **Define expected behaviour**, including errors and abstention.
5. **Freeze pass/fail criteria** before running.
6. **Automate** where repeatable; document manual checks otherwise.
7. **Record what is not covered** and why.

## Detailed procedures

### Test levels

| Level | Scope | Examples |
| --- | --- | --- |
| Unit | Pure functions, small modules | Scoreline matrix sums to 1; Poisson probabilities; Elo update |
| Property-based | Invariants over generated inputs | Probabilities in [0,1]; market probabilities sum correctly |
| Integration | Module + database/queue | Ingestion writes raw then normalized records |
| Contract | Provider/API boundaries | Payload schema, error codes, pagination |
| Data quality | Dataset rules | No duplicate fixtures; goals ≥ 0; referential integrity |
| Regression | Previously fixed defects | Exact reproduction of a past bug |
| End-to-end | Full pipeline | Fixture in, timestamped prediction out, evaluated after result |
| Backtest | Model over history | Walk-forward evaluation, calibration, baseline comparison |
| Reproducibility | Same inputs, same output | Re-run from stored snapshot yields identical probabilities |
| Non-functional | Performance, resilience | Timeout handling, rate-limit backoff, load behaviour |

### Test design rules

- One behaviour per test; a descriptive name states the expected outcome.
- Assert values, not just that no exception occurred.
- Avoid over-mocking: mock at trust boundaries, not internal logic.
- Deterministic tests: fixed seeds, fixed clocks, fixed timezones (UTC), no network.
- Use golden files for complex outputs, with a reviewable update process.
- Test error paths as carefully as success paths.

### Football-specific edge cases

- Kickoff at midnight UTC and across DST transitions.
- Postponed, abandoned, replayed, and awarded (walkover) matches.
- Neutral venue and behind-closed-doors matches.
- Extra time and penalties not contaminating regulation markets.
- Missing lineups, late lineup changes, and unconfirmed availability.
- Newly promoted teams with no top-flight history.
- Duplicate fixtures from re-delivery.
- Corrected results arriving after a prediction was stored.
- Extreme but valid scorelines and very small samples.
- Multiple competitions sharing team names.

### Backtesting validity

- Strict temporal split; no future data in features.
- Frozen protocol and metrics before execution.
- Report baselines and confidence intervals.
- Include a holdout period not used for any tuning.
- Test abstention behaviour on insufficient data.
- Verify that stored predictions are the ones evaluated (no retroactive edits).

### Reproducibility checks

- Same data snapshot + same code version + same parameters → identical output.
- Record environment and dependency versions.
- Fail loudly if a required input version is missing.
- Verify that explanation text cannot alter the numeric probability.

### Failure injection

- Provider timeout, 429, malformed JSON, truncated payload, schema change.
- Database unavailable mid-run; duplicate job execution.
- Clock skew and late-arriving corrections.
- Verify that partial runs are visible and recoverable, not silently successful.

## Quality checklist

- [ ] Each requirement maps to at least one verification method.
- [ ] Assertions are meaningful and specific.
- [ ] Edge cases and failure paths are covered.
- [ ] Tests are deterministic and isolated.
- [ ] Temporal leakage is explicitly tested.
- [ ] Backtest metrics include baselines.
- [ ] Reproducibility is tested end to end.
- [ ] Known gaps are documented.
- [ ] Every fixed defect has a regression test.

## Common failure patterns

- Asserting only HTTP 200 or "no exception".
- Testing with the same data used to develop the feature.
- Random splits for time-dependent data.
- Snapshot tests updated blindly.
- Flaky tests retried instead of fixed.
- Mocking so much that the test verifies the mocks.
- Coverage as the primary quality metric.
- No test for missing data or abstention.

## Expected outputs

- Test plan per component with levels and fixtures.
- Acceptance criteria mapped to requirement IDs.
- Failure-scenario matrix.
- Backtest protocol.
- Coverage gap register.

## Sources and references

- `rules/engineering-rules.md`
- `docs/architecture/quality-attributes.md`
- `docs/data/data-quality.md`

## Limitations

Tests verify specified behaviour, not correctness of the specification. A passing suite can
still encode wrong football assumptions. Domain review remains necessary.
