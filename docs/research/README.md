# Research Reports

Dated research notes produced with the `project-research` skill and the `/research` command.
A research report exists to support a decision. If it does not change or confirm a decision,
it does not belong here.

## Naming

```
docs/research/YYYY-MM-DD-<topic>.md
```

Examples: `2026-11-13-opencode-conventions.md`, `2026-12-02-provider-verification-spike.md`.

Use lowercase kebab-case. One topic per file. Do not rewrite a past report to reflect new
findings; write a new report and link it as a successor.

## Required structure

```markdown
# <Topic>

**Date:** YYYY-MM-DD
**Author:** <agent or person>
**Confidence:** low | medium | high
**Decision affected:** <one sentence>

## Question

What exactly was investigated, and why it matters.

## Context

Constraints, prior decisions, and what was already known.

## Method

How the research was conducted: sources consulted, searches, checks, date of access.

## Verified facts

Numbered facts. Each has a source and an access date.
Distinguish primary sources from secondary.

## Analysis

Comparison, trade-offs, and reasoning. Tables where useful.

## Recommendation

One recommendation, with conditions and the evidence that would change it.

## Assumptions

What was assumed, and why. Not verified.

## Open questions

Unresolved items with an owner and a resolution path.

## Sources

- Title — URL — access date — primary/secondary

## Limitations

What this research cannot establish.
```

## Rules

- **Verified facts** require a source and date, or must be marked `UNVERIFIED`.
- Never fabricate a citation, quotation, price, quota, benchmark, or statistic.
- Separate facts, assumptions, and recommendations explicitly.
- Include the simple/"do nothing" option when comparing alternatives.
- Record sources at the point of use, not only at the end.
- Do not include secrets, credentials, or licensed raw data.
- State confidence honestly; "high" requires primary sources and/or an executed check.
- Link the report from the affected document or ADR.

## Index

| Date | Report | Decision affected | Confidence |
| --- | --- | --- | --- |
| 2026-11-13 | [OpenCode V2 conventions](2026-11-13-opencode-conventions.md) | Agent, skill, and command file formats | High |

## Related documents

- `.opencode/skills/project-research/SKILL.md`
- `.opencode/commands/research.md`
- `docs/decisions/ADR-0001-project-foundation.md`
