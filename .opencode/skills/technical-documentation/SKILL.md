---
name: Technical Documentation
description: Write accurate, maintainable documentation — ADRs, research notes, architecture docs, and API contracts — with clear structure, traceable sources, and no duplication. Use whenever creating or revising project documentation.
---

# Technical Documentation

## Objective

Documentation must let a competent engineer make the right decision without asking the
author, and must not outlive its truth. Prefer precise, short, linked documents over long,
duplicated ones.

## Activation

Use when creating or editing docs, ADRs, research notes, READMEs, or standards; when a
decision changes; or when documentation and reality diverge.

## Required context

- Audience and the decision or task the document supports.
- The authoritative source for each claim.
- Related documents that already cover the topic.
- Whether the content is a decision (ADR), research (note), or reference (guide).

## Workflow

1. **Choose the document type**: ADR (decision), research note (investigation), reference
   (stable facts), guide (procedure).
2. **Find the existing home** for the topic; extend it instead of creating a near-duplicate.
3. **State purpose and scope** in the first paragraph.
4. **Write the content** with concrete language, tables for comparisons, and examples where
   they clarify.
5. **Record sources** with URL and access date for external claims.
6. **List limitations and open questions.**
7. **Link** related documents by relative path.
8. **Update the index or status file** if one exists.

## Detailed procedures

### Document types

| Type | Answers | Lives in |
| --- | --- | --- |
| ADR | Why did we choose this, and what did we reject? | `docs/decisions/` |
| Research note | What did we find, how sure are we? | `docs/research/` |
| Reference | How does this part of the system work? | `docs/architecture/`, `docs/data/`, etc. |
| Guide | How do I perform this task? | `rules/`, skills, READMEs |
| Status | Where are we now? | `PROJECT_STATUS.md`, `memory/` |

Do not mix them: an ADR is not a tutorial, and a status page is not a decision record.

### ADR format

Use the format in `docs/decisions/ADR-0001-project-foundation.md`:
Title, Status, Date, Context, Decision, Alternatives considered, Consequences, Risks,
Related documents.

Rules:
- One decision per ADR.
- ADRs are immutable once accepted; supersede with a new ADR and link both.
- "Alternatives considered" must include the simple/do-nothing option.
- Consequences include operational cost and reversibility.

### Research note format

Follow `docs/research/README.md`:
Question, Context, Method, Verified facts, Analysis, Recommendation, Assumptions, Open
questions, Sources, Confidence, Date.

Rules:
- Verified facts cite a source and date.
- Unverified items are labelled `UNVERIFIED`.
- Recommendations are conditional.
- No fabricated citations or quotations.

### Writing rules

- Lead with the conclusion, then the reasoning.
- One idea per paragraph; short sentences.
- Define terms on first use.
- Use tables for comparisons, not prose lists of attributes.
- Prefer concrete nouns and verbs; avoid "leverage", "robust", "seamless", "powerful".
- State units, timezones, and windows explicitly.
- Use `TBD` or `UNVERIFIED` rather than guessing.
- Keep line length reasonable; use headings to support scanning.
- Do not duplicate a rule; link to it.

### Change tracking

- Update the document in the same change as the decision it describes.
- Record significant revisions in the document's status line or memory, not in a hidden
  comment.
- When superseding, keep the old document accessible and marked `Superseded by ADR-XXXX`.
- Do not rewrite history to make past decisions look better.

### API documentation (future)

- Document the contract, not the implementation: resources, fields, types, errors,
  pagination, idempotency, versioning.
- Provide request/response examples with synthetic, clearly non-real values.
- Document rate limits and failure semantics.
- Keep the contract and tests in sync.

### Link hygiene

- Use relative links inside the repository.
- Verify links after moving files.
- Link to the specific section when useful.
- Avoid linking to transient dashboards or search results.

## Quality checklist

- [ ] Purpose and scope are stated first.
- [ ] The document has one clear type and home.
- [ ] Claims are sourced and dated, or marked `UNVERIFIED`.
- [ ] No duplicated rule or definition; links instead.
- [ ] Limitations and open questions are present.
- [ ] Decisions are recorded as ADRs, not buried in prose.
- [ ] Relative links resolve.
- [ ] No marketing language or padding.
- [ ] Status/date is current.

## Common failure patterns

- Documentation that describes an aspiration as if implemented.
- Copy-pasted rules in five files that drift apart.
- ADRs written after the fact to justify a decision.
- Unsourced numbers presented as facts.
- Tutorials mixed into reference docs.
- Orphaned documents with no inbound link.
- Screenshots of text instead of text.

## Expected outputs

- New or updated documents in the correct location.
- ADR or research note with the required structure.
- Link and status updates.
- A short change summary for the orchestrator.

## Sources and references

- `docs/decisions/ADR-0001-project-foundation.md` (ADR template)
- `docs/research/README.md` (research note standard)
- `AGENTS.md` (documentation policy)
- OpenCode V2 docs for the mechanics of `AGENTS.md`, agents, skills, and commands:
  <https://opencode.ai/docs/>

## Limitations

Documentation cannot substitute for tests or measurements. A document can be internally
consistent and still wrong; verify claims against the system and sources wherever possible.
