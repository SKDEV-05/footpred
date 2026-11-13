# Provider Research

## Purpose and status

This is a research record, not a procurement decision. No provider has been contacted, contracted, or trialled, and no credentials exist. A reference adapter for football-data.org v4 was implemented in Phase 3 against public documentation, but no live call has been made. Nothing below should be read as a statement of a provider's current price, quota, coverage, or quality. Every commercial claim is marked **VERIFY** (a field that must be checked against primary sources) or **UNVERIFIED** (a belief that has not been checked at all).

The purpose is to define how providers will be evaluated and to name the candidate categories and known unknowns so the next phase starts from evidence rather than impressions.

## Evaluation methodology

1. Read official documentation first; use secondary sources only to discover candidates, never as evidence.
2. Verify every number against the primary source and record the access date with the exact statement and URL. Numbers without an access date are not evidence.
3. Prefer a written quote over a paraphrase. If a term is ambiguous, treat it as unknown.
4. Run a small, bounded technical spike before any commitment: fetch a known fixture, a known season, and a deliberately awkward case (postponement, correction, missing lineup).
5. Have licence and redistribution terms reviewed before data enters any environment.
6. A provider moves to "verified" only when an evidence record exists; it moves to "rejected" only with a recorded reason.

## Candidate provider categories

| Category | Examples | Risk notes |
|----------|----------|------------|
| Commercial football data APIs | API-first vendors selling fixtures, results, events, and statistics | Recurring cost, contractual lock-in, provider-specific definitions, quota exposure |
| Open datasets | Research releases of event or match data | Licence and attribution constraints, limited coverage, unclear update path, uncertain production suitability |
| Web sources | Public sites and league pages, including scraping | Terms-of-service and copyright exposure, fragility, no contractual reliability; disfavoured as a primary source |

Scraping is not treated as a neutral option. It carries legal and operational risk that must be assessed explicitly, and it cannot be the sole basis for a product whose value depends on trustworthy history.

## Provider shortlist

| Provider | Type | Likely strengths | Known limitations | Key unknowns | Verification status |
|----------|------|------------------|-------------------|--------------|---------------------|
| API-Football (API-Sports) | Commercial REST API aggregator | Marketed broad competition and fixture coverage; one API surface; documentation is claimed to be public | Aggregated rather than primary; depth of advanced statistics unclear; definitions likely provider-specific | Tier structure, rate limits, historical depth, xG/lineup/event availability, licence, uptime, missing-data behaviour | UNVERIFIED — documentation not reviewed in this phase |
| football-data.org | Commercial API (tier structure unverified) | Long public presence; comparatively simple REST model | Statistical depth may be limited relative to event-data vendors; that belief is itself UNVERIFIED; historical range unknown | Whether advanced stats exist, historical depth, quotas, licence, update latency | UNVERIFIED |
| Sportmonks | Commercial API | Marketed depth across fixtures, lineups, events, and odds; xG-related fields claimed | Cost and integration complexity unknown; per-competition coverage and definitions unknown | xG methodology and provenance, historical depth, limits, licence, support commitments | UNVERIFIED |
| StatsBomb Open Data | Open event dataset | Event-level granularity suited to research and method development | Selected competitions and matches only; not a live or complete feed; licence and attribution must be confirmed | Exact coverage list, licence wording, attribution requirements, permitted commercial use, update cadence | UNVERIFIED — specifics not confirmed |
| Other providers to be discovered | TBD | Possible regional feeds, official league or official-statistics releases, closing-odds sources | Unknown; each carries its own legal and reliability profile | Everything | Discovery only — no candidate evaluated |

No row is a recommendation. Table order carries no preference.

## Verification checklist

Each field below becomes a column in the evidence record for every candidate.

| Field | Why it matters | Evidence required |
|-------|----------------|-------------------|
| Free/paid tiers | Determines trial feasibility and cost shape | Current official pricing or contract statement, with access date |
| Rate limits | Governs ingestion design and backfill feasibility | Documented limits per endpoint and per plan |
| Competition coverage | Defines what the product can analyse | Named competition and season list, not a marketing total |
| Historical depth | Sets backtest horizon | Earliest reliably complete season per competition |
| Live coverage | Determines whether any near-real-time feature is possible | Latency statement and update mechanism |
| Statistics available | Core product input (xG, lineups, events, shots) | Field-level documentation or sample payload |
| Update frequency | Determines staleness windows | Observed cadence during a spike, plus documented promise |
| Documentation quality | Predicts integration cost | Reviewed endpoints, error model, versioning policy |
| Licensing and commercial use | Legal basis for the product | Licence text; written confirmation where ambiguous |
| Attribution requirements | Constrains UI and exports | Exact required wording or logo rules |
| Reliability and uptime | Determines operational resilience | Status history or SLA, if published |
| Missing-data behaviour | Predicts gap handling | Observed response for an unavailable field or fixture |
| Data model quality | Predicts normalization cost | Sample payload structure and identifier stability |
| Support | Determines incident resolution | Support channels and response commitments |
| Exit and portability | Limits lock-in | Whether history can be exported and in what form |

## Open-data considerations

StatsBomb Open Data is event-level and research-oriented. That makes it useful for validating methods and building the feature and evaluation pipeline, not automatically for production.

- Licensing and attribution must be confirmed from the official release terms; do not assume research use implies commercial use. **UNVERIFIED.**
- Coverage is limited to selected competitions and matches; the exact list and its currency must be checked. **UNVERIFIED.**
- There is no expectation of live coverage or a guaranteed update cadence. **UNVERIFIED.**
- Production suitability requires an assessment of completeness over time, identifier stability, refresh path, and licence durability — not just whether a sample loads.
- Any use in evaluation must record the dataset version and retrieval date, per [data-provenance.md](data-provenance.md).

## Recommendation

- Do not integrate any provider in Phase 1. No accounts, keys, or trial calls.
- In the next approved phase, run a bounded verification spike over a small shortlist, using the checklist above as the scoring frame. Fix the timebox and the acceptance criteria before starting.
- Spike scope should include one competition, one historical season, and one awkward case (postponement or post-publication correction) to expose real behaviour.
- Produce a written comparison and a decision record; do not select a provider by default or by familiarity.
- Re-check all pricing, quota, and licensing statements at the moment of decision, since they change.

## Open questions

- Which competitions and seasons define the first release? (Product decision, not a data-vendor decision.)
- Is event-level data required, or are aggregate match statistics sufficient for the first model?
- Should expected goals be licensed, computed from events, or omitted until justified?
- Is any live or near-live capability in scope, or is the product post-match only?
- What is the budget envelope for data? Currently unknown.
- Who owns legal review of provider terms, and when does it happen?
- Is public attribution acceptable in the product, or does it conflict with the intended presentation?

## Related documents

- [Data strategy](data-strategy.md)
- [Data quality](data-quality.md)
- [Data provenance](data-provenance.md)
- [`../../rules/data-rules.md`](../../rules/data-rules.md)
- [`../../AGENTS.md`](../../AGENTS.md)
