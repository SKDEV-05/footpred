# OpenCode V2 Conventions — Verified Formats

**Date:** 2026-11-13
**Author:** orchestrator (Phase 1)
**Confidence:** High for the items below; limited to the documentation pages consulted.
**Decision affected:** How `AGENTS.md`, `.opencode/agents/`, `.opencode/skills/`, and
`.opencode/commands/` are structured in this repository.

## Question

Which OpenCode V2 conventions are actually supported for project instructions, agents, skills,
and commands, so that the foundation uses real formats instead of invented configuration?

## Context

The project uses OpenCode as its terminal agent. Phase 1 creates nine agents, twelve skills,
and six commands. Using V1 field names or guessed properties would silently break discovery.

## Method

Consulted the official OpenCode V2 documentation on 2026-11-13:

- <https://opencode.ai/docs/instructions/>
- <https://opencode.ai/docs/agents/>
- <https://opencode.ai/docs/skills/>
- <https://opencode.ai/docs/commands/>
- <https://opencode.ai/docs/permissions/>
- <https://opencode.ai/docs/llms.txt> (documentation index)

Additionally, after creating skill files, OpenCode advertised the new skills in the session
(skill IDs derived from directory names), which confirms discovery behaviour in practice.

## Verified facts

1. OpenCode V2 recognises `AGENTS.md` only; it does not use `CLAUDE.md` as a fallback. It loads
   the global file and every `AGENTS.md` from the workspace toward the project root. — Source:
   Instructions page.
2. Agent definitions are Markdown files at `.opencode/agents/<name>.md` (project) or
   `~/.config/opencode/agents/<name>.md` (global). The body is the system prompt. — Source:
   Agents page.
3. Agent frontmatter accepts the same fields as an `agents` config entry, including
   `description`, `mode`, `model`, `permissions`, `steps`, `hidden`, `color`, `disabled`, and
   `request`. — Source: Agents page.
4. `mode` accepts `primary`, `subagent`, or `all`. A new custom agent defaults to `primary`.
   Subagents run in child sessions and are launched through the `subagent` tool. — Source:
   Agents page.
5. `permissions` is an ordered list of rules with `action`, `resource`, and `effect`
   (`allow` | `ask` | `deny`). The last matching rule wins. V2 uses `permissions`, `shell`,
   and `subagent`; V1's `permission`, `bash`, and `task` are deprecated. — Source: Agents and
   Permissions pages.
6. Permission actions include `read`, `edit`, `glob`, `grep`, `shell`, `subagent`, `skill`,
   `question`, `webfetch`, `websearch`, `external_directory`, and `execute`. — Source:
   Permissions page.
7. The default base policy allows all actions, except `.env` reads which ask. Agent rules are
   appended after global rules. — Source: Permissions page.
8. Skills use a directory with `SKILL.md`: `.opencode/skills/<skill-id>/SKILL.md`. The
   directory name determines the skill ID. Frontmatter supports `name`, `description`,
   `metadata.opencode/autoinvoke`, and `disable-model-invocation`. A skill without a
   `description` is not advertised to the model. — Source: Skills page.
9. OpenCode discovers skills from `.opencode/skills`, `.claude/skills`, `.agents/skills`,
   global equivalents, and configured `skills` sources. Hidden files, `node_modules`, and
   nesting beyond six directories are skipped. — Source: Skills page.
10. Commands are Markdown files at `.opencode/commands/<name>.md`, invoked as `/<name>`. The
    trimmed body is the prompt template. Frontmatter supports `description`, `agent`, `model`,
    `subagent`, and the deprecated alias `subtask`. — Source: Commands page.
11. `$ARGUMENTS` inserts the full argument string; `$1`, `$2`, etc. are positional. Without a
    placeholder, non-empty arguments are appended after a blank line. — Source: Commands page.
12. `!` + backtick executes a shell block when the command is evaluated, outside the agent's
    tool permission flow. This foundation deliberately does not use shell blocks. — Source:
    Commands page.
13. Project configuration may live in `opencode.json`/`opencode.jsonc` or
    `.opencode/opencode.json(c)`; config changes reload without restart. — Source: Config /
    getting-started guidance.

## Analysis

The foundation uses only file-based definitions: `AGENTS.md`, Markdown agents with YAML
frontmatter, directory skills with `SKILL.md`, and Markdown commands. This avoids JSON schema
guessing and keeps each artefact reviewable in version control.

Agent permissions were chosen to enforce Phase 1 boundaries rather than to grant convenience:

- The orchestrator is `primary` with shell set to `ask` (inspection only with approval).
- Specialists are `subagent` with shell denied and subagent launch denied.
- Each specialist may edit only its owned documentation directory plus `docs/research/`
  (except the security reviewer, whose `.env` reads are denied).

No `model` field is set in agent frontmatter. Subagents then inherit the session model, which
avoids pinning a model ID that may change or be unavailable.

No project `opencode.jsonc` was created: there is no requirement for project-wide permissions
or a default agent, and creating one could alter the developer's session behaviour without
approval.

## Recommendation

Keep the file-based V2 formats used here. When adding an agent, skill, or command:

- use kebab-case IDs matching directory/file names;
- include a concrete `description` (it is how the model discovers the artefact);
- set `mode` explicitly for agents;
- use ordered `permissions` with broad rules first and exceptions after;
- do not use deprecated V1 fields (`permission`, `bash`, `task`, `tools`, `maxSteps`,
  `temperature`, `prompt`).

Re-verify the relevant documentation page before relying on a property not listed above.

## Assumptions

- The documentation at `opencode.ai/docs` describes the OpenCode version in use. This was not
  independently version-checked beyond the site identifying itself as V2.
- Frontmatter is parsed as YAML, as shown in the official examples.

## Open questions

| Question | Owner | Resolution |
| --- | --- | --- |
| Does the installed OpenCode build accept every documented frontmatter field? | Developer | Check `opencode --version` and test an agent with `steps`/`color` if needed |
| Are project `.opencode` definitions discovered when the workspace is above the repository root? | Developer | Confirm project-root detection in the local setup |
| Should a project `opencode.jsonc` later define global permissions? | Developer | Decide when implementation begins |

## Sources

- OpenCode V2 — Instructions — <https://opencode.ai/docs/instructions/> — accessed 2026-11-13
- OpenCode V2 — Agents — <https://opencode.ai/docs/agents/> — accessed 2026-11-13
- OpenCode V2 — Skills — <https://opencode.ai/docs/skills/> — accessed 2026-11-13
- OpenCode V2 — Commands — <https://opencode.ai/docs/commands/> — accessed 2026-11-13
- OpenCode V2 — Permissions — <https://opencode.ai/docs/permissions/> — accessed 2026-11-13
- OpenCode V2 — Documentation index — <https://opencode.ai/docs/llms.txt> — accessed
  2026-11-13

## Limitations

This note verifies documented formats, not every runtime behaviour. Discovery was partially
confirmed by observing skills appear in the session after creation. Agent and command
discovery should be confirmed by the developer in the TUI. Documentation may change between
releases.
