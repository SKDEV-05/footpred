---
name: System Architecture
description: Design system boundaries, module responsibilities, contracts, failure handling, observability, and scalability trade-offs. Use for any structural design, component boundary, or technology-fit question. Avoids premature microservices and unnecessary abstraction.
---

# System Architecture

## Objective

Produce designs that are correct, operable by a small team, and reversible where possible.
Every boundary must have a reason; every external dependency must have a failure path.

## Activation

Use when defining or changing: system layers, module boundaries, data flow, API contracts,
background processing, storage responsibilities, deployment shape, or technology fit.
Not for choosing algorithms (use `statistical-analysis`/`ml-engineering`) or UI structure
(use `anti-ai-slop-design`).

## Required context

- Product requirements and their non-functional priorities.
- Data volumes and freshness needs — if unknown, mark `TBD`, do not invent.
- Team size, operational budget, and phase constraints.
- Existing ADRs and `docs/architecture/`.
- The quality attributes that actually matter (see `docs/architecture/quality-attributes.md`).

## Workflow

1. **State the design question** and the quality attribute it affects.
2. **List constraints** (phase, team, budget, data licensing, latency, compliance).
3. **Map the current system** (or the empty state) before proposing changes.
4. **Separate responsibilities** into modules with one reason to change each.
5. **Define contracts**: inputs, outputs, errors, idempotency, ordering, ownership.
6. **Design failure behaviour** before the happy path.
7. **Evaluate coupling and cohesion** across every proposed boundary.
8. **Compare at least two shapes**, including a simpler one.
9. **Decide and record** in an ADR with consequences and revisit triggers.
10. **Define verification**: how will we know the design works (tests, metrics, load checks).

## Detailed procedures

### Boundary test

A boundary is justified when at least one is true:
- different rate of change (volatile UI vs stable domain rules);
- different failure domain (external provider vs internal computation);
- different scaling profile (batch scoring vs API reads);
- different consistency requirement (raw archive vs derived features);
- different security/trust level.

If none apply, keep it in the same module. Fewer boundaries mean fewer contracts to
maintain.

### Modular monolith defaults

- One deployable application, one relational database, one worker process at the start.
- Modules communicate through in-process interfaces, not network calls.
- Asynchronous work only where latency or reliability requires it (ingestion, scoring
  batches, backfills).
- No message broker, service mesh, or orchestration platform until measured need.
- Design module seams so extraction is possible later, without paying the distribution cost
  now.

### Contract checklist

For each interface define:
- caller and owner;
- input schema and validation rules;
- output schema, including error shape;
- idempotency key or natural key;
- timeout and retry semantics;
- ordering and concurrency assumptions;
- versioning and backward-compatibility policy;
- what happens on partial failure.

### Failure design

- Every external call: timeout, bounded retry with backoff and jitter, circuit-breaking or
  fail-fast decision, and a recorded failure state.
- Prefer failing visibly over returning plausible wrong data.
- Quarantine invalid input rather than dropping it silently.
- Make degradation explicit to the caller (stale marker, missing-field flag, abstention).
- Define recovery: replay from raw payloads, re-run idempotent jobs, reconcile.

### Observability

- Structured logs with correlation/run IDs; no secrets or PII.
- Metrics that answer operational questions: ingest lag, provider error rate, validation
  failure rate, prediction coverage, backtest drift.
- Traces only where a request crosses several modules; avoid instrumentation theatre.
- Alerts must be actionable and tied to a user-visible symptom.

### Scalability reasoning

Estimate with explicit assumptions: fixtures per day, events per match, seasons of history,
predictions per fixture, request rate. If inputs are unknown, present a range and the
decision threshold at which the design changes. Do not optimise for hypothetical scale.

## Quality checklist

- [ ] Every module has one responsibility and an owner concept.
- [ ] Every boundary passes the boundary test.
- [ ] Every external dependency has timeout, retry, and failure behaviour.
- [ ] Data ownership is unambiguous; no shared mutable tables across modules.
- [ ] The simplest viable option was considered and rejected for a stated reason.
- [ ] Predictions are reproducible from stored inputs.
- [ ] Operational cost (people, money, on-call) is stated.
- [ ] An ADR records the decision, alternatives, and consequences.
- [ ] No invented volume, latency, or cost figures.

## Common failure patterns

- **Microservices by default**: distribution added before a measured need.
- **Abstraction astronautics**: interfaces and layers with one implementation and no
  foreseeable second.
- **Shared database coupling**: modules writing each other's tables.
- **Happy-path design**: no failure state for provider errors or partial data.
- **Hidden ordering**: jobs that only work if run in an undocumented sequence.
- **Premature caching**: cache treated as a source of truth.
- **Architecture by popularity**: choosing a stack before stating the requirement.
- **Unbounded retries**: retry storms against a rate-limited provider.

## Expected outputs

- Component diagram and responsibility table.
- Data-flow narrative for the primary use case.
- Interface contracts and failure-mode table.
- ADR draft with alternatives and consequences.
- Open questions with owners.

## Sources and references

- `docs/architecture/architecture-principles.md`
- `docs/architecture/system-overview.md`
- `rules/system-design-rules.md`
- ADR format: `docs/decisions/ADR-0001-project-foundation.md`

## Limitations

Architecture cannot be validated without real workloads. Treat throughput, latency, and
cost figures as hypotheses until measured. This skill does not authorise implementation,
dependency installation, or infrastructure changes.
