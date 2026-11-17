# Phase 7 — Commercial and Licensing Readiness

**Date:** 2026-11-17
**Status:** Assessment only. No licence was obtained, no plan purchased, no terms accepted on
the developer's behalf.
**Verdict:** **NOT READY** for any public, shared or commercial exposure. Suitable only for
private, loopback-only research use.

## 1. What "commercial readiness" means here

Three separate questions, often conflated:

1. **Can the data be displayed?** A provider licence/terms question.
2. **Can the system be exposed safely?** A security and operations question.
3. **Can any claim be made about the analysis?** An evidence question.

A "yes" to one is not a "yes" to another. At Phase 7 the answer to all three is no for public
use, and only the third has partial evidence (private, retrospective, one corpus).

## 2. Data rights

### 2.1 Verified facts (as recorded, with dates)

| Fact | Source | Date |
|---|---|---|
| football-data.org is the only provider used for the stored corpus | Repository, `data/football.db` | 2026-11-17 |
| Free tier was verified for fixtures and results | `docs/research/provider-live-verification.md` | 2026-11-15 |
| Free tier rejects request windows longer than 10 days (`HTTP 400`) | recorded in provider research | 2026-11-15 |
| Free tier returned no `statistics` key for a sampled match | recorded in provider research | 2026-11-15 |
| No H2H endpoint was verified | recorded in provider research | 2026-11-15 |
| Public-display / redistribution rights are **unresolved** (LIM-006) | `memory/known-limitations.md` | open |
| Crest and emblem images are hot-linked provider URLs (LIM-020) | repository | open |

### 2.2 Explicitly UNVERIFIED

These must not be filled in with plausible values:

- whether the current plan permits **public display** of results, derived probabilities, or
  both;
- whether it permits **commercial** use, advertising, or a paid product;
- whether it permits **redistribution** or storage beyond caching limits;
- whether it permits **derived datasets** (features, ratings, evaluation reports);
- what happens to already-displayed data after cancellation (a clause reportedly restricts
  post-cancellation display — the exact wording and its legal effect have not been reviewed
  by a lawyer and are `UNVERIFIED`);
- pricing, quotas, SLA, uptime, correction latency for any paid tier;
- API-Football terms, beyond the free-tier behaviour recorded in the Phase 6 audit.

No price, quota or clause is asserted in this document. Guessing them would be worse than
leaving them open.

### 2.3 Practical consequence

The stored corpus may be used to produce **private** analysis on this machine. It may not be
shown to another person, published, screenshotted into marketing, or used to train or sell a
product until the licence question is answered in writing.

## 3. Security and operational readiness

| Control | State |
|---|---|
| Authentication | Not implemented |
| Authorisation / roles | Not implemented |
| Rate limiting | Not implemented |
| TLS termination | Not implemented |
| Audit logging | Not implemented |
| Backup automation / restore drill | Not implemented (LIM-010) |
| Monitoring / alerting | Not implemented (LIM-012) |
| Secret management | Process environment only (LIM-013) |
| Public exposure | **Rejected** by the Phase 3 security reassessment |
| Private loopback use | Accepted with conditions |
| Phase 3 independent QA | FAIL verdict; final exact-tree re-audit still open |

The backend binds to `127.0.0.1`. There is no write-by-GET surface, but the analysis and
evaluation endpoints **do write** (they persist reports), so exposing them without auth would
create unauthenticated mutation and compute paths.

## 4. Evidence readiness

What exists:

- one provider, 4,892 regulation results, provenance-complete;
- a reproducible 970-match chronological evaluation;
- honest abstention and explicit limitations.

What does not exist:

- independent external QA or ML review;
- a second provider or independent source to cross-check scores;
- true publication timestamps (the corpus is a backfill);
- an out-of-time holdout;
- any evidence about live/in-play behaviour;
- any evidence that the models generalise beyond these 11 competitions and this window.

Therefore no public claim of accuracy, edge, or profitability is supportable. Even a phrase
like "our model is 51% accurate" would misrepresent a retrospective, clustered, single-corpus
measurement.

## 5. Product-boundary check

Phase 7 did **not** add:

- odds ingestion, implied probability, expected value, or value betting;
- paper betting, stake management, ROI, or bankroll features;
- "best bets" or tip ranking;
- subscriptions, payments, advertising, or affiliate links;
- a public deployment, container, or CI/CD pipeline.

`AGENTS.md` defines the product as **not** a tipster service. Any betting-adjacent feature
requires explicit developer approval and an ADR; none exists. The Phase 8 documents that
described such systems as implemented were false and have been frozen as proposals (see
`phase-8-betting-proposals-rejected.md`).

## 6. Readiness matrix

| Use case | Ready? | Why |
|---|---|---|
| Private local research on the stored corpus | **Conditionally yes** | Working pipeline, provenance, reproducible evaluation; licence still restricts distribution |
| Showing the UI to the developer on this machine | **Yes** | Loopback only, no third-party display |
| Demo to an external person | **No** | Licence (LIM-006), no auth, no review |
| Internal team use over a LAN | **No** | No auth/rate limiting/TLS; public/shared exposure rejected |
| Public website or app | **No** | All of the above plus no monitoring/backup |
| Commercial product | **No** | Licence, security, evidence, and legal review all open |
| Betting or tip product | **No, and not approved** | Product boundary and absent ADR |

## 7. What would have to happen before public exposure

In order, with no shortcuts:

1. **Licence**: obtain written confirmation of display, redistribution, derived-data and
   commercial rights; include crest/emblem hot-linking or replace images.
2. **Provider coverage decision**: confirm which competitions and seasons are licensed and
   actually retrieved; document coverage rather than implying it.
3. **Security**: authentication, authorisation, per-client rate limiting, TLS, audit
   logging, secret storage; then a fresh independent security review.
4. **Operations**: backup and restore rehearsal, monitoring/alerting, incident procedure.
5. **Evidence**: independent QA/ML review of the exact tree; a genuine out-of-time
   evaluation; a second results source if any accuracy claim is intended.
6. **Product copy**: review every sentence that could read as a guarantee; keep
   probabilities as estimates with samples and intervals.
7. **Legal/product review** of any betting-adjacent idea before a line of code.

## 8. Cost and commercial model

`UNVERIFIED`. No pricing, quota, conversion, or revenue assumption is recorded because none
was verified. Any business case built on guessed API prices would be fiction.

## 9. Verdict

**BUSINESS QUALITY: FAIL** for commercial readiness, unchanged by Phase 7. Phase 7 improved
technical honesty and evidence quality; it did not resolve a single legal or security gate.

The correct current posture is: private, loopback-only, clearly labelled as a research
prototype with unresolved licensing, and no public claims.

## 10. Related documents

- `docs/research/2026-11-14-provider-evaluation.md`
- `docs/research/phase-6-provider-capability-audit.md`
- `docs/security/phase-3-security-reassessment.md`
- `memory/known-limitations.md` (LIM-006, LIM-009, LIM-010, LIM-012, LIM-013, LIM-020)
- `phase-8-betting-proposals-rejected.md`
