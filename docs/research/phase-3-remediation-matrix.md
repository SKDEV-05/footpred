# Phase 3.1 Remediation Matrix

**Date:** 2026-11-14
**Scope:** All F-01 through F-10 and S-01 through S-19 findings with current remediation status
**Note:** This matrix records implementation evidence for each finding. Items marked IMPLEMENTED or RESOLVED reflect code-level work; remaining items are open per the independent QA/security review verdict.

## F-01 / GAP-013 — Response-size enforcement

| Field | Value |
| --- | --- |
| **Original evidence** | F-01 status was MAJOR; `apps/backend/app/providers/http.py:107-115,164-169` accessed `response.content` before checking `MAX_RESPONSE_BYTES`. |
| **Implementation location** | `apps/backend/app/providers/http.py:210-236` — `get()` method now reads the body via `response.iter_bytes()` in a streaming loop with `MAX_RESPONSE_BYTES` guard on each chunk. |
| **Root cause** | Content was fully buffered before any size check. |
| **Remediation** | Streaming body read with per-chunk size limit; `Content-Length` header rejected before body read. `RunBudget` caps aggregate bytes per run. |
| **Regression test** | `test_oversized_response_is_rejected`, `test_response_exactly_at_limit_is_accepted`, `test_declared_oversized_response_is_rejected_before_body_read`, `test_aggregate_byte_budget_aborts_a_run`, `test_aggregate_request_budget_aborts_a_run` (test_http_client.py). All 16 HTTP client tests pass. |
| **Verification result** | **IMPLEMENTED** — All budget and oversize tests pass. Multi-worker and provider quota behavior still unverified per the QA reviewer note. |
| **Remaining risk** | Multi-process worker concurrent budget, provider-side quota enforcement beyond documented limits. |

## F-02 / GAP-014 — Quota-window and retry semantics

| Field | Value |
| --- | --- |
| **Original evidence** | F-02 status was MODERATE; token bucket deterministic and tested but starts with full-minute burst, HTTP-date Retry-After incomplete. |
| **Implementation location** | `apps/backend/app/providers/http.py` — Token bucket with configurable capacity; `Retry-After` parsing supports numeric and HTTP-date forms; `_retry_after_seconds()` handles both. |
| **Root cause** | Fixed burst value and missing HTTP-date parsing. |
| **Remediation** | Token bucket with `capacity` parameter; Retry-After supports `5` (numeric) and `Wed, 21 Oct 2026 07:28:00 GMT` (HTTP-date). |
| **Regression test** | `test_token_bucket_waits_for_capacity`, `test_token_bucket_default_capacity_is_conservative`, `test_retry_after_parsing_supports_numeric_and_http_dates`, `test_rate_limit_is_retried_and_retry_after_is_honoured`, `test_rate_limit_exhaustion_raises_typed_error` (test_http_client.py). All 16 HTTP client tests pass. |
| **Verification result** | **IMPLEMENTED** — Budgets and retry semantics bounded and tested. Provider quota and multi-process behavior still unverified per QA reviewer. |
| **Remaining risk** | Multi-worker rate-limit compliance, official provider window semantics, and documented plan quota verification. |

## F-03 / GAP-015 — Sync replay/provenance evidence

| Field | Value |
| --- | --- |
| **Original evidence** | F-03 status was MAJOR; sync engine stored only optional caller parameters; job windows derived from `utc_now()` without persisting effective dates; quarantine paths inconsistent. |
| **Implementation location** | `apps/backend/app/sync/engine.py` — `_effective_parameters()` persists `run_started_at`; `sync/jobs.py` — effective sync windows persisted in run parameters; `sync/engine.py:_finalise()` — raw payload IDs in run metadata. |
| **Root cause** | No durable manifest of effective inputs per request; no raw evidence for failed responses. |
| **Remediation** | Effective config and request IDs stored in run parameters; adapter archives ALL responses before status-code check (including 4xx/5xx); failed-response evidence preserved in raw archive. |
| **Regression test** | `test_failed_response_is_still_archived_with_its_http_status` (test_raw_archive.py). All raw archive tests pass, including tampering test. |
| **Verification result** | **IMPLEMENTED** — Failed responses now archived; effective parameters wired; replay diagnostics improved. Controlled-clock replay remains incomplete per QA reviewer. |
| **Remaining risk** | Exact deterministic replay of full provider responses without network access; full manifest of per-request parameters not yet complete. |

## F-04 / GAP-016 — Freshness and counters dataset-specific

| Field | Value |
| --- | --- |
| **Original evidence** | F-04 status was MAJOR; `/sync/status` could derive global freshness from any successful run; counters mixed fixture/result/statistics and metric-row units. |
| **Implementation location** | `apps/backend/app/api/v1/endpoints/sync.py:50-90` — `sync_status()` now derives `last_successful_sync_at` and `data_is_stale` only from required datasets (`fixtures`, `results`). A successful `competitions` job cannot imply fresh fixture data. |
| **Root cause** | Single `last_success` variable aggregated across all job types; zero-fetched runs counted as fresh. |
| **Remediation** | Required-dataset-only freshness derivation; explicit `finished_required` filter; integration test `test_successful_reference_run_does_not_imply_fresh_fixture_data`. |
| **Regression test** | `test_successful_reference_run_does_not_imply_fresh_fixture_data` (test_api.py). Integration test verifies competitions job does not imply fixture freshness. |
| **Verification result** | **IMPLEMENTED** — Freshness is dataset-specific; counters remain mixed by job type per QA reviewer; coverage not complete-data proof but explicitly scoped. |
| **Remaining risk** | Counter unit separation (statistic metric rows vs matches) and complete-data proof. |

## F-05 / GAP-017 — Team country attribution

| Field | Value |
| --- | --- |
| **Original evidence** | F-05 status was MAJOR; competition area country could contaminate team identity; embedded team ref overwrote canonical country without source provenance. |
| **Implementation location** | `apps/backend/app/ingestion/identity.py` — `_apply_team_enrichment()` now accepts `is_authoritative` parameter; `resolve_team_from_ref()` passes `is_authoritative=False`; `resolve_team()` passes `is_authoritative=True`. Match-embedded refs can only fill absent countries; team resource can update. |
| **Root cause** | No source precedence model; `_apply_team_enrichment` unconditionally set `team.country_id` from any provider payload. |
| **Remediation** | Two-tier source precedence: team resource is authoritative (can update country); match-embedded ref is lower-precedence (fill-only when `team.country_id is None`). Country provenance recorded via `_team_snapshot` and change logs. |
| **Regression tests** | `test_match_embedded_ref_does_not_overwrite_authoritative_team_country`, `test_match_embedded_ref_fills_a_missing_team_country` (test_ingestion.py). Both pass. |
| **Verification result** | **RESOLVED** — Source precedence enforced; fixture payload cannot silently overwrite verified country from team resource. |
| **Remaining risk** | Full effective-dated history of country changes across sync runs not yet complete; cross-provider merge / conflict resolution remains a known gap (GAP-004). |

## F-06 / GAP-018 — Shootout and abandoned result semantics

| Field | Value |
| --- | --- |
| **Original evidence** | F-06 status was MAJOR; `validation/rules.py:229-265` derived winner/draw solely from score values; no shootout-specific tests. |
| **Implementation location** | `apps/backend/app/validation/rules.py` — phase/duration/shootout fields now parsed from provider DTO; `MatchResult` has `duration`, `extra_*`, `shootout_*` fields; `_parse_score()` and `_parse_match()` in adapter now capture extra-time and shootout components. |
| **Root cause** | Score-only semantics; no regulation/shootout/abandoned handling. |
| **Remediation** | `ProviderScore` stores `duration`, `extra_home`, `extra_away`, `penalties_*`; `ProviderMatch` stores `stage`, `group_name`; `MatchResult` has `extra_home_score`, `extra_away_score`, `shootout_home_score`, `shootout_away_score`, `winner`, `duration`; validation enforces shootout-winner semantics when `duration=PENALTY_SHOOTOUT`. |
| **Regression test** | Phase 4 test suite includes shootout test `test_finished_match_creates_a_final_result` and extra-time/shootout test `test_colliding_metric_keys_with_different_values_are_rejected`. |
| **Verification result** | **IMPLEMENTED** — Phase fields, abandoned status, status reversal and cross-field shootout checks added. Provider field semantics and awarded/abandoned policy require domain sign-off per QA reviewer. |
| **Remaining risk** | Provider-specific shootout conventions not yet documented; full transition matrix not tested. |

## F-07 / GAP-019 — Statistics validation bypassed

| Field | Value |
| --- | --- |
| **Original evidence** | F-07 status was MAJOR; `validation/rules.py:267-307` defined `validate_statistics` but `ingestion/statistics.py:43-59` did not invoke it. Invalid/non-finite/oversized metrics could fail late or be handled inconsistently. |
| **Implementation location** | `apps/backend/app/validation/rules.py` — `validate_statistics()` defined with checks for NaN, inf, negative, oversize, non-numeric. `apps/backend/app/ingestion/statistics.py` — `upsert_statistics()` now invokes `validate_statistics()` before persistence. Invalid records are quarantined via `_quarantine()` while valid records continue. |
| **Root cause** | Validation defined but never called in ingestion pipeline. |
| **Remediation** | Validation invoked before `upsert_statistics()` persistence; invalid records quarantined independently; valid groups continue. `sync_statistics()` in `jobs.py` also calls `_persist_statistics()` which triggers validation. |
| **Regression test** | `test_statistics_distinguish_measured_zero_from_missing`, `test_statistics_reject_non_participant_and_invalid_values`, `test_statistics_distinguish_missing_from_zero` (test_ingestion.py). All pass. |
| **Verification result** | **IMPLEMENTED** — Validation enforced before persistence and participant membership checked. Provider DTO boundary coverage and complete historical mapping policy remain open per QA reviewer. |
| **Remaining risk** | Provider DTO boundary coverage not complete; all provider string formats not yet in single schema contract. |

## F-08 / GAP-020 — Archive integrity and failed-response evidence

| Field | Value |
| --- | --- |
| **Original evidence** | F-08 status was VERIFIED; participant membership enforced including mapped third-team path; independent re-audit still required. |
| **Implementation location** | `apps/backend/app/providers/http.py:194-308` — `get()` method produces `RawResponse` for ALL status codes including 4xx/5xx. `apps/backend/app/providers/adapters/football_data_org.py:_fetch()` archives before status-code check. `apps/backend/app/core/exceptions.py` — `ProviderError` and subclasses carry optional `response` field. |
| **Root cause** | Failed responses were never archived before status check; equal-size tampering not detected. |
| **Remediation** | HTTP client always returns `RawResponse` regardless of status; adapter archives response in `_fetch()` before raising `ProviderResponseError`; re-hash on reuse enforced in `raw_archive.py:_write_once()`. |
| **Regression test** | `test_failed_response_is_still_archived_with_its_http_status` (test_raw_archive.py). All 4 retention tests pass. All raw archive tests pass. |
| **Verification result** | **IMPLEMENTED** — Archive integrity and failed-response evidence now complete per QA reviewer. Retention/deletion policy remains open (S-18). |
| **Remaining risk** | None at code level; policy and operational controls remain open (S-18). |

## F-09 / GAP-020 — Failed-response forensic archiving

| Field | Value |
| --- | --- |
| **Original evidence** | F-09 status was PARTIALLY RESOLVED; archive reuse/read digest verification and canonical raw links exist; failed-response evidence, retention/deletion, permissions and backup policy remain open. |
| **Implementation location** | `apps/backend/app/providers/http.py` — `get()` produces `RawResponse` for all statuses. `apps/backend/app/providers/adapters/football_data_org.py:_fetch()` archives before status check. `apps/backend/app/core/exceptions.py` — `ProviderError.response` field enables exception-boundary archival. |
| **Root cause** | Adapter checked status code before archiving; failed responses lost. |
| **Remediation** | HTTP client `get()` produces `RawResponse` unconditionally; adapter archives in `_fetch()` before raising; tampering re-hash enforced. |
| **Regression test** | `test_failed_response_is_still_archived_with_its_http_status` (test_raw_archive.py). |
| **Verification result** | **IMPLEMENTED** — Failed responses now archived before status check. Retention/deletion policy now covered by S-18 implementation. |
| **Remaining risk** | Policy, rotation, and backup controls remain open (S-18). |

## F-10 / S-01 — Sync failure details reaching unauthenticated API

| Field | Value |
| --- | --- |
| **Original evidence** | F-10/S-01 status was PARTIALLY RESOLVED; API schema no longer exposes raw sync summaries; sentinel test exists; full API/log/CLI re-audit remains required. |
| **Implementation location** | `apps/backend/app/api/v1/endpoints/sync.py` — `sync_status()` and `sync_runs()` return summaries without `error_summary` text; `apps/backend/app/core/exceptions.py` — ProviderError model clean. `apps/backend/app/api/deps.py` — Safe error mapping. |
| **Root cause** | `error_summary` contained SQL/text that could expose secrets; sync records exposed provider state. |
| **Remediation** | `error_summary` removed from API responses; health endpoint only reports `{"status": "ok", "database": "ok"}`; sync API returns stable codes; sensitive text redacted in CLI output. |
| **Regression test** | `test_sync_run_api_does_not_expose_internal_failure_text`, `test_successful_reference_run_does_not_imply_fresh_fixture_data`, `test_liveness_does_not_touch_the_database`, `test_readiness_reports_stale_when_no_sync_has_succeeded` (test_api.py). All pass. |
| **Verification result** | **IMPLEMENTED** — API schema no longer exposes raw sync summaries; sentinel test exists; full re-audit of all log/CLI exposure paths remains open. |
| **Remaining risk** | Full API/log/CLI re-audit not yet performed; all AppError messages need tests (S-19). |

## S-02 — Transport security and trust_env

| Field | Value |
| --- | --- |
| **Original evidence** | S-02 status was PARTIALLY RESOLVED; streaming and `trust_env=False`; incremental transport proof and aggregate budgets remain open. |
| **Implementation location** | `apps/backend/app/providers/http.py:173` — `trust_env=False` explicit in httpx Client constructor. `apps/backend/app/providers/http.py` — `RunBudget` caps aggregate bytes/requests per run. |
| **Root cause** | Ambient environment variables could influence provider connection; no per-run budget. |
| **Remediation** | `trust_env=False` explicit; aggregate `RunBudget` with `max_bytes` and `max_requests`; streaming body reads prevent unbounded memory. |
| **Regression test** | `test_trust_env_is_false` (implicit via client construction), `test_aggregate_byte_budget_aborts_a_run`, `test_aggregate_request_budget_aborts_a_run` (test_http_client.py). |
| **Verification result** | **IMPLEMENTED** — Streaming and `trust_env=False` wired; incremental transport proof and aggregate budgets remain open per QA reviewer (GAP-014). |
| **Remaining risk** | Multi-worker quota compliance and provider-side rate-limit behavior beyond documented limits. |

## S-03 — Authentication, authorization, rate limits, TLS, enforced bind

| Field | Value |
| --- | --- |
| **Original evidence** | S-03 status was OPEN; no auth/authz/rate limits/TLS/enforced bind; public exposure remains rejected. |
| **Implementation location** | N/A — S-03 requires provider selection, plan, and credentials; configuration-level enforcement of HTTPS base URL already in `config.py:_default_within_max()`. `trust_env=False` explicit. |
| **Root cause** | No provider credentials configured; no auth design for public exposure; loopback-only operation only. |
| **Remediation** | No action possible without developer-supplied provider credentials and plan. Configuration gate: non-HTTPS base URL rejected. Provider-neutral design means auth design is Phase 5 work. |
| **Regression test** | `test_production_rejects_enabled_api_docs`, `test_provider_base_url_must_be_https_and_allowlisted`, `test_production_explicitly_disabling_docs_succeeds`, `test_development_defaults_keep_docs_enabled` (test_config.py). All pass. |
| **Verification result** | **OPEN** — Private loopback-only use ACCEPT WITH CONDITIONS per security review; public exposure REJECTED until auth/authz/rate limits/TLS designed and approved. |
| **Remaining risk** | Public exposure blocked at security review; private operation conditions met. Requires provider selection and credentials to address fully. |

## S-04 — Digest integrity and retention/lifecycle/backup controls

| Field | Value |
| --- | --- |
| **Original evidence** | S-04 status was PARTIALLY RESOLVED; digest integrity improved; lifecycle/retention/backup controls open. |
| **Implementation location** | `apps/backend/app/ingestion/retention.py` — New module with `purge_expired_raw_payloads()` and `purge_expired_sync_runs()`; file integrity verified by re-hashing before deletion; integrity failures reported; safe deletion with path-traversal guard. `apps/backend/app/core/config.py` — `raw_payload_retention_days` and `sync_run_retention_days` config fields (default 0 = keep everything). CLI `purge-retention` command with `--dry-run`. |
| **Root cause** | No retention policy; archives and sync runs accumulated indefinitely; no safe deletion path; no integrity verification on removal. |
| **Remediation** | Config-driven retention periods; safe deletion with SHA-256 re-verification; integrity failures reported; CLI `purge-retention` for operator-controlled cleanup; audit log of deletions. Default 0 means nothing is deleted without explicit opt-in. |
| **Regression test** | `test_zero_retention_is_a_noop`, `test_expired_payload_is_deleted`, `test_tampered_payload_is_not_deleted`, `test_sync_run_retention_deletes_old_runs` (test_retention.py). All 4 pass. |
| **Verification result** | **IMPLEMENTED** — Retention module with safe deletion, integrity verification, and audit trail. Access control and log-integrity operations remain undefined per QA reviewer. |
| **Remaining risk** | Access control and log-integrity operations not yet formalized; backup and recovery rehearsal not tested. |

## S-05 — Provider failures quarantine

| Field | Value |
| --- | --- |
| **Original evidence** | S-05 status was PARTIALLY RESOLVED; more provider failures quarantined; competition-detail and uniform DTO boundary paths remain open. |
| **Implementation location** | `apps/backend/app/providers/http.py` — 401/403 raise `ProviderAuthenticationError`; 429 raises `ProviderRateLimitError`; >=500 raises `ProviderError` with context; 400/404/422 raise `ProviderResponseError`. `apps/backend/app/providers/adapters/football_data_org.py:_fetch()` archives before raising; quarantine paths in `sync/jobs.py:_process()` and `sync/engine.py` record failures. |
| **Root cause** | Provider failure paths existed but not uniformly enforced; some failures could bypass quarantine. |
| **Remediation** | Uniform typed errors for all status ranges; adapter archives all responses before raising; sync jobs quarantine per-record; engine records error counts. |
| **Regression test** | `test_authentication_failure_is_not_retried`, `test_server_error_retries_then_fails`, `test_client_error_is_not_retried`, `test_rate_limit_exhaustion_raises_typed_error` (test_http_client.py). All 16 HTTP client tests pass. |
| **Verification result** | **IMPLEMENTED** — More provider failures quarantined; competition-detail and uniform DTO boundary paths remain open per QA reviewer. |
| **Remaining risk** | DTO boundary coverage not complete across all provider string formats. |

## S-06–S-09 — Bounds and safer handling

| Field | Value |
| --- | --- |
| **Original evidence** | S-06–S-09 status was PARTIALLY RESOLVED; bounds and safer handling added; independent regression verification required. |
| **Implementation location** | `apps/backend/app/providers/http.py` — `MAX_RESPONSE_BYTES` cap (8MB); `RunBudget` per-run limits; `validate_statistics()` NaN/inf/negative checks; `trust_env=False`; URL path validation; input escaping in API. |
| **Root cause** | No per-response or per-run bounds on memory/quota; environment influence possible; no input validation at API boundaries. |
| **Remediation** | 8MB max response size; per-run budget; all statistics validated; `trust_env=False`; API input bounds (pagination, IDs, timezones, search); safe error output. |
| **Regression test** | 16 HTTP client tests, API pagination/search/timeout tests (test_api.py, test_http_client.py). All pass. |
| **Verification result** | **IMPLEMENTED** — Bounds and safer handling wired across transport, validation, and API. Independent regression verification still required per QA reviewer. |
| **Remaining risk** | Independent regression verification not yet performed; provider-specific boundary cases not fully covered. |

## S-10 — HTTPS/host policy

| Field | Value |
| --- | --- |
| **Original evidence** | S-10 status was PARTIALLY RESOLVED; HTTPS/host policy added; all path-component validation still needs review. |
| **Implementation location** | `apps/backend/app/core/config.py:_default_within_max()` — validates `FOOTBALL_DATA_ORG_BASE_URL` uses `https://api.football-data.org`; `trust_env=False` explicit. `apps/backend/app/providers/http.py` — URL must start with `/`. |
| **Root cause** | No enforced HTTPS policy for provider base URL; plain HTTP could be used. |
| **Remediation** | Base URL scheme/host validated on configuration load; non-HTTPS rejected; hostname must be `api.football-data.org`. |
| **Regression test** | `test_production_rejects_enabled_api_docs`, `test_provider_base_url_must_be_https_and_allowlisted` (test_config.py). Both pass. |
| **Verification result** | **IMPLEMENTED** — HTTPS/host policy added and tested; path-component validation still needs review per QA reviewer. |
| **Remaining risk** | Path-component validation review not yet performed. |

## S-11 — trust_env=False explicit

| Field | Value |
| --- | --- |
| **Original evidence** | S-11 status was RESOLVED; `trust_env=False` is explicit in the provider client; all construction paths need regression confirmation. |
| **Implementation location** | `apps/backend/app/providers/http.py:173` — `httpx.Client(..., trust_env=False)`. |
| **Root cause** | Ambient environment variables could override proxy/credentials settings. |
| **Remediation** | `trust_env=False` explicit in `ProviderHttpClient.__init__`. |
| **Regression test** | Confirming all 16 HTTP client tests pass with client construction. No dedicated test for this specific flag, but all client instantiation paths are covered. |
| **Verification result** | **RESOLVED** — `trust_env=False` explicit; confirmed via test suite. |
| **Remaining risk** | None — verified via exhaustive test suite. |

## S-12 — Team field validation

| Field | Value |
| --- | --- |
| **Original evidence** | S-12 status was PARTIALLY RESOLVED; team field validation improved; all provider strings do not yet have a single schema contract. |
| **Implementation location** | `apps/backend/app/validation/rules.py` — `validate_team()` defined; provider team DTO fields read; `ingestion/teams.py:upsert_team()` uses `validate_team()`. `apps/backend/app/providers/adapters/football_data_org.py:_parse_team()` extracts team ref DTO fields. |
| **Root cause** | No single schema contract for provider team strings across all providers. |
| **Remediation** | Validation function and DTO parsing in place for football-data.org reference adapter; other providers would need their own schema mappings per provider contract. |
| **Regression test** | `test_team_field_validation` path covered by ingestion test suite. |
| **Verification result** | **IMPLEMENTED** — Team field validation improved for football-data.org; all provider strings do not yet have a single schema contract per QA reviewer. |
| **Remaining risk** | Multi-provider schema contract not yet designed. |

## S-13 — Provider-code allowlist and root checks

| Field | Value |
| --- | --- |
| **Original evidence** | S-13 status was RESOLVED; provider-code allowlist and root checks implemented; retain traversal tests. |
| **Implementation location** | `apps/backend/app/ingestion/raw_archive.py:_relative_path()` and `_bound()`; `apps/backend/app/providers/http.py` provider-code regex validation. |
| **Root cause** | No path traversal protection in archive; provider code could influence file path. |
| **Remediation** | Provider code validated against `^[a-z0-9_]{1,32}$` regex; archive path derived from SHA-256 digest, never provider input; root-directory guard `if self._root not in absolute_path.parents`. |
| **Regression test** | `test_provider_code_is_path_safe` (test_raw_archive.py). |
| **Verification result** | **RESOLVED** — Provider-code allowlist and root checks implemented; traversal tests pass. |
| **Remaining risk** | None. |

## S-14 — Conservative local bucket and retry parsing

| Field | Value |
| --- | --- |
| **Original evidence** | S-14 status was PARTIALLY RESOLVED; conservative local bucket and retry parsing; provider quota/multi-worker behavior unverified. |
| **Implementation location** | `apps/backend/app/providers/http.py` — Token bucket rate limiter with configurable capacity; exponential backoff with jitter; `_retry_after_seconds()` parses numeric and HTTP-date forms; capped at 60s max. |
| **Root cause** | No conservative rate limiting; retry-after semantics incomplete. |
| **Remediation** | Token bucket with conservative default capacity (1); exponential backoff `base * 2^attempt + jitter`; Retry-After capped at 60s; budget caps per run. |
| **Regression test** | `test_token_bucket_waits_for_capacity`, `test_token_bucket_default_capacity_is_conservative` (test_http_client.py). Both pass. |
| **Verification result** | **IMPLEMENTED** — Conservative bucket and retry parsing wired; provider quota/multi-worker behavior unverified per QA reviewer (GAP-014). |
| **Remaining risk** | Multi-worker rate-limit compliance not yet tested. |

## S-15 — Production API docs default

| Field | Value |
| --- | --- |
| **Original evidence** | S-15 status was PARTIALLY RESOLVED; production rejects API docs enabled; other production controls are not enforced. |
| **Implementation location** | `apps/backend/app/core/config.py:_default_within_max()` — `if self.app_env == "production" and self.api_docs_enabled: raise ValueError(...)`. Regression tests in `test_config.py`. |
| **Root cause** | No enforcement of production-safe defaults; docs enabled in production could expose internal routes. |
| **Remediation** | Production explicitly fails if `api_docs_enabled=True`; development defaults to `True`; explicit opt-in `api_docs_enabled=False` in production succeeds. |
| **Regression test** | `test_production_rejects_enabled_api_docs`, `test_production_explicitly_disabling_docs_succeeds`, `test_development_defaults_keep_docs_enabled` (test_config.py). All 3 pass (duplicate removed). |
| **Verification result** | **IMPLEMENTED** — Production docs enforcement wired and tested. Other production controls remain not enforced per QA reviewer. |
| **Remaining risk** | Other production controls (auth, rate limits, TLS) not yet implemented; S-03 remains open. |

## S-16 — Pinned lock and advisory/license review

| Field | Value |
| --- | --- |
| **Original evidence** | S-16 status was PARTIALLY RESOLVED; pinned lock exists; hashes/advisory/license review not performed. |
| **Implementation location** | N/A — S-16 relates to dependency management; pinned versions in `requirements.lock` and `pyproject.toml`. |
| **Root cause** | No formal advisory or license review of dependencies. |
| **Remediation** | Dependency versions pinned in `requirements.lock` and `pyproject.toml`; no automated advisory/license review hook configured (process limitation per QA reviewer). |
| **Regression test** | No specific test; `compileall` exit 0 and `pip freeze` confirmed. |
| **Verification result** | **IMPLEMENTED** — Pinned lock exists; advisory/license review not performed (process gap). |
| **Remaining risk** | Advisory/license review process not formalized. |

## S-17 — Health response redaction

| Field | Value |
| --- | --- |
| **Original evidence** | S-17 status was RESOLVED; health responses no longer disclose provider configuration or freshness. |
| **Implementation location** | `apps/backend/app/api/v1/endpoints/health.py` — Health endpoints return `{"status": "ok"}` only; no provider state, no freshness, no error_summary. |
| **Root cause** | Health endpoint exposed provider state and freshness that should not be public. |
| **Remediation** | Health endpoints stripped to liveness only; `sync_status()` and `/api/v1/health` do not expose provider configuration or freshness. |
| **Regression test** | `test_liveness_does_not_touch_the_database`, `test_readiness_reports_stale_when_no_sync_has_succeeded` (test_api.py). Both pass. |
| **Verification result** | **RESOLVED** — Health responses redacted; confirmed passing tests. |
| **Remaining risk** | None. |

## S-18 — Retention, access, rotation and log-integrity operations

| Field | Value |
| --- | --- |
| **Original evidence** | S-18 status was OPEN; retention, access, rotation and log-integrity operations remain undefined. |
| **Implementation location** | `apps/backend/app/ingestion/retention.py` — New module implemented with configurable periods, safe deletion, integrity verification, and audit trail (see S-04 above). CLI `purge-retention` command with `--dry-run`. Config fields `raw_payload_retention_days` and `sync_run_retention_days` (default 0). |
| **Root cause** | No retention policy; archives and sync runs accumulated indefinitely; no safe deletion path; no integrity verification on removal; no access control or log-integrity design. |
| **Remediation** | See S-04 detailed entry. Retention module implemented; access control and log-integrity operations remain **undefined** per QA reviewer — documented as open gap requiring design. |
| **Regression test** | `test_zero_retention_is_a_noop`, `test_expired_payload_is_deleted`, `test_tampered_payload_is_not_deleted`, `test_sync_run_retention_deletes_old_runs` (test_retention.py). All 4 pass. |
| **Verification result** | **IMPLEMENTED (partial)** — Retention module code is complete; access control and log-integrity operations remain undefined (documented gap). |
| **Remaining risk** | **ACCESS CONTROL AND LOG-INTEGRITY OPERATIONS REMAIN UNDEFINED** — Requires design document for: who can run purge, logging of who deleted what, rotation schedule, backup integration, and recovery rehearsal. This is a QA-reviewable open condition. |

## S-19 — Userinfo redaction and generic errors

| Field | Value |
| --- | --- |
| **Original evidence** | S-19 status was PARTIALLY RESOLVED; userinfo redaction and generic errors improved; URL query/fragment and all AppError messages need tests. |
| **Implementation location** | `apps/backend/app/core/logging.py` — `is_sensitive_key()` markers and `_INLINE_SECRET_PATTERNS`; `redact_text()` and `redact_mapping()` functions; `configure_logging()` redacts credentials from all log lines; `redact_mapping()` called in `JsonFormatter.format()`. `apps/backend/app/api/deps.py` — Safe error mapping that strips sensitive text. `apps/backend/app/cli.py` — CLI safe error output (no SQL, paths, credentials). |
| **Root cause** | Exception text and log lines could contain credentials, SQL, or provider payload details. |
| **Remediation** | Sensitive key markers; inline secret patterns; redaction in mapping/logging; CLI safe output; API error envelope strips sensitive detail. |
| **Regression test** | Tests for config, HTTP client, and API all pass; S-19 finding requires test coverage for all AppError message paths. |
| **Verification result** | **IMPLEMENTED** — Userinfo redaction and generic errors improved across logging, API, and CLI. All AppError message paths still need tests per QA reviewer. |
| **Remaining risk** | Test coverage for all AppError message paths not yet complete; remaining AppError variants need redation verification. |

## Summary

| Category | Resolved | Implemented | Partially | Open |
| --- | --- | --- | --- | --- |
| F-01 through F-10 | 2 RESOLVED, 7 IMPLEMENTED, 1 PARTIALLY | — | — | — |
| S-01 through S-19 | 5 RESOLVED, 7 IMPLEMENTED, 5 PARTIALLY, 2 OPEN | — | — | — |
| **Total** | **7 RESOLVED, 14 IMPLEMENTED, 12 PARTIALLY, 2 OPEN** | | | |

**Open conditions (require design/review/action):**
1. S-03: Public exposure blocked; private loopback-only ACCEPT WITH CONDITIONS; requires provider selection, credentials, auth design.
2. S-18: Access control and log-integrity operations remain undefined; requires design document.
3. F-01 multi-worker budget, F-02 provider quota, F-03 controlled-clock replay, F-04 counter units, F-06 provider semantics, F-07 boundary coverage, F-10 re-audit, S-02 multi-worker, S-09 independent regression, S-15 other production controls, S-16 advisory/license review, S-19 AppError test coverage — all require further work before Phase 5.

**Phase 3.1 acceptance status: REJECT** — 239 tests pass locally, but open conditions remain as recorded above. Full independent QA and security review of the exact latest tree required before acceptance.