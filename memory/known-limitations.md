# Known Limitations

Missing information, uncertainties, and risks. Update when a limitation is resolved or a new one
is discovered. Never remove an item silently; mark it resolved with the evidence.

## Missing information

| ID | Limitation | Impact | Resolution |
| --- | --- | --- | --- |
| LIM-001 | No provider has been evaluated against a real API; no account exists — **RESOLVED** (2026-11-15): football-data.org was verified live for fixtures and results with a rotated credential | Adapter correctness is now proven for the read-only fixture/result endpoints actually used; statistics and H2H remain unprobed | See LIM-007, LIM-023, LIM-024 |
| LIM-002 | No competition or season coverage has been agreed | Coverage matrix is empty; fixture volume unknown | Product decision, then provider fit check |
| LIM-003 | Data budget is unknown | Cannot compare plans or commit to coverage | Developer decision |
| LIM-004 | Historical depth required for modelling is undecided — **PARTIALLY RESOLVED** (2026-11-17): two seasons per league are stored and 970 matches were evaluated | Per-competition evaluation samples are only 59–100 matches, which cannot rank leagues or stabilise per-competition parameters | Decide a required depth before adding seasons; more depth needs approval and provider budget |
| LIM-005 | No real-world volume, latency, or cost measurements exist | Scalability and SLA claims remain hypotheses | Measure after a live ingestion period |
| LIM-006 | Licence for display and redistribution of provider data is unconfirmed | Public presentation may be blocked | Legal/licence review before publication |
| LIM-007 | Live provider integration is **RESOLVED** (2026-11-15): both providers verified live with rotated credentials; football-data.org returns 105 upcoming + 69 historical; API-Football returns 81 upcoming + 978 historical | Integration works end to end for read-only fixture retrieval | Public-display licence decision before any production use |
| LIM-008 | Provider pricing, quota, coverage, statistics availability, and SLA are **PARTIALLY VERIFIED** — plan names and daily quotas confirmed; season depth, statistics, head-to-head, lineups, and SLA remain unverified | Planning and product promises cannot rely on them | Read current official terms; record access date; run bounded statistics probe |
| LIM-009 | No API authentication, authorisation, or rate limiting | The API must bind to loopback or a trusted network | Auth design and approval before public exposure |
| LIM-010 | No backup automation, restore rehearsal, or retention policy | Data loss recovery is manual and untested | Operational rehearsal before production use |
| LIM-011 | No PostgreSQL verification; non-SQLite URLs fail closed | Portability is a design intention, not a property | Migration plan plus test evidence, if ever needed |
| LIM-012 | No monitoring, alerting, dashboards, or metrics endpoint | Failures are visible only by inspecting logs and tables | Add before production |
| LIM-013 | No secret manager integration | Credentials live in the process environment | Host-level control or a secret store before real use |
| LIM-014 | Independent QA review completed with FAIL verdict; security reassessment completed with private-only conditions (2026-11-14) | Phase 3 acceptance and public exposure remain blocked; GAP-013…GAP-020 and S-01…S-19 are not resolved | Execute `docs/research/phase-3-remediation-roadmap.md`, then obtain fresh independent sign-off |
| LIM-015 | Phase 4 used only synthetic test fixtures and supplied parameters; **RESOLVED for execution** (2026-11-16): Phase 5 runs on 4,905 stored real results with provenance. It still does not prove general football accuracy | The analysis is real-data-backed but the measured backtest is one corpus, not a product claim | Independent review and wider temporal validation before any performance claim |
| LIM-016 | No fitted goal rates, calibrator, or real sample policy exists; **RESOLVED** (2026-11-16): `poisson-v1.1.0` estimates competition baseline, attack/defence strength and form weights from prior results | Model is fitted and evaluated; calibration is reported, not applied as a correction | Measure and review before calling it calibrated |
| LIM-017 | Synthetic-data classification was caller-asserted inside `ResearchContext`; **RESOLVED at the persistence boundary** (2026-11-16): `VERIFIED_REAL` datasets require archived payload ids, provider code, and evidence windows | Pure in-process code can still be handed a mislabelled dataset; the API path cannot certify one without archive evidence | Keep provenance enforcement at the repository/API boundary |
| LIM-018 | Phase 4 digests detect changed input but are not signatures or tamper-proof storage | Reproducibility is weaker than tamper-evidence | Add signing/immutability only with an approved persistence design |
| LIM-019 | The test figure (**321 passed** as of 2026-11-17) is a local run by the implementing assistant, not an independent CI result | It is evidence of local passing, not external acceptance; the same agent wrote most of the tests it runs | Reproduce on a clean environment or in CI after approval, and obtain independent review |
| LIM-020 | Crest and emblem images are hot-linked from provider URLs (`crests.football-data.org`); their display/redistribution licence is part of the unresolved LIM-006 question | Private local display only; the URLs are stored values, never proxied or rehosted | Licence review before any public display |
| LIM-021 | Stored fixture coverage is bounded by `SYNC_LOOKAHEAD_DAYS` (30) and by the 10-day request window; dates outside a successful sync are empty, not "no matches" | A future window can legitimately show zero fixtures until a sync covers it | Re-run the fixtures sync; do not infer absence of a fixture from an empty window |
| LIM-022 | Narrow-screen layout was previously unverified below 486 px — **RESOLVED for the checked routes** (2026-11-17): `/evaluation` and the match analysis panel were executed at 375, 390, 430, 768, 1024, 1280 and 1440 px with no page-level overflow and internal table scrolling | Behaviour is now verified for those routes at those widths | Re-check after any layout change; a real-device pass is still worthwhile before shared use |
| LIM-023 | football-data.org Free tier returns no match statistics (probe 2026-11-15: `/matches/555085` has no `statistics` key on either team) | Statistics ingestion impossible on Free plan; analysis engine must abstain on statistics features | Paid Statistic Add-On or provider decision; not purchasable by agent |
| LIM-024 | football-data.org Free tier has no verified H2H endpoint | H2H features must abstain, not fabricate | Provider decision; no verified path |
| LIM-025 | Historical seasons retrievable by year param (`season=2025` → 380 PL matches) but season-ID filter returns 404 | Historical ingestion must use year parameter, ≤10-day chunks | Verified 2026-11-15; implement in sync history job |
| LIM-026 | Intelligence engine rejected all non-SYNTHETIC datasets; **RESOLVED** (2026-11-16) by ADR-0010 and the repository evidence contract | Real analysis is possible while the synthetic path is unchanged | Keep ADR-0010 tests in the suite |
| LIM-027 | The 50-match PD backtest was the only evaluation — **SUPERSEDED** (2026-11-17) by the Phase 7 evaluation: 970 matches, 11 competitions, 2026-02-25 → 2026-11-14 | The old Brier 0.5722 / skill 0.1417 figures describe one PD window; the Phase 7 figures (Poisson Brier 0.5831, skill 0.1253) describe a different, wider window | Neither is a general accuracy claim. Quote a figure only with its window and sample |
| LIM-028 | The draw under-prediction finding was window-dependent — **SUPERSEDED** (2026-11-17): on the 50-match PD window the draw bin 0.20–0.40 predicted 0.2465 and observed 0.3158, but on 970 matches Poisson's draw gap is +0.0004 (predicted 0.2293 vs observed 0.2289) and Dixon-Coles is +0.0046 | There is no aggregate draw bias to correct on the wider window, and no evidence that DC fixes a real defect | Do not quote the PD draw finding as a general property; re-measure per window |
| LIM-029 | In-match statistics, lineups, and injuries are unavailable on the free tier; the model has no such features | The analysis relies on results and form only; it declares the missing features | Paid statistics tier or a different provider, with explicit approval |
| LIM-030 | Historical results were backfilled in one retrieval window (`resolved_at` spans 2026-11-16 only), so point-in-time filtering uses `MatchResult.resolved_at`, not the true publication time. The evaluation uses a documented `kickoff + 3 h` horizon as a retrospective proxy | The evaluation cannot reconstruct what was known live at each historical moment; if the provider published later than kickoff + 3 h, slightly future information was admitted | Treat all current evaluation as retrospective; record observation times going forward |
| LIM-031 | No independent external review of `poisson-v1.1.0`, `dixon-coles-v1.0.0`, `elo-v1.0.0` or the `phase7-v1` protocol exists. The Phase 7 review is self-produced by the implementing agent | Acceptance cannot be inferred from a self-review or a passing suite | Commission an independent QA/ML review of the exact tree |
| LIM-032 | The bootstrap resamples matches as independent units, but matches are clustered by competition, season, matchday and team | Reported 95% intervals are probably too narrow; "not proven different" may understate uncertainty | Implement a clustered/block bootstrap before quoting intervals as precise |
| LIM-033 | No untouched final holdout. The 970-match corpus informed the protocol and model choices | A small optimistic bias cannot be excluded, even though no hyper-parameter search was run on it | Evaluate on genuinely future matches; do not re-split the same corpus and call it a holdout |
| LIM-034 | The evaluation freezes DC `rho` and Elo's Davidson mapping at each competition's first target kickoff, while the live path refits those parameters on every request | Evaluated DC/Elo numbers describe a more conservative cadence than the live report; a live number is not literally "the evaluated model" | Reconcile the cadences or state the difference wherever a DC/Elo number is shown |
| LIM-035 | Elo ratings are a single global pool: every result in the corpus, including other competitions, updates a team's rating | A Champions League result moves a league rating; "per-competition" Elo fitting applies only to the outcome mapping | Document on every Elo report; consider competition-scoped ratings before any Elo product use |
| LIM-036 | All stored scores come from one provider and were never cross-checked against an independent source | Provider-side score correctness is unverified; a systematic provider error would propagate into every model and metric | Add a second results source and reconciliation before any performance claim |
| LIM-037 | Per-model MCE is dominated by tiny calibration bins (e.g. draw 0.40–0.60 has n = 2), producing values like 0.4497 while ECE is 0.0254 | MCE reads as a catastrophic error when it is a small-sample artefact | Present ECE as the primary summary and MCE as a diagnostic only |

## Implementation gaps

| ID | Gap | Consequence |
| --- | --- | --- |
| GAP-001 | Statistics corrections update current rows but append no `match_change_log` entry | Statistics history is reconstructable from raw payloads, not from the change log |
| GAP-002 | Competition and team renames are updated in place without a change-log entry | Reference-data history is not audited in the change log |
| GAP-003 | Exact normalised names only; no alias table or fuzzy matching | A provider spelling change without an existing mapping becomes a new entity or ambiguity |
| GAP-004 | No cross-provider merge or reconciliation tool | Duplicate internal entities require a reviewed manual correction |
| GAP-005 | No backfill command for arbitrary historical seasons | Widening `SYNC_LOOKBACK_DAYS` is blunt and consumes the request budget |
| GAP-006 | Statistics jobs are limited per run and have no prioritisation beyond recent finished matches | Older matches may never receive statistics unless the limit is raised |
| GAP-007 | No player, lineup, event, injury, venue entity, or odds model | These cannot be ingested, and the API does not expose them |
| GAP-008 | No periodic `teams` job in the scheduler; the CLI job exists, and teams are otherwise created from match references | Team reference data is complete only for teams that appear in synced matches |
| GAP-009 | SQLite allows one writer; no concurrency or load test exists | A second worker or heavy concurrent CLI use is unsupported |
| GAP-010 | Scheduler configuration was inspected; only worker refusal paths are exercised, not successful long-running scheduling | Missed ticks, shutdown and long-run behaviour are unverified |
| GAP-011 | No API versioning policy beyond the `/api/v1` prefix | Breaking changes need a future version and deprecation plan |
| GAP-012 | No coverage guarantee for any competition, season, or metric | The coverage matrix starts empty by design |
| GAP-013 | Provider responses are streamed and capped per response, but aggregate run budgets and transport-level early-abort proof remain incomplete | Per-response memory is bounded in code; live quota/large-run behavior remains unverified |
| GAP-014 | Token bucket uses conservative single-token capacity and bounded numeric/date Retry-After handling, but is process-local | Provider window semantics and multi-worker quota compliance remain unverified |
| GAP-015 | Effective windows, configuration and observed raw IDs are persisted, but no durable per-request manifest exists and failed attempts have no raw evidence | Replay diagnostics are improved but exact replay remains incomplete |
| GAP-016 | Required fixture/result freshness rejects zero-fetched runs, but counters mix provider records, team-stat groups and metric rows | Freshness is not complete coverage proof; counter units require separation |
| GAP-017 | Competition area no longer supplies team country; embedded team country can still change canonical country without field-level source/effective provenance | International identity is improved but country history/conflict handling remains open |
| GAP-018 | Phase components, abandoned status, status invalidation and shootout cross-checks exist | Provider semantics, final-without-score, awarded policy and full transition matrix remain open |
| GAP-019 | Statistics validation, active mapping checks and participant checks are enforced; per-team quarantine continues valid groups | Provider DTO boundary coverage and complete historical mapping policy remain open |
| GAP-020 | Archive reuse/read digest verification and canonical raw links exist | Failed-response evidence, retention/deletion, permissions and backup policy remain open |
| GAP-021 | Finite Poisson matrices represent scores above `K` as overflow categories, with an undecidable overflow-overflow cell | 1X2 must return bounds and derived markets are conditional on the finite representation |
| GAP-022 | Intelligence features are descriptive and not opponent-strength adjusted or shrunk | Predictive usefulness and small-sample behavior are unknown |
| GAP-023 | Evaluation mechanics do not fit calibration, create a final holdout, estimate uncertainty, or persist experiments — **PARTIALLY RESOLVED** (2026-11-17): uncertainty intervals (fixed-seed bootstrap) and persisted, idempotent evaluation runs exist; calibration is diagnostic only and no final holdout exists | Evaluation is now reproducible and auditable; calibration correction and a genuine holdout remain missing (LIM-032, LIM-033) |
| GAP-024 | First-half, provider xG, lineup, injury, standings, tie-state, and competition-strength intelligence are omitted | Unsupported inputs cannot contribute to analysis |
| GAP-025 | 1X2 and double chance are bounds because the overflow-overflow cell is undecidable; correct-score output excludes overflow categories | Consumers must not treat a bound midpoint as a point probability, and correct-score mass is intentionally partial |
| GAP-026 | No confidence intervals, calibration fit, final-holdout execution, or persisted experiment exists — **PARTIALLY RESOLVED** (2026-11-17): confidence intervals and persisted 970-match experiments exist; calibration is fitted as a diagnostic, not applied; no final holdout exists | Evaluation is mechanically exercised on real history; it remains retrospective and clustered (LIM-032, LIM-033) |

## Technical uncertainties

- Whether independent Poisson is an adequate baseline was measured on 970 matches: Dixon-Coles
  is statistically indistinguishable (paired Brier +0.0002, 95% CI spanning zero) and Elo is
  directionally worse but not proven different. This does not establish adequacy beyond this
  corpus, provider and window.
- Whether a **joint** Dixon-Coles fit would outperform the current two-stage approximation is
  unverified; only `rho` is fitted after the rates.
- Calibration method (Platt vs isotonic) depends on sample size per market.
- xG comparability across providers and model versions is unresolved.
- Lineup and injury availability may be too unreliable or too late to use as features.
- Optimal form window and time-decay rate are unknown and must be evaluated out-of-sample.
- Storage shape for Phase 4 features (relational vs columnar) is undecided.
- Authentication and hosting model are undecided; no user accounts exist.
- SQLite behaviour under sustained concurrent reads during a long write transaction is untested.

### Provider-specific limitations (verified 2026-11-15)

- football-data.org Free tier rejects any window over 10 days (`HTTP 400 "Specified period must not exceed 10 days."`). Sync must chunk windows.
- football-data.org Free tier requires both `dateFrom` and `dateTo` together.
- API-Football Free tier returns 0 for `?next=N` and `?from/to` range queries; only per-date `?date=` works.
- API-Football Free tier has no league filter on upcoming fixtures.
- Neither provider's public-display licence is confirmed. football-data.org clause 9.1 bars display after cancellation; API-Football terms not yet read.

Resolved since the foundation phase: the worker mechanism (APScheduler, one process) and the
primary database (SQLite) are decided and implemented.

The close-out inspection above is by the implementing assistant, not an independent audit.
GAP-013 onward are outstanding findings, not approved exceptions or completed fixes. The
Phase 4 audit in `docs/research/phase-4-final-audit.md` is likewise self-produced; its
"VERIFIED" labels mean verified against synthetic automated tests, not against real football.
The Phase 7 review (`docs/research/phase-7-independent-model-review.md`) is a structured
self-review by the agent that wrote the code; it is not independent either (LIM-031).

## Data provider limitations

- Commercial APIs may omit lower tiers, women's football, or historical events.
- Free tiers may prohibit commercial use or require attribution — all terms `UNVERIFIED` until
  read and dated.
- Provider IDs are not portable across providers; identity mapping is required.
- Corrections and late-arriving data are normal; exact behaviour is unverified.
- Live latency is unknown; "live" may mean near-live or post-match.
- Statistics may be absent for matches a provider lists as finished.
- Scraping public statistics pages carries terms-of-service and reliability risk.
- A documented enum or endpoint does not prove entitlement for a specific competition.

## Product risks

- Users may interpret a probability as a guarantee, despite careful presentation.
- Coverage promises may outrun data quality.
- Explanation text may introduce numbers not present in the model output if not constrained.
- Market coverage may expand before calibration is demonstrated.
- A visually polished interface could create unearned trust.
- Scope creep toward live scores, news, tips, or betting is a persistent risk.
- An empty database can look like a broken product; the API reports emptiness honestly, but the
  interface must explain it.

## Model and evaluation risks (Phase 4)

- Historical football relationships may not persist across rule and competition changes.
- Small samples per team-season make team-specific parameters unstable.
- Backtest leakage, especially current-state features, can produce falsely good results.
- Multiple comparisons across markets inflate apparent improvements.
- Calibration drift after promotion/relegation and transfer windows.
- Abstention may be perceived as a missing feature rather than honesty.

## Phase 7 evaluation risks

- Matches are correlated; the fixed-seed bootstrap resamples them as independent and therefore
  reports intervals that are too narrow (LIM-032).
- No untouched holdout exists; the corpus informed protocol choices (LIM-033).
- Observation times are a backfill proxy; the 3 h eligibility horizon is not a replay of live
  knowledge (LIM-030, MR-05).
- The evaluated DC/Elo parameters are frozen per competition window while the live path refits
  per request (LIM-034).
- Elo ratings pool across competitions (LIM-035).
- One provider, never cross-checked (LIM-036).
- MCE is dominated by tiny bins and must not be read as a model-quality summary (LIM-037).
- The four pairwise comparisons have no multiplicity correction; no conclusion currently
  depends on a borderline interval, but a many-market report would need one.

## Process limitations

- Agents cannot verify claims that require external accounts, provider data, or legal review.
- Documentation quality depends on future verification; provider statements remain dated facts,
  not guarantees.
- Memory can lag documentation if not updated with `/update-memory`.
- Between 2026-11-16 and 2026-11-17 six `phase-8-*.md` documents claimed unimplemented betting
  features were complete, and memory described them as implemented. They were deleted and
  replaced by one frozen-proposal record. The safeguard now is that a status claim must name
  the file and test that prove it.
- The repository is under git as of 2026-11-14 with `.gitignore` exclusions for secrets,
  databases, and raw payloads. Phases 1–3 and the Phase 4 finalization are committed; there are
  still no tags or release branches.

## Related documents

- `memory/next-steps.md`
- `docs/data/coverage-matrix.md`
- `docs/data/providers-research.md`
- `docs/architecture/deployment-preparation.md`
- `docs/product/scope.md`
