# Football Domain Model

## Purpose

Defines the football concepts the platform must represent correctly before any data model or model is built. It is conceptual: entity names and identifiers are proposals, not a schema. Implementation detail belongs to the data model design.

## Core entities

| Entity | Key identifiers | Key relationships |
| --- | --- | --- |
| Competition | Internal `competition_id`; name, country or confederation, type (league/cup), tier | Has many seasons; owns format rules that may change by season |
| Season | Internal `season_id`; `competition_id`, label, start and end dates | Contains stages; scopes standings, fixtures and squad registrations |
| Stage / round | Internal `stage_id`; `season_id`, name, format, leg number | Groups fixtures; defines whether ties are single-match or two-legged |
| Team | Internal `team_id`; canonical name, country, alias set | Participates in seasons; home/away side of fixtures; has venue history |
| Venue | Internal `venue_id`; name, city, country; optional capacity and surface | Hosts fixtures; may be neutral for finals or temporary relocations |
| Fixture | Internal `fixture_id`; `season_id`, `stage_id`, `home_team_id`, `away_team_id`, `venue_id`, kickoff UTC, status | Produces one result and many events; subject to postponement and rescheduling |
| Result | `fixture_id`; regulation, half-time, extra-time and penalty scores stored separately | Belongs to exactly one fixture; versioned on correction |
| Match event | Internal `event_id`; `fixture_id`, team, player (nullable), type, period, minute, added time | Belongs to a fixture; ordered by period and minute |
| Lineup | `fixture_id`, `team_id`, `player_id`, role, start and end period | Links players to a fixture; distinguishes starters, substitutes, unused |
| Player | Internal `player_id`; name, date of birth where available | Appears in lineups and events; team affiliation is time-bound |
| Standings | `season_id` or `stage_id`, `team_id`, `as_of` timestamp, tie-break keys | Snapshot of league position; not reconstructible from a final table alone |

Rules for identity: internal IDs are the only stable keys. Provider IDs and display names are mapped in a separate cross-reference with provenance. A display name is never a join key.

## Match structure and phases

| Phase | Content | Modelling consequence |
| --- | --- | --- |
| Regulation | Two halves of 45 minutes plus stoppage time | Base period for 1X2, double chance, total goals, BTTS and correct score |
| Half-time | Score and events after the first half | Required for first-half markets; must be stored separately, not derived by halving |
| Extra time | Two additional periods in competitions whose rules require a winner | Must be excluded from 90-minute markets; changes goal and result distributions |
| Penalty shootout | Post-match tie-break | Decides progression, not match result for most markets; not a stable skill signal |

A fixture may also be abandoned, awarded, or replayed. Each state needs an explicit representation; encoding it as a normal result corrupts historical aggregates. Two-legged ties add an aggregate score that is not a match result and must be derived, not stored as one.

## Competition context

- **League:** round-robin format, points, draws, promotion and relegation. Standings and match importance depend on season phase.
- **Cup:** knockout format, single or two-legged ties, possible neutral final. The away-goals rule and extra-time rules vary by competition and era; they must be stored per competition and season rather than assumed. Some competitions have abolished rules that older seasons used.
- **Fixture congestion:** short rest between matches, travel, and continental commitments affect rotation and performance. Rest days must be computed from actual kickoff times, not nominal dates.
- **International breaks:** league pauses and player travel create discontinuity in form and squad availability.
- **Incentives:** teams already qualified, already relegated, or chasing a tie may play differently. This is context, not a deterministic adjustment.

## Home advantage

Home advantage is the systematic difference in performance between playing at home and away. Contributors include travel, crowd support, familiarity with the venue and pitch, and referee effects whose magnitude is debated (UNVERIFIED). It is not a universal constant: it differs by league, team, competition, season and era, and can change when crowds are restricted or venues are neutral. A single global multiplier is therefore unsafe. Models should estimate a competition baseline plus team-specific deviations, shrink small samples toward the baseline, and allow the effect to vary over time.

## Form and momentum

"Form" is a summary of recent results or performances. It has no single definition, so every use must state the window (last N matches, time-decayed weights, venue-specific) and the adjustment for opponent strength. Short windows are noisy and regress toward the mean; a run of results is weak evidence of a persistent change. Form is descriptive unless a model demonstrates out-of-sample predictive value. Manager changes, squad turnover and schedule difficulty can explain apparent momentum without any underlying change.

## Squad availability and travel

Availability covers injuries, suspensions, registration eligibility, new signings, rotation and manager changes. Data is often incomplete, delayed or unofficial. Travel covers distance, time zones, altitude and recovery time. Neither should be imputed as "fully available" or "no effect"; the platform should expose missing or stale information and reduce confidence accordingly.

## Data limitations

| Limitation | Effect | Required handling |
| --- | --- | --- |
| Missing lineups | Cannot assess availability or player-level context | Mark as missing; do not infer a default XI |
| Ambiguous team names | Joins attach records to the wrong team | Alias mapping with review; quarantine unresolved records |
| Postponed or rescheduled fixtures | Kickoff time and matchweek become wrong | Status history with timestamps; recompute rest days |
| Abandoned or awarded matches | Score may not represent played football | Separate status; exclude from performance aggregates by policy |
| Incorrect kickoff times | Leakage risk in pre-match prediction records | Store source time and correction history |
| Missing half-time scores | First-half markets unsupported | Treat as unavailable, not zero |
| Provider corrections | Historical values change silently | Version records; retain superseded values |
| Competition format changes | Historical comparison across seasons is invalid | Store format and rules per season |

## Descriptive vs predictive information

Descriptive information summarises what happened: goals, shots, standings, observed xG. Predictive information estimates what is likely to happen next. A descriptive metric can be a predictive input, but the two claims must be labelled separately. "Team A has scored in eight consecutive matches" is descriptive; "Team A has a high probability of scoring" is predictive and requires a model, a baseline and evaluation. The platform must never present the first as if it were the second.

## Glossary

| Term | Meaning |
| --- | --- |
| 1X2 | Match result market: home win, draw, away win |
| BTTS | Both teams to score |
| Clean sheet | A team concedes zero goals in a match |
| CS | Correct score |
| DC | Double chance: two of the three 1X2 outcomes combined |
| Fixture | A scheduled match between two teams in a competition |
| O/U | Over/under total goals against a stated line |
| PPDA | Passes allowed per defensive action; a pressing proxy |
| PSO | Penalty shootout |
| Strength of schedule | Difficulty of opponents faced, used to adjust raw performance |
| xG | Expected goals: model estimate of chance quality |
| xGA | Expected goals against |
| xGD | Expected goal difference |

## Related documents

- [Prediction markets](../football/prediction-markets.md)
- [Performance metrics](../football/performance-metrics.md)
- [Requirements](../product/requirements.md)
- [Vision](../product/vision.md)
