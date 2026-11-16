## Immediate next action

1. Obtain independent QA/ML review of the exact analysis tree, the backtest protocol, and the wording of every published probability. The current backtest is a local measurement.

2. Re-run `python -m app.cli coverage`, the full test suite, and `alembic check` before any external claim; attach the output.

3. Decide whether the eleven-competition corpus is sufficient for the intended use. Do not add a paid plan, statistics tier, or new provider without explicit approval.

4. Resolve LIM-006 (display/redistribution licence) before any shared or public display.

5. Keep the service on loopback. Do not add auth, deployment, or public hosting as a shortcut.

## Analysis-specific follow-up

- Measure whether a low-score dependence term (for example Dixon-Coles rho) reduces the measured draw under-prediction; record the decision as an ADR before applying it.
- Add cross-competition and wider temporal backtests before making any accuracy statement beyond the measured PD corpus.
- Improve observation-time recording going forward; the current history was backfilled in one window, so the retrospective evaluation cannot reconstruct earlier knowledge states.
- Keep statistics, lineups, and injuries declared as missing. Do not estimate them from results.
- Re-check the frontend on a phone-width device below 471 px (LIM-022).