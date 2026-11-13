---
description: Investigate a technical or product question with primary sources and produce a dated research note with verified facts, alternatives, and open questions.
---

# /research

Research this question: **$ARGUMENTS**

Do not implement anything. Do not install anything. Do not contact external providers unless
the developer has explicitly authorised it for this task.

## Workflow

1. **Restate the question** as a decision: what will change depending on the answer, and who
   owns the decision. If the question is too broad, narrow it and say so.
2. **Check existing knowledge first.** Search `docs/`, `memory/decisions.md`, and
   `docs/decisions/`. Note what is already settled and do not re-litigate it.
3. **Load the `project-research` skill** and follow it.
4. **Identify what must be verified** versus what is already known or assumed. List the
   sub-questions.
5. **Delegate when useful**, one owner per question:
   - providers, ingestion, storage → `data-engineer`
   - system boundaries, APIs, scalability → `backend-architect`
   - model methods, calibration, evaluation → `ml-researcher`
   - football meaning, metrics, markets → `football-analyst`
   - security, secrets, privacy → `security-reviewer`
   - interface or visualisation questions → `ux-designer`
   - product scope and user needs → `product-architect`
   - verification strategy → `qa-engineer`
   Give each a precise brief: question, constraints, required output, and the rule that
   unverified claims must be marked.
6. **Prefer primary sources**: official documentation, specifications, standards, primary
   datasets. Record URL and access date. Treat blogs and aggregators as leads only.
7. **Compare alternatives** using identical criteria, including "do nothing" and the simplest
   option. State trade-offs, reversibility, and operational cost.
8. **Separate** verified facts, assumptions, recommendations, and open questions. Mark
   anything unconfirmed as `UNVERIFIED`.
9. **Write the report** to `docs/research/YYYY-MM-DD-<topic>.md` following
   `docs/research/README.md`. Include: question, context, method, verified facts, analysis,
   recommendation, assumptions, open questions, sources, confidence.
10. **Link it** from the relevant document or ADR. If the conclusion is an architectural
    decision, draft an ADR instead of burying it in the note.

## Hard rules

- Never fabricate a citation, price, quota, benchmark, or statistic. If you cannot verify a
  number, write `UNVERIFIED` and state how it could be verified.
- Do not present a recommendation as a fact.
- Do not cross the Phase 1 boundary: no installs, no code, no provider calls, no database.
- If the question requires a decision the developer must make, stop and present the options
  with consequences.

## Output

Report back with: the one-paragraph answer, the confidence level, the file path of the
research note, and the open questions that remain.
