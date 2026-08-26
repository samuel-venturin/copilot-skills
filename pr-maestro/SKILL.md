---
name: pr-maestro
description: Single-entry PR automation skill using Python tools for tag, PR creation, and template application with deterministic behavior.
---

# PR Maestro Skill

Use this as the single skill for PR automation when the user asks to:
- create or update pull requests with repository template;
- automate tag + PR flow;
- avoid manual trial-and-error with gh commands.

## Runtime model

All logic must run through Python scripts in:
- `~/.claude/skills/pr-maestro/tools`

Central configuration lives in:
- `~/.claude/skills/pr-maestro/tools/config.json`

`pr_maestro.py` is the entrypoint and applies runtime policy from config (including Python bytecode behavior for spawned Python tools).

Do not manually reconstruct the workflow in chat when these scripts are available.

## Tools

- `pr_maestro.py`: end-to-end orchestrator (recommended entrypoint)
- `pr_create_or_get.py`: idempotent PR creation (create if missing, return if existing)
- `pr_template_apply.py`: apply `.github/pull_request_template.md` to an existing PR via REST patch

## Default execution

```bash
python3 ~/.claude/skills/pr-maestro/tools/pr_maestro.py --base develop --bump auto
```

Behavior note:
- PR create/update flow is enabled by default.
- Use `--no-create-or-update-pr` only when you want tag-only execution.
- Bytecode writing is disabled by default via config (`python.writeBytecode=false`).
- PR body generation is always refined (context-aware, no generic TODO placeholders).
- Quality gate runs by default before PR update/create.
- Default quality commands: `pnpm coverage`, `pnpm run typecheck`, `pnpm run lint`.
- If any configured command fails, PR generation/update is blocked.
- `Tests` and `Coverage` sections are filled from real command results and coverage artifact (`coverage/lcov.info`).

## Safety rules

- Never fabricate test evidence.
- Never create duplicate PRs.
- Prefer GitHub REST patch for body/title updates.
- Keep output machine-readable (JSON) for deterministic chaining.
