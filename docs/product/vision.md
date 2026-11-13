# Product Vision

## Purpose of this document

Defines the intended product, the problem it addresses, and the standard by which progress is judged. It is the reference for scope and prioritisation decisions. It does not specify architecture, data sources, or implementation.

## Vision statement

A football analysis platform that makes the reasoning behind a match assessment inspectable: every probability estimate is traceable to data, a stated method, and an explicit statement of uncertainty, and every estimate is evaluated against what actually happened. The platform is built for people who want to understand a match, not for people who want to be handed a result.

## The problem

- **Fragmentation.** Results, lineups, advanced statistics and competition context live in separate systems with incompatible definitions, coverage and update behaviour. Comparing two teams often means reconciling sources by hand.
- **Unreliable analysis.** Published football analysis frequently mixes description with prediction, ignores sample size, and treats short runs of form as durable signal.
- **Opaque predictions.** Probability claims are commonly presented without method, inputs, uncertainty, or a record of past performance. Users cannot tell a calibrated estimate from a confident guess.
- **No evaluation loop.** Predictions are rarely scored against outcomes in a consistent way, so neither users nor the producers can distinguish improvement from noise.

## Target users

| User | Needs | Explicit non-needs |
| --- | --- | --- |
| Casual analyst | A clear pre-match picture, key statistical drivers, plain-language uncertainty | Betting slips, tip-of-the-day content, live scores |
| Serious fan | Historical context, home/away splits, comparison of teams and seasons | Social feeds, comment sections, push notifications |
| Semi-professional analyst | Reproducible metrics, defined windows, exportable evidence, calibration history | Black-box ratings, vendor-locked dashboards |
| Internal research team | Versioned data, model comparison, evaluation harness, provenance | Presentation polish, growth features |

## What the platform is

A planned, data-first system that discovers fixtures and competitions, stores historical results and match context, computes team and match intelligence, and produces mathematically grounded probability estimates for selected markets. Each output is accompanied by its inputs, method version, uncertainty, and an explanation of the dominant factors. The system abstains when data is insufficient.

## What it is not

Not a live-score service, news publisher, generic chatbot, social network, or guaranteed-tip product. It does not provide betting advice or odds. The full list and rationale are in [non-goals](./non-goals.md).

## Core philosophy

**Data first.** Claims must trace to stored, validated observations. Missing data is a finding, not a gap to fill by assumption.

**Mathematics first.** Probabilities come from explicit models with stated assumptions. Domain reasoning selects and constrains models; it does not replace them.

**Reliability first.** A narrower answer that is well supported is preferred to a broad answer that is not. Abstention is a valid output.

**Prediction quality first.** Models are judged by proper scoring rules and calibration on held-out data, not by illustrative examples.

**UX second.** Interface decisions follow from what the analysis requires the user to understand.

**Visual decoration last.** Charts and styling earn their place only when they reduce misreading.

## Long-term capabilities

Planned, not implemented. Ordering is indicative, not a committed roadmap.

1. Fixture discovery across countries and competitions.
2. Historical results and match statistics.
3. Team performance and match context.
4. Home and away comparison.
5. Attack and defence strength estimation.
6. Statistical pattern identification.
7. Mathematically grounded probability estimates.
8. Comparison of predictions to actual results.
9. Reliability and uncertainty evaluation.
10. Explanations of predictions.
11. Detection of insufficient information.
12. Continuous model evaluation.

## How success will be judged

- **Understanding:** users can identify why an estimate is high or low and what would change it.
- **Calibration:** stated probabilities match observed frequencies within reported uncertainty across enough samples.
- **Transparency:** every estimate exposes its data window, method version, assumptions and known gaps.
- **Abstention quality:** the system declines when evidence is thin, and that behaviour is measured rather than hidden.
- **Discrimination:** models beat stated baselines on proper scoring rules, with gains reported alongside uncertainty.

Accuracy percentages are not a success criterion. No fixed accuracy level is promised. A statistical relationship is never presented as a guaranteed outcome.

## Related documents

- [Requirements](./requirements.md)
- [Scope](./scope.md)
- [Non-goals](./non-goals.md)
- [Football domain](../football/football-domain.md)
- [Prediction markets](../football/prediction-markets.md)
- [Performance metrics](../football/performance-metrics.md)
- Root instructions: `../../AGENTS.md`; project rules: `../../rules/`
