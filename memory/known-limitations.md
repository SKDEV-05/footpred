# Known Limitations

Missing information, uncertainties, and risks. Update when a limitation is resolved or a new one
is discovered. Never remove an item silently; mark it resolved with the evidence.

## Missing information

| ID | Limitation | Impact | Resolution |
| --- | --- | --- | --- |
| LIM-001 | No provider has been evaluated against a real API; no account exists | Adapter correctness is proven only against documented shapes | Time-boxed live verification with recorded evidence |
| LIM-002 | No competition or season coverage has been agreed | Coverage matrix is empty; fixture volume unknown | Product decision, then provider fit check |
| LIM-003 | Data budget is unknown | Cannot compare plans or commit to coverage | Developer decision |
| LIM-004 | Historical depth required for modelling is undecided | Affects storage and backtest design | Model research plus verified availability |
| LIM-005 | No real-world volume, latency, or cost measurements exist | Scalability and SLA claims remain hypotheses | Measure after a live ingestion period |
| LIM-006 | Licence for display and redistribution of provider data is unconfirmed | Public presentation may be blocked | Legal/licence review before publication |
| LIM-007 | Live provider integration is **BLOCKED**: no token, no account, no live call | Cannot claim the integration works end to end | Credentials plus a recorded `check-provider` and sync run |
| LIM-008 | Provider pricing, quota, coverage, statistics availability, and SLA are **UNVERIFIED** | Planning and product promises cannot rely on them | Read current official terms; record access date |
| LIM-009 | No API authentication, authorisation, or rate limiting | The API must bind to loopback or a trusted network | Auth design and approval before public exposure |
| LIM-010 | No backup automation, restore rehearsal, or retention policy | Data loss recovery is manual and untested | Operational rehearsal before production use |
| LIM-011 | No PostgreSQL verification; non-SQLite URLs fail closed | Portability is a design intention, not a property | Migration plan plus test evidence, if ever needed |
| LIM-012 | No monitoring, alerting, dashboards, or metrics endpoint | Failures are visible only by inspecting logs and tables | Add before production |
| LIM-013 | No secret manager integration | Credentials live in the process environment | Host-level control or a secret store before real use |
| LIM-014 | Independent QA and security reviews attempted but both stopped at the tool usage limit (2026-11-14 close-out) | No independent findings or sign-off exist; acceptance is pending | Restore review access or arrange human review; do not treat self-checks or the Phase 4 audit as approval |
| LIM-015 | Phase 4 uses only synthetic test fixtures and supplied parameters | It proves software/math behavior, not football accuracy, calibration, or usefulness | Licensed point-in-time history plus a frozen Phase 5 evaluation protocol |
| LIM-016 | No fitted goal rates, Dixon-Coles rho, Elo policy, calibrator, or real sample policy exists | Mathematical outputs cannot be used as real predictions | Estimate and validate only after Phase 5 approval and verified data |
| LIM-017 | Synthetic-data classification is caller-asserted inside `ResearchContext` | A deliberately mislabelled real dataset cannot be detected in-process | Enforce provenance at the persistence/ingestion boundary in Phase 5, not only in pure code |
| LIM-018 | Phase 4 digests detect changed input but are not signatures or tamper-proof storage | Reproducibility is weaker than tamper-evidence | Add signing/immutability only with an approved persistence design |
| LIM-019 | The 208-test figure is a local run by the implementing assistant, not an independent CI result | It is evidence of local passing, not external acceptance | Reproduce on a clean environment or in CI after approval |

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
| GAP-013 | HTTP size check runs after HTTPX buffers the body; numeric 429 `Retry-After` is capped at 60 seconds, HTTP-date values ignored | Not a memory/download bound; early retries possible. Review before live use |
| GAP-014 | Token bucket starts with a full minute's burst capacity and refills continuously | Average-rate control is not a strict per-minute quota guarantee; provider window semantics need verification |
| GAP-015 | CLI/scheduled jobs do not persist effective configuration/date windows; quarantine does not receive the fetched raw payload id | Run evidence is incomplete for exact replay and rejected-record provenance |
| GAP-016 | Global freshness uses any successful job, including empty/reference-only jobs; counters mix fixture outcomes, statistics groups and metric rows | Fresh status is not proof of current fixture/result coverage; counters are not a row audit |
| GAP-017 | Fixture ingestion assigns the competition's area to embedded teams; mapped team enrichment does not update name/country | International competitions can misattribute team countries; rename/country enrichment needs domain review before trusting live data |
| GAP-018 | Final-score validation derives the winner from full-time goals without a shootout-specific rule | A legitimate shootout winner with level full-time goals can be rejected; regulation/extra-time/shootout interpretation needs regression coverage |
| GAP-019 | Statistics upsert does not invoke `validate_statistics`; invalid key `ValueError`s fail the job rather than quarantine. It resolves team mappings without verifying they match the fixture participants | Statistics boundary is only partially validated; review and regression tests required before accepting live statistics |
| GAP-020 | HTTP errors and oversized responses are not archived; existing archive files are reused based on size without a digest recheck | Archive is not complete transport evidence or tamper-proof storage |
| GAP-021 | Finite Poisson matrices represent scores above `K` as overflow categories, with an undecidable overflow-overflow cell | 1X2 must return bounds and derived markets are conditional on the finite representation |
| GAP-022 | Intelligence features are descriptive and not opponent-strength adjusted or shrunk | Predictive usefulness and small-sample behavior are unknown |
| GAP-023 | Evaluation mechanics do not fit calibration, create a final holdout, estimate uncertainty, or persist experiments | No real validation or reproducible experiment record exists |
| GAP-024 | First-half, provider xG, lineup, injury, standings, tie-state, and competition-strength intelligence are omitted | Unsupported inputs cannot contribute to analysis |
| GAP-025 | 1X2 and double chance are bounds because the overflow-overflow cell is undecidable; correct-score output excludes overflow categories | Consumers must not treat a bound midpoint as a point probability, and correct-score mass is intentionally partial |
| GAP-026 | No confidence intervals, calibration fit, final-holdout execution, or persisted experiment exists | Evaluation code is mechanically tested, not exercised on history |

## Technical uncertainties

- Whether independent Poisson is an adequate baseline, or Dixon-Coles is required, is unverified
  without data.
- Calibration method (Platt vs isotonic) depends on sample size per market.
- xG comparability across providers and model versions is unresolved.
- Lineup and injury availability may be too unreliable or too late to use as features.
- Optimal form window and time-decay rate are unknown and must be evaluated out-of-sample.
- Storage shape for Phase 4 features (relational vs columnar) is undecided.
- Authentication and hosting model are undecided; no user accounts exist.
- SQLite behaviour under sustained concurrent reads during a long write transaction is untested.

Resolved since the foundation phase: the worker mechanism (APScheduler, one process) and the
primary database (SQLite) are decided and implemented.

The close-out inspection above is by the implementing assistant, not an independent audit.
GAP-013 onward are outstanding findings, not approved exceptions or completed fixes. The
Phase 4 audit in `docs/research/phase-4-final-audit.md` is likewise self-produced; its
"VERIFIED" labels mean verified against synthetic automated tests, not against real football.

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

## Process limitations

- Agents cannot verify claims that require external accounts, provider data, or legal review.
- Documentation quality depends on future verification; provider statements remain dated facts,
  not guarantees.
- Memory can lag documentation if not updated with `/update-memory`.
- The repository is under git as of 2026-11-14 with `.gitignore` exclusions for secrets,
  databases, and raw payloads. Phases 1–3 and the Phase 4 finalization are committed; there are
  still no tags or release branches.

## Related documents

- `memory/next-steps.md`
- `docs/data/coverage-matrix.md`
- `docs/data/providers-research.md`
- `docs/architecture/deployment-preparation.md`
- `docs/product/scope.md`
