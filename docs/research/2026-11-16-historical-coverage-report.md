# Historical results coverage (football-data.org free tier)

**Date:** 2026-11-16
**Author:** data-engineer / backend-architect
**Confidence:** high for the stored counts (executed against the live SQLite database and the
raw payload archive); medium for future coverage (the provider's free-tier limits are
documented, not contractually guaranteed).
**Decision affected:** whether the stored real results are sufficient to run the
`poisson-v1.1.0` analysis and rolling-origin backtest (ADR-0010).

## Question

Which historical results are actually stored, how are they evidenced, and is the corpus
large enough to analyse upcoming fixtures without borrowing data from the future or
inventing missing values?

## Context

- Phase 5 is approved under ADR-0010; the synthetic path must remain unchanged.
- `VERIFIED_REAL` datasets require an archived provider payload, a provider code, a
  retrieval window, an observation window, and a digest. A bare "real" label is rejected.
- The provider free tier exposes fixtures and results but no in-match statistics.
- The analysis model needs at least 5 matches per team and 20 competition matches for a
  competition baseline; the backtest needs 50 competition matches after a 40-match warm-up.

## Method

1. Ran the historical sync job (`sync_history`) with `season=<year>&status=FINISHED` for
   the stored competitions, in windows no longer than the provider's 10-day limit.
2. Counted stored rows and archived payload links directly with SQL against
   `data/football.db` (read-only queries).
3. Generated the coverage report from code rather than by hand:

   ```bash
   cd apps/backend
   python -m app.cli coverage --format markdown
   ```

   The command joins competitions, seasons, matches, results, and quarantined records; it
   is reproducible and is the source of the table below.
4. Cross-checked the model corpus against the coverage report (`PD`: 380 + 119 = 499,
   matching the `competition_matches` figure in the live analysis report).

Access date for all provider facts: 2026-11-16.

## Verified facts

1. The database holds **5,322 matches**, of which **4,905 are finished results** and 417
   are upcoming fixtures.
2. **5,322 of 5,322** matches are linked to an archived raw payload
   (`payload_linked_matches = stored_matches`); provenance is complete for every stored
   match.
3. The stored finished results span **2025-02-05 → 2026-11-14**.
4. Eleven competitions have stored matches: BL1, BSA, CL, CLI, DED, ELC, FL1, PD, PL, PPL,
   SA. `EC` and `WC` rows exist as competition records but have **zero** stored matches;
   they are labelled `no_stored_matches`, not counted as coverage.
5. Each league has a complete or near-complete prior season plus the current partial
   season. Premier League 2025/2026 has 380 finished results; La Liga 2025/2026 has 380;
   Serie A 2025/2026 has 380; Bundesliga 2025/2026 has 306; Ligue 1 2025/2026 has 305;
   Championship 2025/2026 has 556; Primeira Liga 2025/2026 has 306; Eredivisie 2025/2026
   has 306; Brasileirão 2025 has 380; Copa Libertadores 2025 has 154.
6. The 2026/2027 seasons are partial and vary: 119 finished results in PD, 110 in SA, 100
   in PL, 90 in FL1, 81 in BL1, 72 in CL, 108 in DED, 98 in PPL, 341 in BSA, 147 in CLI,
   and 0 in ELC (fixtures are stored but none has finished in the retrieved window).
7. **10 provider records were rejected** during the historical sync. All 10 are
   extra-time/penalty-shootout inconsistencies (cumulative extra-time scores below
   full-time scores, or penalty scores without a shootout duration). They are quarantined,
   not silently dropped or merged.
8. The live analysis for match 410 (Real Madrid vs Celta, 2026-11-21) reports
   `historical_matches = 4892`, `competition_matches = 499`, and
   `excluded_extra_time_or_shootout = 13` for its point-in-time window. 4,905 − 13 = 4,892:
   the 13 regulation exclusions account for the difference, and no stored result was removed by
   the kickoff cutoff for this fixture (all stored results predate 2026-11-21).
9. The rolling-origin backtest on 50 out-of-sample PD matches evaluates successfully:
   Brier 0.5722, log loss 0.9581, uniform Brier 0.6667, uniform log loss 1.0986, Brier
   skill 0.1417, ECE 0.0661, MCE 0.3084, test period 2026-10-09 → 2026-11-08.

## Analysis

| Need | Requirement | Availability | Verdict |
| --- | --- | --- | --- |
| Team sample | ≥ 5 prior matches | 68 home / 50 away for match 410; every active top-flight team exceeds 5 | Met |
| Competition baseline | ≥ 20 competition matches | 499 PD matches in the point-in-time corpus | Met |
| Backtest | 40 warm-up + ≥ 10 test folds | 50 folds returned for PD | Met |
| Provenance | Archived payload per result | 100% of stored matches | Met |
| In-match statistics | Shots, possession, xG | Not on the free tier | Unavailable — model abstains, no zero-filling |
| Lineups/injuries | Squad availability | Not ingested | Unavailable — declared limitation |

Strengths:

- Two seasons of top-flight results in the major European leagues support per-team attack
  and defence estimates without borrowing from the future.
- Provenance is complete, so every analysis can be traced to a stored payload and a
  retrieval timestamp.
- The backtest is genuinely out-of-sample and uses the production rate estimator.

Limits:

- The free tier's 10-day query window makes a full-history backfill slow but not
  impossible; this run required many bounded requests.
- `ELC` 2026/2027 has fixtures but no finished results in the retrieved window. It is
  honest coverage, not a defect, but analyses in that competition will rely on prior-season
  history and may abstain for teams with fewer than 5 matches.
- Cup and continental competitions (CL, CLI) have smaller, uneven samples and are not a
  substitute for league form.
- The measured draw under-prediction is documented, not corrected; the independent Poisson
  assumption remains.

## Recommendation

Proceed with `poisson-v1.1.0` on the stored corpus for competitions with a completed prior
season (the eleven listed above), and keep the `INSUFFICIENT_DATA` abstention for teams or
competitions below the documented thresholds. Do not add in-match statistics, lineups, or
a paid plan unless the developer approves the cost and the licence. Re-run
`python -m app.cli coverage` before any evaluation claim and attach its output; the counts
above are a snapshot at 2026-11-16, not a permanent guarantee.

## Assumptions

- A finished result observed before the target kickoff is a valid training observation.
  Validation is chronological: the model only sees matches completed before the analysed
  kickoff.
- The 10 rejected records are genuinely extra-time/shootout cases; the rejection messages
  are specific enough to support that reading, but the raw payloads were not manually
  re-parsed.
- Fixture rows without results are upcoming or unresolved, not missing history.

## Open questions

| Question | Owner | Resolution path |
| --- | --- | --- |
| Will `ELC` 2026/2027 receive finished results, or was the window stale? | data-engineer | Re-run `sync_results` for ELC and inspect the payload timestamps |
| Should extra-time results be stored in a separate corpus for cup analysis? | ml-researcher | Requires an ADR; out of scope for `poisson-v1.1.0` |
| Is the free-tier 10-day window a hard limit or a documented default? | data-engineer | Check the provider's current documentation before a larger backfill |
| Does the public-display licence permit showing real results? | security-reviewer | LIM-006 remains open; private loopback only |

## Sources

- `python -m app.cli coverage --format markdown` — executed 2026-11-16 — primary
  (generated from the live database).
- `apps/backend/app/repositories/analysis.py` — point-in-time loader and provenance checks —
  primary (code).
- `docs/decisions/ADR-0010-verified-real-dataset-contract.md` — provenance contract —
  primary (project decision).
- `docs/research/phase-5-audit-report.md` — provider capabilities and free-tier limits —
  primary (project research).

## Limitations

- The report describes stored coverage, not the provider's full catalogue. Competitions
  that were never synced are absent.
- Counts are a 2026-11-16 snapshot; scheduled refreshes will change them.
- No manual spot-check of individual provider payloads was performed for this report.
- The backtest metrics describe historical out-of-sample behaviour on the stored corpus;
  they are not a guarantee of future accuracy.
