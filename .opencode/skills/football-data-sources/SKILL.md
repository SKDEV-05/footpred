---
name: Football Data Sources
description: Evaluate football APIs and datasets — coverage, history, live data, statistics, licensing, limits, reliability, and missing-data behaviour — without guessing prices or quotas. Use whenever a provider or dataset is considered.
---

# Football Data Sources

## Objective

Select data sources on evidence, not on marketing pages. Produce a comparison that states
what is verified, what is unverified, and what must be tested before any integration.

## Activation

Use for provider selection, coverage questions, licensing checks, historical-data sourcing,
or when a proposed feature depends on data whose availability is unconfirmed.

## Required context

- The exact entities and fields required (fixtures, results, events, lineups, xG, odds).
- Required history depth and update frequency.
- Competition coverage and priority order.
- Commercial model and redistribution constraints (unknown is acceptable; invented is not).
- Budget tolerance (state it or mark `TBD`).

## Workflow

1. **Write the data requirement** as a field-level list with granularity and freshness.
2. **Build a candidate list** from official sources, not from affiliate listicles.
3. **Read the official documentation** for each candidate: data model, endpoints, coverage
   pages, terms of service, attribution and commercial-use clauses.
4. **Record verified facts** with URL and access date. Anything else is `UNVERIFIED`.
5. **Evaluate against a fixed checklist** (below) using the same criteria for each provider.
6. **Identify missing-data behaviour**: nulls, omitted fixtures, partial seasons, delayed
   updates, corrected results.
7. **Assess licensing risk**: redistribution, caching, derived data, display attribution.
8. **Recommend a bounded verification spike**, not an integration: specific fixtures, specific
   fields, specific seasons, pass/fail criteria.
9. **Record open questions** that only the provider or a trial can answer.

## Detailed procedures

### Candidate categories

| Category | Examples | Strengths | Risks |
| --- | --- | --- | --- |
| Commercial football APIs | API-Football, football-data.org, Sportmonks | Structured, documented, broad coverage | Cost, quotas, licensing limits, vendor lock-in |
| Event-data open datasets | StatsBomb Open Data | Rich event detail, research-friendly | Limited competitions/matches, attribution terms, not live |
| Historical results datasets | Football-Data.co.uk and similar | Long results history, simple format | Few advanced stats, quality varies, licence must be checked |
| Community/open APIs | OpenLigaDB and similar | Free, transparent for some leagues | Narrow coverage, upkeep risk |
| Web sources (FBref, Understat, league sites) | Public statistics pages | Broad and detailed | Terms of service, scraping fragility, no SLA |
| Aggregators/marketplaces | RapidAPI listings | Convenience | Pricing and quotas change; verify at source |

Provider names are leads, not endorsements. Confirm every claim in the provider's own
documentation.

### Evaluation checklist (fill for every candidate)

- Free and paid plan structure — **verify, do not estimate**.
- Rate limits and burst behaviour — **verify**.
- Competition coverage, including second tiers and women's football.
- Historical depth per competition and per field.
- Live coverage and latency (is it truly live, near-live, or post-match?).
- Statistics available: events, shots, xG/xGA, lineups, injuries, player stats.
- Update frequency and correction behaviour.
- Documentation quality: schema, error codes, examples, changelog.
- Commercial use, redistribution, caching, and attribution terms.
- Reliability signals: status page, incident history, SLA if published.
- Missing-data behaviour: nulls vs omissions; partial coverage.
- Identity model: stable team/competition/player IDs; alias handling.
- Data model quality: normalised vs nested blobs; consistency across competitions.
- Support responsiveness and language.
- Exit cost: bulk export, ID portability, contract terms.

### What must never be guessed

Do not write a price, free-tier quota, rate limit, coverage count, or historical depth from
memory or inference. If the official page is not accessible, write:
`UNVERIFIED — requires confirmation from official documentation (accessed YYYY-MM-DD)`.

### Licensing and attribution

- Read the terms of service, not only the pricing page.
- Determine whether derived statistics and model outputs may be displayed or sold.
- Determine whether raw payloads may be cached and for how long.
- Record attribution text requirements verbatim where possible.
- Flag any ambiguity as a blocking open question for the developer.

### Verification spike design (for a later approved phase)

- Fixed sample: N competitions, N seasons, N fixtures, including edge cases (postponed,
  abandoned, neutral venue, extra time).
- Field-level assertions: presence, type, range, referential integrity.
- Latency measurement: time from final whistle to result availability.
- Correction test: does a changed result propagate?
- Licence confirmation in writing where required.
- Exit criteria and a stop condition (time-boxed, no production integration).

## Quality checklist

- [ ] Data requirement is field-level and time-aware.
- [ ] Every provider claim is sourced and dated or marked `UNVERIFIED`.
- [ ] The same criteria are applied to every candidate.
- [ ] Missing-data behaviour is described, not assumed.
- [ ] Licensing/attribution is explicitly assessed.
- [ ] No price, quota, or rate limit is invented.
- [ ] A bounded verification spike is proposed instead of an immediate integration.
- [ ] Open questions have owners.

## Common failure patterns

- Copying a provider comparison blog and treating it as fact.
- Quoting a free tier without a date; plans change.
- Assuming an API covers a league because its marketing says "global".
- Ignoring redistribution clauses while planning a public product.
- Treating xG as directly comparable across providers.
- Designing features before confirming lineup or injury availability.
- Building against a provider before testing its identity model.

## Expected outputs

- `docs/data/providers-research.md` updates: matrix, verified facts, unknowns.
- A field-level data requirement note.
- A time-boxed verification plan with pass/fail criteria.
- A licensing risk summary for the developer.

## Sources and references

- `docs/data/providers-research.md`
- `docs/data/data-strategy.md`
- `rules/data-rules.md`
- Provider official documentation (record URL and access date in the research note)

## Limitations

Provider documentation can be incomplete, outdated, or contradicted by the actual API.
Only a trial can confirm behaviour. This skill does not authorise contacting providers,
creating accounts, or integrating data during Phase 1.
