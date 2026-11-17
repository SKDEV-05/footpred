# Next Steps

**Last updated:** 2026-11-17
**Current phase:** Phase 7 complete as self-reviewed work. Phase 8 is **not approved**.
Anything below marked BLOCKED needs a developer decision; do not start it by inference.

## Phase 7 close-out — done

| Item | State |
| --- | --- |
| Model dispatch (`model_selection.py`) with no fallback | Done |
| `?model=` on the analysis endpoint | Done |
| Comparison endpoint on one point-in-time dataset | Done |
| DC leakage guard, `rho` bounds/clipping | Done |
| Elo chronological replay + frozen Davidson mapping | Done |
| Multi-competition evaluation reproduced and persisted | Done |
| 56 new tests (321 total passing) | Done |
| `/evaluation` dashboard from persisted runs | Done |
| Match panel model selector and comparison table | Done |
| Responsive checks at 375–1440 px | Done |
| False Phase 8 docs replaced by a frozen proposal record | Done |
| Orphan `validation.py` / `calibration.py` deleted | Done |

## Immediate open gates (in order)

1. **Independent QA/ML review** — BLOCKED on a reviewer who is not the implementing agent.
   Scope: `poisson-v1.1.0`, `dixon-coles-v1.0.0`, `elo-v1.0.0`, the `phase7-v1` protocol, and
   the claims in `phase-7-final-report.md`. Self-review does not satisfy `AGENTS.md` §7.
2. **Public-display licence (LIM-006, LIM-020)** — BLOCKED on legal/licence review. Until it is
   resolved, the product stays loopback-only and no result, probability or crest may be shown
   to a third party.
3. **Phase 3 acceptance** — prior independent QA verdict FAIL; security accepts private
   loopback only and rejects public exposure. A fresh exact-tree re-audit is required.
4. **Coverage decision (PD-002/PD-003)** — confirm which competitions and seasons are licensed
   and actually retrieved. Eleven competitions have matches; EC and WC have none.

## Model and evaluation work that is justified now

These are research tasks, not approved features. Each needs a plan before code.

1. **Reconcile evaluation cadence with live behaviour (MR-11).** The evaluation freezes DC
   `rho` and Elo's Davidson mapping at the competition's first target kickoff; the live path
   refits per request. Either evaluate the live cadence or make the live path freeze. Decide
   with evidence, not preference.
2. **Clustered bootstrap (MR-03).** Resample by competition/season/matchday rather than by
   match, or report a block bootstrap. Current intervals are optimistic.
3. **Out-of-time holdout (MR-04).** The 970 matches informed protocol choices. A genuine
   holdout requires future matches, not a re-split of the same corpus.
4. **Joint Dixon-Coles MLE.** Replace the two-stage approximation with a joint fit and compare
   it against the current DC before drawing any conclusion about low-score dependence.
5. **Provider second source.** No independent cross-check of stored scores exists. A second
   provider would test provider-side correctness; it also needs a licence review.
6. **Per-competition sample adequacy.** 59–100 evaluation matches per competition cannot rank
   leagues. More seasons or explicit per-competition abstention are the only honest options.

## Explicitly not approved

Do not start any of these without a developer decision and an ADR:

- odds ingestion, market-implied probability, expected value, value betting;
- paper betting, staking, bankroll, ROI or drawdown simulation;
- best-bets ranking or tip presentation;
- probability calibration as a **correction** (temperature scaling, isotonic) applied to
  published probabilities;
- authentication, subscriptions, payments, advertising;
- public deployment, containers, CI/CD, monitoring stack, PostgreSQL;
- machine-learning training, an LLM prediction path, generated analysis text;
- in-match statistics, lineups, injuries or paid-tier xG ingestion.

The Phase 8 proposals are frozen in `docs/research/phase-8-betting-proposals-rejected.md`.
Reading them is not approval to implement them.

## Routine verification before any claim

```
cd apps/backend && PYTHONPATH=. ../../.venv/bin/python -m pytest
.venv/bin/python -m alembic current      # expect 0006 (head)
.venv/bin/python -m alembic check        # expect no new upgrade operations
cd apps/web && npx tsc --noEmit && npm run build
```

Then reproduce the evaluation and confirm the persisted row is reused rather than duplicated.
