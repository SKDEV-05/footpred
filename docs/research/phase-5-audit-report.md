# Phase 5 Audit Report — Repository State, Contract Boundaries, and Provider Coverage

**Date:** 2026-11-15
**Author:** orchestrator (implementing agent), per the Phase 5 directive §2 mandatory first step
**Status:** Audit complete. Implementation plan and required approvals below.
**Decision affected:** Phase 5 real-data analysis contract change (ADR-0010), historical ingestion scope, statistics abstention policy.

## 1. What was inspected

Per the directive's mandatory first step:

- `AGENTS.md`, `CLAUDE.md`, `README.md`, `PROJECT_STATUS.md`
- All ADRs (`ADR-0001` … `ADR-0009`)
- `memory/current-state.md`, `memory/decisions.md`, `memory/known-limitations.md`, `memory/next-steps.md`
- Existing provider adapter (`apps/backend/app/providers/adapters/football_data_org.py`)
- Database schema and migrations (`0001`–`0004`, `alembic check` clean)
- All intelligence modules (`apps/backend/app/intelligence/`, 1,892 lines)
- Existing Next.js app (`apps/web/src`, 15 files)
- Current API endpoints (`/api/v1` read-only surface)
- Phase 3.1 and Phase 4 audit reports
- Live repository evidence: SQLite row counts, stored seasons, stored results, provider match mappings
- Live provider probes (bounded, read-only, this session; credentials never printed)

## 2. What is genuinely implemented

| Area | State | Evidence |
| --- | --- | --- |
| Phase 3 backend | Complete, not accepted | 247 tests pass; Phase 3 QA verdict FAIL; S-01…S-19 open conditions |
| football-data.org adapter | Complete for fixtures/results | `fetch_matches`, `fetch_match_detail`, `fetch_competitions`, `fetch_teams`, `fetch_seasons` |
| Ingestion pipeline | Complete | raw archive → adapter → normalization → validation → identity → persistence |
| Identity resolution | Complete | exact-match only; ambiguity quarantined; missing = absence, never zero |
| Sync engine | Complete | per-item transactions, quarantine, stale-run sweep, partial/success/failed |
| Read-only API | Complete | `/api/v1` GET endpoints, pagination, error envelope, UTC |
| Intelligence package | Complete, synthetic-only | 84 tests; no I/O; `DataClassification.SYNTHETIC_TEST` enforced |
| Next.js UI | Complete for fixtures | fixture list, filters, search, match detail, honest "Not supplied" markers |
| Local live-data slice | Complete | 367 fixtures, 2 results, 285 teams, 13 competitions, 11 seasons |

## 3. What is incomplete or blocked

| Item | State | Why |
| --- | --- | --- |
| Match statistics ingestion | **BLOCKED — provider** | Free tier returns no `statistics` object (probe: `/matches/555085` has no `statistics` key on either team). The `Statistic Add-On €15` is paid. |
| Head-to-head endpoint | **BLOCKED — provider** | No H2H path verified; the adapter has no H2H capability flag. |
| Historical seasons | **AVAILABLE** | Live probe: `season=2025` returns 380 PL matches; `season=2024` global returns 136 matches in 10 days. Season ID filter returns 404; the year parameter is the working form. |
| Analysis endpoint | **NOT IMPLEMENTED** | No `POST /matches/{id}/analyze` exists. |
| Analysis persistence | **NOT IMPLEMENTED** | No analysis/report table exists. |
| Real-data classification | **REJECTED BY ENGINE** | `types.py:35-36` and `engine.py:49-50` reject any dataset not `SYNTHETIC_TEST`. |
| Public-display licence | **UNVERIFIED** | LIM-006; football-data.org clause 9.1. |
| Phase 3 acceptance | **WITHHELD** | DEC-021, DEC-022; independent re-audit pending. |

## 4. Why the engine rejects real historical datasets

### 4.1 The exact rejection points

1. `types.py:22-23` — `DataClassification` is a single-member `StrEnum`:
   ```python
   class DataClassification(StrEnum):
       SYNTHETIC_TEST = "synthetic_test_data"
   ```
2. `types.py:35-36` — `ResearchContext.__post_init__` raises for anything else:
   ```python
   if self.classification is not DataClassification.SYNTHETIC_TEST:
       raise ValueError("only synthetic test data is permitted in Phase 4")
   ```
3. `engine.py:49-50` — `IntelligenceEngine.analyze` re-checks the dataset classification:
   ```python
   if dataset.classification is not DataClassification.SYNTHETIC_TEST:
       raise ValueError("Phase 4 offline engine accepts synthetic test data only")
   ```
4. Every metric, feature, model, and evaluation entry point calls `require_context(context)`, which propagates the same restriction to the entire package.

### 4.2 Why the restriction exists (and must not be weakened)

ADR-0009 approved Phase 4 as **synthetic-test-only** because no verified real data existed. The restriction prevents a caller from presenting unverified provider data as if it were validated research input. The restriction is a *classification* guard, not a *capability* guard: the mathematics is classification-agnostic.

### 4.3 What a real dataset needs that a synthetic one does not

A real dataset carries claims about the world. The contract must therefore require, for `VERIFIED_REAL`:

- **Provenance**: every `HistoricalMatch` must carry its provider, external id, raw payload id, and observation time.
- **Source attribution**: the dataset must name the provider and the retrieval window.
- **Dataset integrity**: a digest over the canonical materialized rows (already present) plus a provider evidence reference.
- **Point-in-time validation**: `observed_at` must be strictly before `as_of` (already enforced by `HistoricalMatch.__post_init__` and `eligible_history`).
- **Quality checks**: the caller must supply a `CoveragePolicy` assessment result and the raw evidence ids; the engine must not trust a bare label.

## 5. Provider Free-tier historical coverage investigation (directive item 9)

Live probes executed 2026-11-15 (bounded, read-only; responses archived; credentials never printed):

| Probe | Request | Result |
| --- | --- | --- |
| Match detail statistics | `GET /v4/matches/555085` | `200`; `homeTeam`/`awayTeam` contain `crest,id,name,shortName,tla` only — **no `statistics` key** |
| Season by ID | `.../competitions/PL/matches?season=2403` | **HTTP 404** |
| Season by year | `.../competitions/PL/matches?season=2025&status=FINISHED` | **200, 380 matches** with full-time scores |
| Season + date window | `.../competitions/PL/matches?season=2025&dateFrom=2025-08-15&dateTo=2025-08-24` | **200, 19 matches** |
| Global historical dates | `GET /v4/matches?dateFrom=2024-08-16&dateTo=2024-08-25&status=FINISHED` | **200, 136 matches** across CLI, PPL, PD, … |
| Season list | `GET /v4/competitions/PL` | **128 seasons** listed back to 2017 |
| Statistics endpoint | not called | Free tier has no statistics in match detail; a dedicated statistics endpoint was not observed |

**Conclusions:**

1. Historical results are retrievable by season year, in ≤10-day chunks, on the Free plan.
2. Match statistics are **not** retrievable on the Free plan. The `Statistic Add-On` is paid; no purchase is authorised.
3. Head-to-head is **not** retrievable through any verified path on the Free plan.
4. The working historical query form is `season=<year>` + optional `dateFrom/dateTo` + optional `status=FINISHED`.

## 6. Backward-compatible contract design (directive item 3)

Add a second classification member without weakening the synthetic path:

```python
class DataClassification(StrEnum):
    SYNTHETIC_TEST = "synthetic_test_data"
    VERIFIED_REAL = "verified_real_data"
```

Rules for `VERIFIED_REAL`:

1. `ResearchContext` accepts `VERIFIED_REAL` only when the dataset carries a `provider_code`, an `evidence` block (raw payload ids, retrieval window, provider last-updated), and a digest over the materialized rows.
2. The synthetic-only restriction remains for `SYNTHETIC_TEST` research workflows: nothing changes for the existing 84 tests.
3. The engine does not estimate, fit, or calibrate anything for real data. It computes descriptive metrics and supplied-parameter primitives exactly as before; the classification only changes *what the inputs are*, never *what the math claims*.
4. Every report produced from `VERIFIED_REAL` data carries `descriptive_metrics_not_validated_predictors` and `no_real_world_performance_claim` limitations, plus the provider evidence reference.
5. A `VERIFIED_REAL` dataset with missing statistics or missing H2H produces explicit abstention (`insufficient_statistics`, `insufficient_head_to_head`), never a zero-filled feature.

## 7. Security and statistical implications

| Implication | Control |
| --- | --- |
| A mislabelled real dataset could enter the engine | Classification is still caller-asserted (LIM-017); the ingestion boundary must construct `VERIFIED_REAL` only from archived raw payloads with provider ids, never from ad-hoc input |
| Real data could be presented as validated | Reports carry explicit limitations and the provider evidence reference; no accuracy claim is possible |
| Statistics absence could become fabricated zeros | Missing stays missing; the statistics feature is absent, and the report records `statistics_unavailable_on_plan` |
| Provider quota exhaustion | Historical backfill is chunked ≤10 days, budgeted, and incremental; never unlimited |
| Licence | Public display remains blocked (LIM-006); this work is private loopback-only |

## 8. Remaining blockers before implementation (directive item 10)

| # | Blocker | Owner | Resolution |
| --- | --- | --- | --- |
| B-01 | ADR-0010 (contract change) not yet approved | developer | Approve or amend the design in §6 |
| B-02 | Public-display licence (LIM-006, clause 9.1) unresolved | developer | Licence decision before any display beyond private loopback |
| B-03 | Phase 3 acceptance withheld (DEC-021/022) | developer | Independent QA/security re-audit of the exact tree |
| B-04 | Match statistics unavailable on Free plan | provider | Paid add-on or provider decision; not purchasable by agent |
| B-05 | H2H endpoint unverified | provider | No verified path; abstain rather than fabricate |
| B-06 | Analysis persistence schema (new tables) | developer + backend-architect | Migration design approval before any write |

**No model fitting, no real prediction, no performance claim, and no public exposure is made or implied by this audit.**

## 9. Implementation plan (after approvals)

Stage 1 — Contract (ADR-0010 + code):
- Add `VERIFIED_REAL` to `DataClassification` with the evidence requirements in §6.
- Keep `SYNTHETIC_TEST` behavior byte-identical; the 84 existing tests must pass unchanged.
- Add tests for both paths: synthetic acceptance, real acceptance with evidence, real rejection without evidence, mislabelled real rejection.

Stage 2 — Historical ingestion:
- New `sync history` job: chunked ≤10-day windows, `season=<year>`, `status=FINISHED`, incremental by season year, budgeted, idempotent.
- Store results with provider provenance; never overwrite verified results.

Stage 3 — Analysis orchestration:
- `POST /api/v1/matches/{match_id}/analyze` following the workflow in the directive §6.
- Build point-in-time features from stored results; abstain on insufficient samples; store the report with model/feature/dataset versions and digests.

Stage 4 — Markets and report:
- 1X2 bounds, double chance, over/under, BTTS, correct-score distribution from the existing primitives.
- Report schema with provenance, freshness, missing-data warnings, abstention reasons.

Stage 5 — Frontend:
- Match detail + Analyze Match button + report display with honest missing-data markers.

Each stage ends with tests, `compileall`, `alembic check`, and `git diff --check`.

## 10. Required approvals before any code change

1. **ADR-0010** — the `VERIFIED_REAL` classification and its evidence requirements (§6, §7).
2. **Historical ingestion scope** — which competitions and how many seasons, given the 10-request/minute budget (§5).
3. **Analysis persistence schema** — new tables for reports and dataset versions (B-06).
4. **Abstention policy** — confirmation that statistics/H2H absence produces abstention, not zero-filled features (§6 rule 5).

Do not begin model fitting or claim real prediction accuracy. Stop for developer approval on the four items above.
