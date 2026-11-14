# Match Intelligence

**Status:** Implemented for offline synthetic tests only.

`IntelligenceEngine.analyze` creates a structured report for a pre-kickoff request. It
contains home and away venue-specific form, competition goal context, H2H context, feature
values, quality assessments, source match IDs, a canonical input digest, and limitations.

## Temporal contract

- `analysis_as_of < target kickoff`;
- historical kickoff is strictly earlier than `analysis_as_of`;
- the exact result must have been observed on or before `analysis_as_of`;
- all times are UTC;
- the target fixture cannot enter its own history.

Adding a future result or a result observed after the cutoff cannot change the report.

## H2H

The unordered team pair identifies meetings; each fixture counts once and historical listed
orientation is normalized to the target home/away team IDs. H2H is context only. It receives
no special predictive weight and cannot justify causal or “bogey team” claims.

## Competition context

The implementation reports historical home, away, and total goal rates and home points per
match for the selected competition. It does not estimate cross-competition strength, account
for stage incentives, or infer neutral venues. Cross-competition pooling is not performed.

## Unsupported context

No squad availability, injury, suspension, lineup, manager, travel, weather, standings,
two-leg state, or tactical claim is produced. Those fields require reliable, timestamped
sources that do not currently exist.
