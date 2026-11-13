# Quality Attributes

## Purpose

Defines the quality scenarios the architecture is expected to satisfy and how each will be verified. Numeric targets are not asserted: nothing has been measured, so any figure would be fabricated. Where a target is structural (verifiable by design rather than by load), it is stated as such; where it is operational, it is marked TBD and linked to the measurement that must precede it.

## Scenario table

| Attribute | Scenario | Target / acceptance direction | Verification | Trade-off |
| --- | --- | --- | --- | --- |
| Correctness | A provider corrects a historical result; a previously stored prediction must remain explainable | Stored prediction and its inputs are unchanged; correction is an appended version; downstream evaluations re-run explicitly | Lineage audit from probability to raw payload; reconciliation tests on known fixtures | Corrections do not silently propagate — some aggregates stay stale until re-run |
| Reproducibility | Re-score a past fixture with the recorded model version, config, and cutoff | Identical probabilities and diagnostics for the deterministic path | Golden-run test comparing stored and regenerated output | Requires immutable inputs and versioned artifacts, which slows iteration |
| Data freshness | A result is published by the provider; the platform must reflect it | Visible within TBD after provider publication; depends on polling interval and provider lag — UNVERIFIED | Timestamp delta between provider publication and stored row, measured per job class | Shorter polling increases provider load, rate-limit risk, and cost |
| Availability | API read during a scheduled worker run or provider outage | Predictions already computed remain served; ingestion failure does not take down reads | Fault injection: stop worker, block provider, query API | Single host means planned maintenance windows and no redundancy |
| Latency (API reads) | Fetch one prediction with explanation at the 95th percentile | TBD; must be measured on target hardware. Constraint: a request may not trigger ingestion or scoring | Load test against stored read models; query plan review | Precomputed read models add write complexity and staleness |
| Throughput (batch scoring) | Score all fixtures for one matchday including features | TBD; matchday window is the natural deadline. Must be measured once the feature set stabilises | Timed batch run on representative history | Wider feature sets improve quality but increase runtime and memory |
| Scalability | Historical backfill grows to full provider history | Vertical scaling first; horizontal splitting only on measured CPU, memory, or IO limits | Profile backfill and scoring separately; identify the first bottleneck | Premature partitioning adds operational cost with no product value |
| Maintainability | A new league or provider is added | Changes confined to adapters, identity map, and config, not prediction code | Dependency check: no imports across module boundaries; diff size on a trial change | Clean boundaries cost upfront interface design |
| Testability | Feature or scoring logic changes | Unit tests run without database or network; leakage and determinism tests exist for each new feature | Test suite review; mutation or fixture-based checks on statistical code | Test harnesses for time-dependent logic take effort to build |
| Observability | A job silently ingests zero rows for a day | Failure is visible as an event with counts, not inferred from missing output | Fault injection on a job class; row-count reconciliation review | Full telemetry adds storage and code noise; must be structured, not verbose |
| Security | Public consumer queries the API; credentials sit on the host | No internal errors, no raw payload access, least-privilege database role, secrets outside the repository | Checklist review by security-reviewer; dependency and secret scans in later phases | Read-only public surface limits product features until auth is designed |
| Cost | Run ingestion, storage, and scoring for a season | TBD; single-host budget must be measured against provider pricing — UNVERIFIED | Cost model built from measured volumes, not estimates | Higher coverage and retention increase storage and provider cost |

## Conflicts and trade-offs

**Freshness versus correctness.** Fast publication of provisional results conflicts with the guarantee that answered queries never change. Resolution: distinguish provisional from confirmed states, expose the distinction in the API, and never edit stored predictions to match updated data.

**Richness versus latency.** More context (lineups, availability, rest, travel) improves estimates but increases feature-build time and failure surface. Resolution: tier features by availability at cutoff, record missingness, and accept narrower coverage per fixture rather than late or guessed inputs.

**Model complexity versus explainability.** A better-scoring model that cannot attribute its output is not usable in this product. Resolution: complexity is admitted only with an explanation path and a measurable out-of-sample gain; otherwise the simpler model wins.

**Cost versus coverage.** Covering every competition multiplies provider cost, entity-resolution work, and calibration data requirements. Resolution: depth before breadth — a league's calibration and evaluation must be defensible before adding another.

**Availability versus single-host simplicity.** Redundancy would improve availability but violates the Phase 1 constraint against premature distribution. Resolution: accept planned downtime, keep recovery simple and documented, revisit only on measured user impact.

## Architectural consequences

- Correctness and reproducibility require immutable raw payloads and stored cutoffs; no recompute-on-read path is permitted, even for convenience endpoints.
- Freshness is provider-dependent, so job cadence is configured per entity class rather than as a global constant.
- Single-host availability makes read-only degradation a requirement: the API serves the last known prediction while ingestion is down, with its timestamp visible.
- Explainability constrains model choice before performance does; evaluation records must store diagnostics, not only probabilities.
- Cost and coverage are coupled through provider pricing, so competition scope is a product decision with a measurable operating cost.

## Verification in later phases

- **Correctness, reproducibility:** lineage queries, golden-run comparisons, and replay of recorded payloads in the ingestion test suite.
- **Freshness, observability:** per-job publication-to-storage deltas and zero-row detection, exercised by fault injection before any public release.
- **Latency, throughput, scalability, cost:** benchmark on stored data at realistic volume; no target is written into a service objective until measured.
- **Maintainability:** boundary checks in review and a trial provider/league addition recorded as an ADR.
- **Security:** boundary review, least-privilege role verification, secret scanning, and response-leak tests.
- **Testability:** enforced by the test strategy skill and QA sign-off on determinism and leakage evidence.

## What must be measured before targets are fixed

Provider publication lag and completeness per competition; payload sizes and daily volumes; historical depth available; feature-build time per matchday; scoring time per model version; API query shapes and latency percentiles; correction frequency in historical data; calibration sample size per competition and outcome class; host and storage cost per season; provider pricing and quota terms — UNVERIFIED.

Until these exist, any SLA, freshness bound, or accuracy claim is unsupported and must not appear in product material.

## Related documents

- [system-overview.md](system-overview.md), [components.md](components.md), [architecture-principles.md](architecture-principles.md).
- [testing strategy](../../.opencode/skills/testing-strategy/SKILL.md), [data rules](../../rules/data-rules.md), [security principles](../security/security-principles.md).
