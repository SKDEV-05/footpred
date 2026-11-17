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

**Phase 7 — model selection, comparison and multi-competition evaluation. Status:
implemented privately and self-reviewed; not independently accepted.** Phase 4 (offline,
synthetic-test-only foundation) was accepted by the developer on 2026-11-14. Phase 5 (private
real-data analysis under ADR-0010) is implemented on loopback. Phase 6 was the provider
capability audit. Phase 3 independent QA remains FAIL and security permits private
loopback-only use with conditions, rejecting public exposure.

Phase 7 added explicit model selection (`poisson`, `dixon_coles`, `elo`), a comparison endpoint
on one point-in-time dataset, a persisted 970-match chronological evaluation, tests, an
evaluation dashboard, and corrected documentation. `poisson-v1.1.0` remains the permanent
baseline. No model is substituted silently, and no general accuracy claim is made.

**Phase 8 (betting analytics: odds, expected value, paper betting, best bets) is NOT
approved and not implemented.** See `docs/research/phase-8-betting-proposals-rejected.md`.

See `PROJECT_STATUS.md` and `memory/current-state.md`.

## 4. Phase boundaries (hard)

Until the developer explicitly approves a new phase (Phase 8 or any scope expansion), agents
must not extend the following beyond what Phase 5/7 already implement:

- fit, train, calibrate, or validate a prediction model on real football data;
- make or publish a real-world match prediction or performance claim;
- persist features or predictions, or modify the SQLite schema for them;
- add machine learning training or an LLM analysis path;
- create a frontend, UI components, or branding;
- add authentication, authorisation, subscriptions, payments, or betting features;
- create containers, deployment configuration, CI/CD, or public hosting;
- connect to a football API for a live run without explicit approval and credentials;
- install a new major technology or change the approved stack;
- run a destructive migration, or delete stored data or archived payloads;
- commit secrets, a real `.env`, or provider data whose licence is unclear;
- seed the database with invented football data, or present synthetic data as real;
- modify global OpenCode configuration or unrelated repositories.

Approved Phase 4 work is limited by
`docs/decisions/ADR-0009-pure-offline-intelligence-boundary.md`: offline, deterministic,
synthetic-test-only calculations with no I/O. Phase 4 remains frozen in that form; later
phases do not retroactively widen it. Phase 8 has no approval and no ADR.

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
