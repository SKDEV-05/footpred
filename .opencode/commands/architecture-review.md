---
description: Review a proposed system design for modularity, reliability, scalability, security, complexity, failure handling, data consistency, observability, and trade-offs.
---

# /architecture-review

Review this design: **$ARGUMENTS**

If no design is named, review the architecture documents in `docs/architecture/` and any
recent proposals. Load the `system-architecture` skill first.

## Evaluation dimensions

For each, state findings and evidence; do not give a generic score.

1. **Modularity** — one responsibility per module; clear ownership; boundaries justified by
   rate of change, failure domain, scaling, consistency, or trust. Flag boundaries with no
   justification.
2. **Maintainability** — could a new engineer understand and change this? Hidden coupling,
   implicit ordering, shared mutable state, magic configuration.
3. **Reliability** — timeouts, retries with backoff, rate-limit handling, partial failure,
   quarantine, idempotency, replay, and visible degradation.
4. **Scalability** — stated assumptions and volumes; where the first bottleneck appears; the
   threshold at which the design must change.
5. **Security** — trust boundaries, input validation, secret handling, least privilege,
   tamper-evidence for predictions.
6. **Complexity** — is each abstraction earning its cost? Is there a simpler option that
   satisfies the same requirement? Flag premature microservices, queues, caches, or patterns.
7. **Failure handling** — what happens when a provider is down, returns partial data, changes
   schema, or sends duplicates? Is failure visible to the user?
8. **Data consistency** — single source of truth, point-in-time correctness, correction
   handling, referential integrity, no silent imputation.
9. **Observability** — can an operator detect ingest lag, validation failure, provider errors,
   stale predictions, and calibration drift? Are logs redacted?
10. **Technical trade-offs** — alternatives considered, reversibility, lock-in, operational
    cost, and what evidence would change the decision.

## Method

1. Restate the design's goal and constraints.
2. Map components, data flows, and trust boundaries.
3. Walk the primary use case end to end (fixture → prediction → evaluation).
4. Adversarially test: provider outage, malformed payload, duplicate delivery, late
   correction, missing lineup, timezone boundary, concurrent jobs.
5. Compare against the simplest viable alternative.
6. Classify findings: **Blocker**, **High**, **Medium**, **Low**, **Nit**.
7. For each finding: location, why it matters, concrete remediation, and residual risk.

## Rules

- Do not invent volumes, latencies, costs, or benchmarks. Mark `TBD` and state the
  measurement needed.
- Do not approve a design that cannot reproduce a stored prediction from stored inputs.
- Do not accept "we will handle errors later" for a data-integrity path.
- Do not require distribution or extra infrastructure without a measured need.
- Do not rewrite the design; identify defects and propose options.

## Output

- A findings list ordered by severity with locations and remediation.
- A one-paragraph verdict: acceptable, acceptable with conditions, or needs revision.
- The decisions that require an ADR.
- Follow-up questions for the owning agent.
