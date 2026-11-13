# Known Limitations

Missing information, uncertainties, and risks. Update when a limitation is resolved or a new
one is discovered. Never remove an item silently; mark it resolved with the evidence.

## Missing information

| ID | Limitation | Impact | Resolution |
| --- | --- | --- | --- |
| LIM-001 | No provider has been evaluated against a real API; no account exists | Cannot confirm coverage, latency, missing-data behaviour, or terms | Authorised verification spike in a later phase |
| LIM-002 | No competition or season coverage has been agreed | Cannot size the data model or the fixture volume | Product decision, then provider fit check |
| LIM-003 | Data budget is unknown | Cannot compare commercial plans | Developer decision |
| LIM-004 | Historical depth required for modelling is undecided | Affects storage and backtest design | Model research + data availability |
| LIM-005 | No real-world volume, latency, or cost measurements exist | Scalability and SLA claims remain hypotheses | Measure after ingestion exists |
| LIM-006 | Licensing for display of derived statistics is unconfirmed | Could block public presentation of some metrics | Legal/licence review before publication |

## Technical uncertainties

- Whether independent Poisson is an adequate baseline for the target competitions, or whether
  Dixon-Coles (or a bivariate approach) is required, is unverified without data.
- Calibration method (Platt vs isotonic) depends on sample size per market.
- xG comparability across providers and model versions is unresolved; provider-specific xG may
  not be usable as a continuous series.
- Lineup and injury availability may be too unreliable or too late to use as features.
- Optimal form window and time-decay rate are unknown and must be evaluated out-of-sample.
- Storage shape for features (relational vs columnar) is undecided.
- Queue/worker mechanism (Celery vs APScheduler) is undecided.
- Authentication and hosting model are undecided; no user accounts exist.

## Data provider limitations

- Commercial APIs may omit lower tiers, women's football, or historical events.
- Free tiers may prohibit commercial use or require attribution — all terms `UNVERIFIED` until
  read and dated.
- Provider IDs are not portable across providers; identity mapping is required.
- Corrections and late-arriving data are normal; exact behaviour is unverified.
- Live latency is unknown; "live" may mean near-live or post-match.
- Scraping public statistics pages carries terms-of-service and reliability risk.

## Product risks

- Users may interpret a probability as a guarantee, despite careful presentation.
- Coverage promises may outrun data quality.
- Explanation text may introduce numbers not present in the model output if not constrained.
- Market coverage may expand before calibration is demonstrated.
- A visually polished interface could create unearned trust.
- Scope creep toward live scores, news, or tips is a persistent risk.

## Model and evaluation risks

- Historical football relationships may not persist (rule changes, competition changes).
- Small samples per team-season make team-specific parameters unstable.
- Backtest leakage (especially current-state features) can produce falsely good results.
- Multiple comparisons across markets inflate apparent improvements.
- Calibration drift after promotion/relegation and transfer windows.
- Abstention may be perceived as a missing feature rather than honesty.

## Research gaps

- No completed provider comparison with verified specifications.
- No benchmark of statistical baselines on actual data.
- No user research on how uncertainty should be presented.
- No accessibility testing with real components (none exist).
- No security review of implementation (none exists).

## Process limitations

- Agents cannot verify claims that require external accounts or data access in Phase 1.
- Documentation quality depends on future verification; some targets are `TBD` by design.
- Memory can lag documentation if not updated with `/update-memory`.

## Related documents

- `memory/next-steps.md`
- `docs/data/providers-research.md`
- `docs/product/scope.md`
- `docs/architecture/quality-attributes.md`
