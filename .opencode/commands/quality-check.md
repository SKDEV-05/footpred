---
description: Review project work for correctness, scope compliance, maintainability, documentation, security, consistency, testing, unverified assumptions, and unnecessary complexity. Reports issues by severity.
---

# /quality-check

Review: **$ARGUMENTS**

If no target is given, review the current phase's deliverables and the repository state. Use
the `testing-strategy`, `data-validation`, and `technical-documentation` skills as needed.

## Review dimensions

1. **Correctness** — does the work do what it claims, under stated inputs? Are definitions
   precise (units, windows, timezones)? Are edge cases handled or explicitly out of scope?
2. **Scope compliance** — does every artefact map to approved scope? Is anything implemented
   that the phase forbids (code, dependencies, database, API integration, models)?
3. **Maintainability** — clear structure, no duplicated rules, no dead files, no unexplained
   configuration, no unnecessary abstraction.
4. **Documentation** — purpose, evidence, limitations, and links. Are claims sourced or
   marked `UNVERIFIED`? Are planned features described as implemented?
5. **Security** — secrets in files or logs, unsafe input handling, missing validation,
   over-broad permissions, exposed provider keys.
6. **Consistency** — terminology, file paths, agent names, skill IDs, command names, and
   cross-references agree across the repository.
7. **Testing** — are acceptance criteria verifiable? Is there a way to falsify the claim? Are
   regression and failure cases covered (or explicitly deferred)?
8. **Unverified assumptions** — list every assumption presented as fact.
9. **Unnecessary complexity** — anything that adds moving parts without a requirement.
10. **Data integrity** — invented data, null/zero confusion, silent imputation, future
    leakage, missing provenance.

## Method

1. Read `AGENTS.md`, the relevant rules, and the phase scope first.
2. Inventory the artefacts under review; verify each path exists and is referenced.
3. Check formatting and metadata validity where relevant (frontmatter, links, IDs).
4. Spot-check claims against their sources; flag unsourced numbers.
5. Run available non-destructive checks (file listing, link checks, manifest detection).
   Do not install tools or run destructive commands.
6. Classify findings:

| Severity | Meaning |
| --- | --- |
| Blocker | Violates a hard rule, phase boundary, or data integrity; must fix before acceptance |
| High | Incorrect or misleading result, missing critical limitation, security risk |
| Medium | Maintainability or clarity problem likely to cause future defects |
| Low | Minor inconsistency or polish |
| Nit | Optional preference; say so explicitly |

7. For each finding: location, evidence, impact, and a concrete fix.
8. State explicitly what you verified and what you could not verify.

## Rules

- Do not report success for an unchecked criterion.
- Do not invent test results, coverage, or measurements.
- Do not accept "it looks right" as verification.
- Do not mark a phase complete if any acceptance criterion is unverified.
- Do not fix issues silently while reviewing; report them, then fix with approval if asked.

## Output

- Findings grouped by severity with locations.
- A verification log: what was checked, how, and the result.
- A list of unverified assumptions and open questions.
- A verdict: pass, pass with conditions, or fail — with the exact conditions.
- Recommended next action, without starting it.
