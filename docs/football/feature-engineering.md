# Feature Engineering

**Status:** Deterministic feature construction implemented; predictive usefulness unvalidated.

## Registry

Feature definitions have a name, version, unit, description, and missing-value policy.
Implemented version-2 features are:

- listed home and away team target-venue points per match;
- listed home and away team target-venue goals for per match;
- listed home and away team target-venue goals against per match;
- listed home-minus-away venue points difference;
- competition non-neutral listed-home and listed-away goal rates.

Version 2 renamed the home/away features to "listed" and "target-venue" so a neutral fixture
cannot be labelled as a true home or away sample.

Each value records `calculated_at`, `cutoff_utc`, `available_at_utc`, the half-open source
window, venue, source match IDs, the research context, and either a numeric value or a
missing reason with an explicit state (`observed`, `missing`, `imputed`,
`not_applicable`). Missing values are never replaced with zero, and a feature whose evidence
was not available strictly before the cutoff is rejected at construction.

## Point-in-time behavior

The feature builder receives summaries already filtered by both kickoff and observation
time. The dataset digest identifies the exact synthetic input. Reordering identical input
matches does not change the digest or result.

## Classification

These are descriptive features. They have not been shown to predict match outcomes. There
is no scaling, imputation, opponent adjustment, shrinkage, xG input, or fitted coefficient.
Any such transformation requires a frozen real-data protocol and Phase 5 approval.
