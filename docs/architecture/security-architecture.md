# Security Architecture

**Status:** Local development controls only; no penetration test has been performed.
Independent security review was attempted but blocked by the tool usage limit. Statements below
describe intent and inspected code, not an independent security certification.
**Binding rules:** `rules/security-rules.md`, `docs/security/security-principles.md`
**Decision records:** ADR-0002, ADR-0003, ADR-0004, ADR-0005

## 1. Assets and trust boundaries

| Asset | Why it matters | Storage |
| --- | --- | --- |
| Provider API token | Grants quota and possibly paid data access | Environment / secret manager only |
| Raw provider payloads | Licensed evidence; may contain restricted data | Local content-addressed files |
| Canonical history | Product value; correctness and auditability | SQLite file |
| Sync metadata | Shows what was fetched, when, and what failed | SQLite |
| Future predictions | Must be tamper-evident and reproducible | Not implemented |

Trust boundaries: provider → client, client → archive, archive → adapter, adapter → domain,
domain → database, client → API, operator → host.

## 2. Authentication and authorisation

- **Provider:** header-based token (`X-Auth-Token` for the reference adapter), loaded from
  configuration, never persisted in the database or logs.
- **API:** no authentication in Phase 3. The API is read-only and must run on a trusted host or
  private interface. Public exposure requires an authentication, authorisation, and rate-limit
  design first.
- **Database:** local file permissions; there are no database roles in SQLite. Host access is
  the effective authorisation boundary. This is a known limitation, not a security claim.
- **CLI/worker:** privileged operations; access is controlled by host user permissions.

## 3. Secret handling

- Settings use `SecretStr` for tokens, reducing accidental disclosure through representation.
  Pattern-based log redaction is defence in depth, not proof that arbitrary text is secret-free.
- `.env` is ignored by version control; `.env.example` contains names and non-functional
  placeholders only.
- The provider client sends the token in a header and never includes it in the URL, the archived
  request metadata, or exception text.
- The logging formatter redacts values for keys containing `token`, `secret`, `password`,
  `authorization`, `cookie`, or `api_key`, and redacts `X-Auth-Token`.
- Startup fails closed when a required value is absent for an operation: a sync job without a
  token refuses to start. The API can start without a provider because serving stored data does
  not require one.

## 4. Input validation

| Boundary | Controls |
| --- | --- |
| Provider JSON | JSON decode errors, structural checks, explicit enum mapping. Size check is after buffering; HTTP errors/oversize responses bypass archive. Parse failures can fail the whole list |
| Provider numbers | Non-negative scores, attendance, statistics; range checks; no coercion from strings |
| Provider text | Length caps in the database; control characters rejected in names; no HTML rendering |
| API query/path | Typed Pydantic/FastAPI validation, enum allowlists, page-size cap, IANA timezone validation |
| File archive | Hash-derived filename, fixed root, no user-supplied path components, no execution |
| SQL | SQLAlchemy bound parameters throughout; no string-built SQL |

## 5. Output and logging

- Structured JSON logs include timestamp, level, logger, request/sync ID, message, and selected
  fields. They exclude payload bodies and credentials.
- API errors return a code, a human-readable message, optional field details, and a request ID.
  They never return stack traces, SQL, file paths, or provider messages.
- Sync errors are truncated/redacted in storage; the read-only sync API exposes error summaries.
  Raw provider response bodies are not deliberately forwarded, but stored summaries must still
  be treated as sensitive operational information.
- Log retention and access control are host responsibilities in Phase 3. No log shipping exists.

## 6. Rate limiting and denial-of-service

- A token bucket controls average provider request rate with a full-minute initial burst.
  Its default equals the documented free-plan figure, not a verified rolling-minute ceiling.
  Retry handling has the limitations recorded in `memory/known-limitations.md` GAP-013/014.
- API list endpoints cap `page_size` at 100 and default to bounded date windows.
- There is no API rate limiting in Phase 3; this is a blocker for public exposure.
- Request body size is not a concern yet because all endpoints are GET with no body.

## 7. Data protection and licensing

- Provider payloads may be licensed and restricted. The archive is for internal audit and
  reprocessing, not redistribution.
- No endpoint serves raw payloads or provider-specific dumps.
- Attribution and display rights are **UNVERIFIED** and must be confirmed before any public
  presentation.
- No personal data is intentionally collected. Provider payloads may include player names and
  dates of birth; Phase 3 does not ingest player entities. If personal data is added later, a
  retention and deletion design is required first.

## 8. Integrity of historical data

- Fixture/result corrections append a change log. Statistics/reference updates are in-place
  without that log; this is partial historical auditing.
- Raw filenames are content-addressed, but filesystem permissions are the integrity boundary;
  no digest recheck on reuse or tamper-evidence verification exists.
- Unique constraints protect provider mappings. Competition/team natural-key duplicates can
  exist and are rejected as ambiguous by resolution rather than prevented by all-table uniqueness.
- Ingestion never deletes canonical rows.
- Future prediction integrity (immutable pre-kickoff records, hashing, restricted writes) is
  designed in the rules but **not implemented**, because predictions do not exist yet.

## 9. Dependency and supply chain

- Dependencies are declared in `pyproject.toml`, pinned, and captured in `requirements.lock`.
- Only packages required for the implemented features are installed.
- No install script from an untrusted source is executed.
- A dependency review for licences and advisories is required before production; it has not
  been performed.

## 10. Residual risks (explicit)

| Risk | Severity | Status |
| --- | --- | --- |
| API has no authentication or rate limiting | High if exposed | Accepted only while private |
| SQLite file has no encryption at rest | Medium | Host/filesystem control required |
| No backup/restore automation | Medium | Documented manual procedure; not verified |
| Provider licence and redistribution rights unknown | High for public use | Blocking open question |
| Live provider behaviour unverified | Medium | Requires authorised spike |
| No dependency vulnerability scan | Medium | Scheduled before production |
| Logs may contain provider data fragments in error messages | Low | Truncation/redaction applied; review before production |
| No audit trail for operator CLI actions beyond sync runs | Low | Accepted in Phase 3 |

## 11. Security acceptance criteria before any deployment

- [ ] Authentication and authorisation for any public endpoint.
- [ ] Per-client rate limiting and request size limits.
- [ ] TLS termination and secure headers at a reverse proxy.
- [ ] Secrets supplied by a secret manager, not a shell history or repository file.
- [ ] Database backup and restore rehearsed.
- [ ] Dependency and container/image scan completed.
- [ ] Provider licence and attribution confirmed in writing.
- [ ] Log retention and access review completed.
- [ ] Incident response contacts and credential rotation procedure written.

Until these are met, the system is a local development and verification environment, not a
production service.
