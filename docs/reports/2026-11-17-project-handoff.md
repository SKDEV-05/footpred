# Project Handoff Report — Football Intelligence Platform

**Date:** 2026-11-17
**Purpose:** A single, self-contained explanation of the project so a new chat/agent can
continue without re-reading the whole repository history.
**Confidence:** High for everything under "Verified current state" (commands were executed on
2026-11-17). Medium for phase status where documentation and code disagree.
**Status of this document:** Current as of the commit and working tree described below. It
does not replace `AGENTS.md`, ADRs, or `PROJECT_STATUS.md`.

---

## 0. How to use this document (for the next chat)

1. Read sections 1–4 first. They define the product, the hard rules, and the real state.
2. Read section 13 before trusting any existing document. Several recent documents are
   **false or stale**.
3. Do not build betting/odds/best-bets features. They are not approved (section 12).
4. Before changing code, read `AGENTS.md`, `rules/`, and the relevant ADR.
5. Re-run the verification commands in section 11 rather than trusting this report blindly.

Abbreviations used below:

- **PD** — La Liga (Primera División), competition id 4.
- **1X2** — home win / draw / away win.
- **DC** — Dixon-Coles model.
- **ECE / MCE** — expected / maximum calibration error.
- **CRPS** — not used in this project.
- **Brier score** — mean squared error of the probability vector; lower is better.
  A uniform 1/3 forecast scores 0.6667.
- **Brier skill** — `1 − model Brier / uniform Brier`; 0 means no better than uniform.

---

## 1. What the platform is

A global football intelligence and match-analysis platform. It is intended to help a user
understand a match through:

- verified historical results with provenance;
- transparent statistical models;
- probability estimates with explicit uncertainty;
- out-of-sample evaluation of those estimates;
- reports that state limitations instead of hiding them.

**It is not:** a live-score site, a news site, a generic chatbot, a tipster service, a
guaranteed-tip product, a statistics dump, or (currently) a betting product.

**Guiding order:** data first, mathematics first, reliability first, prediction quality
first, user experience second, visual decoration last.

**Hard prohibitions (from `AGENTS.md`):**

- no invented data, ever; missing is reported as missing, never as zero;
- no future leakage; no random train/test split for chronological football;
- never evaluate a model on matches it trained on;
- never silently replace a model;
- no betting/subscription/payment features without approval;
- no public deployment while the licence and security gates are open;
- no destructive migrations; no secrets in the repo;
- documentation must never claim unimplemented features are complete.

---

## 2. Executive summary (30 seconds)

- The **data and Poisson analysis pipeline is real and works**: 5,322 stored matches,
  4,905 finished results, every match linked to an archived provider payload.
- The **Phase 7 backend is real**: Dixon-Coles and Elo were implemented, and a
  970-match, 11-competition rolling-origin backtest was executed and persisted.
- **Dixon-Coles does not prove it is better than Poisson.** Elo is not proven worse, but it
  is not better either. Poisson beats both trivial baselines with statistical confidence.
- **Phase 7 is not finished**: no evaluation dashboard, no match model comparison, no new
  tests, 6 required research documents missing, responsive QA missing, verdicts missing.
- **Phase 8 exists only as two untracked, unreferenced Python modules plus documents that
  falsely claim odds/paper-betting/best-bets systems were implemented.** No such code
  exists. Do not trust those documents.
- **Verdicts:** DATA = CONDITIONAL, MODEL = CONDITIONAL, BUSINESS = FAIL.

---

## 3. Verified current state (executed 2026-11-17)

### 3.1 Repository

- Git HEAD: `d3a9490` (`pahse 7`), 2026-11-16 22:20.
- Working tree: modified `memory/current-state.md`, `memory/next-steps.md`; untracked
  `app/intelligence/calibration.py`, `app/intelligence/validation.py`, and seven
  `docs/research/phase-8-*.md` files.
- No commit or push was made after `d3a9490`.
- Python: `.venv`, Python 3.15. Pure-Python maths only — numpy, scipy, pandas, sklearn are
  **not installed** and are not dependencies.

### 3.2 Database (`data/football.db`, SQLite)

| Item | Value |
|---|---:|
| Tables | 20 |
| Countries | 70 |
| Competitions | 13 (11 with stored matches) |
| Seasons | 22 |
| Teams | 334 |
| Matches | 5,322 |
| Finished results | 4,905 |
| Regulation-time results usable by models | 4,892 |
| Extra-time / shootout results excluded | 13 |
| Upcoming fixtures | 417 |
| Match → archived raw payload linkage | complete (5,322 / 5,322) |
| Evaluation runs persisted | 1 |

Integrity checks executed: no duplicate natural key
`(competition, season, kickoff, home, away)`, no `home_team == away_team`, no null scores,
no `resolved_at < kickoff`.

**Important data limitation:** every stored result was backfilled in one retrieval window
on 2026-11-16. `resolved_at` records when this platform first stored the score, not when the
provider published it. All 4,892 observations are therefore classified
`reconstructed_from_backfill`. The backtest uses a documented `kickoff + 3h` horizon and
labels the evaluation retrospective, not a reconstruction of live knowledge.

### 3.3 Verification results

| Check | Result |
|---|---|
| `pytest` (full backend suite) | **265 passed** |
| `alembic upgrade head` | applied `0006` |
| `alembic check` | no drift |
| Phase 5 baseline reproduction | exact (see 5.1) |
| Phase 7 evaluation run | 970 matches, persisted as run id 1 |
| Frontend | unchanged since the last verified build; not re-run in this audit |
| Responsive QA below ~471 px | still unverified (tooling limitation LIM-022) |

The 265 passing tests are the **pre-Phase-7** suite. There are no tests for Dixon-Coles
rho fitting, the fitted Elo/Davidson mapping, the multi-competition engine, evaluation
persistence/API, or model comparison.

---

## 4. Architecture and stack

```
football-data.org
      │  HTTPS + token (loopback only)
      ▼
provider adapter → raw archive (content-addressed files + raw_payloads rows)
      ▼
normalisation → validation → identity resolution → SQLite (SQLAlchemy, Alembic)
      ▼
repositories (point-in-time / corpus datasets with provenance)
      ▼
intelligence (features → rates → model → probability matrix → markets)
      ▼
FastAPI (/api/v1)  ──────────────►  Next.js 16 app (server + client components)
```

- **Backend:** FastAPI 0.162, SQLAlchemy 2.1, Alembic 1.20, Pydantic 2.14, APScheduler,
  httpx. SQLite with foreign keys, WAL, busy timeout; non-SQLite URLs are refused.
- **Frontend:** Next.js 16.4.6 (App Router), React 19, TypeScript 5, Tailwind 4,
  Radix primitives, lucide icons. No chart library is installed.
- **No containers, no CI/CD, no public hosting, no authentication.**

---

## 5. Intelligence layer

### 5.1 Poisson baseline (`poisson-v1.1.0`)

- Competition-baselined independent Poisson goal model.
- Attack/defence strengths estimated only from results observed before the target kickoff.
- Recent form is blended towards the longer-run rate with shrinkage.
- Expected goals are bounded; the score matrix is normalised; 1X2 sums to exactly 1.0.
- Versions: features `features-v1.1.0`, evaluation `evaluation-v1.1.0`.
- One shared estimator is used by the live path and the backtest.

**Reproduced exactly on 2026-11-17** (match 410 checkpoint, PD, 50 out-of-sample matches,
2026-10-09 → 2026-11-08):

| Metric | Value |
|---|---:|
| Brier | 0.5722 |
| Log loss | 0.9581 |
| Uniform Brier | 0.6667 |
| Brier skill | 0.1417 |
| ECE | 0.0661 |
| MCE | 0.3084 |

This 50-match PD window is **not** directly comparable to the 970-match Phase 7 window.

### 5.2 Dixon-Coles (`dixon-coles-v1.0.0`)

- Reuses the Poisson rate estimator, then applies the Dixon-Coles low-score correction.
- `rho` is fitted by time-weighted maximum likelihood on **training matches only**
  (half-life 180 days, bounds ±0.30, per competition), then clipped per match so every
  low-score correction stays positive.
- This is **not** a full joint Dixon-Coles MLE: attack/defence rates are not re-estimated
  jointly with rho. Documented limitation.
- Persisted fitted parameters are visible per competition in the stored report.

### 5.3 Elo (`elo-v1.0.0`)

- Pure chronological Elo replay; K = 20, initial rating 1500, scale 400.
- Outcome mapping is Davidson (1970), driven by the Elo difference; the three
  probabilities sum to 1.0 by construction.
- `home_advantage` and `draw_nu` are fitted by grid MLE on pre-window matches and frozen for
  the competition's evaluation window.
- Elo produces **1X2 only**: no expected goals and no scoreline distribution.
- Simultaneous kickoffs are applied in one batch so they cannot influence each other.

### 5.4 Baselines

- `uniform-v1.0.0` — 1/3 each.
- `frequency-v1.0.0` — expanding historical home/draw/away share for the competition, with
  documented fallbacks to all competitions and then uniform.

### 5.5 Backtest protocol (`phase7-v1`)

- One chronological pass predicts every target match once with every model, from the same
  information cutoff. All models are scored on an **identical match set**.
- A result becomes eligible at `kickoff + 3h`.
- Per competition: the last 100 matches are targets, with at least 40 prior matches.
- Parameters are fitted before the competition's first target kickoff and frozen.
- Confidence intervals are percentile bootstrap, 1,000 resamples, fixed seed `20261116`,
  so a rerun is deterministic.
- Metrics: multiclass Brier, log loss, Brier skill vs uniform, ECE/MCE, reliability bins,
  per-outcome binary metrics, per-competition, per-season, and 25-match timeline buckets.

### 5.6 Measured Phase 7 results (970 matches, 2026-02-25 → 2026-11-14)

| Model | Brier | Log loss | Brier skill | ECE | Brier 95% CI |
|---|---:|---:|---:|---:|---|
| Poisson | 0.5831 | 0.9828 | 0.1253 | 0.0254 | [0.5620, 0.6046] |
| Dixon-Coles | 0.5829 | 0.9821 | 0.1256 | 0.0258 | [0.5620, 0.6037] |
| Elo | 0.5911 | 0.9916 | 0.1133 | 0.0375 | [0.5759, 0.6055] |
| Competition frequency | 0.6405 | 1.0592 | 0.0393 | 0.0143 | [0.6288, 0.6513] |
| Uniform 1/3 | 0.6667 | 1.0986 | 0.0000 | 0.0802 | — |

Paired bootstrap vs Poisson (positive = Poisson worse):

| Candidate | Brier difference | 95% CI | Conclusion |
|---|---:|---|---|
| Dixon-Coles | +0.0002 | [−0.0009, +0.0013] | **No proven gain or loss** |
| Elo | −0.0080 | [−0.0195, +0.0040] | **Not proven different** |
| Uniform | −0.0835 | [−0.1051, −0.0619] | Poisson significantly better |
| Frequency | −0.0573 | [−0.0755, −0.0388] | Poisson significantly better |

Per outcome (mean predicted probability minus observed rate; positive = over-predicted):

| Model | Home | Draw | Away |
|---|---:|---:|---:|
| Poisson | −0.0047 | **+0.0004** | +0.0043 |
| Dixon-Coles | −0.0068 | +0.0046 | +0.0022 |
| Elo | −0.0088 | +0.0211 | −0.0123 |

**Key honesty point:** on the broad 970-match corpus, the Poisson draw gap is +0.0004 —
essentially unbiased. The earlier 50-match PD result suggested draw under-prediction; that
finding does **not** generalise to this wider corpus. Both results must be reported with
their windows.

Per-competition Poisson / DC / Elo Brier (sample sizes are all small):

| Comp | Code | n | Poisson | DC | Elo |
|---|---|---:|---:|---:|---:|
| 1 | BSA | 100 | 0.5368 | 0.5378 | 0.5587 |
| 2 | BL1 | 86 | 0.5588 | 0.5593 | 0.5769 |
| 3 | FL1 | 90 | 0.6077 | 0.6077 | 0.6121 |
| 4 | PD | 91 | 0.5539 | 0.5540 | 0.5855 |
| 5 | ELC | 100 | 0.6611 | 0.6596 | **0.6492** |
| 6 | PL | 100 | 0.6436 | 0.6415 | **0.6360** |
| 7 | CL | 76 | 0.5814 | 0.5849 | **0.5388** |
| 9 | SA | 89 | 0.5127 | 0.5119 | 0.5611 |
| 10 | DED | 88 | 0.6290 | 0.6249 | 0.6296 |
| 11 | PPL | 91 | 0.5228 | 0.5222 | 0.5500 |
| 12 | CLI | 59 | 0.6035 | 0.6065 | **0.5873** |

No competition is labelled `INSUFFICIENT_DATA` in this run; all 11 had ≥50 stored results.
That does **not** mean 59–100 matches prove a model: read the intervals.

---

## 6. API surface (actual)

All routes are under `/api/v1`. FastAPI docs are enabled only when configured.

| Method | Path | Notes |
|---|---|---|
| GET | `/fixtures` | filters, search, pagination |
| GET | `/fixtures/today` | date + timezone |
| GET | `/fixtures/{match_id}` | detail |
| GET | `/fixtures/{match_id}/statistics` | honest "not supplied" when absent |
| GET | `/countries` | reference |
| GET | `/competitions`, `/competitions/{id}` | reference |
| GET | `/seasons` | reference |
| GET | `/teams`, `/teams/{id}`, `/teams/{id}/matches` | reference |
| GET | `/sync/runs`, `/sync/status` | operational |
| POST | `/analysis/matches/{match_id}` | generate/retrieve Poisson analysis (`force` supported) |
| GET | `/analysis/{analysis_id}` | stored report |
| GET | `/analysis/matches/{match_id}/history` | prior reports |
| POST | `/evaluation/run` | run/persist corpus evaluation (`as_of` optional) |
| GET | `/evaluation/latest` | latest persisted run |
| GET | `/evaluation/runs` | run catalogue |
| GET | `/evaluation/{run_id}` | full stored report |

Analysis statuses: `READY`, `INSUFFICIENT_DATA`, `DATA_UNAVAILABLE`, `ANALYSIS_FAILED`.
There is no silent fallback. A provenance failure persists `ANALYSIS_FAILED`.

**Not present:** model selection (`?model=`), match model comparison, odds, bets, auth,
rate limiting, public deployment.

### Evaluation persistence

- Table `model_evaluations` (migration `0006`).
- Unique on `(protocol_version, evaluation_version, dataset_digest)`.
- Re-running on an unchanged corpus returns the existing row; it never duplicates or
  silently recomputes different numbers.
- `dataset.digest` covers the materialised match rows and excludes the evidence block, so
  it is stable across `as_of` for an unchanged corpus.

---

## 7. Frontend surface (actual)

- `/` — fixture explorer: windows (today/tomorrow/7/14/30 days), server-side search, team
  combobox, country/competition filters, pagination, crests, emblems, status, scores,
  freshness/empty/error states.
- `/matches/[id]` — match detail plus the **Analyze Match** panel.
- `MatchAnalysisPanel` renders: 1X2, expected goals, secondary markets, top scorelines,
  sample sizes, competition baseline, team records, head-to-head, model parameters,
  dataset provenance, limitations, and the existing 50-match evaluation block.
- Design: dark UI, consistent tokens; no gradients-as-decoration, no fake charts.

**Not present:** `/evaluation` dashboard, reliability-diagram UI, model-comparison UI,
navigation link for evaluation, any odds/betting UI.

---

## 8. Database schema (summary)

20 tables:

`alembic_version`, `countries`, `competitions`, `seasons`, `teams`, `matches`,
`match_results`, `team_match_statistics`, `data_providers`, `raw_payloads`,
`provider_*_mappings`, `data_sync_runs`, `data_sync_errors`, `quarantined_records`,
`match_change_log`, `match_analyses`, `model_evaluations`.

Key semantics:

- `matches.status` separates finished/timed/scheduled/postponed/cancelled.
- `match_results` carries regular score, half-time score, extra-time and shootout columns;
  extra-time/shootout rows are excluded from model history, never merged.
- `match_analyses` stores the full report, versions, dataset digest and evidence payload.
- `model_evaluations` stores the full evaluation report body as JSON plus identity columns.

Migrations `0001`–`0006`. `0006` is additive; no destructive migration was performed.

---

## 9. Phase history and status

> Naming caution: the repository uses two numbering schemes. `PROJECT_STATUS.md` stops at
> Phase 5, the commit calls the model-validation work "Phase 7", and the newest work calls
> itself "Phase 8". This report uses the phase names, not just numbers.

| Phase | Scope | Status | Gap |
|---|---|---|---|
| 1 | Instructions, agents, skills, rules, docs, memory | DONE | — |
| 2 | Architecture, stack, schema, provider abstraction, sync | DONE | — |
| 3 | Backend, ingestion, read-only API, tests | CONDITIONAL | Phase 3.1 re-audit still open; some provider/security conditions |
| 4 | Offline synthetic-only intelligence primitives | DONE, accepted | — |
| 5 | Private real-data analysis (Poisson, persistence, UI) | DONE privately | Licence (LIM-006), independent review, no public exposure |
| 6 | Provider capability audit | DONE | Statistics/H2H/live events UNVERIFIED |
| 7 | Independent model validation, DC, Elo, multi-competition backtest, dashboard, verdicts | PARTIAL | See section 10 |
| 8 | "Betting analytics" (validation/calibration/odds/paper/best bets) | NOT APPROVED, NOT IMPLEMENTED | See section 12 |

---

## 10. Phase 7 — what is done and what is missing

**Done and verified:**

- DC fitted rho + score matrix.
- Fitted Elo + Davidson mapping + chronological replay.
- Uniform and frequency baselines.
- Multi-competition rolling-origin engine with CIs, per-competition/season/outcome/timeline
  blocks.
- Evaluation persistence + API + CLI `evaluate`.
- Real run persisted (id 1, 970 matches).
- Baseline reproduction verified independently.

**Missing (required by the Phase 7 brief):**

1. Six of seven research documents:
   `phase-7-baseline-audit.md`, `phase-7-independent-model-review.md`,
   `phase-7-dixon-coles-research.md`, `phase-7-multi-competition-backtest.md`,
   `phase-7-model-comparison.md`, `phase-7-commercial-readiness.md`,
   `phase-7-final-report.md`. Only `phase-7-actual-project-status.md` exists, and it is not
   one of the required deliverables.
2. Model-evaluation dashboard in Next.js (overview, comparison table, per-competition,
   per-season, per-outcome, reliability diagrams, timeline, data quality).
3. Match model selection (`model` query parameter) and
   `GET /analysis/matches/{id}/comparison`; no silent fallback.
4. Tests: DC unit suite, Elo unit suite, backtest engine (insufficient data, leakage,
   determinism), evaluation API integration, comparison endpoint.
5. Responsive QA at 375/390/430/768/1024/1280/1440 px.
6. Final DATA/MODEL/BUSINESS verdicts.
7. `PROJECT_STATUS.md` and the four memory files updated to the real Phase 7 state.
8. Commercial licence assessment (`phase-7-commercial-readiness.md`).

---

## 11. Commands verified in this audit

Run from the repository root unless stated otherwise.

```bash
# Backend tests
cd apps/backend && ../../.venv/bin/python -m pytest

# Migrations (must run from the repository root)
.venv/bin/python -m alembic current
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m alembic check

# CLI (module form avoids PATH assumptions)
PYTHONPATH=apps/backend .venv/bin/python -m app.cli status
PYTHONPATH=apps/backend .venv/bin/python -m app.cli coverage --format markdown
PYTHONPATH=apps/backend .venv/bin/python -m app.cli evaluate --summary-only

# Backend (loopback only)
cd apps/backend && setsid nohup ../../.venv/bin/python -m uvicorn app.main:app \
  --host 127.0.0.1 --port 8000 >/tmp/opencode/backend.log 2>&1 &

# Frontend (loopback only)
cd apps/web && setsid nohup npx next dev --hostname 127.0.0.1 --port 3000 \
  >/tmp/opencode/web.log 2>&1 &

# Frontend checks
cd apps/web && npx tsc --noEmit
cd apps/web && npm run build
```

Python modules run from `apps/backend` need `PYTHONPATH=.`.

---

## 12. Phase 8 findings — read before trusting anything

The working tree contains:

- `apps/backend/app/intelligence/validation.py` — 837 lines, re-implements much of
  `backtest.py` as "protocols A–G". It imports successfully but is **not imported by the
  app, API, CLI, or tests**.
- `apps/backend/app/intelligence/calibration.py` — 837 lines, imports `validation.py`.
  No wiring, no persistence, no API, no tests.
- Seven `docs/research/phase-8-*.md` files.

**False claims in those documents:**

- odds / expected-value engine "implemented" — no odds code, schema, or endpoint exists;
- paper-betting system "implemented" — no paper-betting code exists;
- best-bets system "implemented" — no best-bets code exists;
- "all odds/paper/best-bets tests pass; 265/265" — those 265 are the old tests; no new
  tests exist;
- evaluation dashboard "partial" — no dashboard exists at all;
- `memory/current-state.md` says "Phase 8 — Professional Football Intelligence & Betting
  Analytics Platform ... implemented" — not true.

**Scope problem:** odds, value betting, paper betting and "best bets" are betting features.
`AGENTS.md` defines the product as **not** a tipster service; betting features require
explicit developer approval and an ADR. No such ADR exists. These documents also violate
the documentation rule that unimplemented features must not be described as complete.

**Recommended handling (not done in this audit, per instruction):**

- Freeze Phase 8; do not implement odds/betting.
- Either delete the four false documents or relabel them "DESIGN PROPOSAL — NOT
  IMPLEMENTED"; restore memory to the real Phase 7 state.
- Decide whether `validation.py`/`calibration.py` are deleted or adopted under an ADR with
  tests and integration. Leaving untracked orphan modules is the worst option.

---

## 13. Document trust map

| Document | Trust | Note |
|---|---|---|
| `AGENTS.md`, `rules/` | HIGH | Governing rules |
| `docs/decisions/ADR-0001`–`0010` | HIGH | Approved decisions |
| `PROJECT_STATUS.md` | MEDIUM | Accurate for Phase 5; does not reflect Phase 7 |
| `memory/known-limitations.md`, `memory/decisions.md` | MOSTLY HIGH | Check dates |
| `memory/current-state.md`, `memory/next-steps.md` | **LOW (current edit)** | Overwritten with unverified Phase 8 claims |
| `docs/research/phase-7-actual-project-status.md` | LOW–MEDIUM | Real backend facts, but wrong API paths, claims a frontend evaluation dashboard that does not exist, and says 2 tests fail (they do not) |
| `docs/research/phase-8-baseline-audit.md` | LOW | Mixes real facts with false frontend/API claims |
| `docs/research/phase-8-independent-ml-review.md` | LOW–MEDIUM | Review reasoning may be useful; verify every claim |
| `docs/research/phase-8-out-of-sample-validation.md` | LOW | Describes an unintegrated module as a framework |
| `docs/research/phase-8-odds-value-engine.md` | **FALSE** | No implementation |
| `docs/research/phase-8-paper-betting.md` | **FALSE** | No implementation |
| `docs/research/phase-8-best-bets.md` | **FALSE** | No implementation |
| `docs/research/phase-3-*`, `phase-4-*`, `phase-5-*`, `phase-6-*` | MEDIUM–HIGH | Historical; read with their stated scope |
| `docs/architecture/`, `docs/data/`, `docs/football/` | MEDIUM | Design intent, not a live status report |

**Resolution (2026-11-17).** This table records the state at handoff and is retained as
history. In the Phase 7 close-out the six `docs/research/phase-8-*.md` files were deleted and
replaced by `docs/research/phase-8-betting-proposals-rejected.md`; their content survives in
git history at `4aed17d`. `PROJECT_STATUS.md`, `memory/current-state.md`,
`memory/next-steps.md`, `memory/known-limitations.md` and
`docs/research/phase-7-actual-project-status.md` were rewritten from verified state. See
`docs/research/phase-7-final-report.md`.

---

## 14. Known limitations (real)

1. **Provider licence unresolved (LIM-006).** Free API access does not prove commercial
   display/redistribution rights. Public exposure is blocked.
2. **Observation timestamps are reconstructed.** The whole corpus was backfilled in one
   window; `resolved_at` is local ingestion time, not provider publication time.
3. **Single provider, limited depth.** football-data.org only; no statistics, lineups,
   injuries, or live events verified. Statistics endpoints return "not supplied".
4. **Small evaluation samples.** 970 matches overall, 59–100 per competition. CIs are wide;
   no model may be declared "best" from this.
5. **No independent external validation.** All checks are self-run.
6. **Dixon-Coles is a two-stage fit,** not a joint MLE. Elo has no score distribution.
7. **Draw bias is window-dependent.** PD-only showed under-prediction; the broad corpus
   does not.
8. **No auth, rate limiting, TLS, audit logging, or public deployment.**
9. **Mobile verification below ~471 px is unverified** (browser tooling limitation).
10. **No backups/recovery drill documented** for the SQLite file and raw archive.
11. **No CI/CD.** All checks are manual.
12. **Phase numbering is inconsistent** across documents.

---

## 15. Verdicts (provisional, based on executed checks)

| Dimension | Verdict | Basis |
|---|---|---|
| **DATA QUALITY** | **CONDITIONAL** | Strong integrity and provenance; but reconstructed timestamps, one provider, licence unresolved, no external audit |
| **MODEL QUALITY** | **CONDITIONAL** | Beats trivial baselines with confidence; DC shows no proven gain; Elo not proven different; small samples; no external validation |
| **BUSINESS QUALITY** | **FAIL** | Licence unresolved, no security controls, false documentation, unapproved betting direction, no independent review |

Technical progress does **not** equal commercial approval. Public deployment must remain
blocked.

---

## 16. Next steps, in priority order

1. **Restore documentation integrity.** Correct or remove the false Phase 8 documents and
   memory edits; record the real Phase 7 state. No code required.
2. **Close the Phase 7 backend gaps.** Add `model` selection and
   `GET /analysis/matches/{id}/comparison`; never fall back silently.
3. **Add the missing tests.** DC rho (bounds, normalisation, determinism, leakage), Elo
   (probability sum, rating conservation, chronological order), backtest (insufficient
   data, identical match set, determinism), evaluation API (persistence, idempotency,
   provenance failure), comparison endpoint.
4. **Build the evaluation dashboard** from persisted results only, with loading/error/empty
   states and accessible tables; add a nav link.
5. **Run full verification:** pytest, `alembic check`, `tsc`, `npm run build`, browser and
   responsive checks at the seven widths.
6. **Write the seven Phase 7 documents** and issue the three verdicts.
7. **Only then** decide Phase 8 scope. If betting analytics is genuinely wanted, write an
   ADR, state the product and legal risks, and obtain developer approval first.
8. **Before any public exposure:** licence resolution, auth/authz, rate limiting, TLS,
   audit logging, backup/recovery, abuse protection, independent review.

### Definition of done for Phase 7

- Poisson baseline reproduces exactly.
- DC and Elo are independently implemented and evaluated on the identical match set.
- Multi-competition chronological backtest works and is deterministic.
- Leakage checks pass (no test match in training, no post-kickoff result).
- Calibration is reported per outcome.
- Dashboard shows only persisted results.
- Match reports support model comparison without fallback.
- Mobile verification documented.
- Licence blockers explicitly resolved or retained as blockers.
- All tests/builds pass.
- Unresolved issues documented.

---

## 17. File map (where to look)

**Rules and decisions**

- `AGENTS.md`, `CLAUDE.md`, `rules/`
- `docs/decisions/ADR-0001`–`ADR-0010`

**Backend**

- `apps/backend/app/main.py` — app factory
- `apps/backend/app/api/v1/router.py` — route assembly
- `apps/backend/app/api/v1/endpoints/analysis.py` — match analysis
- `apps/backend/app/api/v1/endpoints/evaluation.py` — evaluation runs
- `apps/backend/app/api/v1/endpoints/fixtures.py`, `reference.py`, `sync.py`
- `apps/backend/app/intelligence/prediction.py` — Poisson + features + live path
- `apps/backend/app/intelligence/backtest.py` — multi-model rolling-origin engine
- `apps/backend/app/intelligence/models/poisson.py` — score matrix primitive
- `apps/backend/app/intelligence/models/dixon_coles.py` — DC primitive + fitted rho
- `apps/backend/app/intelligence/models/elo_fitted.py` — fitted Elo + Davidson
- `apps/backend/app/intelligence/baselines.py` — uniform/frequency
- `apps/backend/app/intelligence/evaluation.py` — Brier/log-loss/reliability
- `apps/backend/app/intelligence/probabilities.py` — market arithmetic
- `apps/backend/app/repositories/analysis.py` — point-in-time/corpus datasets
- `apps/backend/app/repositories/evaluation.py` — evaluation persistence
- `apps/backend/app/models/` — SQLAlchemy schema
- `apps/backend/migrations/versions/0001`–`0006`

**Frontend**

- `apps/web/src/app/page.tsx` — fixture explorer
- `apps/web/src/app/matches/[id]/` — match detail
- `apps/web/src/components/MatchAnalysisPanel.tsx` — analysis UI
- `apps/web/src/lib/api.ts`, `apps/web/src/types/index.ts`
- `apps/web/src/app/layout.tsx` — nav

**Data and docs**

- `data/football.db` — local SQLite corpus
- `docs/architecture/`, `docs/data/`, `docs/football/`, `docs/research/`,
  `docs/security/`
- `memory/` — concise state; currently partly inaccurate

---

## 18. Facts, assumptions, open questions

**Verified facts** (executed 2026-11-17): the counts, metrics, tests, migration state, API
paths, and absence of odds/betting code described above.

**Assumptions:**

- The stored corpus is a faithful copy of what the provider returned; only structural
  integrity was checked, not provider-side correctness.
- `resolved_at` is a reasonable upper bound on when a result became available locally.
- The 3-hour horizon is a defensible retrospective proxy, not a measured publication delay.

**Open questions:**

- What exactly does the football-data.org licence permit for commercial display and derived
  data? (UNVERIFIED; legal review required.)
- Should DC/Elo enter the live analysis path, or remain evaluation-only until proven?
- Is the Phase 8 betting direction approved at all? (No evidence of approval; treat as not
  approved.)
- Who performs independent external QA/ML review, and against which protocol?

---

## 19. Glossary

- **Rolling origin** — repeatedly move the evaluation window forward, training only on
  earlier matches.
- **Point-in-time dataset** — results observed before a specific checkpoint; used for live
  analysis.
- **Dataset digest** — SHA-256 of the materialised match rows; identifies an analysis
  input.
- **Provenance** — provider code, archived payload ids, retrieval/observation windows.
- **Brier skill** — improvement over uniform; can be negative.
- **ECE/MCE** — average / worst gap between predicted probability and observed frequency.
- **Reliability bin** — a probability bucket with its predicted mean and observed rate.
- **Davidson model** — Bradley-Terry extension that adds a draw parameter.
- **rho (Dixon-Coles)** — adjusts the 0-0, 1-0, 0-1 and 1-1 score cells.

---

## 20. Change log of this report

- 2026-11-17 — created after auditing commit `d3a9490`, the untracked Phase 8 modules and
  documents, the database, the API definitions, and the test suite. No application code was
  modified.
