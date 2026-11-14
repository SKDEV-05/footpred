# Phase 3 Independent QA Review

**Date:** 2026-11-14
**Reviewer:** `qa-engineer` subagent, independent of the implementing agent
**Confidence:** medium for source findings; high for the executed local test evidence supplied by the orchestrator
**Decision affected:** whether the Phase 3 backend can be accepted as a trustworthy foundation for Phase 5

## Scope and method

This review covered the Phase 3 backend architecture, configuration, SQLite/session and
migrations, provider adapter, normalization, identity, ingestion, synchronization, API,
provenance, tests, and documented GAP-013 through GAP-020 and LIM-006 through LIM-008.
The reviewer read the implementation, tests, rules, ADRs, status/memory, Phase 4 audit,
provider evaluation, and prior security review. No files were modified, no dependencies were
installed, no provider was called, and no destructive database operation was performed.

The delegated QA environment had no shell/command-execution capability, so the reviewer could
not execute pytest or compileall. Separately, the orchestrator executed the commands below in
the repository and reports their actual output without attributing that execution to the QA
reviewer.

## Test evidence

| Check | Result | Evidence / limitation |
| --- | --- | --- |
| Full suite | **VERIFIED** — 208 passed | Orchestrator execution: `PYTHONPATH=apps/backend .venv/bin/python -m pytest -o addopts="" -p no:warnings -q`; 1.95s |
| Tests collected | **VERIFIED** — 208 | `--collect-only`; no skipped/error output |
| Phase 3 integration | **VERIFIED** — 66 passed | Orchestrator execution |
| Unit tests | **VERIFIED** — 142 passed | Orchestrator execution |
| Compilation | **VERIFIED** — exit 0 | `compileall -q apps/backend/app apps/backend/tests` |
| QA subagent execution | **NOT TESTED** | Shell unavailable in delegated session |
| Provider/live coverage | **BLOCKED** | No account, credential, or provider call |
| Load/concurrency/backup/restore/long scheduler run | **NOT TESTED** | Outside current test evidence |

A passing suite is useful evidence for tested behaviours, but does not close the defects below
or establish live provider compatibility, entitlement, licensing, or coverage.

## Findings

### F-01 — MAJOR — Response-size enforcement is post-buffer

**Status:** FAIL. `apps/backend/app/providers/http.py:107-115,164-169` accesses
`response.content` before checking `MAX_RESPONSE_BYTES`. Use streaming reads and abort on the
limit, with a per-run request/byte budget. Verify with a chunked test that reading stops before
the complete body is buffered.

### F-02 — MODERATE — Quota-window and retry semantics are not established

**Status:** PARTIALLY VERIFIED. The token bucket is deterministic and tested, but starts with a
full-minute burst (`http.py:53-55`; `tests/unit/test_http_client.py:184-194`) and HTTP-date
`Retry-After` is ignored/capped behavior is incomplete (`http.py:241-253`). Verify official
provider semantics before live use and test fixed/rolling windows, HTTP-date retries, and
multiple workers.

### F-03 — MAJOR — Sync replay/provenance evidence is incomplete

**Status:** FAIL. `sync/engine.py:284-301` stores only optional caller parameters;
`sync/jobs.py:185-212` derives windows from `utc_now()` without persisting effective dates;
quarantine paths at `sync/jobs.py:276-279` do not consistently preserve raw payload IDs. Persist
effective configuration, request identifiers, and payload linkage. Verify deterministic replay
and malformed-record quarantine linkage.

### F-04 — MAJOR — Freshness and counters are not dataset-specific

**Status:** FAIL. `api/v1/endpoints/sync.py:50-70` can derive global freshness from any successful
run; `sync/engine.py:87-101` and `sync/jobs.py:245-275` mix fixture/result/statistics and
metric-row units. Define freshness per required dataset/job and separate counter semantics.
Verify irrelevant/empty jobs, stale fixture jobs, failed latest runs, and multi-metric statistics.

### F-05 — MAJOR — Competition area can contaminate team identity

**Status:** FAIL. `ingestion/fixtures.py:79-94` passes competition country to embedded team
resolution; `ingestion/identity.py:384-403,525-546` can use that value without reliable team
resource enrichment. Use provider team country and never infer team country from competition
area. Verify an international fixture with teams from different countries.

### F-06 — MAJOR — Shootout semantics are absent

**Status:** FAIL. `validation/rules.py:229-265` derives winner/draw solely from score values;
no shootout-specific tests were found. Separate regulation, extra-time, shootout, awarded and
abandoned semantics. Add level-score/shootout-winner regression cases.

### F-07 — MAJOR — Statistics validation is defined but bypassed

**Status:** FAIL. `validation/rules.py:267-307` defines `validate_statistics`, but
`ingestion/statistics.py:43-59` does not invoke it. Invalid/non-finite/oversized metrics can
fail late or be handled inconsistently. Enforce validation before persistence and quarantine
invalid records while valid records continue.

### F-08 — MAJOR — Statistics team membership is not checked

**Status:** FAIL. `ingestion/statistics.py:33-42` accepts a team ID without checking that it is
one of the match participants. Database referential integrity is insufficient for this semantic
relationship. Verify a mapped third team is quarantined with no metric row.

### F-09 — MAJOR — Archive integrity and failed-response evidence are incomplete

**Status:** FAIL. `ingestion/raw_archive.py:118-120` accepts an existing equal-size file without
re-hashing; `providers/http.py:180-217` does not preserve non-200/oversized response evidence.
Re-hash on reuse, define bounded failure evidence and retention/deletion policy, then test equal-
size tampering and error responses.

### F-10 — MAJOR — Sync failure details can reach an unauthenticated API

**Status:** FAIL. `sync/engine.py:303-319,345-347` stores exception text; `api/v1/endpoints/sync.py:22-42`
returns sync records; mapper/schema paths expose `error_summary`. Expose stable codes/safe
summaries only and test sentinel SQL/path/provider text does not appear.

## Domain and subsystem review

| Area | Status | Conclusion |
| --- | --- | --- |
| Application architecture and boundaries | PARTIALLY VERIFIED | Modular monolith and service seams are coherent; failure and security boundaries remain incomplete |
| SQLite connection management | VERIFIED | SQLite-only guard, foreign keys, WAL, busy timeout, pooled sessions are tested |
| Schema/migrations | VERIFIED | Integration tests verify expected tables, no metadata drift, and idempotent upgrade |
| Provider adapter | PARTIALLY VERIFIED | DTO/capability/error handling exists; live response, entitlement, quota and licence are unverified |
| Normalization and identity | PARTIALLY VERIFIED | Exact identity and ambiguity quarantine are good; country enrichment and boundary validation gaps remain |
| Ingestion | PARTIALLY VERIFIED | Idempotent core upserts and missing-vs-zero semantics exist; statistics and score semantics are incomplete |
| Synchronization | PARTIALLY VERIFIED | Per-item transactions, quarantine, and stale-run handling exist; replay, freshness, counters and unexpected exceptions remain |
| API | PARTIALLY VERIFIED | Read-only routes, schemas, pagination and UTC handling exist; unauthenticated error/health exposure and bounds remain |
| Data provenance/freshness | FAIL | Exact replay and dataset-specific freshness are not established |
| Test quality | PARTIALLY VERIFIED | Meaningful tests exist, but the principal open defects lack regression coverage |

## GAP and limitation status

| Item | Status | Finding |
| --- | --- | --- |
| GAP-013 | FAIL | Post-buffer response cap and incomplete HTTP-date retry handling |
| GAP-014 | PARTIALLY VERIFIED | Deterministic bucket, but quota semantics and full-burst policy unverified |
| GAP-015 | FAIL | Effective windows and raw payload linkage incomplete |
| GAP-016 | FAIL | Freshness/counters are not reliable dataset coverage evidence |
| GAP-017 | FAIL | Competition area can influence team identity |
| GAP-018 | FAIL | Shootout/winner semantics absent |
| GAP-019 | FAIL | Statistics validation and participant membership not enforced |
| GAP-020 | FAIL | Equal-size archive tampering and failed-response evidence gaps |
| LIM-006 | NOT TESTED | Public display/redistribution licence not legally verified |
| LIM-007 | BLOCKED | No credentials or live provider call |
| LIM-008 | BLOCKED | Price, quota, coverage, statistics and SLA remain unverified |

## Test-quality gaps

Missing meaningful regression cases include streaming early abort, HTTP-date retry values,
provider quota windows and multi-worker behavior, persisted sync windows and payload linkage,
dataset-specific freshness, international team-country attribution, shootouts and awarded
matches, statistics validation and participant membership, equal-size archive tampering,
failed-response evidence, unexpected sync-error API leakage, DST transitions, cross-ID duplicate
fixtures, late corrections, and database failure during item/finalization transactions.

## Private development decision

**ACCEPT WITH CONDITIONS.** The system is reasonable for controlled local development when the
operator binds it to loopback, controls the host and data directories, runs one worker, and uses
no unverified live provider data. This is an operational convention, not an application-enforced
network boundary. The decision does not accept live-provider use, shared-network exposure, or
public deployment.

## Final QA verdict

**FAIL — Phase 3 acceptance is not justified.** The implementation is substantial and locally
passes 208 tests, but major correctness, provenance, validation, and exposure defects remain.
Phase 3 must be remediated or each risk explicitly accepted by the developer before Phase 5.
This conclusion is independent of the implementing agent and does not claim that every line of
the repository was revalidated.

## Explicit limits

No provider call, entitlement, licence, coverage, load, concurrency, backup/restore, or long-
running scheduler test was performed. The delegated QA reviewer could not execute commands; the
local test totals above are separately executed evidence, not delegated-review execution.
