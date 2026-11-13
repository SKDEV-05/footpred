# Data Quality

## Purpose

This document defines what "acceptable data" means for the platform and where quality is enforced. It applies to every tier described in [data-strategy.md](data-strategy.md): raw payloads are preserved regardless of quality, but normalized and derived layers may only be built from data that passes the gates below. Nothing here is implemented; it is the acceptance standard future pipelines must satisfy.

Quality is a property of the evidence, not of the presentation. A dashboard that hides gaps is a quality failure even when every visible number is correct.

## Quality dimensions

| Dimension | Definition | Football example | Typical failure |
|-----------|------------|------------------|-----------------|
| Completeness | Required fields and records are present for the scope claimed | A match has a result but no lineup | Lineup-dependent features silently default |
| Accuracy | Values match the authoritative source | Provider reports 2–1; official result is 2–2 after a correction | Wrong probabilities, wrong evaluation |
| Timeliness | Data arrives within its useful window | Post-match statistics appear days late | Features build on partial data |
| Consistency | The same fact agrees across records and sources | Team named "Man Utd" in one endpoint, "Manchester United" in another | Broken joins, split aggregates |
| Validity | Values satisfy domain rules | Negative minutes played; goals outside 0–99 | Corrupt aggregates |
| Uniqueness | Each real-world entity appears once per scope | Same fixture ingested under two provider IDs | Double-counted matches |
| Referential integrity | Every reference resolves | Event references a player absent from the squad table | Orphaned events, dropped rows |

## Null versus zero versus unknown

Three states must remain distinguishable end to end:

| State | Meaning | Example |
|-------|---------|---------|
| `0` | Measured absence, with evidence | A team recorded zero shots |
| `NULL` / missing | Expected but not supplied | Provider omitted the shots field |
| Unknown / not applicable | Cannot be observed or does not apply | VAR data not collected for that competition |

Conflating them corrupts models. If a missing shot count becomes `0`, possession and conversion rates are biased downward and the model learns false scarcity; if an unknown becomes `0`, the same error is hidden one layer deeper. Rules:

- The raw layer preserves exactly what arrived, including absence.
- Normalization never coerces missing to zero; it stores an explicit missing marker with a reason where known.
- Aggregations declare their handling of missing inputs (exclude, propagate, or model) per metric.
- Derived features that depend on missing inputs carry a missingness indicator alongside the value.
- "Zero" is only written when a source explicitly asserts zero or a complete event stream proves it.

## Validation layers

Validation is layered so that a failure is attributed to the narrowest responsible rule.

| Layer | What it checks | Football example | Action on failure |
|-------|----------------|------------------|-------------------|
| Schema and type | Shape, required fields, types, enum membership | `kickoff` parses as a timestamp | Reject record, quarantine payload |
| Domain range | Values within plausible bounds | Goals per team 0–99; minute 0–130 | Reject or flag for review |
| Cross-field | Fields agree within a record | Score equals home plus away goals; lineup size matches formation | Flag, do not auto-correct |
| Referential | Foreign keys and identities resolve | Event's player exists in the canonical player table | Hold until mapping resolved |
| Temporal | Ordering and causality | Events ordered within the match; no data ingested before kickoff claimed as pre-match | Reject or reclassify |
| Cross-source reconciliation | Independent sources agree where both exist | Two providers disagree on full-time score | Escalate; do not pick silently |

Each layer produces a result per dataset version, not a boolean for the pipeline as a whole.

## Duplicate detection

- **Fixture identity**: canonical competition, season, round, home team, away team, and kickoff. Provider IDs are secondary evidence, never the primary key.
- **Event identity**: fixture, sequence, event type, minute, and player where stable. Hashing mutable descriptive fields alone produces false negatives.
- **Provider re-sends**: compare payload hash first, then normalized content hash. Identical payload is a no-op; changed payload is a new version, not an overwrite.
- Detection runs before normalization commits and again before a derived build consumes the data, because duplicates can enter through different paths.

## Stale-data detection

- Expected update windows are defined per data class (fixture list, lineups before kickoff, in-match events, post-match statistics) and are configuration, not hardcoded assumptions.
- A kickoff change invalidates any artefact marked "pre-match" against the old time.
- An abandoned or suspended match is never promoted to a final state because no further updates arrived.
- Staleness is exposed as a data status to downstream consumers; it is never filled with an estimated value.
- A record that stops updating inside its expected window is an incident, not a normal gap.

## Missing-statistics policy

- Mark missing at field level, with the reason when the provider supplies one.
- Never impute silently. No default values, no league averages, no interpolation hidden inside a transformation.
- If imputation is used, it is an explicit model feature with a documented method, version, training basis, and uncertainty; the derived output records that it was imputed.
- Evaluation reports performance separately on observed and imputed inputs so the cost of imputation is visible.
- Imputation may never use information from after the prediction time.

## Quality gates before derived layers

A dataset version may enter derived computation only when:

- identity fields are complete and resolved to canonical IDs;
- referential checks pass for all records the computation will touch;
- temporal ordering is valid for the fixture window;
- scores and aggregates reconcile with event data where both exist;
- duplicate detection is clean for the scope;
- freshness is within the declared window for the intended use.

The gate result is stored with the dataset version. A failed gate quarantines the dataset; it does not produce a partially built feature set.

## Incident handling and quarantine

Quarantine is a separate holding area that no downstream consumer reads. Incidents are classified by impact: identity corruption, result or score error, systematic field gap, isolated field gap. The handling sequence is detect, contain, establish root cause, create a corrected version, reprocess downstream artefacts, and record a post-mortem. Reprocessing is idempotent and labelled so that affected predictions and evaluations can be identified.

## Metrics to track

| Metric | Definition | Primary use |
|--------|------------|-------------|
| Completeness | Required fields present / expected | Detect coverage regressions |
| Null rate | Missing values per field and competition | Distinguish provider gaps from model gaps |
| Duplicate rate | Duplicate records detected / ingested | Validate identity logic |
| Reconciliation mismatch | Conflicting values across sources | Prioritise provider issues |
| Staleness lag | Time since last expected update | Trigger incident response |
| Mapping coverage | Records resolved to canonical IDs / total | Expose entity-resolution debt |
| Quarantine volume | Records held by reason | Track systemic defects |
| Correction rate | Post-publication changes per fixture | Indicates source instability |

## Ownership

The data-engineer owns detection tooling, pipeline enforcement, and quarantine mechanics. The qa-engineer owns acceptance criteria, test evidence, and independent verification that gates are applied. The football-analyst defines domain plausibility bounds. No single role may waive a gate silently; a waiver is recorded with its reason and scope.

## Related documents

- [Data strategy](data-strategy.md)
- [Data provenance](data-provenance.md)
- [Provider research](providers-research.md)
- [`../../rules/data-rules.md`](../../rules/data-rules.md)
- [`../../rules/engineering-rules.md`](../../rules/engineering-rules.md)
