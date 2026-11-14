# Phase 3 Security Reassessment

**Date:** 2026-11-14
**Reviewer:** `security-reviewer` subagent, independent of the implementing agent
**Method:** Static source/configuration review; no provider call, deployment, penetration test,
filesystem permission inspection, dependency scan, or runtime execution by the delegated reviewer.
The orchestrator separately ran the existing test suite.
**Scope:** S-01 through S-19, private development gate, and public exposure gate.

## Overall decisions

### Private development: ACCEPT WITH CONDITIONS

The backend is suitable only for controlled local development when the operator binds the server
to `127.0.0.1`, controls the host and data directories, runs one worker, and does not use
unverified live-provider data. This is a documented operating convention, not an application-
enforced network boundary. `README.md` and deployment guidance document loopback startup, but
`app/main.py` does not reject non-loopback serving.

### Public/shared-network exposure: REJECT

Public exposure is rejected. Authentication, authorization, rate limiting, request-size controls,
TLS/security headers, and code-enforced host policy are absent. S-01, S-02, S-03, S-04, S-05,
S-10, S-11, S-15, S-17, S-18, and S-19 are sufficient blockers; the remaining findings add
material hardening and operational risk.

## S-01 through S-19 reassessment

| ID | Status | Severity | Evidence | Required remediation | Verification |
| --- | --- | --- | --- | --- | --- |
| S-01 | FAIL | MAJOR | `app/sync/engine.py:303-318,345-347`; `app/api/v1/endpoints/sync.py:22-42`; `app/schemas/sync.py:10-23`; `app/api/v1/mappers.py:183` | Keep exception diagnostics internal; expose stable codes/safe summaries or authenticate admin sync routes | Inject an exception containing SQL/path/provider sentinels and assert none appears in `/sync/runs` |
| S-02 | FAIL | MAJOR | `app/providers/http.py:141-178`, especially `response.content` before the size check | Stream response bytes, abort at the limit, and add an aggregate run budget | Chunked transport test proves early abort before full buffering |
| S-03 | FAIL | MAJOR / exposure blocker | No auth/authz/rate limit/CORS or code-level bind enforcement in `app/main.py`, `app/api/**`; loopback is documentation only | Enforce private binding or implement approved authenticated deployment with TLS, authz, limits, headers and audit logging | Startup/network, route authorization, rate-limit and external exposure tests |
| S-04 | FAIL | MAJOR | `app/ingestion/raw_archive.py:118-120`; no retention/deletion mechanism | Re-hash existing archive files on reuse; define licence-based retention, deletion, permissions and backups | Same-size mutation is detected; retention/deletion/permission tests |
| S-05 | PARTIALLY VERIFIED | MAJOR | `app/sync/jobs.py:43-90`; provider text/metric validation can raise plain `ValueError` in normalization and identity paths | Convert boundary validation failures into quarantineable errors; validate all provider strings before persistence | Malformed names, codes, venue values, metric keys and numbers quarantine while valid records continue |
| S-06 | FAIL | MINOR | `app/api/v1/endpoints/fixtures.py:78-100`; `app/core/time.py:44-57` | Bound timezone input, use an allowlist/bounded lookup, and do not echo arbitrary input | Oversized/control-character/malformed timezone tests return bounded 422 without reflection |
| S-07 | FAIL | MINOR | `app/repositories/reference.py:19-23,95-99`; `app/normalization/names.py:40-58` | Validate normalized query, escape LIKE wildcards, reject empty normalized searches, map failures to 422 | Wildcard, Unicode, control-character, empty-normalized and long-query tests |
| S-08 | FAIL | MINOR | `app/api/deps.py:30-50`; endpoint integer parameters | Bound page and IDs; cap result windows or use cursor pagination | Very large page/page-size/ID requests never reach DB execution and return controlled errors |
| S-09 | PARTIALLY VERIFIED | MINOR | `app/main.py:41-51`; `app/api/errors.py:24-35` | Accept strict UUID or `[A-Za-z0-9._-]{1,64}` only; generate otherwise | Invalid/control-character IDs are replaced; valid IDs survive |
| S-10 | FAIL | MINOR, potentially MAJOR with credentials | `app/core/config.py:41-43`; `app/providers/http.py:99-115,256-275` | Require HTTPS, allowlist provider host, restrict overrides, validate external IDs | Config tests reject HTTP/unexpected hosts/credentials in URL/path traversal |
| S-11 | FAIL | MINOR, potentially MAJOR with credentials | `app/providers/http.py:107-115` leaves `trust_env` implicit | Set `trust_env=False` or implement an explicitly approved proxy path | Proxy/TLS environment-variable test verifies default client behavior |
| S-12 | PARTIALLY VERIFIED | MINOR | `app/ingestion/identity.py:460-479,525-546`; model string fields | Validate every provider string with field-specific length/control/null rules | Every provider string field has invalid-value tests and no partial write |
| S-13 | PARTIALLY VERIFIED | MINOR | `app/ingestion/raw_archive.py:36-49,115-116` | Allowlist provider codes and reject separators/dot segments | Constructor traversal, Unicode-separator, empty and oversized tests |
| S-14 | PARTIALLY VERIFIED | MINOR / quota risk | `app/providers/http.py:40-79`; `tests/unit/test_http_client.py:184-193` | Confirm quota window; conservative burst; shared budget if multiple workers; alerting | Deterministic burst, sustained rate, retry, concurrency and multi-process tests |
| S-15 | FAIL | MINOR | `app/core/config.py:26-28,38`; `app/main.py:24-39` | Wire `APP_ENV` to safe defaults; production disables docs by default and rejects unsafe combinations | Settings/app-factory tests for all environments and docs exposure |
| S-16 | PARTIALLY VERIFIED | MINOR process gap | `pyproject.toml`; `requirements.lock` | Hash-enforced reproducible install where supported, dependency/license review and advisory policy | Clean install, dependency tree and dated review evidence |
| S-17 | FAIL | MINOR | `app/api/v1/endpoints/health.py:22-46` | Public liveness must not disclose provider configuration or detailed staleness/readiness | Anonymous response contains only minimal liveness |
| S-18 | FAIL | MINOR, potentially MAJOR for licensed data | `app/core/logging.py:123-138`; deployment documentation | Define retention, rotation, access control, integrity and allowlisted fields; avoid raw exception text | Redaction plus operational retention/permission tests |
| S-19 | FAIL | MINOR | `app/cli.py:163-175,203-229` | Redact database URL userinfo/query secrets and print stable error codes/types only | CLI tests with credential-bearing URLs and sentinel exception text |

## Positive controls verified statically

- `.env` is ignored and `.env.example` contains no real token.
- Provider tokens use `SecretStr`; the token is sent in a header rather than a URL.
- SQLAlchemy expressions use bound parameters; the busy-timeout interpolation is integer-cast.
- Redirects are not intentionally enabled; retries are bounded and typed.
- Raw archive paths are root-checked and temporary files use `mkstemp`.
- No write API routes were found.
- Structured logging includes redaction and bounded text, but does not solve raw sync summaries
  or retention/access-control gaps.

## Public exposure remediation priority

Before any non-loopback exposure, address S-03 first as the security boundary, then S-01, S-02,
S-04, S-05, S-10 and S-11. S-15, S-17, S-18 and S-19 must also be addressed before production-
like operation. Do not treat a changed Uvicorn `--host`, reverse proxy, or `APP_ENV=production`
as a security control.

## Review limitations

This is an independent static reassessment, not a penetration test. The delegated reviewer did
not execute tests or inspect runtime network/filesystem behavior. No provider call, entitlement,
licence, dependency advisory scan, deployment, or Git-history review was performed.
