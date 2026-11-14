# Provider Evaluation for a Global 30-Day Match Window

**Date:** 2026-11-14
**Author:** data-engineer
**Confidence:** medium — primary vendor pages were read and quoted, but no credential exists and no authenticated call was made. Every entitlement claim remains `UNVERIFIED`.
**Decision affected:** Which football data provider and plan to verify first before any Phase 5 procurement, and what evidence a coverage-matrix row requires.

## Question

The product needs, for a rolling 30-day window, **global** fixtures with country and competition, kickoff, status, home/away teams and venue where available; final results plus basic team match statistics for finished matches; and enough history for descriptive form and head-to-head — under a licence that permits **public display**. Which candidate providers can plausibly meet that, which plan should be verified first, and what exactly must be observed before a single row may be written to `docs/data/coverage-matrix.md`?

This is a read-only evaluation. No account was created, no trial started, no terms accepted, no provider endpoint called, and no code changed.

## Context

- **Phase boundary.** Phase 4 is accepted; Phase 5 is **not approved**. `AGENTS.md` §4 forbids live provider calls and integration without explicit developer approval. This report therefore establishes what is *documented*, not what is *entitled*.
- **Existing contract.** `ProviderAdapter` declares `competitions`, `seasons`, `teams`, `fixtures`, `results`, `match_statistics`; `lineups` and `match_events` are modelled as unsupported (`docs/data/provider-integration.md` §2, ADR-0004). DTOs already carry `venue_name`, `attendance`, `ProviderScore` and `ProviderTeamStatistics.metrics` (`apps/backend/app/providers/dto.py`).
- **Existing implementation.** A reference adapter for football-data.org v4 exists and passes tests against documented shapes, but is explicitly **not live-verified** (`docs/data/provider-integration.md` §7).
- **Prior research.** `docs/research/2026-11-13-football-data-org-api.md` established transport, auth, status enums and documented throttling. This note does not re-derive those; it adds commercial, licensing and coverage facts and compares candidates.
- **Coverage matrix is empty by design** (`docs/data/coverage-matrix.md` §1) and may only be filled from observed evidence (§3). Nothing here populates it.
- **Reference facts already known:** no provider account, credential, or licence exists; `PD-002` (provider selection) is open; `LIM-007`/`LIM-008` record that coverage and entitlement are unverified.

## Method

1. Defined the data requirement as entity, field, granularity, history and freshness (above), then turned it into comparison criteria.
2. Read only **official vendor domains** — pricing, coverage, product documentation, terms of service — with the in-app reader; recorded the URL and the access date `2026-11-14` at the point of use.
3. Recorded verbatim quotes where a term is contractual or ambiguous, because a paraphrase of a licence clause is not evidence.
4. Marked every unread, unreachable, or merely implied item `UNVERIFIED` instead of inferring it.
5. Distinguished three different claims that are routinely conflated:
   - **endpoint documented** — a URL and response shape exist in the docs;
   - **field present in a sample** — the docs show the field in an example payload;
   - **entitlement for a competition/season** — an authenticated, paid call returns that data. Only the third supports a coverage row, and it cannot be obtained here.
6. Included the do-nothing option and stated what evidence would reverse the recommendation.

**Access anomaly.** All `api-football.com` and `api-sports.io` documentation URLs returned **HTTP 403** from this environment on 2026-11-14. No primary-source facts about API-Football could be obtained, so that candidate is evaluated as *undocumented here*, not as *poor*. This matches the deferral already recorded in ADR-0004.

## Verified facts

All facts below were read on **2026-11-14** unless stated. Prices and quotas are page snapshots at that moment and must be re-read at decision time.

### football-data.org

| # | Fact | Source (accessed 2026-11-14 unless stated) |
| --- | --- | --- |
| 1 | Published plans: **Free €0** (12 competitions, delayed scores/schedules, 10 calls/min); **Free with Livescores €12** (20/min); **ML Pack Light €29** (12 competitions, live scores, "10 seasons of history", 20/min); **Free + Deep Data €29** (lineups, goals, cards, squads, 30/min); **Standard €49** (30 competitions, 60/min); **Advanced €99** (50 competitions, 100/min); **Pro €199** (100 competitions, 120/min); **Odds Add-On €15** (40 competitions); **Statistic Add-On €15** (corners, free-kicks, goal-kicks, offsides, fouls, ball possession, saves, throw-ins, shots, shots on/off goal, cards). VAT may apply. | <https://www.football-data.org/pricing> — primary |
| 2 | The free tier's competition list is named explicitly: Champions League, Primeira Liga, Premier League, Eredivisie, Bundesliga, Ligue 1, Serie A, La Liga, Championship, Serie A Brazil, Worldcup, European Championships. The coverage table lists roughly 110 competitions, concentrated in Europe and South America plus major world events. | <https://www.football-data.org/coverage> — primary |
| 3 | Documented throttling is **inconsistent across two official pages**: the policies page states "10 requests/minute in the free plan, 30 requests/minute in the Standard plan and 60 requests/minute in all plans above", while the pricing page lists Standard 60, Advanced 100, Pro 120. | <https://docs.football-data.org/general/v4/policies.html> and fact 1 — primary |
| 4 | `null` is an explicitly valid value for an unavailable attribute, and empty lists are valid. Lineups, bookings, substitutions and goals are hidden in match lists unless `X-Unfold-*` headers are set. Date defaults resolve against "now" in UTC. | <https://docs.football-data.org/general/v4/policies.html> — primary |
| 5 | The match resource documents `venue`, `attendance`, `minute`, `injuryTime`, `lastUpdated`, `odds`, `referees`, `goals`, `bookings`, `substitutions`, a `/head2head` subresource, and a per-team `statistics` object whose keys are `corner_kicks`, `free_kicks`, `goal_kicks`, `offsides`, `fouls`, `ball_possession`, `saves`, `throw_ins`, `shots`, `shots_on_goal`, `shots_off_goal`, `yellow_cards`, `yellow_red_cards`, `red_cards`. | <https://docs.football-data.org/general/v4/match.html> — primary |
| 6 | Terms of service (page last updated 1 June 2018): (2.3) the key is tied to a single application and single domain; (7.1) attribution text is prescribed verbatim — "Football data provided by the Football-Data.org API" — in the footer or about section, visibly; (9.1) "After cancellation of the subscription … the Customer is not permitted to reference the football data (incl. match fixtures, results, league tables, player/squad data, top scorers) obtained through the Football-Data API on their own site or service."; (8.1) no warranty of availability or accuracy; (3) fair-use cancellation without notice; (5) no refunds. | <https://www.football-data.org/about> — primary (the `/terms` path returned 404) |

### Sportmonks

| # | Fact | Source (accessed 2026-11-14 unless stated) |
| --- | --- | --- |
| 7 | Published plans: **Starter €29** (any 5 leagues, 2,000 calls/entity/hour); **Growth €99** (30 leagues, 2,500); **Pro €249** (120 leagues, 3,000); **Enterprise** (all 2,200+ leagues, 5,000). Marketing claims "no feature tiers, no add-ons", "Historical data included", and a "From €29 one-time fee" historical add-on for plans where it is not included. | <https://www.sportmonks.com/football-api/> — primary |
| 8 | The same marketing page is **self-contradictory**: it advertises xG and Pressure Index as a paid bundle (€29 reduced to €24/month) while also stating xG is included in every plan. Which is true for which plan is `UNVERIFIED`. | <https://www.sportmonks.com/football-api/> — primary |
| 9 | Documented limits per entity per hour: Free 3,000 (covers **only the Danish Superliga and Scottish Premiership**, no credit card, no expiry), Starter 2,000, Growth 2,500, Pro 3,000, Enterprise 5,000. Limits are per entity, not per endpoint; the hour resets from the first request; breaches return 429 and other entities remain callable. The same page advertises a "14-day free trial of any paid plan, no credit card required upfront". | <https://docs.sportmonks.com/v3/api/rate-limit.md> — primary |
| 10 | Fixtures by date range: `GET https://api.sportmonks.com/v3/football/fixtures/between/{start_date}/{end_date}`, maximum 100-day range, `per_page=50` in the documented example, pagination followed until `has_more` is false, `include=participants` and `filters=fixtureLeagues:501` in the example, with prose confirming includes for scores, statistics, venue, state, league, season, xG, events and lineups. Fixture fields include `league_id`, `season_id`, `venue_id`, `starting_at`, `state_id`, `result_info`, and the page advises retaining specific finished state ids for results. | <https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/fixtures/get-fixtures-by-date-range.md> — primary |
| 11 | Terms of service: reselling the API requires approval; "if you use our data to create something … and start earning money from your creation, everything is fine"; "distribution, transfer, and storage of data provided by our services is allowed, but reselling the product is forbidden"; no 100% accuracy guarantee; "Coverage gaps may exist across certain leagues or competitions"; logos and photos require proof of own IP rights; data is licensed per domain; a trial requires a valid card, which contradicts the rate-limit page's "no credit card required upfront" (fact 9). | <https://www.sportmonks.com/terms-of-service/> — primary |

### TheSportsDB

| # | Fact | Source (accessed 2026-11-14 unless stated) |
| --- | --- | --- |
| 12 | Published plans: **Free $0** (30 req/min, most queries limited); **Single Developer $9/month** (100 req/min, 2-minute livescores, V2 API); **Small Business $20/month** (120 req/min). | <https://www.thesportsdb.com/pricing> — primary |
| 13 | The public free key is `123`; v1 base is `https://www.thesportsdb.com/api/v1/json`, v2 base is `/api/v2/json`; V2 is premium-only and uses an `X-API-KEY` header; documented per-endpoint limits differ sharply by tier (e.g. `eventsday.php` Free 3 / Premium 1,500; `eventsseason.php` Free 15 / Premium 3,000; `all_leagues.php` Free 10 / Premium 3,000); breaches return 429. Event and league fields are documented as string placeholders such as `{idEvent}`, `{strEvent}`, `{strLeague}`, `{strCountry}`, `{strSport}` and `{idLeague}`. OpenAPI specs are published at `/api/spec/v1/openapi.yaml` and `/api/spec/v2/openapi.yaml`. | <https://www.thesportsdb.com/documentation> — primary |
| 14 | Terms of use (last updated 17/09/2026): "You can scrape, copy and modify content returned from the API using the official end points"; the **free** API may not be used to publish apps to an app store unless the developer is a paid subscriber; paid subscribers may build apps and services within the rate limit and "must mention us as the source of the data"; "You cannot resell our API in any way without specific permission"; images carry their own licence and `strCreativeCommons` semantics; a paid subscription does not grant rights to third-party artwork or trademarks. | <https://www.thesportsdb.com/docs_terms_of_use.php> — primary |
| 15 | The site publishes a crowd-sourced contribution workflow — "Contribute Guide", "Apply Editor", "Missing Scores" — so records are editor-maintained rather than scout- or feed-verified. This is a quality attribute to test, not a defect to assume. | <https://www.thesportsdb.com/> (site navigation) — primary |

### API-Football (API-Sports)

| # | Fact | Source (accessed 2026-11-14 unless stated) |
| --- | --- | --- |
| 16 | **No facts could be obtained.** Six documentation and pricing URLs returned **HTTP 403** to this environment on 2026-11-14: `www.api-football.com/pricing`, `www.api-football.com/documentation-v3`, `api-sports.io/documentation/football/v3`, `dashboard.api-football.com`, `www.api-football.com`, `api-sports.io`. Pricing, quota, coverage, statistics, xG, licence, historical depth and reliability are all `UNVERIFIED`. | Attempted 2026-11-14 — no primary source available |

### Sportradar (added candidate)

| # | Fact | Source (accessed 2026-11-14 unless stated) |
| --- | --- | --- |
| 17 | The official soccer overview page (page `updatedAt` 2026-09-17) states "**650+** unique competitions are available in one package", with a public coverage matrix at `coverage-matrix.sportradar.com`; data is collected by on-venue scouts; documented feeds cover schedules, match summaries, lineups, seasonal statistics, missing/injured players, head-to-head, and log/ball-spotting data; extended statistics and push feeds are separate packages; Soccer v4 endpoints include competitions, seasons, daily schedules and summaries, live, sport event summary/lineup, season standings, competitor-vs-competitor and merge mappings. | <https://developer.sportradar.com/soccer/reference/soccer-overview> — primary |
| 18 | Sportradar **pricing, quota, licence and redistribution terms, trial availability** were not read and are `UNVERIFIED`. The commercial model is sales-led, so no price can be inferred from the documentation. | Not fetched — `UNVERIFIED` |

### Provider-neutral

| # | Fact | Source (accessed 2026-11-14 unless stated) |
| --- | --- | --- |
| 19 | No vendor documentation inspected establishes entitlement for a **named competition in a named season on a named plan**. Every one of them describes endpoints, enums, or marketing totals. This is a property of documentation, not a criticism of any vendor. | Facts 1–18 — derived observation |
| 20 | The three vendors with readable terms impose **different** display obligations: football-data.org a fixed sentence (fact 6), Sportmonks per-domain licensing plus a resale prohibition (fact 11), TheSportsDB a source mention on paid tiers (fact 14). None of them grants an unconditional right to display data after the subscription ends. | Facts 6, 11, 14 |

## Analysis

### Capability matrix against identical criteria

`UNV` = `UNVERIFIED`. Cell text is deliberately terse; the fact numbers carry the detail.

| Criterion | football-data.org | Sportmonks | TheSportsDB | Sportradar | API-Football |
| --- | --- | --- | --- | --- | --- |
| Primary docs reachable 2026-11-14 | Yes | Yes | Yes | Yes | **No — 403** (16) |
| Breadth as documented | ~110 competitions, Europe/South America plus world events (2) | 2,200+ marketed; 5/30/120 leagues by plan (7) | Not stated; league catalogue is community-maintained (13, 15) | 650+ competitions in one package (17) | UNV (16) |
| Free/immediate usable entitlement | 12 named competitions (2) | Danish Superliga + Scottish Premiership only (9) | Public key `123`, heavy per-endpoint caps (13) | UNV | UNV |
| Venue per fixture | Documented `venue`, `attendance` (5) | `venue_id` + `venue` include (10) | UNV | Feed list implies match detail; field not checked — UNV | UNV |
| Team match statistics | Documented 14 keys (5) | `statistics` include (10); metric list UNV | UNV | "seasonal statistics" documented; per-match metrics UNV (17) | UNV |
| Historical depth | "10 seasons" advertised on ML Pack Light only (1); per-plan/per-competition UNV | "Historical data included" advertised; per-plan UNV; paid add-on exists (7) | UNV | UNV | UNV |
| Documented rate limit | 10/min free; Standard 30 **or** 60 depending on page (3) | Per-entity hourly: 2,000–5,000 paid, 3,000 free (7, 9) | 30/min free, 100–120/min paid (12, 13) | UNV | UNV |
| Documented price | €0–€199 + €15 add-ons (1) | €29–€249 + Enterprise (7) | $0–$20 (12) | UNV (18) | UNV |
| Public display permitted | Conditional: permitted while subscribed, **prohibited after cancellation** (6) | Conditional: storage/distribution and monetised derivatives allowed, resale forbidden, per-domain (11) | Conditional: paid tier may ship apps/services with a source mention; free tier may not ship to app stores (14) | UNV | UNV |
| Attribution obligation | Fixed sentence, footer/about, visible (6) | Source mention implied by paid terms; exact wording UNV (11) | "must mention us as the source of the data" (14) | UNV | UNV |
| Stable identity model | Integer competition/team/match ids, `tla` codes (5; 2026-11-13 note) | `league_id`/`season_id`/`venue_id` integer ids (10) | String ids (`idEvent`, `idLeague`) and free-text names (13) | Documented "merge mappings" endpoint suggests id reconciliation is a known problem (17) | UNV |
| Missing-data semantics documented | Yes — `null` explicitly valid (4) | UNV | UNV | UNV | UNV |
| Integration effort vs `ProviderAdapter` | **Lowest** — adapter exists, all six capabilities declared | Medium — includes-based expansion, per-entity rate buckets, new auth | Medium–high — string-typed fields, no country/competition guarantee per event, community data | High — new vendor schema, likely XML/JSON variant, sales-led access | Unknown |
| Exit / portability risk | **High** — §9.1 bars continued display after cancellation (6) | Medium — storage allowed, but post-termination display UNV (11) | Low–medium — copying/modifying allowed, resale restricted (14) | UNV | UNV |
| Fit to "global 30-day window" | **Fails as documented** — not global (2) | Plausible at Growth/Pro/Enterprise; league list per plan UNV (7) | Unproven; no breadth claim (12) | **Best documented reach** (17) | Unknown |

### What the matrix actually says

1. **The requirement and the cheapest verification pull in opposite directions.** football-data.org is the only candidate with an implemented adapter, explicit null semantics, documented venue and statistics fields, and a readable, quotable licence — but its own coverage page shows it is **not global**. Verifying it proves the pipeline end to end; it does not prove the product requirement. This distinction must be stated in the ADR rather than buried.
2. **Sportmonks is the best-documented path to breadth at a low entry price.** Its docs are reachable, the date-range endpoint fits a 30-day window in one call (100-day maximum range, 50 fixtures per page in the documented example), venue/statistics/participants are documented includes, and per-entity hourly limits are generous for a daily sync. Two blockers are open: the xG/plan contradiction (8) and per-plan league entitlement (7).
3. **TheSportsDB is cheap and permissive but structurally weak for this product.** String identifiers, free-text team and league names, community editing, and per-endpoint caps that are extremely low on the free tier make entity resolution and re-runnability harder, which is exactly where `apps/backend/app/ingestion/identity.py` refuses to guess. It is a candidate for a *secondary* cross-check, not a primary feed.
4. **Sportradar is the only candidate whose documentation supports "global" at the required breadth**, but it is sales-led with no published price, and its licence terms were not read. Evaluating it requires a commercial conversation the developer has not authorised.
5. **API-Football cannot be evaluated at all here.** It is deferred, not rejected. Nothing in this report should be read as a judgement on its quality.
6. **Licence is the real differentiator, not price.** At €29–€64/month the cost differences are trivial next to the risk of building a product on data that may not be displayed after cancellation (fact 6, clause 9.1), or on a feed whose per-domain licence does not cover the intended surface (fact 11).
7. **Do nothing is a legitimate option.** The coverage matrix stays empty, no money is spent, and the Phase 4 offline work continues. It is the correct choice while Phase 5 is unapproved and no budget owner exists.

### Cost shape of a bounded verification (estimated, not a quote)

A 30-day spike on football-data.org Standard + Statistic Add-On is approximately **€64/month, excluding VAT**, at the snapshot prices in fact 1 (the pricing page says VAT may apply). This is a *derived arithmetic claim from a dated price page*, not a quote, and it excludes any plan change needed for competitions outside the 30-competition allowance. No other candidate has a price that can be totalled without a sales conversation.

## Recommendation

**Verify football-data.org Standard (€49/month) plus the Statistic Add-On (€15/month) first — as a bounded, ~30-day evidence spike, explicitly not as the global feed.**

Rationale: it is the only candidate where a real authenticated call can exercise the **existing** adapter end to end, settle the licence question with a concrete subscription, and produce the first legitimate coverage-matrix rows at the lowest total cost. It also forces the §9.1 question into the open before any product surface depends on the data.

The recommendation is **conditional** on all of the following:

1. The developer approves the spend, the account, and contact with the vendor. Without that approval this recommendation lapses to *do nothing*.
2. `security-reviewer` and the developer review clause **9.1** (continued display after cancellation) and clause **2.3** (one key, one domain) *before* data enters any environment. If 9.1 is unacceptable and cannot be negotiated, football-data.org is disqualified regardless of adapter convenience.
3. The actual rate limit for Standard is confirmed **in writing**, because two official pages disagree (30 vs 60 per minute, fact 3). Design the client for the lower number until confirmed.
4. The target competitions are checked against the coverage table *and* the 30-competition plan allowance, since the plan counts competitions, not countries.
5. Whether the Statistic Add-On is required per competition, and how many competitions it covers, is confirmed. This is `UNVERIFIED`.
6. No row is written to `docs/data/coverage-matrix.md` until every item in §3 of that file exists.

**What would change this recommendation:**

- If the developer confirms the first release must include competitions outside football-data.org's ~110, then football-data.org cannot be the primary feed and the first verification should move to **Sportmonks Growth (€99/month, 30 leagues)** — after the xG/plan contradiction (fact 8) and the per-plan league list are resolved in writing.
- If a genuinely global feed is a hard requirement at launch, **Sportradar** is the candidate to qualify first, which requires a sales conversation the developer must authorise.
- If clause 9.1 is rejected outright, skip football-data.org and verify Sportmonks.
- If no budget is approved, do nothing and keep the matrix empty.

**Shortlist for the next decision:** football-data.org (baseline + adapter), Sportmonks (breadth at low entry price), Sportradar (documented global reach, sales-led). TheSportsDB is retained only as a possible cross-check source. API-Football remains deferred pending documentation access.

### Live-verification steps that would produce a coverage-matrix row

These are the exact observations required by `docs/data/coverage-matrix.md` §3. They are written to be executable once — and only once — the developer approves a credential. **None has been performed.**

**Preconditions**

- Credential stored in the environment, never committed; `PROVIDER_REQUESTS_PER_MINUTE` set to the *lower* of the two documented limits.
- `RAW_STORAGE_DIR` writable; archive and quarantine paths confirmed.
- The plan name recorded exactly as invoiced, because entitlement is a plan property.

**Step 1 — `check-provider` credential and plan check (satisfies §3.1)**

- Call `GET /v4/competitions` once with the token.
- Record: UTC timestamp, provider, invoiced plan name, API base version, HTTP status, archive row id, response SHA-256, and the returned competition count.
- A 200 proves the credential works *at that moment*. It proves nothing about any specific competition.

**Step 2 — entitlement per target competition**

- For each competition in the 30-day window: `GET /v4/competitions/{code}`.
- Record `seasons[]`, `currentSeason`, and HTTP status. A 403 or 404 is recorded as **"not entitled"**, never as "no data".

**Step 3 — fixtures in the window (satisfies §3.3 count 1)**

- `GET /v4/matches?dateFrom=<today>&dateTo=<today+30>` and, per competition, `GET /v4/competitions/{code}/matches?dateFrom=…&dateTo=…`.
- Record matches returned per competition and per day; whether `area` (country) and `competition` are populated on every match; whether `venue` and `attendance` are non-null.

**Step 4 — results (satisfies §3.3 count 3)**

- Same window filtered to `status=FINISHED`, plus one completed past matchday per competition.
- Record finished matches with non-null `score.fullTime.home/away` and with a non-null `winner`.

**Step 5 — statistics (satisfies §3.3 count 4 and §4)**

- Fetch `GET /v4/matches/{id}` for a spread sample — at least 20 finished matches across competitions and matchdays, not 20 from one round.
- Per match and per team, record which of the 14 documented keys (fact 5) are **present**, **explicitly null**, **absent**, or **zero**. The zero column is mandatory per §4: a provider that always returns non-zero may be reporting a gap as zero, and one sample cannot distinguish that.

**Step 6 — run the real sync (satisfies §3.2 and §3.3 count 2)**

- Run the ingestion sync for one competition and the window against the existing pipeline.
- Record run id, fixtures stored, rows quarantined, and matches stored without statistics.
- **Idempotency check:** run the identical sync twice; the stored state must be identical and the second run must create no duplicates. A difference is a defect report, not a coverage note.

**Step 7 — compare against the provider's own page (satisfies §3.4)**

- Open the provider's competition/season page, record the URL and access date, and compare its matchday/fixture count to Steps 3–4.
- Record every discrepancy; do not adjust the provider's number to match the API.

**Step 8 — state the negative (satisfies §3.5)**

- Write explicitly what was **not** observed, e.g. "no statistics returned for matchdays 1–3", "no venue for cup fixtures", "competition X returned 0 fixtures despite being listed as covered".

**Step 9 — temporal coverage (§5), bounded**

- Probe three seasons only: the earliest season the plan claims, one middle season, and the current season. Record the earliest season with fixtures, with results, and with statistics. Do not extrapolate a depth curve from three points; state it as three observations.

**Evidence artefacts to retain**

- Archive id, SHA-256 and fetch timestamp for every call (already produced by the pipeline).
- The counts table from Steps 3–6 and the idempotency diff.
- URL + access date of the vendor page used in Step 7.
- **Not** the licensed payload itself in git — the archive reference and hash are the evidence; committing provider data raises a licensing question (fact 6, 11, 14) and is out of scope.

Until all nine steps exist, `docs/data/coverage-matrix.md` stays exactly as it is. This report does not modify it.

## Assumptions

- **A1.** The 30-day upcoming window and "basic statistics" are the Phase 5 requirement. If the product also needs lineups, events or injuries at launch, every candidate's fit changes and this comparison is incomplete.
- **A2.** "Global" means competitions on multiple continents, not merely "many European leagues". If Europe-first is acceptable for the first release, football-data.org's coverage gap shrinks materially.
- **A3.** €29–€249/month is within a plausible evaluation budget. The budget is not approved and not known.
- **A4.** The football-data.org `/about` page is the operative terms text; `/terms` returned 404, so a newer version may exist elsewhere. Unverified.
- **A5.** The 403 responses from API-Football reflect this environment (network or bot protection), not a general inaccessibility. Unverified.
- **A6.** Dated marketing claims (2,200+ leagues, 650+ competitions, 99.99% uptime) are vendor self-descriptions, not measured facts.
- **A7.** TheSportsDB's `strCreativeCommons` semantics apply to images, not to fixture text. Unverified.

## Open questions

| # | Question | Owner | Resolution path |
| --- | --- | --- | --- |
| Q1 | Is clause 9.1 (no display of data after cancellation) acceptable, or must it be negotiated? | developer + `security-reviewer` | Read the contract at purchase; request written confirmation of post-termination rights before any data enters production |
| Q2 | Which competitions must the first release cover? This decides whether football-data.org is viable at all. | developer / `product-architect` | Written competition list, then compare to the coverage table (fact 2) |
| Q3 | What is the actual per-minute limit on Standard — 30 or 60? | data-engineer | Written vendor confirmation; design for the lower until then (fact 3) |
| Q4 | Does the Statistic Add-On cover every competition in the plan, and is it required per competition? | data-engineer | Vendor confirmation; then Step 5 of the spike |
| Q5 | Is xG included in Sportmonks plans or sold as an add-on? | data-engineer | Written vendor clarification (fact 8) |
| Q6 | Which leagues does each Sportmonks tier actually include, and is "historical data included" true on Starter? | data-engineer | Request the per-plan league list and history statement in writing |
| Q7 | Is Sportradar's licence compatible with public display of derived statistics, and what does it cost? | developer + `security-reviewer` | Sales conversation, only after developer approval |
| Q8 | Is API-Football documentation accessible from another network, and is it worth a second attempt? | orchestrator | Retry from a different egress, or ask the vendor for documentation by email |
| Q9 | What is the data budget, and who approves it? | developer | Decision, not research |
| Q10 | Is public attribution acceptable in the product presentation? | `ux-designer` + developer | Review the fixed sentence (fact 6) and the source mention (fact 14) against the intended UI |

## Sources

- football-data.org — pricing — <https://www.football-data.org/pricing> — accessed 2026-11-14 — primary
- football-data.org — coverage — <https://www.football-data.org/coverage> — accessed 2026-11-14 — primary
- football-data.org — API policies (null semantics, unfolding, throttling) — <https://docs.football-data.org/general/v4/policies.html> — accessed 2026-11-14 — primary
- football-data.org — match resource — <https://docs.football-data.org/general/v4/match.html> — accessed 2026-11-14 — primary
- football-data.org — terms of service and attribution — <https://www.football-data.org/about> — accessed 2026-11-14 — primary
- Sportmonks — football API product and pricing — <https://www.sportmonks.com/football-api/> — accessed 2026-11-14 — primary
- Sportmonks — rate limits — <https://docs.sportmonks.com/v3/api/rate-limit.md> — accessed 2026-11-14 — primary
- Sportmonks — fixtures by date range — <https://docs.sportmonks.com/v3/endpoints-and-entities/endpoints/fixtures/get-fixtures-by-date-range.md> — accessed 2026-11-14 — primary
- Sportmonks — terms of service — <https://www.sportmonks.com/terms-of-service/> — accessed 2026-11-14 — primary
- TheSportsDB — pricing — <https://www.thesportsdb.com/pricing> — accessed 2026-11-14 — primary
- TheSportsDB — documentation and OpenAPI specs — <https://www.thesportsdb.com/documentation> — accessed 2026-11-14 — primary
- TheSportsDB — terms of use — <https://www.thesportsdb.com/docs_terms_of_use.php> — accessed 2026-11-14 — primary
- Sportradar — soccer API overview — <https://developer.sportradar.com/soccer/reference/soccer-overview> — accessed 2026-11-14 — primary
- Sportradar — coverage matrix — <https://coverage-matrix.sportradar.com/> — referenced by the overview, not independently read — primary (unread)
- API-Football / API-Sports — six documentation and pricing URLs — attempted 2026-11-14 — **HTTP 403, no content retrieved**

Internal references: `docs/data/provider-integration.md`, `docs/data/coverage-matrix.md`, `docs/data/providers-research.md`, `docs/decisions/ADR-0004-provider-abstraction.md`, `docs/research/2026-11-13-football-data-org-api.md`, `apps/backend/app/providers/dto.py`, `apps/backend/app/ingestion/identity.py`.

## Limitations

- **No entitlement is verified.** Not one competition, season, statistic or venue field has been observed from an authenticated response. The matrix is a comparison of *documentation*, and documentation describes what an endpoint can return, not what a specific plan will return.
- **No live behaviour was observed.** Latency, correction propagation, missing-as-null-versus-missing-as-zero, duplicate fixtures across competitions, and behaviour under 429 are all `UNVERIFIED` for every provider.
- **Prices, quotas and plan names are a single-day snapshot.** Vendor pages change without notice; every figure must be re-read on the day of purchase.
- **The licence reading is not legal advice.** Clauses 6, 11 and 14 were quoted from published pages; interpretation of "public display", "derived statistics" and "resale" needs `security-reviewer` and, if the product is commercial, a lawyer.
- **One candidate is invisible.** API-Football could not be read at all, so its absence from the comparison is an access failure, not a finding.
- **Coverage breadth is vendor-asserted.** "2,200+ leagues" and "650+ competitions" are marketing totals; neither was checked against a named competition and season, and a total says nothing about depth, completeness or statistics per match.
- **This report is not linked from `providers-research.md` or ADR-0004 yet.** Linking is required by `docs/research/README.md`, but this task was scoped to a single file; the link should be added in a follow-up change with approval.
- **No row added to `docs/data/coverage-matrix.md`** and none should be added until the nine verification steps exist and pass.
