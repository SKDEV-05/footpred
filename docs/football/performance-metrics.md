# Performance Metrics

## Purpose

Defines the team and match metrics the platform may use, what each measures, how it misleads, and whether it is descriptive or potentially predictive. Definitions are conceptual; exact numerators, denominators and window defaults belong in the metric specification that accompanies implementation.

## Metric catalogue

| Metric | What it measures | How it can mislead | Data availability | Classification |
| --- | --- | --- | --- | --- |
| Goals for (GF) | Goals scored per match over a stated window | Depends on opponent strength, game state and a few high-variance events; blowouts distort averages | Universal in result data | Descriptive; weak predictor alone |
| Goals against (GA) | Goals conceded per match over a stated window | Conflates defence, goalkeeper, luck and schedule; low-scoring samples are noisy | Universal in result data | Descriptive; weak predictor alone |
| Goal difference (GD) | GF minus GA over a window | Mixes attack and defence; rewards weak schedules and lopsided results | Universal in result data | Descriptive; useful with adjustment |
| Points per game (PPG) | Points divided by matches played | Depends on competition, tier and draw frequency; ignores performance and schedule | Universal in league data | Descriptive |
| Expected goals (xG) | Sum of estimated goal probabilities for a team's shots | Provider- and model-dependent; excludes non-shot chances and ignores game state | Event data; provider coverage varies | Potentially predictive, with caveats |
| Expected goals against (xGA) | Sum of estimated goal probabilities for opponent shots | Same model dependence; reflects shots faced, not all defensive quality | Event data; provider coverage varies | Potentially predictive, with caveats |
| Expected goal difference (xGD) | xG minus xGA | Inherits both models' errors; not comparable across providers or versions | Event data; provider coverage varies | Potentially predictive, with caveats |
| Shots and shots on target | Shot volume and shots on target per match | Volume is not quality; definitions of blocked shots and woodwork differ by provider | Event data, broadly available | Descriptive |
| Conversion rate | Goals divided by shots over a window | Extremely noisy; affected by shot selection, goalkeeper and opposition; regresses strongly | Event and result data | Descriptive |
| Possession | Share of ball possession or passes, depending on definition | Measures style, not control or threat; leading teams often cede possession | Event data, definition varies | Descriptive |
| Pass accuracy | Completed passes divided by attempted passes | Rewards safe, low-risk passing; ignores progression and chance creation | Event data, definition varies | Descriptive |
| PPDA / pressing | Passes allowed per defensive action in a defined zone; lower implies more pressing | Highly definition- and event-coverage-sensitive; affected by game state and opponent style | Event data with defensive actions | Descriptive |
| Set-piece goals | Goals originating from dead-ball situations | Sparse samples; set-piece classification differs by provider; opponent quality matters | Event data, classification varies | Descriptive |
| Cards and discipline | Cards per match or per foul | Referee, competition and game-state effects dominate; weak evidence of a stable team trait | Result and event data | Descriptive |
| Clean-sheet rate | Share of matches with zero goals conceded | Low-count, opponent-dependent, and sensitive to goalkeeper and sample length | Result data | Descriptive |

## Sample size and variance

Goals are low-count events. A short window of matches contains little information, and a single result can move a rate substantially. Metrics computed over five or ten matches should be presented with uncertainty, not as stable team properties. Conversion, clean-sheet and set-piece rates are especially unstable because their denominators are small. Shrinkage toward a competition baseline, or an explicit prior, is preferable to ranking teams on raw short-window rates. Every published metric states its window and sample size; a rate without a denominator is not a metric.

## Strength of schedule and opponent adjustment

Raw totals reward teams that have played weak opponents and penalise teams that have played strong ones. Adjustment requires an opponent-strength estimate, which is itself uncertain and should be versioned. League position is a crude proxy and is affected by the same schedule. Cup rotation, dead rubbers and promoted or relegated teams break historical baselines. Adjusted and unadjusted values should be distinguishable in any output.

## Home and away splits

Home advantage varies by league, team and era, so home and away performance need separate baselines rather than one pooled rate. Splitting also halves the sample for each venue, widening uncertainty. A team's away record over a short window is weak evidence of a durable away weakness. Neutral venues must be represented as a third category, not assigned to home or away.

## Head-to-head limitations

Head-to-head records are small samples, often spanning different squads, managers and eras. Transfers and tactical changes make old meetings weak evidence about the current fixture. Competition context may differ: a cup meeting with rotation is not comparable to a league match. H2H is context, not a primary predictor, and must never be presented as proof of a "bogey team" effect.

## xG model dependence

xG is the output of a provider-specific model using shot location, body part, pressure and other inputs. Two providers can assign different values to the same shot, and a provider's model can change between versions. xG series are therefore comparable only within the same provider and model version; mixing them without reconciliation creates a false continuous history. xG also omits non-shot attacking actions and does not capture goalkeeper quality or game state directly. Any use records provider, model version and coverage. Building an in-house xG model is a separate project requiring event data and validation.

## Composite and derived indicators

Composite indicators combine metrics into a single score. They can be useful for communication but are prone to double counting, arbitrary weights and overfitting to historical results. A composite must state its purpose, components, weights, normalisation and validation. It must not hide its inputs from inspection. Any claimed predictive gain over a simple baseline is evaluated out of sample, not selected because it fits past seasons.

## Recommended metric hygiene

- Name the metric, competition, season, venue split and window.
- State numerator, denominator, unit and exclusions.
- Record the data source, provider version and retrieval date.
- Report sample size and uncertainty alongside the value.
- Label the metric descriptive or predictive; do not promote one to the other without evaluation.
- Keep raw components available for audit; avoid publishing only a composite.
- Version definitions; a silent definition change invalidates comparisons.
- Do not compare across leagues or tiers without an explicit adjustment and caveat.

## Related documents

- [Football domain model](./football-domain.md)
- [Prediction markets](./prediction-markets.md)
- [Requirements](../product/requirements.md)
- [Vision](../product/vision.md)
