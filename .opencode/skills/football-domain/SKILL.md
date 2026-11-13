---
name: Football Domain Knowledge
description: Apply correct football concepts — competitions, fixtures, team strength, form, goals, xG, home advantage, squad availability, and market definitions — and distinguish descriptive statistics from predictive indicators. Use for any feature, metric, market, or explanation that must be football-sound.
---

# Football Domain Knowledge

## Objective

Prevent models and interfaces from being mathematically tidy but football-wrong. Every
metric must have a precise definition, a context, and a stated limitation.

## Activation

Use when defining features, metrics, prediction markets, match context, team comparison,
form, strength, or explanatory text about football. Mandatory for any claim of the form
"team X is strong/weak/in form".

## Required context

- Competition and season being discussed (rules differ: league, cup, two-legged tie).
- Data availability and granularity (match-level vs event-level).
- The time at which the information would have been available (pre-kickoff).
- Sample size and the window used.

## Workflow

1. **Name the entity precisely**: competition, season, stage, team, fixture, venue.
2. **Define the metric operationally**: numerator, denominator, window, unit, exclusions.
3. **Identify the confounders**: opponent strength, home/away, schedule congestion, squad
   turnover, competition rotation, weather, officiating.
4. **Classify the indicator**: descriptive (what happened) vs potentially predictive (what
   may repeat). Most metrics are descriptive until proven otherwise out-of-sample.
5. **Check sample size** and state the uncertainty.
6. **State what the metric cannot tell you.**
7. **Write it down** in `docs/football/` with the definition and limitations.

## Detailed procedures

### Core entity model

| Entity | Key idea | Common pitfalls |
| --- | --- | --- |
| Competition | League or cup, country/region, tier | Mixing tiers or cup/league rates |
| Season | Time-bounded edition | Cross-season form without adjustment |
| Stage/round | League matchday, cup round, group stage | Treating cup rotation like league intent |
| Team | Club identity | Renamed clubs, reserve teams, merged clubs |
| Fixture | Scheduled match | Postponements, venue changes, neutral grounds |
| Venue | Stadium, home/away/neutral | Neutral venue treated as home |
| Event | Goal, shot, card, substitution | Event definitions differ by provider |
| Lineup | Players available/selected | Late team news, unconfirmed lineups |
| Player | Individual identity | Transfers and duplicate registrations |

### Match structure

- Regulation (90 minutes plus stoppage) is the standard settlement basis for most markets.
- Extra time and penalties are separate phases; never fold them into regulation stats.
- Abandoned, postponed, and replayed matches need an explicit status model.
- Kickoff times change; store UTC plus the local timezone and record the change history.

### Home advantage

Home advantage is real on average but not a universal constant. It varies by league, team,
season, crowd conditions, travel distance, and scheduling. Model it as an estimated
parameter or a team-specific effect; do not hardcode a single multiplier. Neutral venues
must be represented explicitly.

### Form

- Define the window before looking at results (last 5, last 10, weighted by recency).
- Form is descriptive; its predictive value is modest and decays.
- Short windows are dominated by noise and opponent quality. Adjust for opposition or state
  the limitation.
- Promoted/relegated teams break historical baselines; handle league transitions.

### Goals and xG

- Goals are low-count, high-variance events. A 1-0 result carries little information about
  underlying performance.
- xG is the sum of estimated goal probabilities for shots, produced by a provider-specific
  model using location, body part, pressure, and other inputs. It is not ground truth.
- xG and xGA are only comparable within the same provider and model version. Do not mix
  providers in one time series without reconciliation.
- xG does not capture everything (off-ball movement, goalkeeper quality, game state).
- Conversion rate over short windows is noisy; regress it toward a baseline before drawing
  conclusions.

### Strength and opposition

- Team strength is relative to the competition and season.
- Ratings (Elo-style or goal-based) need a defined update rule, home-field term, and
  handling of new teams and resets between seasons.
- Strength of schedule must be considered when comparing raw points or goal difference.
- Cup matches and dead rubbers involve different incentives; rotation is a real confounder.

### Squad availability

Lineups, injuries, suspensions, and rotation materially affect outcomes but are often
unavailable or unconfirmed before kickoff. If a lineup is not confirmed, the system must say
so. Never infer an injury or a lineup from a language model's priors. Without reliable
availability data, the model should reduce confidence or abstain from lineup-dependent
claims.

### Head-to-head

H2H samples are small, often span different squads, managers, and eras, and are frequently
recency-biased. Use H2H as context, not as a primary predictor, and never as proof of a
"bogey team" narrative.

### Descriptive vs predictive

| Kind | Example | Safe use |
| --- | --- | --- |
| Descriptive | Goals scored last 5 matches | Display with window and context |
| Diagnostic | xG difference last 10 | Context for performance, with provider caveat |
| Predictive | Calibrated goal-rate estimate | Model input, evaluated out-of-sample |

Do not relabel a descriptive stat as predictive because it sounds analytical.

## Quality checklist

- [ ] Entity and competition context are explicit.
- [ ] Metric definition includes numerator, denominator, window, and exclusions.
- [ ] Home/away/neutral is handled explicitly.
- [ ] Sample size and uncertainty are stated.
- [ ] Confounders and failure modes are listed.
- [ ] xG provenance (provider/model) is recorded where used.
- [ ] No claim that a pattern guarantees an outcome.
- [ ] No invented statistic, lineup, or injury.

## Common failure patterns

- Comparing raw points across leagues or tiers.
- Treating a five-match run as a stable team rating.
- Using current-season aggregate stats to "predict" earlier matches.
- Mixing xG from different providers.
- Assuming a neutral venue is a home match.
- Presenting H2H as causal.
- Explaining a result with tactics invented after the fact.

## Expected outputs

- Metric or market definitions suitable for `docs/football/`.
- Feature proposals with availability timestamps and limitations.
- Domain review notes on model and UI proposals.
- Clearly labelled illustrative examples (never fake real data).

## Sources and references

- `docs/football/football-domain.md`
- `docs/football/performance-metrics.md`
- `docs/football/prediction-markets.md`
- `rules/data-rules.md`

## Limitations

Football data is incomplete and provider-dependent; many causal questions cannot be answered
from observational match data. This skill provides domain judgement, not proof. Numerical
claims require data and evaluation, not domain intuition alone.
