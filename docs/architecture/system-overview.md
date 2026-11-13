# System Overview

## Purpose and status

This document fixes the proposed logical architecture of the Football Intelligence Platform: module boundaries, data flow, trust boundaries, and deployment shape. It is Phase 1 design only. No application code, database, schema, container, or provider integration exists; every component below is a proposal under evaluation, and no component may be described as implemented in product or investor material.

The architecture is optimised for evidence quality, not for feature count: a probability that cannot be reconstructed from stored inputs is treated as a defect. Technology names appear as candidates only; see [technology-decisions.md](technology-decisions.md).

## System context

| Actor | Interaction with the system | Structural consequence |
| --- | --- | --- |
| Developer/operator | Runs ingestion and scoring, inspects failures, changes models, deploys, answers for correctness | Same small team; no dedicated ops function; few runtime components, strong local tooling |
| Future end user | Reads fixture probabilities, explanations, and historical track record | Read-only public surface, explicit uncertainty, no live in-match product in early phases |
| Data provider | Licensed HTTP APIs or bulk files for fixtures, results, lineups, historical statistics | Untrusted, rate-limited, schema-drifting input behind adapters; provider outage must not corrupt state |
| Model runtime | Training and scoring processes executed by the operator on the same host | Versioned artifacts, deterministic inference, no training inside request path |
| Upstream reference data | Competition, team, venue, and timezone identity | Entity ambiguity propagates into every statistic; resolution is a first-class module |

External dependencies: provider availability, licensing, and field semantics; host OS and Python runtime; clock and timezone database; object storage durability. Provider terms may restrict redistribution of raw data and derived statistics; see [security-principles.md](../security/security-principles.md).

## Design constraints

- **Data first.** Correctness of stored history dominates every other property; a fast wrong answer is a failure.
- **Reproducibility.** Each served probability must be reconstructable from archived inputs, recorded model version, and recorded configuration.
- **Small team.** A single operator must be able to run, debug, and recover the whole system without distributed-systems tooling.
- **Cost sensitivity.** One host, one relational database. No always-on analytics cluster, no GPU fleet, no managed stream processor.
- **No premature distribution.** Microservices, event buses, Kubernetes, and multi-region deployment are excluded from the initial architecture; splitting is allowed only on measured pressure.
- **Explainability and uncertainty are product requirements**, not presentation concerns.

## Logical layers and pipeline

Acquisition (adapters, scheduler, worker) → Storage (raw archive, historical store) → Intelligence (features, team/match models, prediction, calibration) → Decision (explanation, evaluation) → Delivery (API, presentation) → Operations (observability) spanning all layers.

```
 providers ──► provider adapters ──► raw payload archive (immutable, content-addressed)
                    │
                    ▼
             ingestion scheduler ──► background worker (locks, retries, job records)
                    │
                    ▼
       normalization + entity resolution ──► quarantine (unresolved / invalid)
                    │
                    ▼
          historical store (canonical, point-in-time queryable)
            │                    │
            ▼                    ▼
      feature builder      evaluation & backtesting ◄── prediction snapshots + results
            │
            ▼
   team intelligence + match intelligence
            │
            ▼
   statistical prediction engine (deterministic) ──► ML engine (deferred, same contract)
            │
            ▼
   probability calibration (versioned maps)
            │
            ▼
   explanation engine (read-only over stored outputs)
            │
            ▼
   API layer ──► presentation (deferred)
```

Module responsibilities and out-of-scope boundaries are defined in [components.md](components.md). This overview does not restate them.

## Background synchronization

All provider contact and all heavy computation happen in a worker process sharing the application codebase, never inside an HTTP request. The scheduler owns *when*; the worker owns *how*. Job classes: fixture discovery, result and lineup polling, historical backfill, feature recomputation, scoring runs, and evaluation runs. Each job run is recorded with start, end, outcome, counts, and error detail; dispatch is at-least-once, so handlers must be idempotent and safe to replay. A single-flight lock per job key prevents duplicate concurrent work. Retries use bounded backoff and then leave the job in a visible failed state for the operator.

Scheduling frequency is per job class and configuration-driven; no intervals are fixed in Phase 1.

## Data flow: one fixture prediction

1. The scheduler detects a fixture in the provider calendar within the active horizon and enqueues discovery plus subsequent polling jobs.
2. The adapter fetches fixture, result, lineup, and statistics payloads; each response is written to the raw archive before parsing, with provider, URL, fetch timestamp, and content hash.
3. Normalization validates the payload against an expected schema, maps provider entities to internal team/competition/player IDs, and either produces canonical records or quarantines the payload.
4. The historical store upserts canonical records with validity intervals and provenance links; corrections append a new version.
5. At a configured cutoff before kickoff, the feature builder computes a feature vector using only records available at that cutoff, and persists it with feature-definition version and lineage.
6. Team and match intelligence derive strength, form, rest, and context estimates with explicit sample sizes and uncertainty.
7. The statistical prediction engine maps the stored vector to outcome scores; the run records model version, config, and input snapshot.
8. Calibration applies the versioned map for the relevant competition/segment, producing probabilities with intervals and calibration provenance.
9. The API serves the prediction with model version, feature cutoff, data-completeness flags, and explanation assembled from stored intermediates by the explanation engine.
10. After the match, results are ingested and evaluation compares the stored pre-kickoff snapshot to the outcome. The snapshot is never edited; metrics and reliability curves accumulate per segment.

## Deployment view

Conceptually: one Linux host, one deployable application image or virtualenv (API + modules), one worker process from the same codebase, one PostgreSQL instance, and object storage for raw payloads (local filesystem acceptable initially). A reverse proxy terminates TLS. This is a logical sketch; hosting, backups, and hardening are undecided. No message broker is required, no service mesh, no Kubernetes, no multi-region.

## Trust boundaries

| Boundary | Crossing | Control direction |
| --- | --- | --- |
| Provider → adapter | Untrusted payloads, credentials in transit | Schema validation, size limits, quarantine; failures never partially applied |
| Adapter/worker → database | Trusted internal writes | Least-privilege role, transactions, constraints, append-only corrections |
| API → end user | Untrusted requests | Read-only endpoints, validation, rate limiting, no internal error detail |
| Operator → system | Privileged actions | Audited commands, no ad-hoc production SQL as normal workflow |
| Model artifacts → prediction | Versioned inputs | Checksums, recorded version, promotion review; artifact swap is a deployment event |

Provenance records that data *came from* a source; it does not certify the source is correct. Provider errors propagate as visible uncertainty, not silent smoothing.

## What is explicitly not decided yet

- Relational schema, table ownership details, and feature storage shape (wide table vs normalised facts).
- Queue/broker choice, retry budgets, and lock implementation.
- Provider selection, licensing terms, coverage, and redistribution rights.
- Model families, feature set, calibration method, and uncertainty representation.
- Authentication mechanism, hosting provider, backup/retention policy.
- API contract and versioning; latency, freshness, and availability targets (see [quality-attributes.md](quality-attributes.md)).
- Whether market/odds data is used; if so, its ex-ante availability requires proof — UNVERIFIED.

## Related documents

- [architecture-principles.md](architecture-principles.md) — binding principles and review criteria.
- [components.md](components.md) — component catalogue, contracts, failure modes.
- [technology-decisions.md](technology-decisions.md) — candidate technologies and adoption triggers.
- [quality-attributes.md](quality-attributes.md) — scenarios, trade-offs, measurement gaps.
- [ADR-0001](../decisions/ADR-0001-project-foundation.md), [system-design rules](../../rules/system-design-rules.md), [data rules](../../rules/data-rules.md), [engineering rules](../../rules/engineering-rules.md).
