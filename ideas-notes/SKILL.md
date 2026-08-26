---
name: ideas-notes
description: Consult and update persistent idea notes for automation/testing workflows.
---

# Ideas Notes Skill

Use this skill whenever the user asks to:
- capture a new idea;
- revisit prior ideas;
- evolve a proposal into actionable steps;
- check idea status/history before implementation.

This skill must also support:
- listing all registered ideas;
- fetching a specific idea by ID or by topic keywords;
- producing concise and executive summaries of one or many ideas.

## Collaboration mode (mandatory)

- The agent must actively help the user evolve ideas while discussing them.
- Do not act as a passive note taker only.
- During idea conversations, the agent should:
   - propose stronger alternatives;
   - suggest simpler implementations when possible;
   - suggest phased rollout options (MVP -> incremental);
   - compare trade-offs (effort, risk, usability, maintainability);
   - convert abstract ideas into actionable next steps.
- If user idea has gaps, propose concrete improvements and ask focused questions.
- If a better solution is identified, explicitly present it with rationale.

## Trigger phrases (mandatory dispatch)

Whenever user writes idea-intent phrases (or close synonyms), dispatch this skill first.

Examples of trigger phrases:
- "tive uma ideia"
- "tenho uma ideia"
- "pensei numa ideia"
- "me veio uma ideia"
- "vamos anotar uma ideia"
- "quero registrar uma ideia"

After a trigger, the agent must ask this disambiguation question before proceeding:
- "Isso é continuidade de alguma ideia existente ou é uma ideia nova?"

Then map user answer to intent:
- existing idea -> `get` or `update`
- new idea -> `create`

## Source of truth

- Idea index: `~/.copilot/skills/ideas-notes/notes/index.md`
- Idea files: `~/.copilot/skills/ideas-notes/notes/*.idea.md`
- Idea template: `~/.copilot/skills/ideas-notes/notes/template.idea.md`

## Required workflow

1. Read `~/.copilot/skills/ideas-notes/notes/index.md` first.
2. Resolve user intent:
    - `list`: user wants all ideas;
    - `get`: user wants one specific idea (by ID/topic);
    - `summary`: user wants a compact synthesis;
    - `create`: user wants a new idea;
    - `update`: user wants to evolve an existing idea.
   - if trigger phrase was used and user did not clarify, ask the mandatory disambiguation question first.
3. If intent is `list`:
    - return the idea table with ID, topic, status, priority, last update;
    - if requested, filter by status/priority/topic.
4. If intent is `get`:
    - search by explicit ID first (`IDEA-XXX`), then by topic keywords;
    - open the matching `.idea.md` file and return current status, latest revision, next step.
5. If intent is `summary`:
    - summarize by domain and status;
    - highlight risks, blockers, and suggested next action.
6. If intent is `create`:
   - create a new ID (`IDEA-XXX`);
   - create a new file from `template.idea.md` named like:
     - `idea-001-short-topic.idea.md`;
   - add row in `index.md` linking the new file.
7. If intent is `update`:
   - update status/date in `index.md`;
   - add a NEW revision entry at the TOP of the idea file revision log.

## Critical analysis policy (mandatory)

- Do not accept proposals blindly.
- Challenge assumptions with clear technical reasoning when needed.
- Always call out potential:
   - scope leaks;
   - side effects;
   - security risks;
   - usability risks;
   - maintainability concerns.
- Ask clarifying questions when requirements are ambiguous or contradictory.
- When rejecting or warning, provide safer alternatives and trade-offs.

## Internal tools policy

- Skill may create helper scripts for agent-only usage under:
   - `~/.copilot/skills/ideas-notes/tools/`
- Tools catalog file (mandatory):
   - `~/.copilot/skills/ideas-notes/tools/index.md`
- Allowed extensions:
   - `.tool.js`, `.tool.py`, `.tool.sh`
- Example:
   - `~/.copilot/skills/ideas-notes/tools/read-vue-file.tool.py`
- Purpose of tools:
   - inspect project folders/files quickly;
   - extract/minify code for faster agent consumption;
   - build derived artifacts (maps/graphs/indexes) for idea analysis.
- Rules for tools:
   - tools are for agent workflow, not user-facing features;
   - always consult `tools/index.md` before reading tool source files;
   - prefer creating tools only when reuse value is clear;
   - keep tools deterministic and scoped;
   - document tool purpose in file header comment;
   - never print secrets or credentials.

## Rules

- Keep content in English unless the user explicitly asks another language.
- Never delete historical ideas; mark as `blocked`, `needs-improvement`, or `completed` when needed.
- Keep IDs stable once created.
- Keep statuses limited to:
   - `draft`, `planned`, `in-progress`, `validated`, `needs-improvement`, `blocked`, `completed`.
- Never rewrite old revision entries in `.idea.md` files.
- Revision history must be sequential and newest-first.
- Expected order over time:
   - `{datetime} - conclusion`
   - `{datetime} - rev-02`
   - `{datetime} - rev-01`
   - `{datetime} - new-idea`

## Output style

- Concise summary + clear next actions.
- Always reference idea IDs.
- For critical feedback, include: risk, impact, and mitigation.
