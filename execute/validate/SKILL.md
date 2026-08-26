---
name: execute-validate
description: Validate task dependencies, artifacts, and status. Steps 0-3 of execute workflow.
---

# /execute-validate — Validation Phase

> `$TM` = `python3 ~/.claude/scripts/task_manager.py`
> All commands run with `cwd = <PROJECT_ROOT>`.

Input: `$ARGUMENTS` — ticket ID, "next", "resume"/"continua", or empty (defaults to resume).

---

## Step 0 — Identify ticket

Map `$ARGUMENTS` to a task:

| `$ARGUMENTS` | Resolution |
|---|---|
| Ticket ID (e.g. `CTR-1200`) | Use this ticket explicitly |
| "next" / "próxima" | `$TM next` → pick first `waiting` task |
| "resume" / "continua" / empty | `$TM next` → pick first `doing` task; if none, pick `waiting` |
| Multiple `doing` tasks found | Ask user to choose one |

---

## Step 1 — DEPENDENCY_GUARD ⛔

Check if the identified task has a `depends_on` field:

```bash
$TM get <id>
```

If `depends_on` is set:
1. Run `$TM get <depends_on>` to check its status.
2. If status ≠ `done`:
   > "⛔ `<TICKET>` depende de `<depends_on>` (status: `<status>`).
   > Não é possível iniciar esta task até que a dependência esteja concluída.
   > Conclua `<depends_on>` primeiro ou remova a dependência com `/tasks depends <TICKET> none`."
3. **Stop.** Do not continue.

---

## Step 2 — ARTIFACT_GUARD ⛔

Verify all three planning artifacts exist:

```bash
ls <PROJECT_ROOT>/docs/tasks/<TICKET>/PRD.md
ls <PROJECT_ROOT>/docs/tasks/<TICKET>/PROMPT.md
ls <PROJECT_ROOT>/docs/tasks/<TICKET>/QUALITY.md
```

If **any** is missing:
> "⛔ Os artefatos de planejamento para `<TICKET>` estão incompletos:
> - PRD.md: <✅|❌>
> - PROMPT.md: <✅|❌>
> - QUALITY.md: <✅|❌>
>
> Execute `/interpret <TICKET>` primeiro para gerar os artefatos ausentes."

**Stop.** Do not continue without all three files.

---

## Step 3 — STATUS_GATE

Check task status:

| Status | Action |
|--------|--------|
| `waiting` | OK — proceed to next phase |
| `doing` | ⚠️ **Resume mode** — show worktree state; ask user (a) Resume / (b) Restart / (c) Cancel |
| `new` | ⛔ Stop: "Task não foi planejada. Execute `/interpret <TICKET>` primeiro." |
| `awaiting-user-approval` | ⛔ Stop: "Task aguarda aprovação. Forneça o token `APROVAR_EXEC_TASK_001`." |
| `done` | ⛔ Stop: "Task já concluída." |

### Step 3.1 — Resume mode (status = `doing`)

If task status is `doing`, show current worktree state:

```bash
WORKTREE_PATH=../<PROJECT_ROOT_BASENAME>-worktrees/<TICKET>
cd $WORKTREE_PATH && git log --oneline -5 && git status
```

Display the output and ask:
> "A task `<TICKET>` já estava em execução. Estado atual da worktree:
> [show git log + status]
>
> (a) Retomar a partir do estado atual — continua de onde parou
> (b) Reiniciar do zero — relê todos os artefatos e reexecuta (não apaga commits existentes)
> (c) Cancelar"

Wait for user choice (a/b/c) before proceeding.

---

## ✅ SUCCESS PATH

If all validations pass:

1. **If status = `waiting`**: Resume mode = "continue" (fresh start)
2. **If status = `doing` AND user chose (a)**: Resume mode = "continue" (pick up where it left off)
3. **If status = `doing` AND user chose (b)**: Resume mode = "restart" (re-read artifacts)

Return validation result:

```json
{
  "ticket": "<TICKET>",
  "validation_passed": true,
  "resume_mode": "continue | restart",
  "prd_path": "<PROJECT_ROOT>/docs/tasks/<TICKET>/PRD.md",
  "prompt_path": "<PROJECT_ROOT>/docs/tasks/<TICKET>/PROMPT.md",
  "quality_path": "<PROJECT_ROOT>/docs/tasks/<TICKET>/QUALITY.md"
}
```

**Proceed to next phase: `/execute-setup`**

---

## Safety rules

- Never skip DEPENDENCY_GUARD — do not execute a task whose dependency is not `done`.
- Never skip ARTIFACT_GUARD — do not execute without PRD + PROMPT + QUALITY.
- Always clarify resume mode when status = `doing`.
