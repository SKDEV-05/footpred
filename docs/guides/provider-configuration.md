# Provider Configuration Guide

**Status:** the adapter is implemented; no live provider call has been made from this
repository. Provider selection, entitlement, coverage, and licence remain unverified.
**Reference adapter:** football-data.org API v4.
**Evidence:** `docs/research/2026-11-13-football-data-org-api.md` (access date 2026-11-13).
**Decision:** `ADR-0004` (provider abstraction).

## 1. What is implemented

- One `ProviderAdapter` contract (`apps/backend/app/providers/base.py`) with explicit
  capability flags. A dataset the platform does not model is declared unsupported and raises;
  it never returns empty data.
- One concrete adapter for football-data.org v4
  (`apps/backend/app/providers/adapters/football_data_org.py`), built only from fields the
  vendor's public documentation describes.
- One HTTP client with timeout, bounded retries, `Retry-After` handling, a token-bucket rate
  limiter, a response-size cap, and typed errors.
- A raw archive that stores accepted HTTP 200 responses before parsing; HTTP errors and
  oversized responses are not archived.
- Configuration through `FOOTBALL_DATA_ORG_TOKEN` and `PROVIDER_REQUESTS_PER_MINUTE`.

## 2. What is not established

The following are **UNVERIFIED** and must not be stated as facts in product copy or code:

- pricing, contract terms, and which plan is held;
- coverage of specific competitions and seasons;
- historical depth per competition;
- whether statistics are available for a given competition, match, or plan;
- licence terms for storing, displaying, or redistributing data;
- service level, rate limits on a paid plan, and quota behaviour.

The public documentation states limits for unauthenticated and free access, but a plan can
change and the publisher states limits can be raised on request. The configured rate is a
local ceiling, not proof of entitlement.

## 3. Configure a token

```bash
# .env — never commit this file
FOOTBALL_DATA_ORG_TOKEN=your-token-here
PROVIDER_REQUESTS_PER_MINUTE=10
```

Leave the token empty to run without provider access. The API over stored data does not need
it. An empty token is normalised to `None`; a whitespace-only value is treated as empty.

## 4. Verify configuration

```bash
PYTHONPATH=apps/backend .venv/bin/python -m app.cli check-provider
```

Behaviour:

| Situation | Exit code | Output |
| --- | --- | --- |
| No token | 2 | `configured: false` with a message; no request is sent |
| Token present, request succeeds | 0 | Provider code, number of competitions returned, archive row id, a five-item sample |
| Token present, request fails | 1 | Error code and message |

A successful call verifies credentials at that moment. It does **not** verify pricing,
entitlement for every competition, statistics availability, or licence terms. The command's
own output says so.

`check-provider` archives the response it fetches. That is intentional: the verification itself
is evidence.

## 5. Rate limiting and retries

- `PROVIDER_REQUESTS_PER_MINUTE` defaults to 10, matching the free-plan figure in the public
  documentation. Lower it if the plan requires; do not raise it without a documented reason.
- The limiter is per process. Running two workers doubles the request rate. Phase 3 documents
  one worker.
- The bucket starts full and refills continuously. It controls the long-run rate, not a strict
  rolling-minute count: a burst followed by refills can exceed 10 calls in one minute.
  Verify the provider's window semantics and adjust pacing before an approved live run.
- Retries apply to timeouts, 5xx, and 429. `Retry-After` is honoured. 401/403 and invalid JSON
  are not retried.
- A response larger than 8 MiB is rejected after HTTPX buffers it. This is a parsing limit,
  not a download/memory bound; streaming enforcement remains a known gap.

## 6. Switching provider

Switching is not a configuration change. It requires:

1. A research note for the new provider with primary-source evidence.
2. An adapter implementing the same contract and declaring only capabilities it can deliver.
3. Fixtures for the documented response shapes and error cases.
4. An ADR recording the decision, trade-offs, and licence position.
5. Developer approval before any live call or stored data is used publicly.

Do not add a second adapter "just in case". Two half-verified integrations are worse than one
honest, unimplemented capability.

## 7. Failure behaviour

| Failure | Behaviour |
| --- | --- |
| No token | Live operations exit non-zero with a clear message; nothing is fabricated |
| 401/403 | Run fails; no retry; credential problem is reported |
| 429 | Wait per `Retry-After` within the retry budget, then fail the run |
| 5xx / timeout | Bounded retries, then fail the run |
| Invalid JSON or undocumented structure | Parse error; archive retained; record/run fails visibly |
| Unknown enum value | Record quarantined; the rest of the run continues |

The API never contacts the provider. A provider outage affects freshness, not availability of
stored data.

## 8. Credentials

- The token is a `SecretStr`; `repr`, logs, and API responses do not expose it.
- Log redaction removes common inline credential forms and sensitive keys.
- The raw archive strips sensitive request parameters before storing them.
- Rotate the token outside the application, update `.env` (or the environment), and restart.
  There is no credential store or rotation automation in Phase 3.
