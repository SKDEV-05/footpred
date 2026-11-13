# Quality Attributes

**Status:** Phase 3 verification is limited to local functional tests. No load, latency,
availability, cost, or provider-volume measurement has been performed. Numeric targets remain
unset because any figure would be fabricated.

## 1. Scenarios and Phase 3 evidence

| Attribute | Scenario | Phase 3 verification | Remaining gap |
| --- | --- | --- | --- |
| Correctness | A provider corrects a result after ingestion | Change log records previous/new values; upsert tested | No real correction observed; live behaviour unverified |
| Reproducibility | Re-run an ingest over the same window | Idempotency test: second run creates no duplicate and reports unchanged | No prediction path yet |
| Data integrity | Duplicate fixture delivered twice | Provider mapping + natural key + unique constraint tested | Multi-provider duplicates are intentionally not auto-merged |
| Missing data | Provider omits a statistic or score | Zero-versus-null and absent-metric tests | Real provider omission patterns unverified |
| Freshness | Result published after kickoff | `last_synced_at`, sync status, stale flag implemented | Publication lag not measured |
| Availability | Worker stops; API still serves | API reads only the DB; no provider call in request path | No fault-injection or uptime measurement |
| API latency | Read one fixture list | Functional tests only | No benchmark on realistic volume |
| Throughput | Backfill one season | Not measured | Rate limit and volume unknown |
| Maintainability | Add a second provider | Contract and capability design documented | Not exercised with a second real adapter |
| Testability | Pure normalisation/validation logic | Unit tests run without network/DB | Coverage is not a target; critical paths tested |
| Observability | Sync ingests zero rows | Run counts and errors persisted; health/sync endpoints | No alerts or dashboards |
| Security | API exposed to untrusted clients | Read-only, validated, generic errors, no secrets | No auth/rate limiting: public exposure blocked |
| Cost | Run for a season | Not measured | Provider pricing UNVERIFIED |
| Portability | Move to PostgreSQL | SQLAlchemy-only persistence, portable types | **Not tested; no compatibility claim** |

## 2. Structural guarantees (verifiable by inspection)

- The API module does not import provider or ingestion modules.
- Provider adapters do not import ORM models.
- Every provider response is archived before parsing.
- Every canonical update goes through one ingestion path with validation and identity resolution.
- Raw payloads and change logs are append-only by design.
- Statistics cannot represent "missing" as zero: absence is the absence of a row.
- Default API list queries are bounded by date or page size.

## 3. Trade-offs

**Correctness versus freshness.** A provisional score is not stored as a final result. The
platform may show a fixture without a score for longer, but it will not later rewrite a "final"
result silently. Corrections append history.

**Coverage versus identity certainty.** Ambiguous teams/matches are quarantined instead of
merged. Coverage is lower, but a wrong merge would corrupt every downstream statistic.

**Simplicity versus throughput.** One SQLite writer and one worker are simple and adequate for
the current workload. They will not scale to concurrent write-heavy use; the migration trigger is
documented rather than pre-solved.

**Explainability versus model freedom.** Phase 4 model choices are constrained by the need to
attribute outputs. No model is admitted just because it scores well.

**Test depth versus breadth.** Tests focus on validation, identity, idempotency, missing data,
and failure paths, not on a coverage percentage.

## 4. Measurements required before targets are set

- Provider publication lag and completeness per competition.
- Real historical depth and correction frequency.
- Payload sizes and daily request volume under the chosen plan.
- API query latency at the 50th/95th percentile on stored data.
- Backfill duration and rate-limit headroom.
- Sync batch duration and SQLite lock wait time.
- Database and archive growth per season.
- Provider cost per season for the chosen coverage.

Until these exist, no SLA, freshness bound, accuracy, or scale claim may appear in product
material.

## 5. Verified locally

- The test suite executes against temporary SQLite databases and mocked HTTP transports.
- Alembic `upgrade head` creates the schema, and a drift test compares migrated tables with the
  ORM metadata.
- No test requires a paid API or real credentials.
- Actual test results are recorded in `PROJECT_STATUS.md`; they are not asserted here.

## Related documents

- [system-overview.md](system-overview.md), [components.md](components.md),
  [data-flow.md](data-flow.md), [security-architecture.md](security-architecture.md)
- `docs/guides/testing.md`, `rules/data-rules.md`, `rules/system-design-rules.md`
