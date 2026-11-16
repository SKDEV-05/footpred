# Phase 3.1 Full Remediation Report

**Date:** 2026-11-14
**Scope:** Backend remediation only; Phase 5 remains blocked and unimplemented.
**Decision:** **REJECT Phase 3.1 for final acceptance** pending the explicitly open conditions below.

## A. Implementation

### Files changed

- Provider transport/configuration: `app/providers/http.py`, `app/core/config.py`.
- API safety: pagination/ID/timezone bounds, request IDs, minimal health, safe sync schema,
  search escaping, `app/api/v1/*`, `app/main.py`.
- Archive/provenance: `raw_archive.py`, `SyncEngine`, sync jobs, `0002_result_semantics.py`,
  `0003_provenance_linkage.py`, core/provenance models.
- Data integrity: team-country resolution, statistics validation/participant checks, active
  mapping requirement, result phase validation and status invalidation.
- CLI: safe database URL and generic unexpected-error output.
- Tests: transport/config/API/archive/sync/statistics/result/identity/migration regressions.
- Documentation: API, data provenance/quality/synchronization, troubleshooting, status and memory.

### Defects corrected

- Response bytes are streamed and bounded during transfer; `Content-Length` is checked early.
- Default limiter burst is conservative; numeric and HTTP-date `Retry-After` are parsed and capped.
- Effective sync parameters, date windows, competition IDs, limits, run timestamp, and observed
  raw payload IDs are persisted.
- Sync item transactions now use the owning engine's injected session factory.
- Fixture, result, change-log, statistics, errors, and quarantine records can link to raw payloads.
- Dataset freshness requires non-empty successful fixture and result runs; unrelated reference
  jobs cannot reset the match freshness flag.
- Competition geography is no longer used as team country; embedded team country is preserved.
- Statistics validation is enforced before persistence and participant membership is checked.
- Invalid team-stat groups are quarantined independently while valid groups continue.
- Extra-time/shootout components are stored separately; abandoned status is explicit; result
  invalidation occurs when a previously final fixture becomes unsettled.
- Archive reuse and reads recalculate SHA-256; provider-code path validation is enforced.
- Failed provider responses are archived before the status-code check, so forensic replay can
  reconstruct the exact bytes the provider returned, including 4xx/5xx evidence.
- Sync run API no longer exposes `error_summary`; health no longer exposes provider state or
  freshness; CLI database URLs and unexpected errors are safer.
- API query, pagination, identifier, timezone, search and request-ID inputs are bounded.
- **Aggregate transfer budget (2026-11-14):** `RunBudget` caps total bytes and requests per run
  at the HTTP client, so a job fetching many resources cannot exhaust memory or quota; error
  responses that will be retried consume no budget. Regression tests cover byte- and
  request-budget exhaustion.
- **Freshness honesty (2026-11-14):** `/sync/status` no longer derives
  `last_successful_sync_at` from any successful run; only required fixture/result datasets
  count. A successful `competitions` job can no longer imply fresh fixture data.
- **Production docs default (2026-11-14):** configuration tests assert production fails closed
  on the development docs default and that explicitly disabling docs succeeds (S-15 regression).
- **Team country source precedence (2026-11-14):** the team resource is authoritative for
  country attribution; a match-embedded team ref is lower-precedence and only fills a country
  that is currently absent. A fixture payload can no longer silently overwrite a verified
  country. Two regression tests prove the precedence rule and the gap-fill path (F-05).
- **Archive and sync-run retention (2026-11-14):** a retention module
  (`app/ingestion/retention.py`) with configurable periods deletes expired raw payloads and
  sync runs. Deletion re-hashes files before removal, refuses tampered payloads, reports
  integrity failures, and is a no-op when retention is 0. A CLI `purge-retention` command
  with `--dry-run` makes cleanup auditable. Four regression tests cover no-op, expiry,
  tamper-refusal, and sync-run cascade deletion (S-18/S-04).

### Database changes

- `0002_result_semantics`: extra-time and shootout score components plus constraints.
- `0003_provenance_linkage`: raw payload references on matches, results and change-log rows.
- Both migrations are additive and tested on a populated `0001` schema in a temporary SQLite
  database. No real application database was modified or reset.

## B. Finding resolution

| Finding | Current status | Evidence / remaining condition |
| --- | --- | --- |
| F-01 / GAP-013 | PARTIALLY RESOLVED | Streaming implementation and tests exist; true incremental early-abort/aggregate run budget still needs independent verification |
| F-02 / GAP-014 | PARTIALLY RESOLVED | Bounded retries, conservative burst, HTTP-date parsing, aggregate RunBudget on bytes and requests; provider quota and multi-process behavior remain unverified |
| F-03 / GAP-015 | PARTIALLY RESOLVED | Run parameters, raw manifest and canonical raw links added; failed-response evidence is now archived before the status-code check; controlled-clock replay remains incomplete |
| F-04 / GAP-016 | PARTIALLY RESOLVED | Empty required runs no longer count as fresh; `/sync/status` derives `last_successful_sync_at` from required datasets only; regression test added. Counters still mix units (statistic metric rows vs matches); coverage is not complete-data proof |
| F-05 / GAP-017 | RESOLVED | Competition/team separation implemented; source precedence enforced (team resource authoritative, match-embedded refs fill-only); 2 regression tests prove overwrite-prevention and gap-fill |
| F-06 / GAP-018 | PARTIALLY RESOLVED | Phase fields, abandoned status, status reversal and cross-field shootout checks added; provider field semantics and awarded/abandoned policy need domain sign-off |
| F-07 / GAP-019 | PARTIALLY RESOLVED | Canonical validation enforced and mixed group continuation tested; provider-wide boundary coverage remains incomplete |
| F-08 | VERIFIED | Participant membership enforced, including mapped third-team path; independent re-audit still required |
| F-09 / GAP-020 | PARTIALLY RESOLVED | Digest read/reuse verification and migration linkage added; adapter archives responses before the status-code check; retention/deletion policy remains open |
| F-10 / S-01 | PARTIALLY RESOLVED | API schema no longer exposes raw sync summaries and sentinel test exists; full API/log/CLI re-audit remains required |
| S-02 | PARTIALLY RESOLVED | Streaming and `trust_env=False`; incremental transport proof and aggregate budgets remain open |
| S-03 | OPEN | No auth/authz/rate limits/TLS/enforced bind; public exposure remains rejected |
| S-04 | PARTIALLY RESOLVED | Digest integrity improved; retention module with safe deletion, integrity verification, and audit trail implemented; backup/recovery rehearsal remains open |
| S-05 | PARTIALLY RESOLVED | More provider failures quarantine; competition-detail and uniform DTO boundary paths remain open |
| S-06–S-09 | PARTIALLY RESOLVED | Bounds and safer handling added; independent regression verification required |
| S-10 | PARTIALLY RESOLVED | HTTPS/host policy added; all path-component validation still needs review |
| S-11 | RESOLVED | `trust_env=False` is explicit in the provider client; all construction paths need regression confirmation |
| S-12 | PARTIALLY RESOLVED | Team field validation improved; all provider strings do not yet have a single schema contract |
| S-13 | RESOLVED | Provider-code allowlist and root checks implemented; retain traversal tests |
| S-14 | PARTIALLY RESOLVED | Conservative local bucket and retry parsing; provider quota/multi-worker behavior unverified |
| S-15 | PARTIALLY RESOLVED | Production rejects API docs enabled; other production controls are not enforced |
| S-16 | PARTIALLY RESOLVED | Pinned lock exists; hashes/advisory/license review not performed |
| S-17 | RESOLVED | Health responses no longer disclose provider configuration or freshness |
| S-18 | PARTIALLY RESOLVED | Retention, rotation, and deletion policy implemented with configurable periods, safe deletion, integrity verification, and audit trail; access control and log-integrity operations remain undefined |
| S-19 | PARTIALLY RESOLVED | Userinfo redaction and generic errors improved; URL query/fragment and all AppError messages need tests |
| LIM-006 | BLOCKED | Public-display/redistribution licence unresolved |
| LIM-007 | BLOCKED | No credentials or live provider call |
| LIM-008 | BLOCKED | No named plan/competition/season entitlement or quota evidence |

## C. Test results

Executed after the latest remediation changes:

| Check | Result |
| --- | --- |
| Full pytest suite | **239 passed**, 0 failed, 0 skipped, 0 errors; 5.97s |
| `compileall` | Exit 0 |
| SQLite migration suite | 4 passed, including populated `0001 → head` preservation |
| `alembic upgrade head` on scratch DB | Exit 0; revisions `0001`–`0003` applied |
| `alembic check` | No new upgrade operations detected |
| Phase 3 integration tests | Included in full suite; current total differs because remediation regressions were added |
| Phase 4 tests | Included in full suite; no Phase 4 source changed |
| Provider calls | None |
| Real football data | None |
| Destructive DB operations | None |

## D. Independent reviews

Fresh post-remediation QA, security, data-engineering, football-domain and backend-architecture
reviews were delegated. Their reports are incorporated only after they return. Earlier delegated
reviews found:

- QA: FAIL while the prior tree still lacked the latest fixes; shell execution was unavailable.
- Security: private loopback-only ACCEPT WITH CONDITIONS; public exposure REJECT.
- Data: FAIL for complete provenance/freshness/archive requirements before the latest raw-linkage
  and session/freshness changes.
- Football: conditional FAIL before the latest phase/status validation additions.
- Architecture: FAIL before the latest engine-owned session-factory fix.

No independent reviewer may be represented as accepting the final tree until a review explicitly
covers this exact latest state.

## E. Security posture

### Private local development

**ACCEPT WITH CONDITIONS.** Loopback-only, one worker, trusted host/data directories, no live
provider data, no tunnel/reverse proxy/shared network.

### Public/shared-network exposure

**REJECT.** S-03 is still open; S-01/S-02/S-04/S-05/S-10/S-18 and operational gaps also prevent
public exposure.

## F. Phase 3.1 acceptance

**REJECT for final acceptance at this point.** The remediation is substantial and locally
verified with 239 passing tests, but counter semantics, provider quota behavior, full
provenance replay, and public security (S-03 auth/authz/TLS) remain incomplete or unverified.
Failed-response evidence and retention/lifecycle are now implemented. The remaining
conditions are recorded rather than hidden.

## G. Phase 5 readiness

| Gate | Status |
| --- | --- |
| Phase 3.1 acceptance | BLOCKED — current decision REJECT |
| Independent QA approval of latest tree | BLOCKED pending final exact-tree review |
| Independent security approval of latest tree | BLOCKED; public exposure rejected |
| Provider selected | BLOCKED |
| Provider plan selected | BLOCKED |
| Credentials obtained by developer | BLOCKED; none exist |
| Named competition/season entitlement | BLOCKED |
| Historical availability | BLOCKED |
| Fixture coverage | BLOCKED; matrix remains empty |
| Public display/redistribution licence | BLOCKED |
| Approved public security boundary | BLOCKED |
| Explicit Phase 5 authorization | BLOCKED |

No Phase 5 work was performed: no frontend, model fitting, real prediction, provider call,
prediction persistence, or public deployment.
