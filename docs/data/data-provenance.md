# Data Provenance

## Purpose

Every number the platform displays, evaluates, or feeds to a model must be traceable to the bytes it came from, the code that transformed it, and the time it was known. Without that chain, a correction cannot be distinguished from a bug, a backtest cannot be reproduced, and a published probability cannot be defended. Provenance is therefore a product requirement, not an operational nicety.

This document defines the provenance record and lineage model. Phase 3 implements raw payload
rows, sync-run parameters, raw payload links on normalized statistics/errors/quarantine where
available, and content-digest verification. Full historical versioning and provider correction
lineage remain deferred.

## Provenance record fields

| Field | Meaning | Notes |
|-------|---------|-------|
| Provider | Source system or dataset | Includes dataset name for open data |
| Endpoint / resource | Exact path, query, or file identifier | Not a generic label such as "fixtures" |
| Request parameters | Everything that changes the response | Pagination, season, competition, filters |
| Fetched at | UTC timestamp of retrieval | Distinct from the provider's own timestamps |
| Payload hash | SHA-256 digest of the stored raw bytes | Recomputed on archive reuse and read |
| Schema version | Expected payload shape at parse time | Bumped when the contract changes |
| Parser version | Code version that produced normalized fields | Separate from overall application version |
| Ingest run ID | Identifier for the execution that stored the payload | `data_sync_runs` stores effective parameters and timestamps |
| Transformation ID | Identifier for each normalization or derivation step | Must be resolvable to code |
| Code version | Commit or artefact version that executed | Includes model and feature code where relevant |
| Source record ID | Provider's identifier for the entity | Stored even when unstable, with the instability noted |

## Lineage model

The chain is fixed even as implementations change:

```text
raw payload
  -> normalized record (versioned)
  -> feature set (as-of snapshot)
  -> model input vector
  -> prediction record
  -> evaluation result
```

Each edge stores: transformation ID, code version, input snapshot IDs, and the time the output was produced. A record may have many inputs; lineage is a graph, not a single parent link.

## Worked example: one fixture's 1X2 probability

1. The provider returns a fixture payload. It is stored verbatim with request parameters, fetch time, and payload hash; the ingest run is recorded.
2. The parser creates a normalized fixture version, resolving teams and competition to canonical IDs. The version links to the raw payload and parser version.
3. A feature build selects historical matches known before kickoff, computes home and away attack/defence rates, and writes a feature set tagged with the as-of time and the normalized versions used.
4. The model input vector is materialised from that feature set, with the feature definition version and model version attached.
5. The prediction record stores the probability triple, model and calibration versions, input vector ID, creation time, and the kickoff time known at creation.
6. After the match, the evaluation record links the prediction to the final result version and records the scoring rule applied.

Any step can be re-run and compared. If the provider later corrects the fixture, a new normalized version appears; the existing prediction still points to the original input snapshot.

## Immutability and audit

- Raw payloads are write-once. A re-fetch records a new fetch observation; where the content hash is identical it may reference the existing stored bytes instead of duplicating them, but it never creates a new canonical record. The observation time remains evidence even when the bytes do not change.
- Corrections create a new normalized version with a `supersedes` link and a reason. Previous values remain queryable.
- Deletions are tombstones with actor, reason, and time; rows are not silently removed.
- No transformation may overwrite its own output in place when that output has been consumed downstream.
- Audit query: given a prediction ID, retrieve every input, transformation, and version that contributed to it, in order.

## Reproducibility requirements

A prediction is reproducible when, from stored inputs and identified code, the same output can be regenerated:

- raw inputs are retained and addressable;
- exact code versions for parsing, features, model, and calibration are recorded;
- parameter sets and feature definitions are versioned, not edited in place;
- random seeds are stored where stochastic methods are used;
- dependency environments are locked or captured;
- ordering is deterministic where the method is order-sensitive;
- if a model is genuinely non-deterministic, the produced output and seed are stored and the limitation is documented.

Reproduction is verified by rebuilding in a clean environment and comparing outputs, not by assuming determinism.

## Retention and access

Raw payloads and provenance rows are retained longer than the derived artefacts they support.
Phase 3 filters sensitive request parameters and uses content-addressed paths, but does not
implement deletion or automated retention. Retention duration and deletion ownership remain
blocked on provider licensing. Existing payloads must not be deleted automatically. Provenance is
read-mostly and local operator access is assumed; public exposure is rejected.

## Relationship to backtesting and point-in-time correctness

Backtesting consumes feature snapshots that represent knowledge as of a stated time. Provenance proves which snapshot was used and when it was created, which is the difference between a genuine out-of-sample result and a reconstruction that has seen the future. When historical data is corrected, existing prediction records are not rewritten; a replay produces new records under a new experiment identifier and is reported separately.

## Open questions

- Which hash algorithm and canonicalisation rule to use for payload identity.
- Whether model binaries are retained or only version identifiers plus parameters.
- How to version exploratory notebooks and one-off analyses that influence features.
- How granular transformation IDs must be before they stop being useful.
- Whether full payload retention is affordable at the intended corpus size; unquantified.
- How to reference provider records that have no stable identifier.
- Whether provenance for evaluation results needs the same depth as provenance for predictions.

## Related documents

- [Data strategy](data-strategy.md)
- [Data quality](data-quality.md)
- [Provider research](providers-research.md)
- [Components](../architecture/components.md) and [quality attributes](../architecture/quality-attributes.md)
- [`../../rules/data-rules.md`](../../rules/data-rules.md)
- [`../../rules/engineering-rules.md`](../../rules/engineering-rules.md)
