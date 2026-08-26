---
name: execute-transition
description: Transition task status to doing. This phase only changes state before implementation loop.
---

# /execute-transition — Status Transition Phase

> `$TM` = `python3 ~/.claude/scripts/task_manager.py`

Input (from `/execute-tdd-red` output + previous phases):
- `$TICKET` — validated ticket ID
- `$TDD_RED_PASSED` — must be `true`
- `$E2E_DOMAIN_PATH` — must be `<WORKTREE_PATH>/e2e/tests/<dominio>`
- `$E2E_TARGET_SPECS` — targeted E2E specs for this ticket

---

## Step 5 — Transition to `doing`

```bash
$TM set-status <TICKET> doing
```

Confirm:
> "✅ Task `<TICKET>` transitioned to `doing`."

---

## ✅ SUCCESS PATH

Return:

```json
{
  "ticket": "<TICKET>",
  "transition_passed": true,
  "status": "doing",
  "ready_for_implementation": true,
  "e2e_domain_path": "<WORKTREE_PATH>/e2e/tests/<dominio>",
  "e2e_target_specs": ["<WORKTREE_PATH>/e2e/tests/<dominio>/<flow>.spec.ts"]
}
```

**Proceed to next phase: `/execute-implementation`**

---

## Safety rules

- Foreground-only.
- Never run this phase if `tdd_red_passed != true`.
- This phase only updates status. It does not implement code or execute QA gates.
- Never accept protocolo djalma; pass only `e2e/tests/<dominio>` targets forward.
