# Phase 6 Provider Capability Audit

**Date:** 2026-11-15  
**Status:** COMPLETE — bounded read-only verification performed on 2026-11-15  
**Access date for all primary-source claims:** 2026-11-15 unless stated  
**Evidence:** `docs/research/provider-live-verification.md` (live HTTP responses archived) and `docs/research/2026-11-14-provider-evaluation.md` (official documentation pages read on 2026-11-14)

## 1. Purpose and method

This audit records what each provider **actually returned** in a bounded, read-only verification session on 2026-11-15, plus what each vendor's official documentation states. It deliberately separates:

- **Verified** — observed from an actual authenticated HTTP response (archived in `raw_payloads`).
- **Documented** — stated in official vendor documentation pages.
- **UNVERIFIED** — not observed and not confirmed by documentation read in this session.

No claim is inferred from marketing copy, memory, or another site's fixture list. Where a feature is documented but not yet observed live, it is marked UNVERIFIED rather than assumed present.

## 2. Provider A — football-data.org (API v4)

| Item | Value | Status | Source |
| --- | --- | --- | --- |
| Base URL | `https://api.football-data.org/v4` | Verified | `.env`, live call |
| Auth header | `X-Auth-Token` | Verified | `build_http_client` (`http.py:383`) |
| Auth | `GET /v4/competitions` returned `HTTP 200` | **VERIFIED** | live call 2026-11-15 |
| Plan | Free tier (`TIER_ONE` in response filters) | Verified | live call |
| Rate limit | 10 requests/minute | Documented (config `PROVIDER_REQUESTS_PER_MINUTE=10`) | `.env` |
| Max date window | 10 days (both `dateFrom` and `dateTo` required) | **VERIFIED** | live call — HTTP 400 otherwise |
| Competitions visible | 13 | **VERIFIED** | live call |
| Competition codes | BSA, ELC, PL, CL, EC, FL1, BL1, SA, DED, PPL, CLI, PD, WC | **VERIFIED** | live call |
| Upcoming fixtures (10-day window) | 105 matches | **VERIFIED** | live call |
| Historical finished matches (9-day window) | 69 matches, all with FT scores | **VERIFIED** | live call |
| 30-day window support | **NO** — HTTP 400 | **VERIFIED** | live call |
| Statistics availability | Not called | **NOT VERIFIED** | budget conservation |
| Fixture statistics availability | Not called | **NOT VERIFIED** | budget conservation |
| Head-to-head availability | Not called | **NOT VERIFIED** | budget conservation |
| Lineups / events / players | Not called | **NOT VERIFIED** | budget conservation |
| Historical season depth | Not probed beyond 9-day window | **NOT VERIFIED** | budget conservation |
| Public-display licence | UNVERIFIED (clause 9.1 risk documented) | UNVERIFIED | `2026-11-14-provider-evaluation.md` fact 6 |

### What football-data.org returned (verified)

The verified live call returned:
- 13 competitions the free plan serves for this token.
- Upcoming fixtures in a 10-day window: 85 TIMED + 20 SCHEDULED = 105 matches.
- Historical finished fixtures in a 9-day window: 69 matches, all with full-time scores.
- A 30-day window request returned `HTTP 400 "Specified period must not exceed 10 days."` — so every historical backfill must be chunked into ≤10-day requests.
- `dateFrom` without `dateTo` returns `HTTP 400`.

### What is NOT verified for football-data.org

- Whether `/matches/{id}` returns team statistics for finished matches (the statistics endpoint was not called).
- Whether `/competitions/{id}/head2head` or equivalent exists and returns H2H records.
- How many completed seasons are accessible per competition (only the last 9–10 days were queried).
- Whether the Statistic Add-On (documented €15) covers per-match statistics keys on the Free plan.
- Whether historical results go back beyond the current season on the Free plan.

## 3. Provider B — API-Football / API-Sports (api-sports.io v3)

| Item | Value | Status | Source |
| --- | --- | --- | --- |
| Base URL | `https://v3.football.api-sports.io` | Verified | `.env` |
| Auth header | `x-apisports-key` | Documented | official docs |
| Auth | `GET /status` returned `HTTP 200` | **VERIFIED** | live call 2026-11-15 |
| Plan | Free | Verified | live call |
| Quota used today | 8 of 100 requests | **VERIFIED** | live call |
| Quota reset | Daily (Free plan) | Verified | live call |
| Leagues visible | 1,244 (current=true, one page) | **VERIFIED** | live call |
| Historical fixtures (yesterday, FT) | 978 matches with scores | **VERIFIED** | live call |
| Upcoming fixtures (`date=tomorrow`) | 81 matches | **VERIFIED** | live call |
| Upcoming fixtures (`next=30`) | 0 results | **VERIFIED** | live call |
| Upcoming fixtures (`from`/`to` range) | 0 results | **VERIFIED** | live call |
| Per-date query | `?date=YYYY-MM-DD` works | **VERIFIED** | live call |
| Range query support | **NO** — `?from=...&to=...` returns 0 on Free | **VERIFIED** | live call |
| League filter on upcoming | **NO** — `?next=30&league=39` returns 0 | **VERIFIED** | live call |
| Statistics availability | Not called | **NOT VERIFIED** | budget conservation |
| Fixture statistics availability | Not called | **NOT VERIFIED** | budget conservation |
| Head-to-head availability | Not called | **NOT VERIFIED** | budget conservation |
| Lineups / events / players | Not called | **NOT VERIFIED** | budget conservation |
| Historical season depth | Not probed | **NOT VERIFIED** | budget conservation |
| Public-display licence | UNVERIFIED — terms not read in this session | UNVERIFIED | budget conservation |

### What API-Football returned (verified)

- Authentication works (`GET /status` HTTP 200).
- 1,244 leagues are visible on the Free plan (`current=true`).
- Yesterday's finished fixtures returned 978 matches with scores.
- Tomorrow's upcoming fixtures returned 81 matches via per-date query.
- Per-date querying (`?date=`) is the only working retrieval mode on Free.

### Free-plan restrictions (verified)

1. **No date-range query.** `?next=30`, `?next=7`, `?from=...&to=...` all return 0 results. Only `?date=YYYY-MM-DD` returns fixtures.
2. **No league filter on upcoming fixtures.** `?next=30&league=39` returns 0. Upcoming fixtures cannot be scoped to one league/competeition on Free.
3. **Timezone parameter has no effect** on `next=N` (still 0).

These are plan-level restrictions, not adapter defects. A historical backfill on Free requires one request per calendar date.

### What is NOT verified for API-Football

- Whether `/fixtures/statistics` returns team match statistics.
- Whether `/fixtures/head2head` returns H2H records.
- How many completed seasons are accessible per league (only yesterday's date was queried).
- Whether the statistics/H2H endpoints return data on the Free plan or require a paid tier.
- Public-display licence terms.

## 4. Capability matrix against identical criteria

`UNV` = UNVERIFIED (not observed in the bounded live session and not confirmed by documentation read this session).

| Criterion | football-data.org | API-Football |
| --- | --- | --- |
| Authentication verified | Verified (X-Auth-Token, /competitions 200) | Verified (x-apisports-key, /status 200) |
| Competitions/leagues list | 13, verified | 1,244, verified |
| Historical finished fixtures | 69 matches (9-day window), verified | 978 matches (yesterday), verified |
| Upcoming fixtures | 105 matches (10-day window), verified | 81 matches (per-date), verified |
| Date-range query | Yes, ≤10 days, both dates required | **No** on Free — per-date only |
| Window limit | Max 10 days | N/A (per-date only) |
| League filter on upcoming | N/A (competition-scoped path exists) | **No** on Free |
| Team match statistics | **UNV** (not called) | **UNV** (not called) |
| Fixture statistics | **UNV** (not called) | **UNV** (not called) |
| Head-to-head | **UNV** (not called) | **UNV** (not called) |
| Historical season depth | **UNV** (9-day window only) | **UNV** (yesterday only) |
| Lineups / events / players | **UNV** | **UNV** |
| Request budget (Free) | 10 requests/minute | 100 requests/day |
| Public-display licence | UNVERIFIED (clause 9.1 risk) | UNVERIFIED (terms unread) |

## 5. Competition-by-competition coverage matrix

This matrix records **only** what was actually observed. Cells for seasons/statistics/H2H are empty because those capabilities were not verified in the bounded session — they are UNVERIFIED, not "probably fine".

| Competition (internal) | Provider code | Provider | Seasons verified | Fixtures verified | Results verified | Statistics verified | H2H verified | Evidence | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| PL (Premier League) | PL | football-data.org | None | 10-day upcoming window | 9-day finished window | — | — | live call 2026-11-15 | 13 codes returned; per-competition fixture counts not broken out in this session |
| ELC (Championship) | ELC | football-data.org | None | 10-day upcoming window | 9-day finished window | — | — | live call 2026-11-15 | |
| CL (Champions League) | CL | football-data.org | None | 10-day upcoming window | 9-day finished window | — | — | live call 2026-11-15 | |
| FL1 (Ligue 1) | FL1 | football-data.org | None | 10-day upcoming window | 9-day finished window | — | — | live call 2026-11-15 | |
| BL1 (Bundesliga) | BL1 | football-data.org | None | 10-day upcoming window | 9-day finished window | — | — | live call 2026-11-15 | |
| SA (Serie A) | SA | football-data.org | None | 10-day upcoming window | 9-day finished window | — | — | live call 2026-11-15 | |
| PD (La Liga) | PD | football-data.org | None | 10-day upcoming window | 9-day finished window | — | — | live call 2026-11-15 | |
| BSA (Serie A Brazil) | BSA | football-data.org | None | 10-day upcoming window | 9-day finished window | — | — | live call 2026-11-15 | |
| DED (Eredivisie) | DED | football-data.org | None | 10-day upcoming window | 9-day finished window | — | — | live call 2026-11-15 | |
| PPL (Primeira Liga) | PPL | football-data.org | None | 10-day upcoming window | 9-day finished window | — | — | live call 2026-11-15 | |
| CLI (Championship Ireland) | CLI | football-data.org | None | 10-day upcoming window | 9-day finished window | — | — | live call 2026-11-15 | |
| EC (European Championships) | EC | football-data.org | None | No fixtures in window | No results in window | — | — | live call 2026-11-15 | EC had no fixtures inside the synced window |
| WC (World Cup) | WC | football-data.org | None | No fixtures in window | No results in window | — | — | live call 2026-11-15 | WC had no fixtures inside the synced window |
| (all leagues) | — | API-Football | None | Yesterday (978 matches) | Yesterday (978 matches) | — | — | live call 2026-11-15 | Per-date query only; no range query on Free |

**No row claims statistics, H2H, or multi-season depth.** Those cells are blank because they were not verified.

## 6. Request budget analysis

### football-data.org (Free, 10 requests/minute)

The 30-day lookahead window must be chunked into three ≤10-day requests. A single competition's 30-day fixture pull costs ~3 requests. All 13 entitled competitions would cost ~39 requests per full refresh — within the per-minute token bucket but not sustainable for repeated full backfills. A bounded historical backfill of 3–5 completed seasons per competition would require `seasons × competitions × chunks` requests, which quickly exceeds a reasonable Free-plan budget.

**Recommendation:** Current season → previous season → additional seasons only if quota permits. Never attempt unlimited backfill on a 10-requests/minute plan.

### API-Football (Free, 100 requests/day)

Per-date querying means a 30-day backfill costs 30 requests per league, plus one request per day for upcoming fixtures. A full 3–5 season backfill across many leagues would exhaust the daily quota rapidly.

**Recommendation:** Current date window first. Additional seasons only when the daily budget allows. Do not attempt range backfills — they are not supported on Free.

## 7. What is NOT verified (explicit negatives)

The following capabilities were **not** called on either provider (budget conservation, per `provider-live-verification.md` §9):

- Team match statistics (shots, possession, corners, fouls, cards, saves, pass accuracy)
- Fixture-level statistics
- Head-to-head records
- Historical seasons beyond the 9-day / yesterday windows
- Lineups, events, players, injuries, standings
- Public-display licence terms (football-data.org clause 9.1; API-Football Free terms unread)

None of these may be assumed present. The coverage matrix cells for statistics, H2H, and season depth are intentionally empty.

## 8. Decision implications for Phase 6

1. **Statistics collection** — requires calling statistics endpoints not yet verified. A bounded statistics probe is the next gate before any ingestion is planned.
2. **Historical depth** — neither provider's multi-season history was probed. 3–5 completed seasons per competition is the Phase 6 target, but no evidence yet shows it is accessible on either Free plan.
3. **H2H** — not verified on either provider. H2H feature preparation cannot proceed without evidence.
4. **Provider selection** — football-data.org has an existing adapter and verified auth; API-Football has verified auth and broader league visibility but per-date-only retrieval on Free. Neither is selected as the Phase 6 primary feed yet.
5. **Licence** — public-display rights for both providers remain UNVERIFIED and block any production display of provider-derived data (DEC-018, LIM-006).

## 9. Related documents

- `docs/research/provider-live-verification.md` — live HTTP evidence from 2026-11-15
- `docs/research/2026-11-14-provider-evaluation.md` — documentation comparison from 2026-11-14
- `docs/data/coverage-matrix.md` — empty by design; no row may be added until live verification evidence exists
- `docs/decisions/ADR-0004-provider-abstraction.md` — provider abstraction contract
- `docs/decisions/ADR-0008-phase-4-5-entry-gates.md` — Phase 5 entry gates (closed)
- `AGENTS.md` §4 — hard phase boundaries
