# Research Note — football-data.org API v4

**Access date:** 2026-11-13
**Scope:** Verify the transport, authentication, response shapes, status enums, throttling
statements, and error format needed to implement a provider adapter.
**Sources (primary only):**

- <https://www.football-data.org/documentation/quickstart>
- <https://docs.football-data.org/general/v4/match.html>
- <https://docs.football-data.org/general/v4/competition.html>
- <https://docs.football-data.org/general/v4/policies.html>
- <https://docs.football-data.org/general/v4/errors.html>
- <https://docs.football-data.org/general/v4/lookup_tables.html>

## Verified facts

| # | Fact | Source |
| --- | --- | --- |
| 1 | Base path is `/v4`; example calls use `https://api.football-data.org/v4/...` | quickstart |
| 2 | Authentication uses the request header `X-Auth-Token` | match/competition examples, lookup tables |
| 3 | `GET /v4/competitions` returns `{count, filters, competitions[]}`; a single competition (`/v4/competitions/{code}`) returns `area`, `id`, `name`, `code`, `type`, `currentSeason`, `seasons[]`, `lastUpdated` | competition |
| 4 | `GET /v4/competitions/{code}/matches` accepts `season`, `matchday`, `status`, `dateFrom`, `dateTo`, `stage`, `group` and returns `{filters, resultSet, competition, matches[]}` | competition |
| 5 | `GET /v4/matches` defaults to matches on the current UTC date and accepts `date`, `dateFrom`, `dateTo`, `status` (documented filters for the match list resource) | policies, match |
| 6 | `GET /v4/matches/{id}` returns a match with `area`, `competition`, `season`, `id`, `utcDate`, `status`, `matchday`, `stage`, `group`, `lastUpdated`, `homeTeam`, `awayTeam`, `score`, `venue`, `attendance` | match |
| 7 | Team objects include `id`, `name`, `shortName`, `tla`, `crest`; match team objects may include `statistics` and `lineup`/`bench` | match |
| 8 | `score` has `winner`, `duration`, `fullTime.home/away`, `halfTime.home/away`; `duration` enum is `REGULAR \| EXTRA_TIME \| PENALTY_SHOOTOUT` | match, lookup tables |
| 9 | Match status enum is `SCHEDULED \| TIMED \| IN_PLAY \| PAUSED \| EXTRA_TIME \| PENALTY_SHOOTOUT \| FINISHED \| SUSPENDED \| POSTPONED \| CANCELLED \| AWARDED` | lookup tables |
| 10 | Competition type enum is `LEAGUE \| LEAGUE_CUP \| CUP \| PLAYOFFS` | lookup tables |
| 11 | `null` is an explicitly valid value for unavailable attributes and empty lists are valid | policies |
| 12 | Match list responses hide lineups, bookings, substitutions and goals unless the headers `X-Unfold-Lineups`, `X-Unfold-Bookings`, `X-Unfold-Subs`, `X-Unfold-Goals` are set to `true` | policies |
| 13 | Documented throttling: unauthenticated 100 requests / 24 h (areas and competitions only); registered free plan 10 requests/minute; Standard 30 requests/minute; higher plans 60 requests/minute. The publisher states limits can be raised on request. | policies |
| 14 | Error responses are JSON `{"error": "..."}` with 400, 403, 404 and 429 documented | errors |
| 15 | The API resolves date-sensitive defaults against **now in UTC** | policies |

## What this note does not establish

- **Pricing, contract terms, licence, attribution, redistribution rights, SLA, and historical
  depth per competition — UNVERIFIED.** They require reading the current pricing and terms
  pages and, for a production decision, written confirmation.
- **Whether a given plan exposes lineups, events, or statistics for a given competition —
  UNVERIFIED.** The documentation shows fields; entitlement is plan- and competition-specific.
- **Reliability, latency, and missing-data behaviour under load — UNVERIFIED.** They require a
  live, authorised spike with credentials.
- **Response shapes beyond the documented examples.** The adapter parses only documented
  fields and rejects payloads that do not match the expected structure.

## Consequence for Phase 3

A `football-data.org` adapter can be implemented against documented, verifiable request and
response shapes without inventing endpoints. It is a **reference adapter**, not a final
procurement decision. Live integration is `IMPLEMENTED BUT NOT LIVE-VERIFIED` until a request
with real credentials succeeds. Provider selection remains an open developer decision
(PD-002) and needs a licence review before any public display of data.

## Synthetic test fixtures

Test payloads in `apps/backend/tests/fixtures/` reproduce the documented *structure* with
invented names, scores, and identifiers. They are labelled `SYNTHETIC TEST DATA` and are never
loaded into a production database. They are not evidence about any real competition.
