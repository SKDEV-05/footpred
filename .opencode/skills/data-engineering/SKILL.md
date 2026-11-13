---
name: Data Engineering
description: Design reliable ingestion, normalization, entity resolution, storage, provenance, and recovery for football data. Use for pipeline design, idempotency, backfills, late-arriving data, and data lifecycle questions.
---

# Data Engineering

## Objective

Make data ingestion and transformation predictable: re-runnable, traceable, and honest about
gaps. A pipeline that silently drops or invents records is a product defect.

## Activation

Use when designing or reviewing: provider ingestion, scheduling, backfills, normalization,
entity resolution, deduplication, historical storage, caching, or recovery.

## Required context

- Source contract: endpoint, payload shape, rate limits, update cadence.
- Target model: entities, keys, required fields, relationships.
- Freshness and history requirements.
- Failure tolerance: what may be delayed, what must never be wrong.
- Retention and licensing constraints on raw payloads.

## Workflow

1. **Model the data before the pipeline**: entities, natural keys, relationships, history.
2. **Land raw payloads first**, unmodified, with fetch metadata and a content hash.
3. **Validate and normalise** into canonical entities with explicit mapping rules.
4. **Resolve identities** (teams, competitions, players, venues) with aliases and review.
5. **Upsert idempotently** using natural keys and versioning; never rely on insert order.
6. **Record provenance** for every derived record.
7. **Design failure handling**: retries, quarantine, dead-letter, alerting, replay.
8. **Define backfill and correction procedures** before they are needed.
9. **Verify with reconciliation** against the source and across sources.

## Detailed procedures

### ETL vs ELT

- **ETL** transforms before loading. Useful when the target schema is strict and the
  transformation is stable.
- **ELT** loads raw first, transforms in the warehouse/database. Better for auditability and
  re-processing when rules change.
- For this project, raw-first landing followed by in-database transformation is the safer
  default: provider payloads are retained, transformations are versioned, and mistakes are
  recoverable without re-fetching.

### Idempotency

- Define a natural key per entity (provider + provider_id, or a canonical composite).
- Use upserts keyed on the natural key; never assume a job runs once.
- Make deletes explicit and soft where history matters.
- Store a deterministic payload hash to detect change versus re-delivery.
- Re-running a job for the same window must produce the same state.

### Incremental sync and watermarks

- Track a watermark per source and entity (last successful update time or cursor).
- Overlap windows deliberately (late corrections arrive after the first fetch).
- Handle clock skew and provider timezone assumptions explicitly.
- Separate "new data" from "corrected data" in logs and metrics.

### Late-arriving and corrected data

- Results, lineups, and events can be corrected after publication.
- Keep versions; expose the effective timestamp and the fetch timestamp.
- Recompute dependent derived data when a correction lands; record which predictions used
  which version.
- Never rewrite a historical prediction to match a later correction without preserving the
  original.

### Entity resolution

- Prefer provider IDs; they are stable within a provider, not across providers.
- Maintain an alias table with source, raw name, canonical ID, confidence, and reviewer.
- Handle: accents and transliteration, abbreviations (FC, CF, AFC), sponsor-prefixed names,
  renamed clubs, reserve/youth teams, and duplicate competition names across countries.
- Never auto-merge on fuzzy match alone; require a threshold and a review path.
- Record merge history so downstream references remain explainable.

### Deduplication

- Fixtures: same competition, season, home team, away team, kickoff (with tolerance).
- Events: same fixture, minute, type, player, and provider event ID.
- Provider re-sends are common; treat them as updates, not new rows.

### Point-in-time correctness

- Store effective-dated attributes (team name, competition membership, ratings).
- For backtesting, reconstruct the state as of a timestamp before kickoff.
- Current-state tables are not valid historical inputs; snapshot or version them.

### Caching

- Cache only derived or expensive results with a clear invalidation rule.
- A cache is never the source of truth.
- Cache keys include model/version and input version.
- Document staleness tolerance per cached item.

### Failure handling

| Failure | Detection | Response |
| --- | --- | --- |
| Provider timeout | Request timeout | Bounded retry with backoff; mark run partial |
| Rate limit | HTTP 429 / documented code | Respect reset; queue; do not hammer |
| Schema change | Validation failure | Quarantine payload; alert; keep raw |
| Partial payload | Missing required fields | Quarantine record; do not partially write |
| Duplicate delivery | Hash match | No-op update; log |
| Correction after publish | Version mismatch | New version; recompute dependents |
| Abandoned/postponed match | Status field | Keep status; exclude from settled stats |

### Backfill

- Backfills are explicit jobs with a scope, a rate budget, and an idempotent target.
- Never backfill into production without a dry run and a row-count reconciliation.
- Record the backfill run, parameters, and outcome.

## Quality checklist

- [ ] Raw payloads are immutable and hashed.
- [ ] Natural keys are defined for every entity.
- [ ] Re-running a job is safe (idempotent).
- [ ] Late corrections produce new versions, not silent overwrites.
- [ ] Entity merges are reviewable and recorded.
- [ ] Point-in-time reconstruction is possible for backtests.
- [ ] Failure paths quarantine data instead of dropping it.
- [ ] Provenance fields are present on derived records.
- [ ] No fabricated or imputed values without an explicit flag.

## Common failure patterns

- Treating a provider's omission as "no data" and a null as zero.
- Keying on mutable names instead of IDs.
- Retrying aggressively against a rate-limited API.
- Overwriting history on correction, destroying auditability.
- Auto-merging teams on fuzzy name similarity.
- Using current standings to backtest past matches.
- Storing only transformed data and losing the ability to reprocess.

## Expected outputs

- Conceptual pipeline design with stages and contracts.
- Entity/key definitions and resolution rules.
- Idempotency and provenance specifications.
- Failure-mode table with detection and recovery.
- Backfill and reconciliation procedures.

## Sources and references

- `docs/data/data-strategy.md`
- `docs/data/data-quality.md`
- `docs/data/data-provenance.md`
- `rules/data-rules.md`

## Limitations

Designs must be validated against real provider payloads in a later phase. Volume, rate, and
latency figures are unknown until measured. This skill does not authorise implementation or
provider access in Phase 1.
