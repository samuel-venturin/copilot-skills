---
name: dev-day
description: Orchestrates the developer desk for a sprint day — Jira mine/sprint, interpret into Documents/copilot-workspace, execute in worktrees, fix-evidence screenshots+Jira attach, then qa-test-tutorial. Commands - today, plan, interpret, start, parallel, evidence, tutorial.
---

# /dev-day — Developer desk orchestrator

> `$JIRA` = `python ~/.cursor/scripts/jira.tool.py`
> `$WS` = `python ~/.cursor/scripts/workspace_paths.py`
> `$TM` = `python ~/.cursor/scripts/task_manager.py`

Input: `$ARGUMENTS` — subcommand + optional keys.

This skill **orchestrates**; it does not re-implement engines. Call:

| Engine | When |
|--------|------|
| `interpret` | Planning artifacts |
| `execute` | Implementation in worktree |
| `fix-evidence` | Success screenshots + optional Jira upload |
| `qa-test-tutorial` | QA manual tutorial **after** evidence |

Pipeline after code is ready: **`evidence` → (confirm Jira) → `tutorial`**.

Max **3** parallel Task agents/worktrees.

---

## Subcommands

| `$ARGUMENTS` | Action |
|--------------|--------|
| empty / `today` | Day panel: sprint + mine + interpret/execute/evidence gaps |
| `plan` | Sprint plan ordered by priority/status + interpret gaps |
| `interpret [KEY\|all-sprint]` | Jira fetch → interpret → Documents workspace |
| `start KEY` | Transition toward In Development (if applicable) + `execute KEY` |
| `parallel KEY1,KEY2,...` | Up to 3 Task agents with `execute` |
| `evidence KEY` | Invoke `fix-evidence` |
| `tutorial KEY` | Invoke `qa-test-tutorial` (prefer after evidence) |

---

## Shared helpers

### Resolve project for a ticket

```bash
$WS ensure <TICKET> --repo <PROJECT_ROOT>
```

If `$WS` reports ambiguous project, ask once and:

```bash
$WS set-project <slug> --repo <PROJECT_ROOT> --prefixes <PREFIX>
```

### Fresh interpret check

1. `$JIRA get <TICKET>` → read `issue.updated`
2. `$WS is-fresh <TICKET> --jira-updated <updated>`
3. If `fresh: true` and PRD/PROMPT/QUALITY exist → skip reinterpret unless user forces

Artifact root (not git `docs/tasks`):

```text
%USERPROFILE%\Documents\copilot-workspace\<project-slug>\<TICKET>\
```

---

## `today` / default

1. `$JIRA myself` (fail fast on credentials).
2. `$JIRA sprint --max 50`
3. `$JIRA mine --max 50`
4. For each sprint/mine key, `$WS resolve` / state index — mark:
   - missing interpret
   - interpret stale (`is-fresh` false)
   - ready to execute
   - evidence missing
5. Show a compact board to the user with suggested next actions (`interpret`, `start`, `evidence`, `tutorial`).

---

## `plan`

1. Load sprint issues.
2. Order by priority then status (In Development first among active, then To Do / Backlog).
3. Annotate interpret gaps and dependencies if known from workspace `meta` / task index.
4. Present ordered plan; do not start work until user asks.

---

## `interpret [KEY|all-sprint]`

1. Resolve keys (single KEY or all from `$JIRA sprint`).
2. For each key:
   - Skip if `$WS is-fresh` and artifacts present (unless user said regenerate).
   - Else invoke **`interpret`** skill with the key (Jira-first).
   - After interpret succeeds, ensure docs landed under Documents via `$WS ensure` + write meta:
     ```bash
     $WS write-meta <TICKET> --jira-updated <updated> --repo <PROJECT_ROOT>
     ```
3. Report per-key: skipped | interpreted | failed.

---

## `start KEY`

1. `$JIRA transitions KEY` — if a transition toward development exists (e.g. name contains `Development` / `In Progress` / `Em desenvolvimento`), ask before applying:
   ```bash
   $JIRA transition KEY --to "<Name>"
   ```
   Use `--dry-run` first if the user wants a preview.
2. Invoke **`execute KEY`** (worktree flow unchanged under `../<repo>-worktrees/<TICKET>`).
3. On execute completion (user approved / GREEN), suggest `dev-day evidence KEY`.

---

## `parallel KEY1,KEY2,...`

1. Parse keys (comma/space separated). Cap concurrent agents at **3**; queue the rest.
2. For keys without fresh interpret → run interpret first (serial or light parallel).
3. For each active key: spawn a Task agent with a fixed prompt pointing at Documents `PROMPT.md` / `QUALITY.md` from `$WS resolve`, instructing it to follow `/execute`.
4. Aggregate status when agents return; do not exceed 3 simultaneous.

---

## `evidence KEY`

1. Invoke **`fix-evidence KEY`** (follow that skill fully).
2. Do not start `qa-test-tutorial` automatically; after success, offer `dev-day tutorial KEY`.

---

## `tutorial KEY`

1. Prefer that `evidence/` already has a `manifest.json`. If missing, warn and ask whether to run `fix-evidence` first.
2. Invoke **`qa-test-tutorial`** for KEY.
3. Remind: correction PNG upload is owned by `fix-evidence`, not the tutorial skill.

---

## Safety rules

- Never publish Jira attachments/comments without user confirmation (`fix-evidence` already asks).
- Never store or echo Atlassian tokens.
- Never invent transitions — only use IDs/names from `$JIRA transitions`.
- Keep code worktrees separate from Documents planning/evidence paths.
