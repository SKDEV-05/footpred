# Database Design

**Status:** Implemented in Phase 3 against SQLite. PostgreSQL is not installed or verified.
**Owner:** data-engineer (schema), backend-architect (persistence boundaries)
**Decisions:** ADR-0003 (SQLite), ADR-0006 (identity, provenance, statistics)
**Binding rules:** `rules/data-rules.md`, `rules/system-design-rules.md`

## 1. Scope and principles

The schema stores **canonical football facts and the evidence behind them**, not predictions.
Phase 3 creates no prediction, feature, or user tables.

Design rules applied:

- A stable internal identity exists for every competition, season, team, and match. Provider
  identifiers are mapped, never used as primary keys.
- Raw payloads are archived before parsing; canonical rows reference their run and, where
  meaningful, their raw payload.
- Corrections update the current row and append to `match_change_log`; history is not rewritten.
- Missing is not zero. Statistics use one row per metric so absence is representable.
- All timestamps are stored in UTC. SQLite does not preserve timezone offsets, so the
  application normalises to UTC on write and treats stored values as UTC on read.
- No table is created for data the platform cannot obtain or reliably maintain. Players,
  lineups, events, injuries, standings, and odds are deliberately **not** modelled in Phase 3.

## 2. Entity groups

| Group | Tables |
| --- | --- |
| Reference | `countries`, `competitions`, `seasons`, `teams` |
| Fixtures and results | `matches`, `match_results` |
| Provider identity | `data_providers`, `provider_competition_mappings`, `provider_season_mappings`, `provider_team_mappings`, `provider_match_mappings` |
| Provenance and operations | `raw_payloads`, `data_sync_runs`, `data_sync_errors`, `quarantined_records`, `match_change_log` |
| Statistics | `team_match_statistics` |

## 3. Table specifications

### 3.1 `countries`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | integer PK | no | surrogate |
| `name` | varchar(120) | no | unique, canonical display name |
| `normalized_name` | varchar(120) | no | unique; casefolded, accent-free exact-match key |
| `iso_code` | varchar(3) | yes | provider-supplied when available; not assumed |
| `created_at`, `updated_at` | datetime | no | UTC |

### 3.2 `competitions`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | integer PK | no | surrogate |
| `name` | varchar(160) | no | display name |
| `normalized_name` | varchar(160) | no | exact-match key derived from `name` |
| `code` | varchar(32) | yes | short code, provider-independent |
| `type` | enum | no | `league`, `league_cup`, `cup`, `playoffs` |
| `country_id` | FK → `countries.id` | yes | null for international competitions |
| `emblem_url` | varchar(512) | yes | provider-supplied HTTP(S) URL; null when absent |
| `created_at`, `updated_at` | datetime | no | |

Indexes: `name`, `normalized_name`, `country_id`. No unique constraint on name: distinct
competitions can share a name across countries; ambiguity is handled at resolution time, not by a
database guess.

### 3.3 `seasons`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | integer PK | no | |
| `competition_id` | FK → `competitions.id` | no | |
| `label` | varchar(32) | no | derived deterministically, e.g. `2024/2025` or `2024` |
| `start_date`, `end_date` | date | no | provider-declared |
| `current_matchday` | integer | yes | provider value; not inferred |
| `is_current` | boolean | no | platform flag from the provider's current season |
| `created_at`, `updated_at` | datetime | no | |

Constraints: `UNIQUE(competition_id, label)`; `UNIQUE(id, competition_id)` to support the
composite foreign key from `matches`; `CHECK(end_date >= start_date)`.
Index: `(competition_id, start_date)`.

The composite key guarantees a match cannot reference a season from another competition.

### 3.4 `teams`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | integer PK | no | |
| `name` | varchar(160) | no | display name |
| `normalized_name` | varchar(160) | no | exact-match key derived from `name` |
| `short_name` | varchar(80) | yes | |
| `tla` | varchar(8) | yes | three-letter abbreviation when supplied |
| `country_id` | FK → `countries.id` | yes | |
| `venue_name` | varchar(200) | yes | free text; not a venue entity |
| `founded` | integer | yes | |
| `crest_url` | varchar(512) | yes | provider-supplied HTTP(S) URL; null when absent |
| `created_at`, `updated_at` | datetime | no | |

Indexes: `name`, `normalized_name`, `country_id`.
`CHECK(founded IS NULL OR founded BETWEEN 1850 AND 2100)`.

No venue table is created in Phase 3: the provider supplies a free-text venue name without a
stable identifier, and inventing one would create false identity. The name is stored on the
match and team where supplied.

### 3.5 `matches`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | integer PK | no | stable internal match identity |
| `competition_id` | FK → `competitions.id` | no | |
| `season_id` | FK → `seasons.id` | no | composite FK with competition |
| `home_team_id` | FK → `teams.id` | no | |
| `away_team_id` | FK → `teams.id` | no | |
| `kickoff_utc` | datetime | no | UTC; local time is not stored as truth |
| `status` | enum | no | canonical status (section 4) |
| `matchday` | integer | yes | provider value |
| `stage` | varchar(48) | yes | provider stage, normalised to lower snake case |
| `group_name` | varchar(16) | yes | e.g. `group_a`; null when not applicable |
| `venue_name` | varchar(200) | yes | |
| `attendance` | integer | yes | null when unpublished |
| `first_seen_at` | datetime | no | first successful persist |
| `last_synced_at` | datetime | no | last observation, even if unchanged |
| `provider_last_updated` | datetime | yes | provider's `lastUpdated`, if supplied |
| `created_at`, `updated_at` | datetime | no | |

Constraints:

- `CHECK(home_team_id <> away_team_id)`.
- `CHECK(attendance IS NULL OR attendance >= 0)`.
- `CHECK(matchday IS NULL OR matchday > 0)`.
- `UNIQUE(season_id, home_team_id, away_team_id, kickoff_utc)` — duplicate safety net. It does
  not replace identity resolution; a violation is quarantined, not silently ignored.
- Composite FK `(season_id, competition_id) → seasons(id, competition_id)`.

Indexes: `kickoff_utc`, `(competition_id, kickoff_utc)`, `(home_team_id, kickoff_utc)`,
`(away_team_id, kickoff_utc)`, `status`.

### 3.6 `match_results`

One row per match at most, holding the currently accepted result. History lives in
`match_change_log`.

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `match_id` | PK, FK → `matches.id` | no | one-to-one |
| `home_score`, `away_score` | integer | yes | full-time score |
| `ht_home_score`, `ht_away_score` | integer | yes | half-time score |
| `winner` | enum | yes | `home_team`, `away_team`, `draw` |
| `duration` | enum | yes | `regular`, `extra_time`, `penalty_shootout` |
| `status` | enum | no | match status when the result was recorded |
| `is_final` | boolean | no | true only for `finished`/`awarded` |
| `provider_last_updated` | datetime | yes | |
| `resolved_at` | datetime | no | platform observation time |
| `created_at`, `updated_at` | datetime | no | |

Constraints: non-negative scores; full-time scores either both present or both absent;
half-time scores either both present or both absent.

A result row is only created for statuses `finished` or `awarded`. Provisional in-play scores
are not stored as results.

### 3.7 Provider identity tables

`data_providers`: `id`, `code` (unique), `name`, `base_url`, `is_enabled`, timestamps.

The four mapping tables share this shape:

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | integer PK | no | |
| `provider_id` | FK → `data_providers.id` | no | |
| `external_id` | varchar(64) | no | vendor identifier as text |
| `competition_id` / `season_id` / `team_id` / `match_id` | FK | no | internal identity |
| `confidence` | float | no | 0.0–1.0, recorded at resolution time |
| `is_active` | boolean | no | false for retired mappings |
| `first_seen_at`, `last_seen_at` | datetime | no | |

Constraints: `UNIQUE(provider_id, external_id)` and
`UNIQUE(provider_id, <internal_id>)`; `CHECK(confidence BETWEEN 0 AND 1)`.

Mappings are never deleted by application code. A mapping change is a reviewed operation.

### 3.8 `raw_payloads`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | integer PK | no | |
| `provider_id` | FK | no | |
| `resource_type` | varchar(64) | no | e.g. `matches`, `match_detail` |
| `request_path` | varchar(500) | no | path only, never the token |
| `request_params` | JSON | yes | query parameters |
| `fetched_at` | datetime | no | UTC |
| `http_status` | integer | no | |
| `content_sha256` | varchar(64) | no | content address |
| `storage_path` | varchar(500) | no | file path relative to the raw root |
| `content_type` | varchar(120) | yes | |
| `byte_size` | integer | no | |

Indexes: `content_sha256`, `fetched_at`. Multiple fetch observations may share a hash; the file
is written once and each observation is a separate row. `CHECK(byte_size >= 0)`.

### 3.9 `data_sync_runs`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | integer PK | no | |
| `provider_id` | FK | yes | null only for provider-independent jobs |
| `job_type` | varchar(64) | no | e.g. `fixtures`, `results`, `statistics` |
| `status` | enum | no | `running`, `success`, `partial`, `failed` |
| `started_at` | datetime | no | |
| `finished_at` | datetime | yes | |
| `parameters` | JSON | yes | exact job arguments |
| `records_fetched` | integer | no | |
| `records_created` | integer | no | |
| `records_updated` | integer | no | |
| `records_unchanged` | integer | no | |
| `records_rejected` | integer | no | |
| `error_count` | integer | no | |
| `error_summary` | varchar(2000) | yes | short, redacted |

Indexes: `started_at`, `(job_type, started_at)`, `status`.

### 3.10 `data_sync_errors`

`id`, `sync_run_id` FK, `stage`, `code`, `message`, `entity_type`, `external_id`,
`raw_payload_id` FK nullable, `created_at`. Indexed by run, code, and time. Messages are capped
at 2000 characters and must not contain credentials.

### 3.11 `quarantined_records`

`id`, `provider_id`, `sync_run_id`, `raw_payload_id`, `entity_type`, `external_id`,
`reason_code`, `reason_message`, `payload_excerpt` (JSON, redacted and truncated), `created_at`,
`resolved_at`, `resolution_note`.

Quarantine is a visible holding state. Quarantined records never enter canonical tables and are
never auto-resolved by name similarity.

### 3.12 `match_change_log`

`id`, `match_id` FK, `sync_run_id` FK nullable, `change_type` (`fixture`, `result`),
`changed_fields` JSON (list), `previous_values` JSON, `new_values` JSON,
`provider_last_updated`, `created_at`.

Append-only. It is the audit trail for corrections; it is not a full row snapshot store. The raw
archive remains the complete evidence. Statistics metric rows currently record their
`sync_run_id` but do not append a change-log entry; that gap is listed in
`memory/known-limitations.md`.

### 3.13 `team_match_statistics`

| Column | Type | Null | Notes |
| --- | --- | --- | --- |
| `id` | integer PK | no | |
| `match_id` | FK → `matches.id` | no | |
| `team_id` | FK → `teams.id` | no | |
| `metric` | varchar(64) | no | normalised snake_case provider metric |
| `value` | float | no | numeric value in the documented unit |
| `provider_last_updated` | datetime | yes | |
| `raw_payload_id` | FK | yes | evidence |
| `sync_run_id` | FK | yes | |
| `created_at`, `updated_at` | datetime | no | |

Constraints: `UNIQUE(match_id, team_id, metric)`, `CHECK(value >= 0)`,
`CHECK(length(metric) > 0)`. Indexes: `match_id`, `(team_id, metric)`.

**Zero versus missing:** a measured zero is a row with `value = 0`; an unavailable metric has no
row. No default, fill, or zero substitution is permitted anywhere in the write path.

## 4. Canonical enumerations

| Enum | Values |
| --- | --- |
| `competition_type` | `league`, `league_cup`, `cup`, `playoffs` |
| `match_status` | `scheduled`, `timed`, `in_play`, `paused`, `extra_time`, `penalty_shootout`, `finished`, `suspended`, `postponed`, `cancelled`, `awarded` |
| `match_winner` | `home_team`, `away_team`, `draw` |
| `match_duration` | `regular`, `extra_time`, `penalty_shootout` |
| `sync_status` | `running`, `success`, `partial`, `failed` |

Provider values are translated in the adapter/normalisation layer. An unrecognised value is a
validation failure and is quarantined; it is never mapped to a convenient default.

## 5. Relationships

```
countries 1─* competitions 1─* seasons 1─* matches *─1 teams
                                   │              │
                                   └──────────────┘ (composite FK)
matches 1─1 match_results
matches 1─* team_match_statistics *─1 teams
matches 1─* match_change_log
data_providers 1─* provider_*_mappings
data_providers 1─* raw_payloads
data_sync_runs 1─* data_sync_errors
data_sync_runs 1─* quarantined_records
```

Deletion policy: canonical football records are not deleted by ingestion. `RESTRICT` is used on
identity-bearing foreign keys. Cleanup of operational rows is a separate, audited operation.

## 6. Time handling

- All datetimes are UTC. The application rejects naive datetimes at the boundary and normalises
  aware values to UTC.
- SQLite has no native timezone type; `DateTime(timezone=True)` is used for portability, and the
  read path re-attaches UTC.
- A local kickoff time is only produced at the API edge from an explicit IANA timezone supplied
  by the caller. The platform does not guess a venue timezone.
- `GET /fixtures/today` computes a UTC window from the requested IANA zone; it never compares a
  local calendar date with stored UTC values.
- `provider_last_updated` is preserved separately from `last_synced_at`; they answer different
  questions (when the source changed vs when the platform observed it).

## 7. Update and transaction strategy

- One transaction per bounded sync batch, not per HTTP request. Each item resolution/upsert is a
  unit of work; a rejected item records a quarantine/error row and the batch continues.
- A failed batch rolls back its writes but keeps the run record and errors, which are committed
  in a separate finalisation step.
- Idempotency: resolve by provider mapping, then natural key; compare fields; update only when a
  value changed; always refresh `last_synced_at`.
- Safe upserts are implemented with ORM `SELECT` + `INSERT`/`UPDATE` inside a transaction.
  Unique constraints are the final guard. SQLite-specific `ON CONFLICT` is not used.
- Statistics are upserted per `(match, team, metric)`. A metric that disappears from a later
  payload is retained with its last observation time; deletion requires a reviewed correction.
- Nested transactions are avoided. The sync engine never opens a second session while a write
  transaction is active.

## 8. SQLite-specific operational notes

Enabled on every connection:

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;        -- configurable
PRAGMA synchronous = NORMAL;      -- with WAL
PRAGMA busy_timeout = 5000;       -- configurable
```

- WAL allows readers during a write but still permits only one writer at a time.
- The sync worker is single-instance. Batch sizes are bounded to keep write locks short.
- Backup must use SQLite's backup API or a quiescent copy; copying a file mid-write is unsafe.
- `Alembic` uses `render_as_batch=True` for column changes.
- Database file location is configuration, not source.

## 9. Portability to PostgreSQL

The schema uses only portable SQLAlchemy types (`Integer`, `String`, `DateTime`, `Date`,
`Boolean`, `Float`, `JSON`, `Enum(native_enum=False)`). No SQLite-only SQL is used in business
logic. Moving to PostgreSQL would still require a data migration, sequence resets, index
review, and a full verification run. **Compatibility is not claimed.**

## 10. Deliberately absent tables

| Table | Why absent in Phase 3 |
| --- | --- |
| `venues` | Provider supplies free text without a stable ID; inventing identity is worse than storing text |
| `players`, `match_lineups` | No player model or identity resolution yet; provider lineups are not ingested |
| `match_events` | Not required for the Phase 3 foundation and would need event-level validation |
| `injuries`, `suspensions` | No verified, stable feed; a missing injury must never be shown as "fit" |
| `team_season_statistics` | Derivable from match data later; storing it now would duplicate a calculation |
| `predictions`, `features`, `models` | Phase 4 scope; explicitly excluded |
| `users`, `subscriptions` | Out of scope; no authentication in Phase 3 |
