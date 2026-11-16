# Retention and Deletion Policy

**Date**: 2026-11-14  
**Scope**: Raw payload archive, sync run history, logs, and backups  
**Status**: IMPLEMENTED (code complete, policy documented)

## A. Retention Periods

### Raw Payload Archive
- **Default**: 0 days (keep everything)
- **Configurable**: `RAW_PAYLOAD_RETENTION_DAYS` environment variable
- **Location**: `apps/backend/app/core/config.py:62`
- **Behavior**: Payments older than the configured period are eligible for deletion

### Sync Run History
- **Default**: 0 days (keep everything)
- **Configurable**: `SYNC_RUN_RETENTION_DAYS` environment variable
- **Location**: `apps/backend/app/core/config.py:63`
- **Behavior**: Sync runs older than the configured period are eligible for deletion

### Log Files
- **Current Status**: Logs written to stdout/stderr; no file-based rotation configured
- **Recommendation**: Implement log rotation if persistent logging is required (future work)

## B. Safe Deletion Enforcement

### Integrity Verification
Before any raw payload file is deleted:
1. File is re-hashed using SHA-256
2. Hash is compared against stored digest in `raw_payloads.content_sha256`
3. If mismatch detected: file is kept, failure is logged, deletion is skipped
4. Integrity failures are reported in `RetentionResult.integrity_failures`

### Path Safety
- Archive root directory is resolved and validated
- Storage path must be within archive root (traversal guard)
- Provider code validated against `^[a-z0-9_]{1,32}$` regex
- Files outside root are never deleted

### Database Cascade
When sync runs are deleted:
1. `data_sync_errors` rows deleted first
2. `quarantined_records` rows deleted second
3. `match_change_log` rows deleted third
4. `data_sync_runs` row deleted last

## C. Access Control

### Operator Requirements
The `purge-retention` CLI command requires:
- Local shell access to the application server
- Python environment with dependencies installed
- Database write permissions

### Recommended Restrictions
- **Production**: Only designated operators should execute retention policies
- **Audit**: All deletions are logged with counts and integrity status
- **Dry-run**: Use `--dry-run` flag first to preview deletions without executing

### Current Limitations
- No role-based access control (RBAC) implemented
- No API endpoint for retention operations (CLI only)
- No automated schedule (manual operator execution required)

## D. Backup Procedures

### Current State
- **Automated backups**: NOT IMPLEMENTED
- **Manual backup procedure**: Documented below

### Manual Backup Steps
1. Stop application (if running)
2. Copy SQLite database file: `cp data/football.db data/football.db.backup`
3. Copy raw archive directory: `cp -r data/raw data/raw.backup`
4. Verify backup integrity by opening database and running `PRAGMA integrity_check;`
5. Store backup in secure location

### Recovery Steps
1. Stop application
2. Restore database: `cp data/football.db.backup data/football.db`
3. Restore raw archive: `rm -rf data/raw && cp -r data/raw.backup data/raw`
4. Run migrations if needed: `python -m app.cli migrate`
5. Start application and verify data integrity

## E. Recovery Rehearsal

**Status**: NOT EXECUTED  
**Requirement**: Execute isolated backup and recovery test before production use

### Recommended Rehearsal Plan
1. Create test database with synthetic data
2. Execute manual backup procedure
3. Delete test database
4. Execute recovery procedure
5. Verify data matches original
6. Document results and time required

## F. Audit Trail

### Log Events
Retention operations emit structured logs with:
- `event`: `retention.raw_payloads` or `retention.sync_runs`
- `component`: `ingestion`
- Deletion counts (rows, bytes)
- Integrity failure count

### CLI Output
The `purge-retention` command returns JSON with:
- `raw_payloads_deleted`: count of deleted payload rows
- `raw_bytes_freed`: total bytes freed
- `integrity_failures`: list of failure descriptions
- `sync_runs_deleted`: count of deleted runs
- Dependent record counts (errors, quarantine, change log)

## G. Operational Checklist

Before enabling retention (setting days > 0):
- [ ] Backup procedure tested and verified
- [ ] Operator access restricted to authorized personnel
- [ ] Audit logging configured and monitored
- [ ] Recovery procedure documented and rehearsed
- [ ] Retention period reviewed for business requirements

## H. Policy Review

This policy should be reviewed:
- Before first production deployment
- After any retention-related incident
- Annually or when operational requirements change