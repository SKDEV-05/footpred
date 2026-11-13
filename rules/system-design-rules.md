# System Design Rules

Binding rules for architecture and system structure. They assume the default shape: a modular
monolith with one relational database and a background worker, deployed simply.

---

## S1 — Modular monolith first

Start with one deployable application and one worker.

MUST NOT introduce without a measured requirement and an ADR:
- microservices or independently deployed services;
- a message broker or event streaming platform;
- a service mesh, orchestration platform, or multi-region topology;
- a separate feature store or vector database.

Design module seams so extraction is possible later; do not pay the distribution cost now.

## S2 — Boundaries must be justified

A module boundary is justified only by at least one of:

- different rate of change;
- different failure domain;
- different scaling profile;
- different consistency requirement;
- different trust or security level.

If none apply, keep the code together. Fewer boundaries mean fewer contracts to maintain and
fewer ways to be inconsistent.

## S3 — Explicit ownership

- Every table and dataset has exactly one owning module.
- Other modules read through a defined interface, not by writing the owner's tables.
- Shared mutable state is prohibited.
- Cross-module transactions are avoided; prefer explicit state machines and idempotent steps.

## S4 — Contracts before implementations

Every module interface defines:
- inputs and validation rules;
- outputs and error shape;
- idempotency or natural key;
- timeout and retry semantics;
- ordering and concurrency assumptions;
- versioning and compatibility policy.

Contracts are tested. An undocumented behaviour is not a contract.

## S5 — Deterministic computation

Given the same stored inputs and parameters, a prediction must produce the same output.

- Separate data retrieval from computation.
- No hidden dependence on wall-clock time, random seeds, environment, or mutable global state
  inside the prediction path.
- Record the version of every input and transformation.
- The explanation layer is read-only over computed results and cannot alter probabilities.

## S6 — Failure handling is designed

For every external dependency:
- timeout;
- bounded retry with exponential backoff and jitter;
- respect for rate limits and reset headers;
- a defined behaviour when retries are exhausted;
- a visible stale/degraded state.

For internal jobs:
- idempotency;
- partial-failure visibility;
- quarantine for invalid input;
- replay from raw data;
- no unbounded queues or retry storms.

## S7 — Data flow is one-directional where possible

Raw → normalized → derived → model input → prediction → evaluation.

- Downstream modules do not mutate upstream data.
- Corrections create new versions and trigger explicit recomputation.
- Predictions are immutable once stored; evaluation references them, never edits them.

## S8 — Point-in-time correctness

- Historical features are computed from data available before the prediction timestamp.
- Current-state tables are not used as historical inputs.
- Effective-dated attributes are versioned.
- Backtests use the same reconstruction path as production.

Violating this rule invalidates every evaluation result derived from it.

## S9 — Observability by design

Every module exposes enough to answer:
- is it running, and how fresh is its data?
- how many records succeeded, failed, or were quarantined?
- what is the provider error rate and latency?
- how many predictions were produced, abstained, or served stale?
- has calibration drifted on settled predictions?

Logs are structured and redacted. Metrics are tied to user-visible symptoms. Alerts must be
actionable; no alert without a documented response.

## S10 — Security and trust boundaries

- Validate input at every boundary, including provider payloads.
- Secrets never enter source, logs, prompts, or error messages.
- Least privilege for database roles, provider keys, and agent permissions.
- Prediction records are tamper-evident and access-controlled.
- See `rules/security-rules.md` for the binding controls.

## S11 — Scalability claims require numbers

- State assumptions: fixtures/day, events/match, seasons of history, predictions/fixture,
  request rate.
- If unknown, give a range and the threshold at which the design changes.
- Do not optimise for hypothetical scale.
- The first bottleneck must be identified and measured, not guessed.

## S12 — Configuration over hardcoding

- Environment-specific values come from configuration, not source.
- Required configuration fails closed at startup.
- No magic numbers in model or data logic without a named constant and a rationale.
- Configuration is documented by name; values and secrets are never committed.

## S13 — Reversibility and decision records

- Prefer reversible choices for uncertain requirements.
- Record significant decisions in an ADR with alternatives and consequences.
- State the evidence that would trigger a revisit.
- Do not change an approved architecture silently; supersede the ADR.

## S14 — Simplicity in operations

- One database, one application, one worker until proven insufficient.
- Prefer scheduled jobs over always-on infrastructure where latency allows.
- Backups, restore tests, and retention are designed before production, not after an incident.
- Operational runbooks are written for anything that can fail at 2 a.m.

## S15 — Testing shape follows risk

- Pure logic: unit and property-based tests.
- Boundaries: contract and integration tests.
- Data: quality and reconciliation tests.
- Models: temporal backtests and calibration checks.
- Whole pipeline: reproducibility and end-to-end tests.

Correctness of data and probabilities outranks coverage percentage.

---

## Enforcement

Architecture reviews (`/architecture-review`) check S1-S15 explicitly. Any exception requires
an ADR and developer approval.

## Related documents

- `docs/architecture/architecture-principles.md`
- `docs/architecture/system-overview.md`
- `docs/architecture/components.md`
- `docs/architecture/quality-attributes.md`
- `rules/engineering-rules.md`
- `rules/data-rules.md`
