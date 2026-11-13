---
description: Evaluate a football data provider or dataset — coverage, history, live data, statistics, licensing, limits, reliability, and suitability — without guessing specifications.
---

# /data-source-review

Evaluate: **$ARGUMENTS**

If no provider is named, review `docs/data/providers-research.md` and evaluate the shortlisted
candidates. Load the `football-data-sources` and `data-engineering` skills first.

Do not contact the provider, create an account, or integrate anything. If a specification
cannot be confirmed from official documentation, mark it `UNVERIFIED`.

## Required evidence standard

- Use the provider's **official** documentation, terms of service, coverage pages, and status
  page. Record URL and access date for every claim.
- No prices, quotas, rate limits, coverage counts, or historical depths from memory,
  inference, or third-party comparison blogs.
- If a page is dynamic or inaccessible, quote the wording you saw and the date, or mark the
  item `UNVERIFIED`.
- Distinguish "documented", "observed in a trial" (only if a trial was authorised), and
  "unknown".

## Comparison fields

Produce a table with identical fields per provider:

| Field | What to record |
| --- | --- |
| Provider / dataset | Name and official source URL |
| Type | Commercial API, open dataset, community API, web source |
| Competition coverage | Which competitions, tiers, countries, women's football — verified |
| Historical depth | Earliest season per field; whether events/xG/lineups exist historically |
| Live data | True live, near-live, or post-match; documented latency if published |
| Statistics | Events, shots, xG/xGA, lineups, injuries, player stats, standings |
| Update frequency | Documented cadence and correction behaviour |
| Free access | Whether a free tier exists; quota `UNVERIFIED` unless official and dated |
| Rate limits | Documented limits and burst behaviour, with source |
| Commercial licensing | Redistribution, caching, derived data, attribution — with source |
| Reliability | Status page, published SLA, incident history |
| Data model | Identity stability, normalisation, consistency across competitions |
| Missing-data behaviour | Nulls vs omitted records; partial seasons; postponed matches |
| Documentation quality | Schema completeness, error codes, examples, changelog |
| Exit cost | Bulk export, ID portability, contract terms |
| Suitability | Fit to the project's stated requirements, with conditions |

## Method

1. Restate the data requirement field by field, including freshness and history.
2. Evaluate each provider against the same fields.
3. Identify missing-data behaviour explicitly; this is usually the deciding factor.
4. Assess licensing risk before technical fit — a perfect API you cannot legally use is not a
   candidate.
5. Design a bounded verification spike (competitions, seasons, fixtures, fields, pass/fail
   criteria, time box). Do not propose production integration.
6. Record open questions that only a trial or the provider can answer.

## Rules

- Never invent a specification to fill a table cell.
- Never describe a provider as reliable without evidence.
- Never recommend a source whose licensing is unresolved for the intended use.
- Do not assume cross-provider xG is comparable.
- Do not integrate, scrape, or contact anyone in Phase 1.

## Output

Update `docs/data/providers-research.md` and, if the analysis is substantial, write a dated
report in `docs/research/`. Report: recommendation with conditions, the top three risks, the
licensing status, and the exact unknowns that require a trial.
