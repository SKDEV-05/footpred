# ADR-0007 — Synchronisation and scheduling model

**Status:** Proposed — implemented in Phase 3.
**Date:** 2026-11-13
**Owners:** data-engineer, backend-architect
**Related:** `docs/data/synchronization.md`

## Context

Fixtures, results, and statistics arrive from a rate-limited external API. The platform must
run scheduled and manual synchronisation, be safe to re-run, record failures visibly, and avoid
downloading the same data repeatedly. Phase 3 has one operator, one host, and one database.

## Decision

- One worker process runs APScheduler (`python -m app.worker`) against the same codebase and
  database as the API. The API process never schedules or performs provider calls.
- Scheduling is disabled unless `SYNC_ENABLED=true`; the worker refuses to start without a
  configured provider token.
- Jobs are declared as named functions with explicit parameters and are executed through a
  single `SyncEngine` that creates a `data_sync_runs` row before work starts and finalises it
  afterwards with counts and status (`success`, `partial`, `failed`).
- Manual runs use the CLI (`python -m app.cli sync-*`). There is no public write endpoint.
- APScheduler uses `max_instances=1`, `coalesce=True`, and a misfire grace period; combined with
  a single worker this prevents overlapping runs of the same job class.
- Every HTTP call passes through one client with: timeout, bounded retries with exponential
  backoff and jitter, `Retry-After` handling for 429, and a token-bucket rate limiter configured
  below the provider's documented limit.
- Ingestion is idempotent: re-running a window resolves existing mappings and natural keys,
  compares values, and only updates changed fields. Unchanged records count as `unchanged`.
- Failures are recorded per item in `data_sync_errors`; invalid records go to
  `quarantined_records` with a reason. A run with rejected records ends as `partial`.
- The scheduler cadence is configuration, not a hard-coded promise. Defaults are conservative.

## Alternatives considered

- **Celery + Redis.** Rejected for Phase 3: adds a broker and a second stateful system for one
  worker. Revisit if jobs must survive process restarts, need multiple workers, or retry logic
  is reimplemented.
- **Cron plus a script.** Viable and simpler, but loses in-process job registration and
  observable run state. The CLI remains usable from cron if desired.
- **Synchronous sync inside API requests.** Rejected: couples user latency to provider latency,
  bypasses rate limiting discipline, and creates unbounded request work.
- **At-most-once assumptions ("run once per day").** Rejected: provider retries and operator
  re-runs are normal; handlers must be idempotent.

## Consequences

- A crashed worker leaves a `running` run behind. The next startup marks stale `running` runs as
  `failed` with a reason, so they do not look like live work.
- Rate limiting is per process; running two workers would double the request rate. The
  documented deployment is one worker.
- APScheduler does not persist job state. Missed ticks are acceptable because the sync window
  overlaps and is idempotent.
- Manual backfills can be run with explicit date ranges and are bounded by the same limiter.

## Risks

- A large backfill can monopolise the rate limit and delay scheduled updates. Backfills should
  be run with explicit ranges and monitored.
- A clock change can affect APScheduler intervals. The worker logs its timezone and uses UTC
  internally.
- Without authentication, the CLI is the only write path; host access control is the security
  boundary in Phase 3.

## Revisit conditions

Multiple workers, durable queues, job priorities, or retry semantics that outgrow this design.
