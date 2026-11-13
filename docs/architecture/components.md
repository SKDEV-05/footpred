# Components

## Purpose

Catalogue of the proposed modules of a single deployable application plus one worker process. Components are *modules in one codebase*, not services: they communicate through typed in-process interfaces and share one relational database, with ownership rules per [architecture-principles.md](architecture-principles.md). Nothing here is implemented; all contracts are proposals.

Phase labels below indicate the earliest sensible introduction, not a committed roadmap; sequencing is subject to ADR approval. Names in the columns are internal identifiers, not provider or library choices.

| Component | Responsibility | Inputs | Outputs | Owns data | Failure modes | Phase |
| --- | --- | --- | --- | --- | --- | --- |
| Provider adapter layer | Translate each provider's transport and schema into one internal fetch contract | Credentials, endpoints, query parameters | Bytes plus fetch metadata (provider, URL, timestamp, hash) | Adapter configuration only | Auth expiry, rate limits, schema drift, silent field renames | Acquisition |
| Ingestion scheduler | Decide what to fetch and when; dispatch jobs | Fixture calendar, job definitions, retry state | Job runs with idempotency keys | Schedule and cursor state | Missed runs, duplicate dispatch, unbounded backfill | Acquisition |
| Raw payload archive | Preserve exactly what was received | Fetch bytes and metadata | Immutable objects addressable by content hash | Raw payload objects | Disk/write failure after fetch, unmanaged growth | Acquisition |
| Normalization and entity resolution | Validate payloads, map provider entities to internal IDs | Raw payloads, identity map | Canonical records, quarantine entries | Identity map, quarantine | Wrong merges, unresolved entities, silent coercion | Acquisition |
| Historical store | Authoritative canonical history with validity intervals | Canonical records | Queryable fixtures, results, lineups, statistics | All canonical relational data | Constraint violations, partial loads, corrupt corrections | Acquisition |
| Feature builder | Compute point-in-time features from stored history | Historical store, cutoff timestamps, definitions | Versioned feature vectors with lineage | Feature definitions and metadata | Lookahead leakage, non-deterministic aggregation, stale cache | Intelligence |
| Team intelligence | Estimate team strength, form, and consistency as of a cutoff | Features | Team state estimates with uncertainty | Derived team-state records | Small-sample overfit, rating instability, cross-league bias | Intelligence |
| Match intelligence | Derive match context: rest, travel, availability, competition importance | Features, fixture context | Match-context factors with missing-data flags | Derived match-state records | Missing context treated as neutral, unverified inputs | Intelligence |
| Statistical prediction engine | Deterministic mapping from stored inputs to outcome scores | Feature vector, model version, config | Score vector, diagnostics, run record | Model definitions in code; run records | Silent model change, numeric instability, input drift | Intelligence |
| ML engine (deferred) | Learned models where out-of-sample gain over baselines is demonstrated | Feature sets, labels, fixed splits | Versioned artifacts, metrics | Artifacts, experiment records | Leakage in splits, overfit, unreproducible training | Later |
| Probability calibration | Map engine outputs to calibrated probabilities and intervals | Raw scores, stored outcomes, segment definition | Calibrated probabilities, uncertainty, map version | Calibration maps and metadata | Calibration on thin data, drift after rule or provider change | Intelligence |
| Explanation engine | Assemble reasons from verified stored intermediates | Prediction record, feature contributions | Structured explanation, referenced factors | Explanation templates and records | Post-hoc rationalisation, text contradicting numbers | Product surface |
| Evaluation and backtesting | Score stored pre-kickoff predictions against results and baselines | Prediction snapshots, confirmed results, baselines | Metrics, reliability curves, segment error | Evaluation records | Survivorship bias, hindsight edits, unregistered baseline changes | Intelligence |
| API layer | Serve predictions, explanations, track record, and metadata | Stored read models | JSON over HTTP | Read models and views | Unbounded queries, internal detail leakage, stale cache | Product surface |
| Background worker and synchronization | Execute scheduled and queued jobs outside request handling | Job payloads | Execution records, retries, failure states | Job execution records | Duplicate execution, stuck jobs, clock skew | Acquisition |
| Observability and operations | Make failures and data state visible and auditable | Logs, metrics, run records, health checks | Alerts, dashboards, audit trail | Operational telemetry | Alert fatigue, missing data-error signal | Foundation |

## Component boundaries

### Provider adapter layer
Adapters are stateless: they fetch and return, and never write to the canonical store. Every response is archived before parsing, so a parser regression cannot destroy evidence. Out of scope in Phase 1: provider selection, credential handling, pagination and backoff policy values.

### Ingestion scheduler
Dispatch is at-least-once with idempotency keys derived from (provider, entity type, entity id, date window). Re-running a window produces no duplicate canonical rows. Out of scope: distributed scheduling, priority queues, streaming ingestion.

### Raw payload archive
Content-addressed and append-only; corrections create new objects rather than overwriting. Out of scope: retention duration, compression format, cold-tier migration.

### Normalization and entity resolution
Unresolved or invalid entities are quarantined and block downstream use rather than being guessed; every canonical row links to a raw object hash. Out of scope: fuzzy-match thresholds, manual review UI, cross-provider reconciliation strategy.

### Historical store
Single owner of canonical truth. Corrections append versions with reason and actor; no in-place rewrite of history. Out of scope: concrete schema, partitioning, read replicas — schema belongs to the data documentation set.

### Feature builder
Every feature is computed as of an explicit cutoff using only data available then, and is stored with its definition version. Out of scope: online feature serving, a standalone feature-store product, streaming features.

### Team intelligence
Outputs carry sample size and uncertainty; no rating is published without a stated basis. Out of scope: player tracking data, market values, scouting judgements.

### Match intelligence
Each context factor traces to a stored record; absent data remains marked missing. Out of scope: injury-severity models, tactical or formation inference.

### Statistical prediction engine
A pure function of (stored feature vector, model version, config): no network calls, no clock reads, no randomness at inference. Identical inputs must produce identical outputs. Out of scope: model-family selection, hyperparameter tuning, live in-match probabilities.

### ML engine (deferred)
When introduced, it must share the prediction engine's input/output contract, record training snapshots and splits, checksum artifacts, and be promoted only after out-of-sample improvement over the statistical baseline. Out of scope in Phase 1: any ML code, GPU infrastructure, experiment-tracking tooling.

### Probability calibration
Applied after the engine and versioned separately. Recalibration supersedes with a new model version; it never rewrites stored past predictions. Out of scope: method choice, per-competition calibration policy.

### Explanation engine
Read-only over stored predictions and contributions. It cannot alter a probability, and every explanation cites the model version and cutoff it describes. Out of scope in Phase 1: any generation or LLM code, and UI copy. If an LLM is used later for phrasing, it remains read-only over verified stored outputs per `rules/ai-usage-rules.md`.

### Evaluation and backtesting
Consumes immutable pre-kickoff snapshots and confirmed results. Late result corrections are recorded and trigger re-evaluation; stored predictions are never recomputed silently. Out of scope: public leaderboards; market-odds comparison unless licensed ex-ante data is proven available — UNVERIFIED.

### API layer
Read-only for public consumers in early phases. Responses include model version, feature cutoff, and completeness flags; internal errors are not exposed. Out of scope: authentication provider, versioning scheme, pagination limits, write endpoints.

### Background worker and synchronization
Same codebase as the API, separate process. Long-running work is queued, retried with bounded backoff, then surfaced as a visible failure. Out of scope: broker choice, autoscaling, multi-worker sharding.

### Observability and operations
Every job, fetch, parse, score, and evaluation records start, end, counts, and errors; data-quality failures are first-class events rather than log lines. Out of scope: vendor selection, numeric SLOs, dashboard design.

## Related documents

- [system-overview.md](system-overview.md) — context, data flow, deployment sketch.
- [architecture-principles.md](architecture-principles.md) — boundary and provenance rules.
- [quality-attributes.md](quality-attributes.md) — verification of component behaviour.
