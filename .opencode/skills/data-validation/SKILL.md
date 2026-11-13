---
name: Data Validation
description: Specify schema, type, range, referential, temporal, duplicate, and cross-source checks; distinguish null from zero; detect stale data. Use when defining data contracts, quality gates, or investigating data defects.
---

# Data Validation

## Objective

Detect bad data at the boundary, before it corrupts features, predictions, or explanations.
Validation must be explicit, automated where possible, and loud when it fails.

## Activation

Use when defining a data contract, reviewing a dataset, designing ingestion, investigating a
suspicious number, or deciding how to handle missing values.

## Required context

- Schema and field semantics (units, allowed ranges, nullability).
- Source of truth and update cadence.
- Entity keys and relationships.
- Downstream consumers and their tolerance for missing or stale data.

## Workflow

1. **Write the contract**: fields, types, nullability, units, ranges, keys, enums.
2. **Classify nullability**: required, optional, unknown-allowed, not-applicable.
3. **Define checks** by layer: syntax, domain, cross-field, referential, temporal, cross-source.
4. **Set severity**: blocking (quarantine), warning (record and continue), informational.
5. **Implement at the boundary** (later phase), not deep inside consumers.
6. **Quarantine failures** with the raw payload and a reason; never drop silently.
7. **Reconcile** against the source and, where possible, a second source.
8. **Monitor** failure rates and staleness as operational metrics.

## Detailed procedures

### Null vs zero vs unknown

| Value | Meaning | Action |
| --- | --- | --- |
| `0` | Measured zero (e.g. zero shots) | Valid value; use as zero |
| `null` | Not provided / not collected | Do not impute silently; mark missing |
| `unknown` | Deliberately unavailable (e.g. no lineup yet) | Exclude from claims requiring it |
| `not_applicable` | Concept does not apply (e.g. xG for a walkover) | Exclude with a reason |

Conflating these is one of the most damaging data defects in football analytics. A match
with no recorded shots is not the same as a match whose shot data was not collected.

### Check catalogue

| Layer | Examples | Severity |
| --- | --- | --- |
| Schema/type | Field present, correct type, enum membership | Blocking |
| Range | Goals 0-20, possession 0-100, minute 0-120 | Blocking or warning |
| Cross-field | Full-time score equals sum of goal events; lineup count ≤ squad size | Blocking |
| Referential | Fixture references existing teams and competition | Blocking |
| Temporal | Kickoff in expected window; events after kickoff; no future-dated results | Blocking |
| Sequence | Event minutes non-decreasing; halves ordered | Warning |
| Duplicate | Same fixture/event identity appears twice | Blocking or dedupe |
| Cross-source | Result agrees with a second source | Warning + investigation |
| Staleness | No update within expected window | Warning/alert |
| Distribution | Goal rate far outside league range | Warning (possible unit error) |

### Outlier detection

- Use robust statistics (median, MAD) rather than mean/standard deviation for skewed data.
- Distinguish impossible values (negative goals) from surprising but valid ones (a 9-0 result).
- Never auto-delete outliers; quarantine and review.
- For xG, check the provider's documented semantics rather than assuming: most models output a
  probability in [0, 1] per shot, but definitions, caps, and aggregation rules vary. Validate
  against the provider's documented range.

### Staleness

- Define an expected update window per source and entity (e.g. results within hours of the
  final whistle — exact expectation `TBD` until measured).
- Store `fetched_at` and compare to the expected window.
- Mark downstream data as stale; do not present stale probabilities as current.
- Kickoff changes and postponements invalidate pre-match assumptions; detect and re-evaluate.

### Cross-source reconciliation

- Use a second source to confirm results, kickoff times, and team identities.
- Treat disagreement as a signal, not as noise to average away.
- Record which source won and why; keep both values.
- Do not silently prefer the most recent fetch.

### Quality gates

- Raw layer: payload integrity and basic schema.
- Normalized layer: referential integrity and identity resolution.
- Derived layer: completeness thresholds and distribution sanity.
- Model input: feature availability and no-leakage assertions.
- Prediction record: all required inputs present and versioned.

### Incident handling

1. Quarantine affected records with the raw payload and validation error.
2. Estimate impact: which features, fixtures, and predictions are affected.
3. Stop publication of affected predictions if correctness is compromised.
4. Fix the cause (parser, mapping, source) and reprocess idempotently.
5. Record the incident and add a regression check.

## Quality checklist

- [ ] Every field has a type, unit, nullability, and allowed range.
- [ ] Null, zero, unknown, and not-applicable are distinct.
- [ ] Blocking versus warning severity is defined.
- [ ] Failures are quarantined, never silently dropped.
- [ ] Temporal and staleness checks exist.
- [ ] Entity references are validated.
- [ ] Cross-source disagreements are recorded.
- [ ] A regression check is added for each fixed defect.

## Common failure patterns

- `fillna(0)` on football statistics.
- Validating only types and not semantics.
- Treating a missing fixture as a 0-0 result.
- Deleting duplicates by name instead of stable ID.
- Ignoring timezone offsets in kickoff validation.
- Averaging conflicting sources instead of investigating.
- Alert fatigue from non-actionable warnings.

## Expected outputs

- Data contract per entity.
- Validation rule table with severity and error message.
- Quarantine and incident procedure.
- Reconciliation rules.
- Metrics for validation failure and staleness.

## Sources and references

- `docs/data/data-quality.md`
- `docs/data/data-provenance.md`
- `rules/data-rules.md`
- `docs/architecture/quality-attributes.md`

## Limitations

Validation can only detect violations you have specified. Semantic correctness (e.g. a
plausible but wrong lineup) may pass all automated checks. Cross-source reconciliation and
spot audits remain necessary.
