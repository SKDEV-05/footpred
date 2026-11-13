# Technology Decisions

## Purpose and status

Evaluation record for candidate technologies. Nothing is selected, installed, licensed, or version-pinned; Phase 1 produced documentation only, and no package manager, container runtime, or database was invoked. Every row is **Under evaluation**. Version numbers, prices, and support windows are deliberately absent — UNVERIFIED.

Selection is decided by architecture need first, then by evidence gathered in a later phase. A technology enters the stack only through an ADR after the trigger conditions below are met.

## Selection criteria

Fit to the actual problem; maturity and maintenance activity; operational simplicity for one operator; team familiarity; quality of the data/statistics ecosystem; licensing and redistribution compatibility; exit cost if the choice proves wrong; performance only where it constrains a real workload. Popularity is not a criterion.

## Evaluation table

| Technology | Layer | Purpose | Why it may help | Disadvantages / risks | Class | Earliest sensible introduction | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Python | Language/runtime | Application, ingestion, modelling | One language across API, data and models; strongest statistics ecosystem | GIL limits CPU parallelism; dynamic typing needs tests and discipline | Essential | Foundation | Under evaluation |
| FastAPI | API framework | HTTP API and OpenAPI contract | Typed models via Pydantic, async support, generated docs | Async/sync driver mismatches; framework conventions to learn | Essential | Product surface | Under evaluation |
| Pydantic | Validation | Boundary validation of provider payloads and API contracts | Explicit schemas, actionable validation errors | Runtime cost on large payloads; model-definition churn | Essential | Acquisition | Under evaluation |
| SQLAlchemy | Persistence | Canonical store access and transactions | Mature, explicit transactions, single source of query construction | ORM misuse hides N+1 and lazy loads; complex SQL leaks abstractions | Essential | Acquisition | Under evaluation |
| Alembic | Migrations | Versioned schema migrations | Reviewable, ordered migrations tied to models | Hand-edited migrations; branch conflicts with parallel work | Essential | Acquisition | Under evaluation |
| Pandas | Dataframes | Ad-hoc analysis and small/medium transforms | Ubiquitous, fast to write, familiar | Memory blowup, index semantics, silent dtype coercion | Optional | Intelligence | Under evaluation |
| Polars | Dataframes | Larger transforms with strict typing | Lazy plans, multithreading, explicit schemas | Smaller ecosystem; different API; team familiarity unproven | Optional | When measured volume demands | Under evaluation |
| NumPy | Numerics | Arrays, linear algebra, simulation | Foundation of the statistics and ML stack; stable | Not a data model; dtype and NaN pitfalls | Essential | Intelligence | Under evaluation |
| PostgreSQL | Database | Canonical store, constraints, transactions | ACID, range types, JSONB, window functions for point-in-time queries, single-node simplicity | Operator owns backups, vacuum, tuning; not a job queue | Essential | Acquisition | Under evaluation |
| Redis | Cache/queue | Optional cache or Celery broker | Simple, fast, well understood | Second stateful system; invalidation bugs; risks becoming an accidental source of truth | Optional | Only when justified | Under evaluation |
| scikit-learn | ML | Baselines, calibration, metrics, CV | Reliable implementations; isotonic/Platt calibration; clean evaluation utilities | Easy pipeline leakage; not for large or deep models | Essential (baselines) | Intelligence | Under evaluation |
| XGBoost | ML | Gradient boosting | Strong tabular performance; mature tooling | Overfitting, tuning cost; second GBM library duplicates capability | Optional | After baselines are beaten | Under evaluation |
| LightGBM | ML | Gradient boosting | Fast, memory-efficient, categorical support | Same overfit/leakage risk; duplicates XGBoost capability | Optional | After baselines are beaten | Under evaluation |
| PyTorch | ML | Deep learning, sequence models | Flexible; strong research ecosystem | GPU/ops cost; likely insufficient data volume; poor explainability | Deferred | Evidence-gated, later | Under evaluation |
| Celery | Task queue | Queued execution, retries, routing | Mature retry/routing semantics; multiple workers | Broker dependency and operational surface for one worker | Optional | When retries outgrow scheduler | Under evaluation |
| APScheduler | Scheduling | In-process periodic jobs | Minimal footprint; no broker; adequate for a single worker | No durable queue; retries hand-built; assumes single process | Optional | Acquisition | Under evaluation |
| Next.js | Frontend | Presentation layer | SSR, routing, TypeScript integration | Adds build/runtime surface; premature before contract stability | Deferred | Product surface | Under evaluation |
| TypeScript | Frontend language | Typed UI and API client | Contract types, safer refactors | Duplicate type definitions unless generated from OpenAPI | Deferred | Product surface | Under evaluation |
| Docker | Packaging | Reproducible runtime and deployment | Environment parity; pinned OS-level dependencies | Extra debugging layer; image hygiene; unnecessary on one host initially | Optional | When environment drift appears | Under evaluation |
| Linux | OS | Host runtime | Standard, low-cost, well-supported | Operator owns patching and monitoring | Essential | Foundation | Under evaluation |
| Git | VCS | Code, docs, migrations, config history | Reviewable history and ADR trail | Data and large payloads must stay out of the repository | Essential | Foundation | Under evaluation |

## Leading hypothesis for the core

"Class" below reflects how important a technology would be if the project builds the stack
described here; it is not an adoption decision. Every row remains under evaluation, and
adoption requires an ADR after the trigger conditions are met.

Python + PostgreSQL + FastAPI + SQLAlchemy/Alembic is the working hypothesis, not a decision. The reasoning: one language covers ingestion, statistics, and serving; PostgreSQL provides constraints, transactions, and the window/range queries that point-in-time feature reads require without adding a second store; FastAPI and Pydantic keep the provider and API boundaries typed; Alembic makes schema change reviewable. This combination is also the least surprising to a small team and the cheapest to operate on one host.

The hypothesis fails if measured feature-building or scoring throughput cannot be met vertically, or if provider data volume forces columnar processing earlier than expected.

## When Polars versus Pandas matters

Pandas is adequate for exploratory work and modest transforms, where development speed dominates. Polars becomes relevant when a backfill or feature build exceeds available memory or when strict schemas would prevent silent dtype coercion. The choice is per workload, not per repository: mixing both is acceptable if the boundary is explicit and tested. Neither is required for the first ingestion milestone.

## Redis as optional infrastructure

Redis is a cache and, if Celery is adopted, a broker. It must never hold canonical state: cache loss may cost latency, never correctness. Adoption requires a cache-invalidation design and a rule that every cached value is derivable from PostgreSQL. Until read latency or job throughput is measured as insufficient, Redis is unjustified complexity.

## Celery versus APScheduler

APScheduler fits a single worker with periodic jobs and no broker; retries, locking, and failure visibility must then be implemented explicitly. Celery brings durable queues, retry semantics, and multiple workers at the cost of a broker and more moving parts. The deciding evidence is operational, not stylistic: jobs surviving process restarts, several workers, or retry logic that has already been rewritten twice. Either way, handlers remain idempotent.

## PyTorch, Next.js, and Docker

PyTorch is deferred until gradient boosting and statistical baselines are beaten out-of-sample on stored evaluation data, with enough data volume to justify sequence models and an explanation path that does not collapse into "the network said so". Next.js and TypeScript are deferred until the API contract is stable and UX work is scheduled; otherwise the frontend encodes a contract that is still moving. Docker is deferred as a packaging convenience: valuable once environment drift causes reproducibility failures or a second deployment target exists, but not required to run one process on one host.

## Decision triggers

| Candidate | Evidence that would justify adoption | Prerequisite |
| --- | --- | --- |
| Redis | Measured read latency or queue throughput that PostgreSQL polling cannot meet at acceptable cost | Cache-invalidation design; explicit non-source-of-truth rule |
| Celery | Jobs outlive process restarts, need multiple workers, or retry logic has been reimplemented | Broker operations plan; idempotency audit of handlers |
| Polars | Feature build or backfill exceeds memory or time budget on realistic stored data | Benchmark on the actual dataset, not synthetic volumes |
| XGBoost / LightGBM | A statistical baseline is consistently beaten out-of-sample on stored evaluation data | Fixed split protocol, calibration comparison, one GBM library chosen |
| PyTorch | Demonstrated gain over tree/statistical models on sequence or relational structure | Data-volume assessment, inference cost, explanation path |
| Docker | Environment drift causes reproducibility failures, or a second target host appears | Pinned base image; no secrets baked into images |
| Next.js / TypeScript | API contract versioned and stable; UX implementation scheduled | Client types generated from the OpenAPI schema |
| Pandas / Polars both | — | Choose one primary dataframe library before the feature builder ships; record in an ADR |

## Explicit status note

No installation, dependency resolution, or licence review occurred in Phase 1. Licensing compatibility for providers and libraries remains UNVERIFIED and must precede any adoption.

## Related documents

- [system-overview.md](system-overview.md), [components.md](components.md), [quality-attributes.md](quality-attributes.md).
- [ADR-0001](../decisions/ADR-0001-project-foundation.md), [engineering rules](../../rules/engineering-rules.md).
