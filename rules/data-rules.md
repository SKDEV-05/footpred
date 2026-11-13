# Data Rules

Binding rules for all data handling and for any number that reaches a user. Data integrity is
the foundation of prediction quality; a model cannot recover from corrupted inputs.

---

## D1 — Never invent data

MUST NOT fabricate:
- fixtures, results, scorelines, or events;
- lineups, injuries, suspensions, or availability;
- xG, xGA, possession, or any statistic;
- historical trends or "typical" values presented as real;
- provider prices, quotas, rate limits, or coverage claims.

Hypothetical examples are allowed only when clearly labelled as illustrative and not
mistakable for real data.

## D2 — Missing is not zero

Distinguish four states explicitly: measured zero, missing/null, unknown/not yet available,
and not applicable.

- Never use `fillna(0)` on football statistics.
- Never treat an omitted fixture as a 0-0 result.
- Never convert "no lineup published" into "no changes".
- Downstream logic must handle missing values explicitly, including abstention.

## D3 — Provenance for every derived value

Every derived record must be traceable to:
- source provider and resource;
- fetch timestamp (UTC) and request parameters;
- raw payload hash;
- parser and transformation version;
- ingest run identifier;
- source record identifier.

If a number cannot be traced, it is not trusted.

## D4 — Raw before transformed

- Land provider payloads unmodified before normalization.
- Raw payloads are immutable and retained according to licensing and retention policy.
- Transformations are versioned and re-runnable from raw data.
- Do not discard the ability to reprocess after a rule change.

## D5 — Idempotency

- Every ingestion and transformation job is safe to re-run.
- Use natural keys and upserts; never rely on execution order or "run once" assumptions.
- Duplicate deliveries are updates, not new records.
- A re-run over the same window produces the same state.

## D6 — Point-in-time correctness

- Features used for a prediction must be computed from information available before the
  prediction timestamp.
- Current-state tables are not valid historical inputs.
- Backtests reconstruct the state as of each prediction time.
- No future information may leak into training, features, or evaluation.

Violations invalidate the evaluation and must be treated as a defect, not a tuning issue.

## D7 — Corrections are versioned

- Provider corrections create a new version with an effective timestamp.
- Historical predictions are never rewritten to match later corrections.
- Dependent derived data is recomputed explicitly, and the recomputation is recorded.
- Both the original and corrected values remain auditable.

## D8 — Identity is stable and reviewed

- Prefer provider IDs; maintain a cross-provider mapping.
- Team, competition, player, and venue merges require a reviewable rule and a recorded
  history.
- Never auto-merge entities on fuzzy name similarity alone.
- Handle renamed clubs, reserve teams, and duplicate competition names explicitly.

## D9 — Competition context is preserved

- Do not pool leagues, tiers, cup competitions, or eras without modelling the difference.
- Store competition, season, stage, and venue type on every fixture.
- Separate regulation-time statistics from extra time and penalties.
- Neutral venues are not home matches.

## D10 — Quality gates before use

Data must pass defined checks before entering derived layers or model inputs:

- schema and type;
- range and domain;
- cross-field consistency;
- referential integrity;
- temporal validity;
- duplicate detection;
- staleness;
- cross-source reconciliation where available.

Failures are quarantined with the raw payload and a reason. Silent dropping is prohibited.

## D11 — Licensing is a data constraint

- Record the licence and attribution requirements for every source.
- Do not cache, redistribute, or derive beyond what the terms permit.
- Do not present licensed data publicly until the developer has confirmed the rights.
- Flag ambiguous terms as blocking open questions.

## D12 — Evaluation data is sacred

- Freeze the evaluation protocol before looking at results.
- Use temporal splits; never random splits for time-dependent data.
- Report baselines and proper scoring rules.
- Do not tune on the holdout set.
- Record the exact data snapshot and version used for every reported metric.

## D13 — Staleness is visible

- Track expected update windows per source and entity.
- Mark stale data as stale at the point of use.
- Stop serving predictions that depend on data known to be stale or invalid.
- Detect kickoff changes, postponements, and abandoned matches; do not assume the schedule is
  stable.

## D14 — No silent imputation

- Imputation is allowed only as an explicit, documented model feature.
- Record which values were imputed and with what method.
- Never impute a value that will later be presented as observed.
- Prefer abstention over imputation for decision-critical fields (e.g. whether a match has
  started).

## D15 — Retention and deletion are designed

- Define retention per data tier and per licence.
- Personal data, if ever collected, follows minimisation and deletion requirements.
- Raw payload retention must respect provider terms.
- Deletion is auditable and does not corrupt derived provenance silently.

---

## Enforcement

- `data-engineer` owns the rules; `qa-engineer` specifies the checks; `security-reviewer`
  reviews licensing and privacy; `ml-researcher` enforces D6 and D12 in every evaluation.
- Any exception requires an ADR and developer approval.

## Related documents

- `docs/data/data-strategy.md`
- `docs/data/data-quality.md`
- `docs/data/data-provenance.md`
- `docs/data/providers-research.md`
- `rules/engineering-rules.md`
- `.opencode/skills/data-validation/SKILL.md`
