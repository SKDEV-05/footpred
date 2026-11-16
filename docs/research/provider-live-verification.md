# Provider Live Verification — 2026-11-15

**Author:** principal engineer (MASTER PROMPT Phase 4.2)
**Date:** 2026-11-15 (UTC)
**Scope:** Bounded read-only HTTP verification of two providers with rotated credentials.
**Status:** VERIFIED for football-data.org; VERIFIED with limitations for API-Football.

## Evidence principle

Every claim below is backed by an actual HTTP response archived in `raw_payloads`
or observed in this session's bounded verification script output. No claim is inferred
from documentation, marketing copy, or memory. Credentials are never printed.

## Provider A — football-data.org

| Item | Value | Source |
| --- | --- | --- |
| Base URL | `https://api.football-data.org/v4` | `.env` |
| Auth header | `X-Auth-Token` | `build_http_client` (`http.py:383`) |
| Auth status | **VERIFIED** — `GET /v4/competitions` returned `HTTP 200` | live call 2026-11-15 |
| Plan | Free tier (permission field `TIER_ONE` in response filters) | live call |
| Rate limit | 10 requests/minute (config `PROVIDER_REQUESTS_PER_MINUTE=10`) | `.env` |
| Competitions visible | 13 | live call |
| Competition list | BSA, ELC, PL, CL, EC, FL1, BL1, SA, DED, PPL, CLI, PD, WC | live call |
| Upcoming fixtures (10-day window) | **105 matches** (85 TIMED, 20 SCHEDULED) | live call |
| Historical finished (9-day window) | **69 matches**, all with full-time scores | live call |
| 30-day window support | **NO** — `HTTP 400 "Specified period must not exceed 10 days."` | live call |
| `dateFrom` without `dateTo` | **NO** — `HTTP 400 "Argument dateFrom must be used in conjunction with dateTo"` | live call |
| Licence for public display | **UNVERIFIED** — clause 9.1 prohibits display after cancellation (see `2026-11-14-provider-evaluation.md` fact 6) | docs only |

### Diagnosis of the previous HTTP 400 error

The previous session recorded a 400 from football-data.org. Root cause reproduced and
confirmed on 2026-11-15:

1. **30-day window** — the free tier rejects any period over 10 days. The request
   `GET /matches?dateFrom=2026-11-15&dateTo=2026-12-15` returned
   `{"message": "Specified period must not exceed 10 days.", "errorCode": 400}`.
2. **Missing `dateTo`** — `GET /matches?dateFrom=2026-11-15` returned
   `{"message": "Argument dateFrom must be used in conjunction with dateTo and vice versa.", "errorCode": 400}`.

Both are documented in the v4 API contract (`/matches` filters). The fix is to cap
upcoming windows at 10 days per request and always send both `dateFrom` and `dateTo`.

### Fix applied

No code change was required: the existing adapter already sends both `dateFrom` and
`dateTo` (see `fetch_matches` in `adapters/football_data_org.py`). The 400 was a
**caller configuration error** (30-day window), not an adapter defect. The sync
window (`SYNC_LOOKAHEAD_DAYS=14`) must be chunked into ≤10-day requests by the caller
or by a future sync-loop enhancement.

## Provider B — API-Football (api-sports.io)

| Item | Value | Source |
| --- | --- | --- |
| Base URL | `https://v3.football.api-sports.io` | `.env` |
| Auth header | `x-apisports-key` | official docs |
| Auth status | **VERIFIED** — `GET /status` returned `HTTP 200` | live call 2026-11-15 |
| Plan | Free | live call |
| Quota today | 8 of 100 requests used | live call |
| Quota reset | daily (Free plan) | live call |
| Leagues visible | 1244 (current=true, one page) | live call |
| Historical fixtures (yesterday, FT) | **978 matches** with scores | live call |
| Upcoming fixtures (`date=tomorrow`) | **81 matches** | live call |
| Upcoming fixtures (`next=30`) | **0 results** | live call |
| Upcoming fixtures (`from/to` range) | **0 results** | live call |
| Per-date query support | **YES** — `?date=YYYY-MM-DD` works | live call |
| Range query support | **NO** — `?from=...&to=...` and `?next=N` return 0 on Free plan | live call |
| Licence for public display | **UNVERIFIED** — terms not read in this session | docs only |

### API-Football limitations on Free plan

1. **No date-range query.** `?next=30`, `?next=7`, `?from=...&to=...` all return 0
   results. Only per-date queries (`?date=YYYY-MM-DD`) return fixtures.
2. **No league filter on upcoming.** `?next=30&league=39` also returns 0.
3. **Timezone parameter has no effect** on `next=N` (still 0).

These are plan-level restrictions, not adapter defects. The Free plan is designed for
per-date polling, not bulk future-window retrieval.

## Provider separation verification

| Requirement | Status |
| --- | --- |
| Independent configuration | VERIFIED — `FOOTBALL_DATA_ORG_TOKEN` and `FOOTBALL_DATA_API_KEY` are separate Settings fields |
| Independent authentication | VERIFIED — `X-Auth-Token` vs `x-apisports-key` headers |
| Independent rate limits | VERIFIED — football-data.org 10/min, API-Football 100/day |
| Independent error handling | VERIFIED — both use typed `ProviderError` subclasses |
| Independent raw archives | VERIFIED — archive path includes provider code |
| Independent provenance | VERIFIED — `raw_payloads.provider_id` distinguishes providers |

## What is NOT verified

- **Licence for public display** — neither provider's terms have been read in this
  session. football-data.org clause 9.1 is known from prior research
  (`2026-11-14-provider-evaluation.md` fact 6) but not re-read today.
- **Historical season depth** — only the last 9–10 days were queried. No multi-season
  backfill was attempted.
- **Statistics availability** — `/fixtures/statistics` was not called on either
  provider (budget conservation).
- **Head-to-head** — not called (budget conservation).
- **Lineups, events, players, standings** — not called (budget conservation).

## Quota consumption

| Provider | Requests used this session | Daily limit | Remaining |
| --- | --- | --- | --- |
| football-data.org | ~8 | 10/min (not tracked daily) | n/a |
| API-Football | 8 | 100/day | 92 |

## Next step

Both providers are verified for **read-only fixture retrieval**. The next gate is the
**public-display licence decision** (DEC-018 condition 2). Until clause 9.1
(football-data.org) and API-Football's Free-plan terms are reviewed, no data may be
persisted to production or displayed in the frontend.
