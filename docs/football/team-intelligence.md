# Team Intelligence

**Status:** Implemented for offline synthetic tests; predictive value is not validated.

## Population

A `HistoricalMatch` is an explicitly regular-duration result with:

- resolved competition, season, and team identities;
- regulation-time full-time goals;
- UTC kickoff and the UTC time at which the result became known;
- explicit neutral-venue state.

Extra time, shootouts, awarded results, incomplete scores, and unknown venue state are not
represented by this Phase 4 contract. Current ORM records are not automatically eligible.

## Form metrics

For the latest `n` eligible observations before `as_of`, from the requested competition and
venue scope:

- wins, draws, losses;
- points under an explicit `PointsPolicy`;
- goals for, goals against, and goal difference;
- points and goals per match;
- scoring, clean-sheet, failed-to-score, BTTS, and over 1.5/2.5/3.5 rates;
- population standard deviation of goals for and against.

Rates divide by eligible match count. When the count is zero, rates and averages are `None`.
Raw counts remain zero because zero observations contributed; they must not be interpreted as
measured team performance.

Venue is one of home, away, neutral, or overall. Neutral matches never enter a home or away
split. Metrics are descriptive, not opponent-strength adjusted, and do not establish future
performance.

## Points

No universal 3/1/0 rule is hidden in the implementation. A caller supplies a versioned
points policy. Synthetic tests use a policy explicitly named
`synthetic-standard-3-1-0`; that is test configuration, not a historical rules claim.

## First-half and provider statistics

The observation contract can validate paired half-time scores and named non-negative metrics,
but Phase 4 does not publish first-half, xG, or provider-statistic aggregates. Provider
semantics and coverage are unverified. Missing xG is never approximated or called official
xG.
