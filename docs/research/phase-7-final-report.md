# Phase 7 — Final Report

**Date:** 2026-11-17
**Author:** implementing agent (orchestrator role)
**Status:** Engineering scope delivered and self-verified. **Not independently accepted.**
**DoD verdict:** **PARTIAL** (see §7).
**Phase 8 recommendation:** **do not approve the betting-analytics phase** (§8).

---

## 1. Before

At the start of this phase the repository at `4aed17d` contained a working private analysis
stack and a broader evaluation engine than any status document described.

Verified before any change:

- Git HEAD `4aed17d` ("phase 7 audit") on top of `d3a9490` ("pahse 7"); all Phase 7 work
  uncommitted.
- 265 backend tests passing — **not** "265 passed, 2 failed" as one status document claimed.
- Alembic `0006 (head)`, `alembic check` clean.
- 5,322 stored matches, 4,905 finished results, 4,892 regulation results usable by models,
  all matches linked to an archived payload, 11 competitions with matches.
- `poisson-v1.1.0` serving the live analysis path; Dixon-Coles and Elo implemented but
  reachable only from the evaluation engine.
- A persisted 970-match multi-competition evaluation already existed (run 1), but had no
  dashboard, no comparison UI, no model selector, and no tests covering the new model code.
- Two untracked modules (`validation.py`, `calibration.py`) and six `phase-8-*.md` documents
  describing an odds/EV/paper-betting platform that did not exist.
- Memory and `PROJECT_STATUS.md` described Phase 5 or Phase 8, neither of which matched the
  code.

## 2. Found

### 2.1 Real gaps

1. No way to request DC or Elo from the analysis API. Every report was Poisson, so a
   "comparison" would have been the same model three times.
2. No comparison endpoint and no UI to compare models on one fixture.
3. No evaluation dashboard; the persisted runs were visible only through JSON.
4. No tests for `fit_rho`, the Davidson mapping, the multi-model engine, evaluation
   persistence, or the comparison path.
5. A real 500: comparison responses nested per-competition model blocks without `model_id`
   and `model_version`, which the strict schema rejected.

### 2.2 Documentation defects (the larger risk)

| Claim found | Reality |
|---|---|
| Six `phase-8-*.md` files: odds, EV, paper betting, best bets "implemented" | No table, endpoint, component or test existed |
| `memory/current-state.md`: `validation.py` implements protocols A–G; `calibration.py` implements calibration | Both untracked, imported by nothing, untested duplicates of `backtest.py` |
| "970 matches across all 13 competitions" | 11 competitions contribute; EC/WC have no stored matches |
| "265 passed, 2 failed" | 265 passed, 0 failed |
| "Evaluation API `/api/evaluation/...`" | Prefix is `/api/v1/evaluation` |
| "Frontend includes evaluation dashboard" | No `/evaluation` route existed |
| `PROJECT_STATUS.md`: "265 tests", "`0005 (head)`" | 265 tests at the time, `0006 (head)` |

### 2.3 Data and model facts established

- The corpus is one backfill observed on 2026-11-16. `resolved_at` is ingestion time, not
  provider publication time. Every historical observation is a reconstruction.
- The 3 h eligibility horizon is a documented retrospective proxy.
- DC on this corpus is indistinguishable from Poisson; Elo is directionally worse. Neither
  supports a default change.

## 3. Changed

### 3.1 Backend

| File | Change |
|---|---|
| `app/intelligence/model_selection.py` | **New.** `MODEL_SPECS`, `require_model_spec`, `replay_elo`, `_dixon_coles_prediction`, `_elo_prediction`, `compute_model_prediction`. The only key→implementation map; unknown key raises before computation. |
| `app/api/v1/endpoints/analysis.py` | `model` query parameter; `POST /matches/{id}/comparison`; `NotFoundError` fixed where it was returning 500; permissive model parameters; Poisson-only embedded evaluation. |
| `app/api/v1/endpoints/evaluation.py` | Minor correction to the endpoint surface. |
| `app/intelligence/backtest.py` | `result_is_available(...)` extracted as a tested rule; multi-model engine; protocol settings in the report. |
| `app/intelligence/models/dixon_coles.py` | `fit_rho` filters `kickoff_utc < reference_kickoff` internally; `rho` bounded and clipped to the admissible interval. |
| `app/schemas/analysis.py` | Comparison schemas; `model_parameters: dict[str, Any] | None` so Elo need not publish Poisson-shaped fields. |
| `app/schemas/evaluation.py` | `NestedModelMetricsOut` with optional nested identity — fixes the real 500. |
| `app/intelligence/validation.py` | **Deleted.** Unreferenced, untested duplicate of `backtest.py`. |
| `app/intelligence/calibration.py` | **Deleted.** Same, and depended on `validation.py`. |

### 3.2 Tests (265 → 321 passing)

| File | Tests | Coverage |
|---|---:|---|
| `tests/phase7_support.py` | — | Shared builders and fixtures |
| `tests/unit/test_phase7_models.py` | 26 | Dispatch and no-fallback, DC normalisation/determinism, rho bounds/abstention/leakage guard, Elo point conservation, pre-match ratings, simultaneous kickoffs, duplicate-team rejection, Davidson bounds, outcome indexing |
| `tests/unit/test_phase7_backtest.py` | 16 | Eligibility boundary (+3 h / −1 s), naive timestamps, negative horizon, identical match set, abstention, determinism, calibration blocks, seeded intervals, identity reporting, persistence semantics |
| `tests/integration/test_evaluation_api.py` | 5 | Run/latest/runs/{id}, idempotency, unknown id, unavailable corpus |
| `tests/integration/test_analysis_api.py` | 11 → 20 | Model selection, unknown model 422, comparison lifecycle, missing report 404, Poisson-only evaluation |

### 3.3 Frontend

| File | Change |
|---|---|
| `apps/web/src/app/evaluation/page.tsx` | **New.** Dashboard rendered from persisted runs only: provenance, overview, paired differences, per-outcome calibration, per-competition, per-season, timeline, run list, loading/error/empty states. |
| `apps/web/src/components/MatchAnalysisPanel.tsx` | Model selector, "Analyze with …", "Compare all models", comparison table, model-aware copy (Elo produces no xG/markets), generic parameter rendering, report cleared on model change. |
| `apps/web/src/app/layout.tsx` | Navigation links to `/evaluation`; mobile nav visible. |
| `apps/web/src/lib/api.ts`, `apps/web/src/types/index.ts` | Model, comparison and evaluation types/clients. |

No schema migration was required; `0006` remains head.

### 3.4 Documentation and memory

New:

- `docs/research/phase-7-baseline-audit.md`
- `docs/research/phase-7-independent-model-review.md` (internal, explicitly not independent)
- `docs/research/phase-7-dixon-coles-research.md`
- `docs/research/phase-7-multi-competition-backtest.md`
- `docs/research/phase-7-model-comparison.md`
- `docs/research/phase-7-commercial-readiness.md`
- `docs/research/phase-8-betting-proposals-rejected.md`
- this report

Rewritten:

- `docs/research/phase-7-actual-project-status.md` — corrected 13→11 competitions, 289→321
  tests, real API paths, real dashboard status.
- `PROJECT_STATUS.md` — Phase 7, 321 tests, `0006`, evaluation results, explicit Phase 8
  rejection.

Memory:

- `memory/current-state.md`, `memory/next-steps.md`, `memory/known-limitations.md`,
  `memory/decisions.md` (DEC-028 model selection, DEC-029 evaluation protocol, DEC-030 Phase 8
  rejection and module deletion).

Deleted:

- The six false `docs/research/phase-8-*.md` documents (retained in git history at `4aed17d`),
  replaced by one frozen-proposal record.

### 3.5 Decisions that required judgement

| Decision | Choice | Why |
|---|---|---|
| Keep or delete `validation.py` / `calibration.py` | **Delete** | No imports, no tests, duplicate logic; keeping two engines creates two truths |
| Comparison verb | **POST** | It computes and persists reports; GET would misstate side effects |
| Unknown model status | **422 `unknown_model`** | It is a client error, not a record-validation or server error |
| `model_parameters` type | Permissive mapping | Elo reports ratings; forcing Poisson fields would fabricate structure |
| Non-Poisson embedded evaluation | `null` | A Poisson measurement attached to Elo would misdescribe it |
| Phase 8 documents | Delete, keep proposals | False status reports are worse than no document |
| Default model | Poisson unchanged | No evidence supports a change; DC indistinguishable, Elo not better |

## 4. Verification

All commands were executed on 2026-11-17 in this working tree.

| Check | Command | Result |
|---|---|---|
| Full backend suite | `cd apps/backend && PYTHONPATH=. ../../.venv/bin/python -m pytest` | **321 passed**, 0 failed, 0 skipped, 1 third-party Starlette/httpx deprecation warning |
| Alembic current | `.venv/bin/python -m alembic current` | `0006 (head)` |
| Alembic drift | `.venv/bin/python -m alembic check` | "No new upgrade operations detected." |
| Type check | `cd apps/web && npx tsc --noEmit` | Clean, exit 0 |
| Production build | `npm run build` | Passes; `/evaluation` emitted |
| Lint | `npm run lint` | 7 pre-existing errors (six `react-hooks/set-state-in-effect`, one impure-function-in-render) in `page.tsx`, `MatchDetailClient.tsx` and the `MatchAnalysisPanel` mount effect; the new evaluation page and types add no error |
| Evaluation recompute | `run_multi_competition_backtest` on the loaded corpus | `models` and `comparisons` byte-equal to run 2; only `dataset.observed_to` differs (it records the load time) |
| Evaluation idempotency | `evaluate_corpus` twice at the same checkpoint | Same row id `2`, same digest `48bc547bf6a88850…`, no third row |
| Comparison lifecycle | `POST /api/v1/analysis/matches/410/comparison` twice | 3 models, one digest `2e2120e17f474329…`, reports #37/#28/#27 reused |
| Unknown model | `POST /api/v1/analysis/matches/410?model=not_a_model` | 422 `unknown_model`, nothing persisted |
| Responsive | `/evaluation` and `/matches/3` at 375, 390, 430, 768, 1024, 1280, 1440 px | No page-level overflow; analysis comparison table scrolls internally below ~700 px; no `NaN`/`undefined`; Elo report shows no xG/market numbers |
| Provenance | Dataset construction | `VERIFIED_REAL` requires provider, archived payload ids, windows and digest; missing evidence raises |

### 4.1 Reproduced evaluation (run 2)

`phase7-v1` / `evaluation-v1.2.0`, dataset `ds_corpus_61252c4622bbc0db`, digest
`48bc547bf6a88850…`, **970 matches**, 11 competitions, 2026-02-25T20:00Z →
2026-11-14T23:30Z.

| Model | Brier | Log loss | Skill | ECE | Top-pick |
|---|---:|---:|---:|---:|---:|
| Poisson | 0.5831 | 0.9828 | 0.1253 | 0.0254 | 51.55% |
| Dixon-Coles | 0.5829 | 0.9821 | 0.1256 | 0.0258 | 51.34% |
| Elo | 0.5911 | 0.9916 | 0.1133 | 0.0375 | 51.55% |
| Frequency | 0.6405 | 1.0592 | 0.0393 | 0.0143 | 45.36% |
| Uniform | 0.6667 | 1.0986 | 0 | 0.0802 | 45.36% |

Paired Brier vs Poisson: DC **+0.0002** [−0.0009, +0.0013]; Elo **−0.0080**
[−0.0195, +0.0040]; uniform **−0.0835** [−0.1051, −0.0619]; frequency **−0.0573**
[−0.0755, −0.0388].

### 4.2 What the verification does not cover

- It does not prove provider-side score correctness (one source, no cross-check).
- It does not prove behaviour under live/latency conditions (no live provider call in tests).
- It does not prove general football accuracy beyond this corpus and window.
- It does not constitute independent review; the author wrote most of what was tested.
- It does not close the licensing or public-exposure gates.

## 5. Findings register (carried forward)

| ID | Finding | Severity |
|---|---|---|
| MR-01 | DC shows no proven gain over Poisson (+0.0002 Brier) | Informational |
| MR-02 | Elo not proven different from Poisson; worse draw calibration | Informational |
| MR-03 | Bootstrap ignores clustering; intervals likely too narrow | Medium |
| MR-04 | No untouched holdout; protocol chosen with corpus knowledge | Medium |
| MR-05 | 3 h eligibility horizon is a retrospective proxy | Medium |
| MR-06 | MCE dominated by tiny bins; use ECE as primary | Low |
| MR-07 | Elo ratings pool across competitions | Low |
| MR-08 | DC is a two-stage fit, not joint MLE | Low |
| MR-09 | Draw bias is window-dependent (PD-only vs 970-match corpus) | Medium |
| MR-10 | No external independent review of any model | High |
| MR-11 | Evaluated DC/Elo parameters are frozen per window; live path refits per request | Medium |

## 6. Blockers

| Blocker | Consequence | Owner |
|---|---|---|
| No independent QA/ML review | Phase 7 cannot be accepted by the author | Developer / independent reviewer |
| LIM-006 public-display/redistribution licence unresolved | No shared or public display of results, probabilities or crests | Developer / legal |
| LIM-020 hot-linked crests/emblems | Part of the licence question | Developer / legal |
| Phase 3 QA verdict FAIL; security accepts private loopback only | Public/shared exposure rejected | Developer |
| Single provider, no second source | Provider correctness unverified | Developer decision |
| Retrospective observation times | Cannot claim live knowledge reconstruction | Structural |
| No untouched holdout | Small optimistic bias possible | Future data |

## 7. Definition of Done

| Criterion | Verdict | Evidence |
|---|---|---|
| Scope compliance (no Phase 8/betting, no database migration, no model default change) | **PASS** | §3; `git status`; `0006` unchanged; no odds/betting code |
| Audit against the real repo, not documents | **PASS** | §1–2; direct DB/API/code checks |
| Model selection and comparison implemented | **PASS** | §3.1–3.3; 56 new tests |
| No silent fallback or model substitution | **PASS** | 422 `unknown_model`; dispatch unit tests |
| Chronological, identical-set, leakage-guarded evaluation | **PASS** | `phase7-v1` tests; `fit_rho` guard |
| Evaluation reproducible and idempotent | **PASS** | §4; row reuse; identical metrics |
| Tests added for new logic and failure paths | **PASS** | 321 passed |
| Full pytest / Alembic / typecheck / build | **PASS** | §4 |
| Responsive verification at required widths | **PASS** | 7 widths, two routes |
| Documentation and memory accurate | **PASS** | Rewritten; false docs removed |
| Lint clean | **PARTIAL** | 7 pre-existing errors outside new files |
| Independent review / acceptance | **FAIL** | Self-review only (MR-10) |
| Licensing / public exposure readiness | **FAIL** | LIM-006, LIM-020; not in scope to resolve |
| General accuracy claim | **NOT ATTEMPTED** | Deliberately: no evidence, no claim |

**Overall: PARTIAL.** The engineering deliverables are complete and verifiable. Acceptance is
blocked on independence and licensing, neither of which this agent can supply.

## 8. Phase 8 recommendation

**Do not approve Phase 8 as "Professional Football Intelligence & Betting Analytics".**

Reasons:

1. The product is defined in `AGENTS.md` as **not** a tipster service. Betting analytics is a
   different product with legal, licensing and responsible-gambling obligations.
2. No odds source is licensed or verified. Expected value and paper betting without verified,
   timestamped odds would simulate stakes against invented prices.
3. The evidence base is one provider, one backfill, one corpus, one window, and a bootstrap
   that understates uncertainty.
4. The public-display licence and the security gates are still open. A betting UI would
   amplify both.

If the developer wants a next phase, the defensible one is **evaluation and evidence
hardening**, not betting:

| Candidate Phase 8A | Gate |
|---|---|
| Independent QA/ML review of the three models and the protocol | External reviewer |
| Clustered bootstrap / block resampling | Design note + tests |
| Genuine out-of-time holdout on future matches | Time and data accumulation |
| Reconcile frozen evaluation cadence with live refit (MR-11) | Developer decision |
| Second results source for cross-checking | Provider + licence approval |
| Licence resolution (LIM-006/LIM-020) | Legal review |
| Coverage and depth decision (PD-002/PD-003) | Developer decision + budget |

Only after those could a betting-adjacent phase even be considered, and it would still need
its own ADR, a licensed odds source, a settlement policy and independent review.

## 9. What may and may not be claimed

May be claimed:

- the platform runs privately on real stored results with provenance;
- three statistical models and two baselines are evaluated on the identical 970-match
  chronological sample;
- Poisson beats both trivial baselines with paired intervals excluding zero;
- Dixon-Coles is indistinguishable from Poisson on this corpus;
- Elo is directionally worse but not proven different;
- evaluation is reproducible and persisted.

May **not** be claimed:

- that any model is "the best" or "accurate to X%";
- any profit, edge, ROI or guaranteed outcome;
- that DC or Elo is production-ready;
- that these numbers generalise beyond the stored corpus, provider or window;
- that the evaluation reconstructs what was known live;
- that Phase 8 exists.
