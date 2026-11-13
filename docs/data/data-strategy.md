# Data Strategy

## Purpose

This document records the data commitments the platform must satisfy before any storage engine, provider, or pipeline is chosen. It defines logical tiers, ingestion behaviour, time semantics, historical correctness, and entity identity. It is not an implementation plan: no database, object store, scheduler, or data provider has been selected. Binding requirements live in [`../../rules/data-rules.md`](../../rules/data-rules.md); this document explains intent and does not restate those rules.

Audience: data engineers, backend architects, ML researchers, QA. Any later design that cannot be traced to a commitment here is incomplete.

## Data-first principles

| # | Principle | What it requires |
|---|-----------|------------------|
| 1 | Single source of truth | Each fact class has one authoritative record; derived copies are never edited directly. |
| 2 | Raw before transformed | Provider payloads are persisted before parsing, so a parser defect is fixable without re-fetching. |
| 3 | Provenance by default | Every derived value resolves to its inputs, transformation, and code version (see [data-provenance.md](data-provenance.md)). |
| 4 | Idempotent by construction | Replaying an ingest for identical input leaves the system in the same state. |
| 5 | Explicit gaps | Missing, zero, and unknown are distinct states; absence is recorded, not hidden (see [data-quality.md](data-quality.md)). |

Conflict order is deliberate: provenance outranks storage convenience, and an explicit gap outranks a complete-looking table. No ordering below this is negotiable at implementation time without a recorded decision.

## Logical data tiers

| Tier | Responsibility | Typical contents | Mutability | Retention intent |
|------|----------------|------------------|------------|------------------|
| Raw landing | Preserve exactly what the provider returned plus request context | Payload bytes, headers, request parameters, fetch time, hash | Append-only; never edited | Long enough to rebuild normalized and derived layers and to answer audits; duration deferred |
| Normalized | Canonical entities, identifiers, typed and validated fields | Fixtures, teams, competitions, players, events, lineups, results | Versioned corrections only | Full history of identity-affecting and result-affecting changes |
| Derived | Reusable computation over normalized data | Features, aggregates, model inputs, predictions, evaluation outputs | Regenerated from lower tiers and a code version | Regenerable, except predictions and evaluation records, which are retained permanently |

Data moves only downward: raw feeds normalized, normalized feeds derived. No tier reads from a higher tier, and derived outputs never flow back as normalized facts.

## Ingestion patterns

| Pattern | Trigger | Requirements |
|---------|---------|--------------|
| Scheduled incremental sync | Fixture window and provider update cursor | Bounded overlap to catch late edits; idempotent upserts; per-run record |
| Backfill | Historical range requested | Same code path as incremental where possible; rate-limited; explicit range metadata |
| Manual correction | Operator identifies an error | New version with reason and actor; never an in-place edit |
| Late-arriving data | Provider publishes after first ingest | Accepted and versioned; dependent derived artefacts marked stale; recomputation is explicit |

Idempotency requirements:

- Natural keys are deterministic and provider-independent (for example, canonical fixture identity), not surrogate IDs assigned per run.
- Payload and content hashes suppress duplicate re-sends for canonical upserts: an identical payload creates no new canonical record, while a changed payload creates a new version. Fetch observations may still be appended to the raw archive under its retention policy.
- Each run has an ID that appears in provenance; replaying a run is safe and observable.
- A new adapter must pass a replay test (same input twice, same state) before it is enabled.

## Time handling

- All persisted timestamps are UTC. Local kickoff time is stored alongside the venue's IANA timezone identifier, never a fixed offset.
- DST transitions are resolved from the timezone identifier at display time; local times are not the storage form.
- Kickoff changes are versioned. A prediction records the kickoff value known when it was produced.
- Postponed, abandoned, awarded, and void fixtures are explicit statuses, never inferred from missing events or unchanged scores.
- Season and matchday labels are competition- and provider-defined; they are not mapped onto calendar assumptions.
- "Current" is a query over versioned data, not a mutable flag that overwrites history.

## Historical data and point-in-time correctness

Backtests must reproduce what was knowable at decision time. A table that stores only current values destroys that: a late result correction or lineup edit rewrites the past and inflates measured accuracy (lookahead bias). The platform therefore needs effective-dated records (when a fact was true in the world) and ingestion-dated records (when the platform learned it), with as-of queries that separate the two.

Corrections must not retroactively change a stored backtest. If history is replayed with newer knowledge, the replay is a new, labelled experiment with its own results, not an overwrite of the original.

## Entity resolution

- Canonical internal IDs exist for competition, season, team, player, venue, and fixture.
- Provider IDs map many-to-one onto canonical IDs; the mapping is versioned, not edited in place.
- Aliases, abbreviations, transliterations, renames, and relocations are first-class records.
- Merges and splits are reversible, audited, and never silent.
- Low-confidence matches are quarantined for review rather than auto-accepted.
- Resolution confidence is recorded on the mapping at decision time; it is not reconstructed later.

## Storage expectations (conceptual only)

- A relational core is the working assumption for entities, fixtures, events, and versioned relationships. PostgreSQL is the leading candidate and has not been selected.
- Object storage is the natural home for raw payloads and large artefacts.
- Caching is added only after a measured access pattern justifies it; a cache is never authoritative.
- A separate analytical store may become necessary; that is not assumed now.

## Data lifecycle and retention

Raw payloads outlive the parsers that consumed them. Normalized history is retained so point-in-time queries remain answerable. Derived features are disposable and rebuildable; prediction and evaluation records are not. Quarantined data is retained until resolution plus an audit window. Logs and exports are subject to the redaction rules in [`../../rules/security-rules.md`](../../rules/security-rules.md). If personal data ever enters the system, a deletion and export path is required before launch.

## Deferred decisions

- Provider selection and contract terms.
- Database engine, object store, and analytical store.
- Retention durations, partitioning strategy, and archival format.
- Batch versus streaming ingestion for live-adjacent data.
- Whether a feature store is warranted or derived tables suffice.
- Corpus scope: which competitions, seasons, and stat depths are in scope for the first release.

## Related documents

- [Data quality](data-quality.md)
- [Data provenance](data-provenance.md)
- [Provider research](providers-research.md)
- [`../../rules/data-rules.md`](../../rules/data-rules.md)
- [System overview](../architecture/system-overview.md) and [technology decisions](../architecture/technology-decisions.md)
- [`../../AGENTS.md`](../../AGENTS.md)
