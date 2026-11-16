# ADR-0010 — Verified real dataset contract for the intelligence package

**Status:** Approved by developer (Phase 5 directive, B-01…B-04), 2026-11-15
**Date:** 2026-11-15
**Owners:** backend-architect, data-engineer, ml-researcher
**Related:** [ADR-0009](ADR-0009-pure-offline-intelligence-boundary.md),
[Phase 5 audit](../research/phase-5-audit-report.md),
`apps/backend/app/intelligence/types.py`

## Context

Phase 4 shipped a pure intelligence package that accepts only
`DataClassification.SYNTHETIC_TEST` datasets (`types.py:22-36`, enforced at every entry
point via `require_context`). That guard was correct for Phase 4: no verified real data
existed, and the developer's approval covered synthetic tests only.

Phase 5 is now approved. The analysis workflow must run the same descriptive metrics and
supplied-parameter primitives on **real stored results** ingested from football-data.org.
The engine currently raises `ValueError` for any non-synthetic classification, so real
analysis is impossible without a contract change.

The developer approved the change subject to strict conditions: preserve the synthetic
workflow, require provenance for real data, never silently downgrade validation, and
abstain on missing statistics rather than fabricate them.

## Decision

Add a second classification member and a real-data evidence contract. The synthetic path
remains byte-identical.

### 1. Classification enum

```python
class DataClassification(StrEnum):
    SYNTHETIC_TEST = "synthetic_test_data"
    VERIFIED_REAL = "verified_real_data"
```

### 2. Real-data evidence contract

A `VERIFIED_REAL` dataset is accepted only when `ResearchContext` carries a
`DatasetEvidence` value satisfying all of:

- `provider_code` — non-empty provider identity (`football_data_org`).
- `raw_payload_ids` — non-empty tuple of archived raw payload ids proving the rows came
  from the raw archive, not ad-hoc input.
- `retrieval_window` — `(retrieved_from_utc, retrieved_to_utc)` with
  `retrieved_from_utc < retrieved_to_utc`, both UTC-aware.
- `payload_digest` — the SHA-256 digest over the canonical materialized rows (already
  computed by `IntelligenceDataset.digest`).
- `observed_from_utc`, `observed_to_utc` — the historical observation window covered,
  UTC-aware, `from < to`.

`SYNTHETIC_TEST` datasets require **no** evidence and behave exactly as before.

### 3. Enforcement points

- `ResearchContext.__post_init__` validates the evidence block only for `VERIFIED_REAL`;
  it raises `ValueError` on missing/malformed evidence. It never weakens the digest or
  protocol checks that apply to both classifications.
- `IntelligenceEngine.analyze` keeps its existing synthetic re-check and adds the same
  evidence re-check for `VERIFIED_REAL`, so the engine and the context validator agree.
- Reports carry `data_classification` and (for real data) the evidence reference, so a
  consumer can see which trust class produced the numbers.

### 4. What does not change

- No estimation, fitting, calibration, or parameter learning is added. The mathematics is
  classification-agnostic; the classification only changes *what the inputs are*.
- `SYNTHETIC_TEST` behavior, tests, and reports are unchanged (verified by the existing
  84 tests passing without modification).
- `require_context` still rejects unknown classifications and non-context inputs.
- Missing statistics and missing H2H remain absence, never zero (B-02, B-03).

## Alternatives considered

- **Remove the classification guard entirely.** Rejected: a bare label cannot prove the
  data came from an archived provider response; it would let ad-hoc input masquerade as
  research data.
- **Keep synthetic-only and fork the package.** Rejected: duplicates the math, violates
  the no-duplicate-modules rule, and splits validation.
- **Trust a caller flag without evidence.** Rejected: same as removing the guard; the
  flag is exactly what LIM-017 records as unenforcible in-process. Evidence ties the
  label to archived raw payloads.

## Consequences

- Real analysis becomes possible with provenance: provider id, raw payload ids, retrieval
  window, payload digest, and observation window are mandatory and visible in reports.
- The ingestion boundary must construct `VERIFIED_REAL` datasets only from archived raw
  payloads; the analysis service must not accept a bare real label from an API caller.
- A `VERIFIED_REAL` dataset with absent statistics or H2H produces explicit abstention
  (`statistics_unavailable_on_plan`, `insufficient_head_to_head`), never a zero-filled
  feature.
- Reports from real data carry `descriptive_metrics_not_validated_predictors` and
  `no_real_world_performance_claim`; no accuracy or profitability claim is possible.
- Digests detect changed input but are not signatures (LIM-018); evidence references are
  audit hooks, not tamper-proof storage.

## Risks

- Classification remains caller-asserted (LIM-017). Evidence narrows the trust gap but
  cannot cryptographically prove provenance in-process; the persistence boundary must
  construct evidence from the archive, never from request input.
- A real dataset with a wrong observation window could leak future results; the existing
  `observed_at < as_of` guard (types.py HistoricalMatch, eligible_history) remains the
  temporal control and is tested for both classifications.
- The Free plan serves no match statistics (LIM-023); statistics-dependent features must
  abstain, which the analysis service must surface explicitly.

## Revisit when

- A second provider is added (evidence must carry that provider's identity).
- Persisted prediction storage is designed (evidence must be stored with each report).
- The synthetic-only research workflow needs a separate audit trail.
