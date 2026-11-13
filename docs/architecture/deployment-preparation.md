# Deployment Preparation

**Status:** constraints and prerequisites only. No deployment is implemented or approved.
**Scope:** what must be true before this backend is exposed beyond a developer machine.

This document does not describe a current deployment. There is no container, orchestrator,
reverse proxy, CI pipeline, or hosted environment in Phase 3.

## 1. Process topology

| Process | Responsibility | Instances |
| --- | --- | --- |
| API | Serve read-only HTTP over stored data | One (a second is possible only after concurrency is tested) |
| Worker | Run scheduled sync through APScheduler | Exactly one |
| CLI | Manual sync, migration, inspection | On demand, not concurrent with a long worker job |

One worker is a correctness constraint, not a preference: rate limiting is per process, and
SQLite allows one writer. Running two workers doubles provider requests and increases lock
contention. Running a manual sync during a scheduled run has the same effect.

## 2. Configuration and secrets

- All configuration comes from the environment or `.env`; no secret is committed.
- `FOOTBALL_DATA_ORG_TOKEN` is required only for live sync. The API serves stored data without it.
- Secrets are redacted from logs and never returned by an endpoint.
- There is no secret manager integration. A production deployment needs one, or an equivalent
  host-level control, before real credentials are used.
- Rotating the token means updating the environment and restarting the worker.

## 3. Filesystem and state

| Path | State | Backup |
| --- | --- | --- |
| `DATABASE_URL` file (`data/football.db`) | Canonical data, sync history, quarantine | Required |
| `RAW_STORAGE_DIR` | Provider response evidence | Required |
| `.env` | Configuration and secret | Store securely, not in backups shared broadly |

The database and archive are a pair. A database restored without its archive loses the evidence
behind stored values. WAL mode creates `-wal` and `-shm` files; use SQLite's backup command or
stop the writers before copying, rather than copying a live file blindly.

No backup schedule, retention policy, restore rehearsal, or off-host copy exists yet.

## 4. Network exposure

Phase 3 has:

- no authentication;
- no authorisation;
- no rate limiting;
- no TLS termination;
- no CORS policy;
- no request size limit beyond the framework defaults.

Therefore the API must bind to loopback (`127.0.0.1`) or a trusted private network. Exposing it
publicly is not approved and would be a defect. Adding auth is a scope change requiring approval,
not a configuration tweak.

## 5. Health and readiness

| Endpoint | Checks | Use |
| --- | --- | --- |
| `GET /health` | Process only | Liveness probe |
| `GET /api/v1/health` | Database reachable; provider configured; last successful sync; staleness | Readiness and operator check |

`data_is_stale=true` is a valid response, not an outage. A deploy that treats staleness as
"unhealthy" will restart a healthy service that simply has no fresh provider data.

## 6. Observability

- Logs are JSON objects on stdout with `event`, `component`, `request_id` or `sync_run_id`, and
  error codes. Secret values are redacted.
- Sync state is durable in `data_sync_runs`, `data_sync_errors`, and `quarantined_records`.
- No metrics endpoint, tracing exporter, alerting rule, or dashboard exists.

Minimum before production:

- retention and rotation for stdout logs;
- an alert for repeated `failed` runs;
- an alert for `data_is_stale` beyond an agreed threshold;
- a review queue or scheduled report for quarantine growth;
- a disk-space alert for the archive and database.

## 7. Migrations in a deployed environment

- Apply migrations before starting a new application version.
- Back up the database and archive first.
- Test on a copy with representative data; SQLite table rebuilds can be expensive.
- A destructive migration requires explicit developer approval.
- There is no automatic migration-on-start. That is deliberate: it prevents a restart loop from
  repeatedly attempting a failing schema change.

## 8. What production would still require

| Requirement | State |
| --- | --- |
| Developer approval of Phase 2/3 outputs | Pending |
| Live provider verification with recorded evidence | Not done |
| Licence decision for display and redistribution | Not done |
| Backup automation and restore rehearsal | Not done |
| Authentication and authorisation | Not designed for Phase 3 |
| Rate limiting and abuse controls | Not implemented |
| TLS and reverse proxy | Not implemented |
| Monitoring, alerting, dashboards | Not implemented |
| Load and concurrency testing | Not done |
| PostgreSQL evaluation | Not done; not supported |
| Incident response and correction announcement | Not documented |

## 9. Explicit non-goals for Phase 3

- No container image, Kubernetes manifest, or infrastructure-as-code.
- No CI/CD pipeline.
- No multi-region, replication, or failover.
- No public API launch.
- No prediction serving.
