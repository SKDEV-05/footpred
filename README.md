# Football Intelligence Platform

A global football intelligence and match-analysis platform. The goal is not to publish
more predictions, but to publish *explainable, reproducible, evaluated* ones: reliable
statistics, historical performance, mathematically grounded probability estimates, and an
honest statement of uncertainty.

> Status: **Phase 1 — foundation complete.** No application code, database, or model exists
> yet. See [`PROJECT_STATUS.md`](PROJECT_STATUS.md).

## What this repository contains

| Path | Purpose |
| --- | --- |
| `AGENTS.md` | Root instructions for every AI agent working here |
| `.opencode/agents/` | Nine specialised agent definitions (orchestrator + eight specialists) |
| `.opencode/skills/` | Twelve reusable operational skills |
| `.opencode/commands/` | Six project commands (`/research`, `/plan-phase`, ...) |
| `docs/product/` | Vision, requirements, scope, non-goals |
| `docs/architecture/` | System overview, principles, components, technology evaluation, quality attributes |
| `docs/football/` | Domain model, prediction markets, performance metrics |
| `docs/data/` | Data strategy, provider research, quality, provenance |
| `docs/design/` | UI/UX principles and the anti-AI-slop constraints |
| `docs/security/` | Security principles for future implementation |
| `docs/research/` | Dated research reports containing verified facts and open questions |
| `docs/decisions/` | Architecture Decision Records (ADRs) |
| `memory/` | Concise current-state memory for humans and agents |
| `rules/` | Binding engineering, design, data, AI-usage, and security rules |
| `apps/` | Reserved for future applications (empty in Phase 1) |

## Principles

**Data first. Mathematics first. Reliability first. Prediction quality first.
User experience second. Visual decoration last.**

- Evidence before implementation; official sources before opinion.
- The simplest architecture that satisfies the requirement.
- Missing data is reported as missing — never invented, never silently imputed.
- Every prediction must be reproducible, timestamped before kickoff, and evaluated.
- A percentage means a calibrated probability estimate, not a confidence score.
- Language models may explain verified results; they never generate the numbers.

## How to work in this repository

1. Read [`AGENTS.md`](AGENTS.md) — it is binding.
2. Check [`PROJECT_STATUS.md`](PROJECT_STATUS.md) and [`memory/current-state.md`](memory/current-state.md)
   before starting work.
3. Read the rules relevant to your task in [`rules/`](rules/).
4. Use the OpenCode agents and skills rather than improvising a process.
5. Record decisions as ADRs and research as dated reports.

## Working with the agent ecosystem

- Select the `orchestrator` agent for coordinated work. It delegates to the eight specialist
  subagents by domain and enforces the phase boundaries.
- Specialists can also be invoked directly for a narrow question, but they write only within
  their owned documentation paths and cannot run shell commands.
- Project commands: `/research`, `/plan-phase`, `/architecture-review`, `/data-source-review`,
  `/quality-check`, `/update-memory`. Each has a defined workflow and output location.
- Skills are discovered automatically by their descriptions; mention a skill as `@skill-id`
  to load it explicitly (for example `@statistical-analysis`).

Agents do not select their own model; they inherit the session model unless a model is
configured explicitly.

## Phase 1 boundaries

Phase 1 produced engineering artefacts only. No dependencies were installed, no API was
contacted, no database or application was created, and no prediction logic was written.
Work beyond foundation requires explicit developer approval.

## Documentation map

- Product: [`docs/product/vision.md`](docs/product/vision.md) →
  [`requirements.md`](docs/product/requirements.md) → [`scope.md`](docs/product/scope.md) →
  [`non-goals.md`](docs/product/non-goals.md)
- Architecture: [`docs/architecture/system-overview.md`](docs/architecture/system-overview.md)
- Foundation decision: [`docs/decisions/ADR-0001-project-foundation.md`](docs/decisions/ADR-0001-project-foundation.md)
- Next steps: [`memory/next-steps.md`](memory/next-steps.md)
