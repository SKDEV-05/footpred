# ADR-0004 — Provider abstraction and the Phase 3 reference adapter

**Status:** Proposed — reference adapter implemented; live integration not verified.
**Date:** 2026-11-13
**Owners:** data-engineer, backend-architect
**Related:** `docs/data/provider-integration.md`, `docs/research/2026-11-13-football-data-org-api.md`

## Context

The platform must ingest football data without coupling the domain model to one vendor. No
provider account, licence, or paid plan exists. Phase 1 marked every provider claim
`UNVERIFIED`. The master brief requires at least one real adapter while explicitly allowing
live integration to remain unverified when credentials are unavailable.

## Decision

1. Define a provider-neutral contract (`ProviderAdapter`) that returns **internal DTOs**, never
   raw vendor payloads. The domain and persistence layers do not import vendor modules.
2. Implement one reference adapter against **football-data.org API v4**, because its request
   format, response shape, enums, error format, and throttling statements are publicly
   documented and were verified on 2026-11-13.
3. Keep provider-specific quirks (authentication header, path layout, field names, folding
   headers, status/type/enum translation) inside the adapter.
4. Declare capabilities explicitly. A method the adapter cannot or does not yet support raises
   `UnsupportedCapabilityError`; it never returns fabricated or empty data that looks real.
5. Archive every HTTP response body before parsing, with a content hash, so parser changes and
   audits never require a re-fetch.
6. Treat the adapter as a **reference implementation**, not a procurement decision. Provider
   selection (PD-002) still requires a live, authorised verification spike and a licence review.

## Capabilities declared for the reference adapter

| Capability | Declared | Note |
| --- | --- | --- |
| Competitions | yes | list + detail |
| Seasons | yes | derived from competition detail (`seasons[]`) |
| Teams | yes | competition team list, embedded match teams |
| Fixtures / results | yes | date-range match lists and match detail |
| Team match statistics | yes | only keys present in the payload; units are provider-defined |
| Lineups | no | provider documents them, but Phase 3 has no player model; not ingested |
| Events (goals, cards, substitutions) | no | same reason |
| Injuries / suspensions | no | not modelled and not documented as a stable feed |

`no` means "the platform does not model it in Phase 3", not "the vendor cannot supply it".

## Alternatives considered

- **API-Football (API-Sports).** Broad marketed coverage, but the documentation site returned
  HTTP 403 to this environment and no account exists; its response schema could not be verified
  from a primary source here. Deferred, not rejected.
- **Sportmonks.** Documentation is reachable, but validating plan entitlements and field
  semantics needs credentials. Deferred.
- **StatsBomb Open Data.** Event-level and research-oriented; not a fixture/result feed and its
  licence must be confirmed. Deferred.
- **Scraping.** Rejected: terms-of-service, fragility, and no contractual reliability.
- **Hard-coding one vendor throughout the app.** Rejected: makes the identifier and schema
  coupling irreversible and blocks a second source.

## Reasons

- The abstraction is the smallest one that supports a second provider without changing the
  domain model.
- football-data.org's documented v4 response is sufficient to build and test a real parser,
  including awkward cases (postponed matches, null scores, missing statistics).
- No live call is needed to verify the parser against documented structure, so the work is
  honest: the code exists, the live path does not.

## Consequences

- Each new provider requires an adapter plus capability declaration, mapping tests, and a
  coverage-matrix update.
- Provider-specific statistics keys are normalised to snake_case metric names and stored as
  provider-defined metric rows; a metric catalogue documents units.
- The response archive grows with every fetch and needs a retention policy before production.

## Risks

- A documented field may be absent or differently typed on a real plan; the adapter validates
  and quarantines rather than guessing. **Live behaviour is UNVERIFIED.**
- Vendor changes can break parsing; archived payloads make diagnosis possible.
- Implementing a second provider may reveal that the DTO contract is not neutral enough. That
  is expected; the contract is versioned in code and tested.

## Verification required before this ADR can be accepted

- A real authenticated request succeeds for one competition and one season.
- A real match list and match detail payload parse without quarantine.
- Licence, attribution, and redistribution terms are read and recorded with an access date.
- The provider's actual rate limit for the chosen plan is observed, not assumed.
