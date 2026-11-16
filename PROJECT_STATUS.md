# Project Status

**Project:** Football Intelligence Platform
**Current phase:** Phase 5 — Private real-data match analysis
**Phase 4:** Accepted by the developer on 2026-11-14 as an offline, synthetic-test-only
foundation
**Phase 5:** Approved by the developer under ADR-0010; implemented privately on loopback,
not publicly deployed
**Last updated:** 2026-11-16

## Current private analysis slice (2026-11-16)

Private, loopback-only, read-only ingestion from football-data.org is running.
`data/football.db` holds 70 countries, 13 competitions, 11 seasons, 285 teams, **5,322
matches**, **4,905 finished results**, and 417 upcoming fixtures. Finished results span
**2025-02-05 → 2026-11-14** across eleven competitions and two seasons. Every stored match
is linked to an archived raw payload.

The Next.js app lists stored fixtures with crests, competition emblems, countries, status
and score; offers Today / Tomorrow / 7 / 14 / 30-day windows, server-side search, a team
combobox and country/competition filters; and shows a match detail view with honest "Not
supplied" markers plus a working **Analyze Match** panel.

The analysis panel calls `POST /api/v1/analysis/matches/{id}` and renders:

- 1X2 probabilities that sum to 100%, expected goals, secondary markets, and top scorelines;
- the sample size, competition baseline, historical record, head-to-head, and model
  parameters;
- out-of-sample Brier, log loss, uniform baselines, Brier skill, calibration bins, and the
  evaluation period;
- dataset provenance (provider, archived payload count, retrieval and observation windows,
  digest) and explicit limitations;
- the four statuses `READY`, `INSUFFICIENT_DATA`, `DATA_UNAVAILABLE`, `ANALYSIS_FAILED`;
- prior reports for the same match.

The live report for Real Madrid vs Celta (match 410, kickoff 2026-11-21) is `READY` with
1X2 **60.9% / 23.2% / 15.9%** (sum 100%), expected goals **1.74 / 0.76**, model
`poisson-v1.1.0`, and a 50-match rolling-origin backtest: Brier **0.5722**, log loss
**0.9581**, uniform Brier 0.6667, Brier skill **0.1417**, ECE **0.0661**.

There is no paid plan, no public deployment, no in-match statistics, no lineup or injury
data, and no performance guarantee. The measurement is one competition (PD) on one stored
corpus, not a claim of general accuracy.

## Phase summary

| Phase | Scope | Status |
| --- | --- | --- |
| 1 | Foundation: instructions, agents, skills, commands, docs, rules, memory | Complete |
| 2 | System architecture: stack, database, provider abstraction, API, identity, sync | Complete |
| 3 | Python backend, SQLite schema, ingestion, read-only API, tests, guides | **Phase 3.1 remediation implemented locally; final acceptance rejected pending re-audit** |
| 4 | Offline intelligence, mathematical primitives, evaluation mechanics | **Accepted by developer (synthetic-only); Phase 3 review pending** |
| 5 | Real historical ingestion, fitted analysis, persistence/API, frontend | **Implemented privately; live-verified on loopback; licence and review gates open** |

Status vocabulary for deliverables: **VERIFIED**, **IMPLEMENTED BUT NOT LIVE-VERIFIED**,
**PARTIALLY IMPLEMENTED**, **NOT IMPLEMENTED**, **BLOCKED**.

## Phase 3 deliverables

| Area | Deliverable | Status |
| --- | --- | --- |
| Configuration | Typed settings, `SecretStr` token, `.env.example` | VERIFIED |
| Database | SQLite engine, foreign keys, WAL, busy timeout, fail-closed non-SQLite URL | VERIFIED |
| Schema | SQLAlchemy models, constraints, indexes | VERIFIED |
| Migrations | Alembic revisions `0001`–`0005`; `upgrade head`; `alembic check` no drift | VERIFIED |
| Provider contract | Capability declaration, DTOs, typed errors | VERIFIED |
| Reference adapter | football-data.org v4 parsing; live reads verified for competitions, matches, results, crests and emblems | PARTIALLY VERIFIED |
| HTTP client | Streaming response bounds, bounded retries and safer provider URL policy; quota evidence remains unverified | PARTIALLY IMPLEMENTED |
| Raw archive | Content-addressed file plus `raw_payloads` row, before parsing | VERIFIED |
| Normalisation | Names, enums, statuses, season labels, metric keys | VERIFIED |
| Validation | Statistics, participant, result-phase and abandoned-status checks; extra-time/penalty defects quarantined with reasons | PARTIALLY IMPLEMENTED |
| Identity | Mapping → exact natural key → create; ambiguity and conflicts quarantined | VERIFIED |
| Ingestion | Core upserts, team-country separation and raw linkage; historical backfill executed | VERIFIED (local) |
| Statistics model | One row per `(match, team, metric)`; missing ≠ zero | VERIFIED |
| Sync engine | Runs, counts, per-item transactions, errors, quarantine, stale-run sweep | VERIFIED |
| Scheduler / worker | Wiring inspected; invalid startup tested, successful scheduling unverified | IMPLEMENTED BUT NOT LIVE-VERIFIED |
| CLI | `migrate`, `status`, `check-provider`, `sweep-runs`, `sync <job>`, `coverage` | VERIFIED |
| API | Read-only fixtures/reference/sync endpoints plus write-by-POST analysis endpoints | VERIFIED (loopback) |
| Tests | 265 tests passing locally; no skips or errors | VERIFIED (local run) |
| Provenance / freshness | Archive, run metadata, dataset digest and analysis evidence windows exist | VERIFIED for analysis datasets |
| Independent QA review | Prior **FAIL**; final exact-tree re-audit pending | BLOCKED |
| Independent security review | **ACCEPT WITH CONDITIONS** for private loopback-only use; **REJECT** public exposure | PARTIALLY IMPLEMENTED |
| Provider evaluation | Read-only comparison completed; no entitlement or licence approved | IMPLEMENTED BUT NOT VERIFIED |
| Phase 3.1 remediation | F-01…F-10 and S-01…S-19 addressed to varying degrees; open conditions remain | PARTIALLY IMPLEMENTED |
| Live provider integration | Real credential, coverage, statistics, licence | PARTIALLY VERIFIED (results and fixtures only) |
| Coverage guarantee | Any competition or season | **NOT IMPLEMENTED** (no coverage claim) |
| API auth / rate limiting | — | **NOT IMPLEMENTED** |
| Backup automation | — | **NOT IMPLEMENTED** |
| PostgreSQL support | — | **NOT IMPLEMENTED** (not supported) |

## Phase 5 deliverables

| Area | Deliverable | Status |
| --- | --- | --- |
| Historical ingestion | Bounded `season=<year>&status=FINISHED` sync; 4,905 results stored | VERIFIED (local) |
| Coverage reporting | `python -m app.cli coverage` JSON/markdown from live counts | VERIFIED |
| Point-in-time dataset | Regulation-only results observed before kickoff; extra time and shootouts excluded | VERIFIED (unit + integration) |
| Provenance contract | Provider code, archived payload ids, retrieval/observation windows, content digest; missing evidence fails closed | VERIFIED |
| Features | Competition baseline, attack/defence strength, venue shrinkage, recent form, missing-feature reporting | VERIFIED (synthetic tests) |
| Probability model | Independent Poisson `poisson-v1.1.0`, `features-v1.1.0`; 1X2 sums to 1.0 | VERIFIED (mathematically) |
| Evaluation | Rolling-origin backtest `evaluation-v1.1.0`, Brier/log loss, uniform baselines, calibration bins | VERIFIED on 50 PD matches; NOT a general accuracy claim |
| Persistence | `match_analyses` table, migration `0005`, report history | VERIFIED |
| Analysis API | `POST /analysis/matches/{id}`, `GET /analysis/{id}`, `GET .../history`; idempotent reuse and `force` | VERIFIED (loopback) |
| Abstention | `INSUFFICIENT_DATA`, `DATA_UNAVAILABLE`, `ANALYSIS_FAILED`; no fabricated numbers | VERIFIED |
| Frontend | Analyze Match panel with four statuses, probabilities, evidence, calibration, history | VERIFIED (build + browser at 471 px) |
| Public display | Licence for real data | **BLOCKED** (LIM-006) |
| In-match statistics / lineups | Provider plan and ingestion | **NOT IMPLEMENTED** |

## Verification evidence

Latest local verification: 2026-11-16 session (process logs use the host's UTC clock).

| Check | Result |
| --- | --- |
| `PYTHONPATH=apps/backend .venv/bin/python -m pytest` | **265 passed**, 1 third-party deprecation warning |
| `alembic check` | No new upgrade operations detected |
| `alembic current` | `0005 (head)` |
| `python -m app.cli coverage` | 5,322 stored matches, 4,905 results, 5,322 payload-linked |
| Live analysis, match 410 | `READY`; 1X2 0.6092 / 0.2320 / 0.1588; xG 1.74 / 0.76; `poisson-v1.1.0` |
| Backtest, 50 out-of-sample PD matches | Brier 0.5722; log loss 0.9581; skill 0.1417; ECE 0.0661; MCE 0.3084 |
| Idempotency | Repeated POST returned the same analysis id; `?force=true` created a new report |
| Provenance failure | Missing archived payload yields `ANALYSIS_FAILED`, never a placeholder id |
| Exclusions | 10 extra-time/penalty records quarantined with reasons; 13 regulation exclusions in the match-410 window |
| Frontend | `npm run build` passed; browser showed no console errors; no horizontal overflow at 471 px |
| Provider | Live reads made for fixtures and results with the local credential; no paid plan added |

The test suite uses synthetic payloads labelled `SYNTHETIC TEST DATA`. A passing suite is not
evidence of provider compatibility, and the Phase 5 tests are not evidence of football
predictive usefulness. The backtest is evidence about one stored corpus, not a guarantee.

## Architecture decisions

| ADR | Decision | Status |
| --- | --- | --- |
| ADR-0001 | Project foundation | Proposed — per its recorded status |
| ADR-0002 | Python backend stack | Proposed — implemented |
| ADR-0003 | SQLite primary database | Proposed — implemented |
| ADR-0004 | Provider abstraction | Proposed — implemented, live-verified for read-only fixture/result/media reads |
| ADR-0005 | Read-only API contract | Proposed — implemented |
| ADR-0006 | Identity and provenance | Proposed — implemented |
| ADR-0007 | Synchronisation model | Proposed — implemented |
| ADR-0008 | Phase 4/5 entry gates | Approved — gates partly unmet |
| ADR-0009 | Pure offline intelligence boundary | Approved — implemented, amended after review |
| ADR-0010 | Verified real dataset contract | Approved by developer — implemented |

"Proposed — implemented" means the code exists and is tested, but the decision still needs
developer sign-off.

## Deliberately not built

- Public deployment, shared-network exposure, or a public data display.
- Authentication, authorisation, subscriptions, payments, betting.
- Live-score push, news, notifications.
- Machine-learning training, an LLM numerical engine, or generated analysis text.
- In-match statistics, lineups, injuries, or xG from a paid tier.
- Docker, CI/CD, monitoring stack, PostgreSQL, message broker, cache, multi-worker execution.
- Any coverage or accuracy guarantee.

## Blockers and pending decisions

| ID | Item | Impact |
| --- | --- | --- |
| PD-002 | Final provider selection | Adapter is a reference implementation, not a commitment |
| PD-003 | Competition and season coverage | No coverage guarantee; eleven competitions stored |
| PD-004 | Data budget / plan | Pricing, quota, and statistics depth remain unverified |
| LIM-006 | Display/redistribution licence | Public data display is blocked; loopback only |
| LIM-022 | Mobile below 486 px | Not emulated; responsive classes are not visually verified below that width |
| — | Phase 3 independent QA review | Prior FAIL; final exact-tree re-audit pending |
| — | Phase 3 security conditions | S-01…S-19; public exposure rejected until addressed |
| — | Provider statistics | Free tier has no in-match statistics; model abstains instead of filling zeros |
| — | Analysis review | Independent QA/ML review of `poisson-v1.1.0` has not been performed |

No paid subscription was purchased, no provider account was created, and no provider terms were
accepted on the developer's behalf.

## Next

1. Obtain independent QA/ML review of the exact analysis tree and the measured backtest.
2. Review `docs/research/2026-11-16-historical-coverage-report.md` and decide whether the
   stored corpus is sufficient for the intended competitions.
3. Close the Phase 3 QA/security conditions; public exposure remains rejected.
4. Resolve LIM-006 before any shared or public display of real results.
5. Extend coverage only with explicit approval; do not add a plan or statistics tier.
6. Re-run `python -m app.cli coverage`, the test suite, and `alembic check` before any claim.

Reports: [A — Phase 2](docs/reports/phase-2-architecture-report.md),
[B — Phase 3](docs/reports/phase-3-implementation-report.md),
[C — Phase 4 audit](docs/research/phase-4-final-audit.md),
[Phase 3 QA review](docs/research/phase-3-independent-qa-review.md),
[Phase 3.1 remediation report](docs/research/phase-3.1-remediation-report.md),
[Phase 3 security review](docs/reports/phase-3-security-review.md),
[security reassessment](docs/security/phase-3-security-reassessment.md),
[provider evaluation](docs/research/2026-11-14-provider-evaluation.md), and
[historical coverage](docs/research/2026-11-16-historical-coverage-report.md).

See [`memory/next-steps.md`](memory/next-steps.md) and
[`memory/known-limitations.md`](memory/known-limitations.md).
