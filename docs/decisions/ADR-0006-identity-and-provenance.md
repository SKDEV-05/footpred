# ADR-0006 — Identity, provenance, and statistics storage model

**Status:** Proposed — implemented in Phase 3.
**Date:** 2026-11-13
**Owners:** data-engineer, backend-architect
**Related:** `docs/architecture/database-design.md`, `docs/data/identity-resolution.md`

## Context

External providers assign their own identifiers. The same team, competition, or match can
appear in several providers with different IDs and names, and a provider may rename an entity
or correct a result. Predictions must later be reproducible from stored inputs, so the system
needs stable internal identity, raw evidence, and an explicit history of accepted changes —
without over-engineering full bitemporal tables in Phase 3.

## Decision

### Identity

- Internal entities use integer surrogate primary keys. They are stable for the lifetime of the
  record and never reused.
- Provider identifiers live in separate mapping tables:
  `provider_competition_mappings`, `provider_season_mappings`, `provider_team_mappings`,
  `provider_match_mappings`, each unique on `(provider_id, external_id)`.
- Mapping rows are append-only in practice: they are marked inactive, never deleted. Each row
  records `confidence`, `first_seen_at`, and `last_seen_at`.
- Resolution order: **provider mapping → exact natural key → create**. Name similarity is never
  used to merge entities.
- Match natural-key fallback is `(season, home team, away team, kickoff within a configurable
  window)`. If more than one candidate matches, the record is quarantined as ambiguous and no
  merge occurs.
- A provider mapping is unique per `(provider, internal entity)` as well as per
  `(provider, external id)`, preventing one internal match from silently absorbing two provider
  records.

### Provenance

- Every fetch writes the response body to a content-addressed file **before** parsing, and
  inserts a `raw_payloads` row with provider, resource path, request parameters, fetch time,
  HTTP status, SHA-256, content type, and byte size.
- Canonical rows that derive from a fetch carry `raw_payload_id` and `sync_run_id` where the
  relationship is meaningful (statistics, results, quarantine entries).
- `match_change_log` is append-only and records `change_type`, changed field names, previous
  values, new values, the sync run, and the provider's `lastUpdated` value. Corrections update
  the current row **and** append a change record; they never rewrite the log.
- Provider payloads are immutable evidence. A parser bug is fixed and re-run from the archive.

### Statistics storage

Team match statistics are stored as **one row per `(match, team, metric)`** rather than a wide
nullable table.

Reasons:

- The provider's metric set may vary by competition and plan; a wide table would require
  migrations for every new key and would silently drop unknown keys.
- Availability is explicit: a missing metric has **no row**; a measured zero has a row with
  `value = 0`. This directly enforces data rule D2.
- Metric names are normalised to snake_case; units are documented in the coverage matrix.

Trade-off: reading a full match requires pivoting several rows. At the expected volume this is
cheap in SQLite and is done in one query per match in the API layer.

## Alternatives considered

- **Use provider IDs as primary keys.** Rejected: blocks a second provider and makes merges
  destructive.
- **Full bitemporal tables with `valid_from`/`valid_to` on every entity.** Rejected for Phase 3:
  high write and query complexity before the feature layer exists. The append-only change log
  plus raw archive provides auditability; a later ADR can add effective-dated tables when
  point-in-time queries require it.
- **Wide `team_match_statistics` table with nullable columns.** Rejected for the reasons above.
- **JSON blob per match.** Rejected: loses queryability, range checks, and explicit
  zero-versus-null semantics at the row level.
- **Fuzzy name matching to resolve teams.** Rejected by data rule D8; ambiguous cases are
  quarantined for review.

## Consequences

- Adding a provider requires mapping tables only, not schema changes to core entities.
- Statistics are queryable by metric and can be pivoted by the API or a future feature builder.
- The change log will grow with every update; retention is deferred but must be decided before
  production.
- The natural-key fallback window is configuration, not a hard-coded tolerance.

## Risks

- A wrong provider mapping can attach a match to the wrong internal record. Mitigations:
  exact external IDs first, confidence recorded, ambiguity quarantined, change log reviewable.
- The change log stores previous and new values as JSON; very large diffs are truncated and the
  raw payload remains the full evidence.
- Two providers can create two internal records for the same real fixture. The system prefers
  duplicates over wrong merges; cross-provider reconciliation is a later, reviewed operation.
