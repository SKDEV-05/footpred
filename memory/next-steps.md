# Next Steps

**Phase 4 is accepted (DEC-018). Phase 5 is approved under ADR-0010 and implemented privately
on loopback (DEC-027).** It is not a public product, has no performance guarantee, and must not
be exposed on a shared network. The current evidence and limits are in
[`PROJECT_STATUS.md`](../PROJECT_STATUS.md), [`memory/current-state.md`](current-state.md), and
[`docs/research/2026-11-16-historical-coverage-report.md`](../docs/research/2026-11-16-historical-coverage-report.md).

## Completed this session (2026-11-16)

- Historical ingestion: 4,905 finished results stored across eleven competitions, 100%
  payload-linked; 10 extra-time/penalty records quarantined with reasons.
- Point-in-time dataset loader with real provenance, regulation-only filtering, and a
  content-stable digest.
- `poisson-v1.1.0` / `features-v1.1.0` / `evaluation-v1.1.0` with a shared rate estimator,
  rolling-origin backtest, calibration, uniform baselines, and explicit model parameters.
- Analysis API with four statuses, abstentions, idempotent reuse, forced regeneration, and
  append-only history.
- Next.js **Analyze Match** panel with probabilities, xG, markets, scorelines, historical
  records, evaluation, calibration, provenance, limitations, and prior reports.
- `python -m app.cli coverage [--format json|markdown]` and the coverage research report.
- 265 backend tests pass; `alembic check` clean; `npm run build` passes; browser check at the
  available 471 px viewport shows no console errors or horizontal overflow.

## Immediate next action

1. Obtain independent QA/ML review of the exact analysis tree, the backtest protocol, and the
   wording of every published probability. The current backtest is a local measurement.
2. Re-run `python -m app.cli coverage`, the full test suite, and `alembic check` before any
   external claim; attach the output.
3. Decide whether the eleven-competition corpus is sufficient for the intended use. Do not add
   a paid plan, statistics tier, or new provider without explicit approval.
4. Resolve LIM-006 (display/redistribution licence) before any shared or public display.
5. Keep the service on loopback. Do not add auth, deployment, or public hosting as a shortcut.

## Analysis-specific follow-up

- Measure whether a low-score dependence term (for example Dixon-Coles rho) reduces the measured
  draw under-prediction; record the decision as an ADR before applying it.
- Add cross-competition and wider temporal backtests before making any accuracy statement beyond
  the measured PD corpus.
- Improve observation-time recording going forward; the current history was backfilled in one
  window, so the retrospective evaluation cannot reconstruct earlier knowledge states.
- Keep statistics, lineups, and injuries declared as missing. Do not estimate them from results.
- Re-check the frontend on a phone-width device below 471 px (LIM-022).

## Phase 3 / security conditions still open

1. Review `docs/research/phase-3.1-remediation-report.md`; final acceptance remains rejected
   until failed-response evidence, retention, counter units, exact replay and domain conditions
   are resolved or explicitly risk-accepted.
2. Review the security reassessment and remediate or explicitly risk-accept S-01…S-19 before any
   public or shared-network exposure; public exposure is currently rejected.
3. Obtain fresh independent QA/security/data/domain/architecture review of the exact latest tree.
4. Backups, restore rehearsal, monitoring, and secret-manager integration remain unbuilt.

## Provider selection (PD-002) — status

- football-data.org: verified live, 13 competitions, 10-day window limit, clause 9.1 licence risk.
  Statistics/H2H/season depth UNVERIFIED; the free tier has no statistics.
- API-Football: verified live, 1,244 leagues, per-date query only on Free plan, licence
  unverified. Statistics/H2H/season depth UNVERIFIED.
- Sportmonks, TheSportsDB, Sportradar: docs verified, no credential, no live call.
- The existing adapter is football-data.org only; API-Football would require a new adapter.
- The developer must decide provider, plan, competitions, seasons, and the display licence.

## Phase 3 close-out checklist

- [x] Architecture docs, ADRs, and guides written.
- [x] Schema, migrations, ingestion, sync, API, CLI implemented.
- [x] 265 tests passing locally (2026-11-16 session).
- [x] Known gaps documented, including GAP-013 through GAP-020.
- [x] Phase 4 final acceptance report and provider capability audit written.
- [ ] Resolve/review live-data integrity and transport findings; add regression coverage.
- [ ] Independent review by QA and security specialists; previous attempts were blocked.
- [ ] Developer sign-off.
- [x] Version control initialised with a `.gitignore` excluding `.env`, databases, and raw data.

## Phase 4 close-out checklist

- [x] Pure intelligence package with synthetic-only guards (ADR-0009).
- [x] Mathematical primitives, evaluation mechanics, and 84 intelligence tests.
- [x] Final acceptance report and developer acceptance.
- [x] Real-data contract recorded in ADR-0010 without weakening the synthetic path.

## Phase 5 close-out checklist

- [x] Historical results ingested with archive provenance.
- [x] Point-in-time dataset, regulation-only corpus, no future leakage.
- [x] Fitted Poisson model, exact 1X2 normalization, deterministic maths.
- [x] Rolling-origin backtest with Brier, log loss, uniform baselines, and calibration bins.
- [x] Persistence, analysis API, abstentions, idempotency, and report history.
- [x] Analyze Match frontend with four statuses and explicit provenance/limitations.
- [x] Coverage command and coverage research report.
- [x] 265 backend tests, clean schema check, passing frontend build.
- [ ] Independent QA/ML review and wider evaluation.
- [ ] Licence decision and any public display.
