---
name: execute-setup
description: Create or locate worktree for task execution. Step 4 of execute workflow.
---

# /execute-setup — Worktree Setup Phase

> `$TM` = `python3 ~/.claude/scripts/task_manager.py`

Input (from `/execute-validate` output):
- `$TICKET` — validated ticket ID
- `$PROJECT_ROOT` — project root directory

---

## Step 4 — WORKTREE_GUARD

Locate the worktree:

```bash
WORKTREE_PATH=../<PROJECT_ROOT_BASENAME>-worktrees/<TICKET>
```

### If worktree **exists**:

1. Display status:
   > "✅ Worktree encontrada: `<WORKTREE_PATH>`"
2. Always sync runtime/config files from project root:
   ```bash
   mkdir -p $WORKTREE_PATH/public $WORKTREE_PATH/e2e
   [ -f <PROJECT_ROOT>/.env ] && cp <PROJECT_ROOT>/.env $WORKTREE_PATH/.env
   [ -f <PROJECT_ROOT>/public/config.json ] && cp <PROJECT_ROOT>/public/config.json $WORKTREE_PATH/public/config.json
   [ -f <PROJECT_ROOT>/.npmrc ] && cp <PROJECT_ROOT>/.npmrc $WORKTREE_PATH/.npmrc
   [ -f <PROJECT_ROOT>/e2e/.env.e2e ] && cp <PROJECT_ROOT>/e2e/.env.e2e $WORKTREE_PATH/e2e/.env.e2e
   ```
3. Proceed to next phase.

### If worktree **does not exist**:

1. Warn:
   > "⚠️ Worktree `<WORKTREE_PATH>` não encontrada. A worktree deveria ter sido criada pelo `/interpret`.
   > Criar agora a partir de `origin/develop`?"

2. If user confirms:
   ```bash
   git fetch origin
   git worktree add $WORKTREE_PATH <branch_from_index> origin/develop
   mkdir -p $WORKTREE_PATH/public $WORKTREE_PATH/e2e
   [ -f <PROJECT_ROOT>/.env ] && cp <PROJECT_ROOT>/.env $WORKTREE_PATH/.env
   [ -f <PROJECT_ROOT>/public/config.json ] && cp <PROJECT_ROOT>/public/config.json $WORKTREE_PATH/public/config.json
   [ -f <PROJECT_ROOT>/.npmrc ] && cp <PROJECT_ROOT>/.npmrc $WORKTREE_PATH/.npmrc
   [ -f <PROJECT_ROOT>/e2e/.env.e2e ] && cp <PROJECT_ROOT>/e2e/.env.e2e $WORKTREE_PATH/e2e/.env.e2e
   ```

3. If user declines:
   > "⛔ Worktree creation cancelled. Cannot proceed."
   > **Stop.**

---

## ✅ SUCCESS PATH

If worktree exists or was created successfully:

1. **From this point, `PROJECT_ROOT = WORKTREE_PATH`** (for all subsequent operations).

Return setup result:

```json
{
  "ticket": "<TICKET>",
  "setup_passed": true,
  "worktree_path": "<WORKTREE_PATH>",
  "status": "created | existing"
}
```

**Proceed to next phase: `/execute-transition` (transition to `doing`)**

---

## Safety rules

- Never delete or reset existing worktrees without explicit user confirmation.
- Always sync `.env`, `public/config.json`, `.npmrc`, and `e2e/.env.e2e` to maintain environment consistency.
