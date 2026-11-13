# Architecture Principles

## Purpose

These principles arbitrate design disputes and act as review criteria, not aspirations. Each states the consequence it forces on the codebase. A change that violates one requires an ADR naming the trade-off, per [ADR-0001](../decisions/ADR-0001-project-foundation.md) and [system-design rules](../../rules/system-design-rules.md).

## Principles

### 1. Modular monolith first
The domain is not yet correctly partitioned, and the team is small; distribution would harden guesses into network contracts.
**Implies:** one repository, one deployable, modules imported in-process; no internal HTTP; any module can be extracted later without changing its callers.

### 2. Explicit module boundaries and contracts
Implicit coupling is the dominant maintenance cost inside a monolith.
**Implies:** each module exposes a typed public interface; no imports of another module's internals; no module writes another module's tables; dependencies flow one way (acquisition → storage → intelligence → delivery).

### 3. Data provenance as a first-class requirement
A statistic without a traceable source cannot be audited, corrected, or defended.
**Implies:** every canonical row references the raw object hash and fetch time it derived from; provenance is queryable, not merely logged.

### 4. Point-in-time correctness
Historical accuracy is void if a feature embeds information unavailable before kickoff.
**Implies:** features and predictions store their cutoff; queries filter on event time and, where relevant, ingestion time ≤ cutoff; leakage tests are mandatory for every new feature.

### 5. Idempotent ingestion
Providers retry, schedulers duplicate, operators re-run backfills.
**Implies:** handlers keyed by natural identity plus content hash; replayed deliveries create no duplicate rows and no double-counted statistics.

### 6. Reproducibility of predictions
An output that cannot be regenerated cannot be debugged or defended.
**Implies:** model version, feature-definition version, config, and input snapshot are recorded with every prediction; scoring is a pure function of stored inputs.

### 7. Separate prediction from explanation
Explanations that can influence numbers degrade into post-hoc rationalisation.
**Implies:** the engine emits probabilities and diagnostics; the explanation module reads stored outputs and has no write path to them.

### 8. Calibration is part of the product
A raw score is not a probability; uncalibrated output misstates risk.
**Implies:** calibration maps are versioned artifacts with their own evaluation; the API never labels an uncalibrated score as a probability.

### 9. Fail visibly and loudly
Silent degradation is worse than an outage in an evidence product.
**Implies:** no swallowed exceptions; failed jobs enter a visible failed state; missing data is served as missing, never as zero, average, or stale value.

### 10. Observability by design
Data failures are invisible in HTTP error rates.
**Implies:** every fetch, parse, job run, scoring run, and evaluation emits structured records with counts and durations; row-count reconciliation is routine operation.

### 11. Configuration over hardcoding
Thresholds, cutoffs, endpoints, and weights change faster than code.
**Implies:** parameters live in versioned configuration; secrets live in environment or a secret store; no model coefficient is edited without a versioned artifact.

### 12. Security by default
The system holds licensed data and publishes claims that others may rely on.
**Implies:** least-privilege database roles, read-only public API surface, validation at every boundary, no internal error detail in responses; see [security-principles.md](../security/security-principles.md).

### 13. Testability
Logic that cannot be tested in isolation cannot be trusted with probabilities.
**Implies:** feature and prediction logic run without database or network in unit tests; golden-run tests pin historical outputs; ingestion is tested against recorded payload fixtures.

### 14. Simplicity over cleverness
The operator on call is also the author of the code.
**Implies:** prefer boring, documented mechanisms; no abstraction with fewer than two concrete users; every new dependency states the problem it removes.

### 15. ADR-driven change
Without a record, decisions decay into folklore and get reversed by accident.
**Implies:** structural changes (boundaries, schema ownership, technology adoption, model promotion) require an ADR; ADRs are immutable and superseded, never rewritten.

### 16. No hidden data mutation
Retrospective edits destroy evaluation integrity and the audit trail.
**Implies:** corrections are append-only versions carrying reason and actor; no stored prediction, confirmed result, or archived payload is updated in place.

### 17. No LLM in the numerical prediction path
Probabilistic output must be deterministic, versioned, and auditable.
**Implies:** LLMs may assist with text or developer tooling but never produce, adjust, select, or veto a probability; any future use needs an ADR and a deterministic path that does not depend on it.

## Deliberately rejected principles

| Rejected stance | Why it is rejected here | What we do instead |
| --- | --- | --- |
| "Move fast and break data" | Historical errors are permanent and poison every backtest and calibration | Slow, reviewed migrations; quarantine over guessing; corrections are versioned |
| Microservices from day one | Team size and unknown boundaries make network contracts premature and expensive | Modular monolith with enforceable internal contracts; split on measured pressure |
| LLM-as-oracle | Non-deterministic, unauditable, and cannot supply calibrated uncertainty | Deterministic statistical engine; explanations assembled from stored intermediates |
| Accuracy as a headline promise | Fixed accuracy claims are unfalsifiable across competitions and time | Publish calibration, sample sizes, segment track record, and uncertainty |
| UI-first development | A polished surface over unverified data manufactures false confidence | Data and evaluation before presentation; UX second by charter |
| Schemaless flexibility | Ambiguous types and silent coercion are the main source of statistical error | Explicit schemas, constraints, and validation at ingestion |

## Enforcement in review

- Pull requests state which principles are touched and how the change satisfies them; violations are rejected, not deferred.
- Boundary changes require an ADR approved before implementation; the ADR records alternatives and the reversal condition.
- Data-affecting changes require review by the data engineer: migration, backfill plan, idempotency, and provenance.
- New features or models require leak tests and a recorded baseline comparison; the QA engineer verifies reproducibility evidence.
- Security-relevant boundaries (auth, provider credentials, public endpoints) require security-reviewer sign-off.
- Determinism checks run on scoring code: same inputs, same model version, same output.
- Principles that are routinely waived indicate the text is wrong; amendment happens through ADR, not habit.

## Related documents

- [system-overview.md](system-overview.md), [components.md](components.md), [quality-attributes.md](quality-attributes.md).
- [data rules](../../rules/data-rules.md), [engineering rules](../../rules/engineering-rules.md), [AGENTS.md](../../AGENTS.md).
