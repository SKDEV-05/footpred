# AGENTS.md — Football Intelligence Platform

Root instructions for every agent working in this repository. Read this file first.
Detailed rules live in `rules/`; product and architecture context lives in `docs/`.
This file states what applies always; it does not duplicate those documents.

## 1. What this project is

A global football intelligence and match-analysis platform. It helps users understand
football matches through reliable statistics, historical performance, mathematical
analysis, and carefully evaluated probability estimates.

It is **not** a live-score site, a news site, a generic chatbot, a tipster service, or a
statistics dump. A prediction without traceable evidence is a defect, not a feature.

## 2. Objective

Produce analysis that is *correct, reproducible, and honest about uncertainty*:

- trustworthy historical and contextual data;
- explicit, mathematically grounded probability estimates;
- predictions timestamped before kickoff and evaluated against actual results;
- explanations of **why** a number exists, including when evidence is insufficient.

The platform must never promise guaranteed outcomes or a fixed accuracy figure.

## 3. Current phase

**Phase 1 — Foundation. Status: complete, pending developer review.**
Only foundation artefacts exist: instructions, agents, skills, commands, documentation,
memory, and rules. There is no application code and no database.

See `PROJECT_STATUS.md` and `memory/current-state.md`.

## 4. Phase boundaries (hard)

Until the developer explicitly approves a new phase, agents must not:

- install packages or system software (Python, Node, OS packages);
- create application source code, endpoints, frontends, containers, or deployment config;
- connect to football APIs or any external data provider;
- create databases, schemas, migrations, or seed/mock football data;
- implement models, backtests, or prediction algorithms;
- modify global OpenCode configuration or unrelated repositories.

If a task appears to require any of these, stop and request approval. Do not "helpfully"
cross the boundary because the next step seems obvious.

## 5. Engineering philosophy

DATA FIRST · MATHEMATICS FIRST · RELIABILITY FIRST · PREDICTION QUALITY FIRST ·
USER EXPERIENCE SECOND · VISUAL DECORATION LAST.

Practically: evidence before implementation, the simplest design that satisfies the
requirement, explicit uncertainty instead of confident guesses, and no invented data.

Full rules: `rules/engineering-rules.md`, `rules/system-design-rules.md`,
`rules/data-rules.md`, `rules/ai-usage-rules.md`, `rules/design-rules.md`,
`rules/security-rules.md`.

## 6. Evidence and research

Prefer official documentation and primary sources. Record the source and access date.
Separate **verified facts**, **recommendations**, **assumptions**, and **open questions**.
If a detail cannot be verified, mark it `UNVERIFIED` — never fill the gap with a plausible
number, price, quota, or citation. Research procedure:
`.opencode/skills/project-research/SKILL.md`.

## 7. Agent delegation

- `orchestrator` coordinates, reviews, and decides what to delegate. It does not perform
  every specialist task itself.
- Specialists (`product-architect`, `backend-architect`, `data-engineer`,
  `football-analyst`, `ml-researcher`, `qa-engineer`, `security-reviewer`, `ux-designer`)
  are `subagent` agents. Delegate by domain; do not assign two agents the same
  responsibility.
- Never let a specialist silently change an approved decision. Changes require an ADR
  (`docs/decisions/`) and developer approval.
- The orchestrator must not approve its own work; independent review is required.

Agent definitions: `.opencode/agents/`. Domain skills: `.opencode/skills/`.

## 8. Documentation policy

- Documentation describes intended design and constraints; it never claims unimplemented
  features are complete.
- One topic, one home. Link instead of duplicating rules or definitions.
- Architecture decisions become ADRs in `docs/decisions/` using the format in
  `docs/decisions/ADR-0001-project-foundation.md`.
- Research reports go to `docs/research/` using the structure in
  `docs/research/README.md`.
- Update affected docs in the same change as the decision they describe.

## 9. Memory policy

`memory/` is a concise, current summary for humans and agents — not a copy of `docs/`.

Update memory when phase, state, decisions, limitations, or next steps change:
`memory/current-state.md`, `memory/decisions.md`, `memory/known-limitations.md`,
`memory/next-steps.md`. Use `/update-memory`. Never rewrite history: supersede a decision
and record why.

## 10. Architecture decisions

Before an important design change: state the problem, list realistic alternatives, list
trade-offs, check the rules, record the decision in an ADR, and obtain developer approval.
Do not present a preference as a verified fact. Do not add a technology because it is
popular.

## 11. Testing and quality expectations

Correctness outranks coverage theatre. Any future implementation needs, at minimum:
unit tests for pure logic, contract tests at data boundaries, data-quality checks,
regression tests for known bugs, and temporal backtesting for models (no leakage from the
future). A change is not done because it runs; it is done when it is verified and its
limitations are documented. See `.opencode/skills/testing-strategy/SKILL.md`.

## 12. Design restrictions

Future interfaces must follow `rules/design-rules.md` and
`.opencode/skills/anti-ai-slop-design/SKILL.md`. No AI-template aesthetics: no
blue-to-purple gradients, purple/pink branding, decorative blobs or particles, excessive
glassmorphism, neon effects, fake charts, or animation without a usability purpose.
No final palette or branding is chosen in Phase 1.

## 13. No invented data — ever

Never fabricate statistics, fixtures, results, lineups, injuries, xG values, provider
pricing, API quotas, or sources. Never present an assumption as verified. Missing data is
reported as missing; it is never replaced with zero or a plausible guess. If a requested
output depends on unavailable data, say so and stop.

## 14. Human approval required

Explicit developer approval is required before: starting a new phase; changing approved
architecture; adding a major technology; installing dependencies in a restricted phase;
destructive operations; scope expansion; publishing or sharing data covered by provider
licensing.

## 15. Commands and skills

Project commands: `/research`, `/plan-phase`, `/architecture-review`, `/data-source-review`,
`/quality-check`, `/update-memory`. Definitions: `.opencode/commands/`.

Load the matching skill before specialised work: `project-research`,
`system-architecture`, `football-domain`, `football-data-sources`, `data-engineering`,
`statistical-analysis`, `ml-engineering`, `data-validation`, `testing-strategy`,
`security-basics`, `technical-documentation`, `anti-ai-slop-design`.

## 16. Definition of done

Work is done when: scope compliance is verified, evidence is recorded, relevant docs and
memory are updated, limitations are stated, and a reviewer has checked it. Otherwise report
the remaining gaps explicitly.
