---
name: Project Research
description: Investigate technical or product questions with primary sources, separate verified facts from assumptions, compare alternatives, and produce a reproducible research note. Use before any significant design or technology decision.
---

# Project Research

## Objective

Produce decision-grade research: what is actually true, what is uncertain, which options
exist, what each costs, and what should be decided. Research exists to reduce the risk of a
decision, not to produce a long bibliography.

## Activation

Use when a question affects architecture, technology selection, provider choice, model
design, security, or scope, and the answer is not already established in `docs/` or an ADR.
Do not use it to re-research settled decisions or to decorate a document with links.

## Required context

- The decision this research informs, and who owns that decision.
- Existing docs, ADRs, and `memory/decisions.md` (avoid re-litigating).
- The project's constraints: phase, team size, data sensitivity, licensing, cost tolerance.
- What "good enough" looks like for this decision.

## Workflow

1. **Frame the question.** Write one sentence: "We need to decide X because Y." List the
   sub-questions that must be answered to decide.
2. **Check what is already known.** Search the repository first. Mark what is settled.
3. **Plan sources.** Prefer, in order: official specification/reference, official vendor
   documentation, primary dataset documentation, standards bodies, peer-reviewed or
   well-documented practitioner sources. Treat blogs and aggregators as leads, not evidence.
4. **Collect evidence.** For each claim record: statement, source URL, publication or access
   date, and whether it is primary. Quote exact wording for numbers and limits.
5. **Test the claim.** Where feasible, verify with a minimal reproducible check (documentation
   example, schema, changelog). If it cannot be tested now, mark `UNVERIFIED`.
6. **Compare options.** Use the same criteria for each option. Include "do nothing" and the
   simplest viable option. State criteria weights only if they are real.
7. **Analyse trade-offs.** For each option: benefits, costs, risks, reversibility, operational
   burden, and what evidence would change the recommendation.
8. **Recommend.** One recommendation, conditional on stated assumptions. Include the
   conditions under which it should be revisited.
9. **Record unknowns.** Unresolved questions with an owner and a way to resolve them.
10. **Write the note** using the structure in `docs/research/README.md`.

## Detailed procedures

### Source quality ladder

| Tier | Source | Use |
| --- | --- | --- |
| 1 | Official specification, standards, vendor reference docs | Authoritative claims |
| 2 | Official changelog, pricing page, status page | Current-state claims (record date) |
| 3 | Maintainer statements, design documents, issue threads | Context and intent, mark as such |
| 4 | Practitioner blogs, tutorials, forum answers | Leads only; verify elsewhere |
| 5 | Aggregators, listicles, AI-generated summaries | Do not cite as evidence |

### Handling numbers

- Every price, quota, rate limit, benchmark, or coverage figure needs a source and date, or
  the label `UNVERIFIED`.
- Do not convert currencies, extrapolate plans, or average published limits.
- If a vendor page is dynamic, record the exact wording you saw and the access time.
- Never present a planned or announced feature as available.

### Comparison discipline

- Use a table with identical criteria per row.
- Distinguish "must have", "nice to have", and "irrelevant here".
- Reject options explicitly and say why; silent omission looks like incomplete research.
- Note switching costs and lock-in, including data egress and licensing.

### Reproducibility

A reader should be able to re-run the reasoning: include exact URLs, query terms, versions
where relevant, and any commands used for a local check. Do not include credentials.

## Quality checklist

- [ ] The decision and owner are stated.
- [ ] Every factual claim has a source and date, or is marked `UNVERIFIED`.
- [ ] Facts, assumptions, and recommendations are in separate sections.
- [ ] At least one alternative is analysed seriously, including the simple option.
- [ ] Trade-offs include operational cost, not only features.
- [ ] Unresolved questions are listed with a resolution path.
- [ ] No fabricated citation, number, or quotation.
- [ ] The recommendation is conditional and revisitable.
- [ ] The note is linked from the relevant doc or ADR.

## Common failure patterns

- **Confirmation research**: collecting only evidence for a preferred option.
- **Source laundering**: citing a blog that cites the vendor instead of the vendor.
- **Stale numbers**: quoting a price or quota without a date.
- **False precision**: inventing an estimate to fill a table cell.
- **Scope drift**: answering a broader question than the decision requires.
- **Recommendation without conditions**: presenting a choice as universally correct.
- **Duplicated research**: redoing work already recorded in an ADR.

## Expected outputs

- A dated research note in `docs/research/` with: question, context, method, verified facts,
  analysis, recommendation, assumptions, open questions, sources, confidence.
- Optionally, a draft ADR when the decision is architectural.
- A short summary (5-10 lines) suitable for the orchestrator and the developer.

## Sources and references

- `docs/research/README.md` (report standard)
- OpenCode V2 documentation: <https://opencode.ai/docs/>
- Project rules: `rules/engineering-rules.md`

## Limitations

Research cannot eliminate uncertainty. Vendor documentation may be incomplete or wrong;
verify with a bounded spike when the cost of being wrong is high. This skill does not grant
permission to install software, contact providers, or cross a phase boundary.
