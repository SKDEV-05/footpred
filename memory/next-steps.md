# Next Steps

**Phase 4 is not approved.** Do not begin prediction, ML, frontend, auth, or deployment work
without explicit developer approval.

## Immediate next action

Developer review of Phases 2 and 3:

1. Read `PROJECT_STATUS.md`, `memory/current-state.md`, and the two phase reports.
2. Review the architecture decisions (ADR-0002 … ADR-0007) and the stack/database choice.
3. Review `docs/data/coverage-matrix.md`: it is empty because nothing is live-verified.
4. Decide the provider, plan, competition coverage, and licence position.
5. Accept, amend, or reject the data foundation before any model work starts.

## Phase 3 close-out checklist

- [x] Architecture docs, ADRs, and guides written.
- [x] Schema, migrations, ingestion, sync, API, CLI implemented.
- [x] 124 tests passing locally (2026-11-14 session); pagination validator regression fixed.
- [x] Known gaps documented, including close-out findings GAP-013 through GAP-020.
- [ ] Resolve/review live-data integrity and transport findings; add regression coverage.
- [ ] Independent review by QA and security specialists — both attempts blocked by tool usage
      limits; no review outcome exists. Restore access or arrange human review.
- [ ] Developer sign-off.
- [ ] Version control initialised with a `.gitignore` excluding `.env`, databases, and raw data.

## Live verification (requires approval and credentials)

Time-boxed, read-only, and recorded:

Before starting: resolve or explicitly review the data-integrity and transport gaps listed in
`memory/known-limitations.md` (GAP-013 onward). Local test success is not live-data acceptance.

1. Obtain a token for a known plan; do not purchase on the developer's behalf.
2. Record the plan, date, and provider terms reviewed.
3. Run `python -m app.cli check-provider`; keep the archive id.
4. Sync one competition and one season; record run counts.
5. Compare returned fixtures, results, and statistics with the provider's own presentation.
6. Record what was observed and what was **not** in `docs/data/coverage-matrix.md`.
7. Confirm display/redistribution rights before anything is shown publicly.

Stop if a paid commitment, legal agreement, or unclear licence is required.

## Phase 4 prerequisites (not started)

- [ ] Developer approval of Phases 2/3.
- [ ] Provider, plan, competitions, and licence decided.
- [ ] Live verification evidence recorded.
- [ ] Point-in-time feature table design and leakage test protocol.
- [ ] Baseline model and evaluation protocol fixed before results are inspected.
- [ ] Prediction store with immutability and tamper-evidence.
- [ ] Calibration segments and coverage decisions.
- [ ] Decision on whether live data is in scope.
- [ ] Independent review of the data foundation.

## Pending decisions

| ID | Decision | Owner | Blocks |
| --- | --- | --- | --- |
| PD-002 | Final provider selection | Developer + data-engineer | Live verification, coverage |
| PD-003 | Competition/season coverage | Developer + product-architect | Coverage matrix, evaluation |
| PD-004 | Data budget and plan | Developer | Provider choice, quota |
| PD-005 | xG: licensed, computed, or omitted | Developer + football-analyst | Feature set |
| PD-006 | ~~Storage stack confirmation~~ Resolved: SQLite for Phase 3; PostgreSQL deferred | Developer + backend-architect | Closed |
| PD-007 | Whether live data is in scope initially | Developer | Architecture, ingestion |
| PD-008 | Uncertainty presentation approach | Developer + ux-designer | Interface design |
| PD-009 | Display/redistribution licence position | Developer | Public API or UI |
| PD-010 | Version control and review workflow | Developer | Traceability, rollback |

## Recommended sequencing after approval

1. Live provider verification and coverage record.
2. Fix any adapter defect the live payload reveals; add a regression test.
3. Point-in-time data audit: confirm stored inputs are sufficient and correctly timestamped.
4. Feature design with an explicit leakage review.
5. Baseline model, fixed evaluation protocol, then results.
6. Prediction store and evaluation report.
7. Interface only after the numbers are trustworthy.

Do not reorder modelling ahead of verified data. A model trained on unverified coverage and
unverified missing-data behaviour produces confident nonsense.

## Stop conditions

Stop and ask the developer if:

- a provider requires a paid commitment or legal agreement;
- licensing terms are ambiguous for the intended use;
- required history is unavailable at usable quality;
- a design requires a technology not approved;
- work would cross into Phase 4 without explicit approval;
- a migration would destroy or rewrite stored data;
- real provider data would be committed or published.

## Related documents

- `PROJECT_STATUS.md`
- `memory/known-limitations.md`
- `memory/decisions.md`
- `docs/data/coverage-matrix.md`
- `docs/architecture/implementation-plan.md`
