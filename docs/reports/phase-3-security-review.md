# Phase 3 Independent Security Review

**Date:** 2026-11-14
**Reviewer:** `security-reviewer` subagent (independent of the implementing agent)
**Scope:** Phase 3 backend source and repository configuration
**Method:** Static source review. No shell or test execution was available in the reviewer
session, so no runtime probe was performed. No files were modified.
**Verdict:** **ACCEPT WITH CONDITIONS** for continued private, loopback-only operation.
**REJECT** for any public, shared-network, or live-provider exposure in the current state.

## Conditions summary

No blocker was found in secret handling, SQL parameterisation, redirect policy, or the absence
of write routes. The conditions separate "must fix before exposure" from "must fix before
production/live use".

## Findings

| ID | Severity | Area | Evidence | Impact | Required mitigation |
| --- | --- | --- | --- | --- | --- |
| S-01 | MAJOR | Logging/error exposure | `app/sync/engine.py:407-412`, `:305`, `:345-347`; `app/api/v1/endpoints/sync.py:22-42`; `app/api/v1/mappers.py:183`; `app/schemas/sync.py:22` | Unauthenticated `GET /api/v1/sync/runs` returns `error_summary`; for unexpected failures this is raw exception text containing SQL, bound values, and paths. Contradicts ADR-0005 and `app/api/errors.py`. | Store detail internally; expose a code-only summary, or move it behind an authenticated admin route. Add a test forcing an unexpected DB error and asserting no SQL/path/provider string appears. |
| S-02 | MAJOR | SSRF/outbound | `app/providers/http.py:36`, `:164-169`; client built at `:107-115` without streaming | `MAX_RESPONSE_BYTES` is checked after the body is buffered; unbounded memory before the cap fires (GAP-013). | Use `client.stream(...)`, abort as soon as the cap is exceeded, add a per-run byte budget, and test early abort rather than post-hoc rejection. |
| S-03 | MAJOR | API exposure | No auth/authz/rate-limit/CORS in `app/main.py` or `app/api/**`; enforcement is documentation only (`--host 127.0.0.1`) | A single flag change exposes all stored licensed data, sync metadata, and anonymous enumeration/DoS. | Keep loopback as a hard requirement; refuse startup on non-loopback unless explicitly acknowledged; add auth and per-IP limits before exposure. |
| S-04 | MAJOR | Data integrity/licensing | `app/ingestion/raw_archive.py:118-120` reuses on matching size without a digest recheck; no retention/deletion path | Equal-size tampering is silently accepted (GAP-020); licensed payloads are retained indefinitely with no owner or deletion mechanism. | Verify SHA-256 on reuse/replay; define licence-based retention and an auditable deletion path; document permissions and backup boundary. |
| S-05 | MAJOR | Boundary validation/availability | `app/sync/jobs.py:62-90`; `app/ingestion/statistics.py:44-59`; `normalization/status.py:107-125`; `identity.py:181,460`; `normalization/names.py:20-37` | One malformed provider record can abort the entire sync run instead of being quarantined; no quarantine evidence of the offending record. | Convert provider-text validation failures into `RecordValidationError` (quarantine), add regression tests, and cap provider strings at the boundary. |
| S-06 | MINOR | Input validation/reflection | `app/api/v1/endpoints/fixtures.py:80-81`; `app/core/time.py:52` | Unbounded `timezone` parameter echoed verbatim into 422 responses and logs. | `max_length=64`, IANA pattern allowlist, fixed message without echoing input. |
| S-07 | MINOR | Query handling | `app/repositories/reference.py:19-22,95-98`; `normalization/names.py:20-37` | `q=%%%` normalises to an empty pattern and returns the whole table; control characters raise `ValueError` → 500. | Test the normalised value, escape `%`/`_`/`\`, map normalisation failures to 422. |
| S-08 | MINOR | DoS/robustness | `app/api/deps.py:30-34`; `repositories/base.py:37`; `fixtures.py:106-113`; `reference.py:56-67` | Huge `page` → huge `OFFSET`; ids above 2^63 raise `OverflowError` → 500. | Bound `page`, constrain ids to `1..2^63-1`, test a 25-digit id. |
| S-09 | MINOR | Logging integrity | `app/main.py:43-50`; `app/api/errors.py:32` | Client-supplied `X-Request-ID` becomes an attacker-controlled log field and echoed response value. | Accept only `^[A-Za-z0-9._-]{1,64}$` or a UUID; otherwise generate one. |
| S-10 | MINOR | SSRF/credential egress | `app/core/config.py:42`; `http.py:107-115,270` | A wrong or tampered `FOOTBALL_DATA_ORG_BASE_URL` can send the token over plain HTTP or to an unexpected host. | Require `https`, allowlist the provider host, refuse overrides without an explicit dev flag. |
| S-11 | MINOR | Credential egress | `app/providers/http.py:107-115` | `trust_env=True` lets `HTTPS_PROXY`/`SSL_CERT_FILE` reroute or intercept credentialed traffic. | `trust_env=False` on the provider client. |
| S-12 | MINOR | Boundary validation | `app/ingestion/identity.py:539-546`, `:203`; `app/models/core.py:120-125,181` | `short_name`, `tla`, `venue_name`, and `code` reach storage unvalidated; SQLite does not enforce declared lengths. | Route all provider strings through `clean_display_name`/`normalize_code`; reject rather than truncate. |
| S-13 | MINOR | Path handling | `app/ingestion/raw_archive.py:44-48,115-116` | `provider_code` is interpolated into the archive path; traversal is blocked today but one refactor from regressing. | Validate `provider_code` against `^[a-z0-9_]{1,32}$`. |
| S-14 | MINOR | Rate limiting | `app/providers/http.py:51-59`; `tests/unit/test_http_client.py:184-193`; GAP-014 | The first minute can issue the full quota instantly, and a test locks that in. Provider window semantics are unverified. | Verify the provider's window from official terms, then encode the verified rule and update the test. |
| S-15 | MINOR | Configuration/fail-closed | `app/core/config.py:27,38`; `app/main.py:28-39` | `APP_ENV` is declared but never read; `api_docs_enabled=True` by default, so `production` changes nothing. | Wire `app_env`; production forces docs off unless overridden; warn on unsafe combinations. |
| S-16 | MINOR | Supply chain | `requirements.lock`; `pyproject.toml:12-21` | Exact versions but no hashes; no advisory scan has run. | `--require-hashes`, CI scanner, recorded review date. |
| S-17 | MINOR | Information disclosure | `app/api/v1/endpoints/health.py:40-46` | Anonymous callers learn whether a token is configured and whether data is stale. | Drop `provider_configured` from any externally reachable variant. |
| S-18 | MINOR | Log retention/access | `app/core/logging.py:123-138` | Stdout only; no retention, rotation, access control, or request access log. | Define operational retention/rotation and access control before non-local use. |
| S-19 | MINOR | Operator output | `app/cli.py:174,226` | `migrate` prints the database URL; unexpected exceptions may print SQL. | Redact URL userinfo; print exception type only. |

## Verified good

- `.env` is gitignored, `.env.example` has no secret, no `.env` exists in the tree.
- Token is `SecretStr`, unwrapped once into a request header; never logged, archived, or placed in
  a URL; 401/403 bodies are not forwarded.
- JSON logging with request/sync context and redaction; bounded messages.
- All SQL is SQLAlchemy-parameterised; the only interpolation is an `int()`-cast pragma.
- Redirects are not followed; retries are typed and bounded; `Retry-After` is capped.
- Raw archive is content-addressed, written before parsing, root-escape checked, 0600 files.
- No write routes exist; no CORS middleware; 500s return a generic envelope.
- `CheckConstraint("value >= 0")` partially mitigates GAP-019 for negative/NaN metrics.

## Conditions before any public exposure

1. Authentication, authorisation, per-IP/per-account rate limiting, request-size caps, TLS and
   security headers at the edge, plus a code-level refusal to serve on a non-loopback interface
   (S-03).
2. Code-only error exposure over HTTP; never exception text with SQL, paths, or values (S-01).
3. Streaming size abort, hard per-run byte/request budget, `https`-only allowlisted base URL,
   `trust_env=False`, and verified quota-window behaviour (S-02, S-10, S-11, S-14).
4. Archive digest re-verification, restricted permissions, and licence-based retention/deletion
   with an owner (S-04).
5. Boundary hardening and quarantine for every provider string and metric key; bounded query
   parameters; escaped LIKE wildcards; validated request ids; `APP_ENV` wired to hardening
   defaults (S-05…S-09, S-12, S-15).

## Limits of this review

- Static only: no test execution, import probing, or runtime behaviour was observed.
- No live provider call: transport, TLS, response shapes, quota semantics, and licence terms are
  UNVERIFIED.
- No git history inspection: the reviewer verified the working tree, so it cannot state that no
  secret was ever committed.
- No deployment review: TLS termination, reverse proxy, file permissions, log shipping, and
  host-level secret storage are outside the repository.
- No dependency CVE scan; S-16 is a process gap, not a CVE claim.
- This is not a penetration test and does not prove the absence of vulnerabilities.
