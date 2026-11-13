---
description: Update project memory from verified changes — current state, decisions, limitations, and next steps — without rewriting history or duplicating documentation.
---

# /update-memory

Update project memory after: **$ARGUMENTS**

If no change is named, review the repository state and determine what has changed since the
last memory update. Load the `technical-documentation` skill.

## Read first

- `memory/project-context.md`, `current-state.md`, `decisions.md`, `known-limitations.md`,
  `next-steps.md`
- `PROJECT_STATUS.md`
- Recent ADRs in `docs/decisions/` and research notes in `docs/research/`
- The actual files changed (verify, do not assume)

## Rules

- Memory is a **summary**, not a copy of the documentation. Link to the detailed document.
- Never delete or rewrite a historical decision. Supersede it: add a new entry with date,
  reason, and a link to the superseding ADR.
- Record only verified changes. If something is planned but not done, it belongs in
  `next-steps.md`, not `current-state.md`.
- Do not invent progress. "Partially complete" is a valid and useful state.
- Keep entries short: what changed, why, date, link.
- Do not duplicate content that already lives in `docs/`; summarise and link.

## Update each file as applicable

### `project-context.md`
Only if the product vision, objective, users, or philosophy changed. These should be stable;
changes here are significant and require developer approval.

### `current-state.md`
- Current phase and status.
- Completed work with paths.
- Existing capabilities (be precise: "documented", "designed", "not implemented").
- Structure changes.
- Work explicitly not started.

### `decisions.md`
- New approved decisions with date, rationale, and ADR link.
- Rejected approaches with the reason (this prevents repeated proposals).
- Superseded decisions marked as such, with the replacement link.

### `known-limitations.md`
- Missing information and unresolved technical questions.
- Data provider limitations (mark `UNVERIFIED` where applicable).
- Product and model risks.
- Research gaps with an owner or next action.

### `next-steps.md`
- Next phase candidate and its status (`not approved`, `approved`, `in progress`).
- Prerequisites and pending decisions.
- Expected deliverables.
- Anything blocked and by whom/what.

## Method

1. Diff the current state against the existing memory; list what actually changed.
2. Separate: completed, changed, newly decided, newly uncertain, still pending.
3. Update only the affected files; leave accurate content untouched.
4. Add dates (`YYYY-MM-DD`) to new entries.
5. Verify every path and link you add.
6. Cross-check `PROJECT_STATUS.md`; update it if phase status changed.

## Output

Report: which memory files changed, the key state change in one sentence, any decision that
needs developer approval, and any inconsistency you found between memory and the repository.
