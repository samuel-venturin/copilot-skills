---
name: tasks
description: Manage the task queue — list, next, inspect, set dependencies, and transition status.
---

# /tasks — Task Queue Manager

> `$TM` = `python3 ~/.claude/scripts/task_manager.py`
> All commands run with `cwd = <PROJECT_ROOT>`.

Input: `$ARGUMENTS` — subcommand + optional arguments (see routing table below).

---

## Intent routing

Before doing anything, map `$ARGUMENTS` to the correct subcommand:

| `$ARGUMENTS` | Action |
|---|---|
| empty / "list" / "lista" / "todas" | `$TM list` + display table |
| "next" / "próxima" / "o que fazer" | `$TM next` + display card |
| "doing" / "em andamento" | `$TM list --status doing` + display |
| "waiting" / "aguardando" | `$TM list --status waiting` + display |
| "done" / "concluídas" | `$TM list --status done` + display |
| "get <id\|TICKET>" | `$TM get <id>` + display full card |
| "done <id\|TICKET>" | → See DONE_GUARD below |
| "depends <id\|TICKET> <depends-on>" | `$TM set-depends-on <id> <depends-on>` |
| "sync" | `$TM sync-specs` → report new specs found |
| "global" | `$TM global-list` + display cross-project |
| Intent unclear | Ask: "Você quer listar, ver a próxima, inspecionar um ticket ou atualizar dependências?" |

---

## Display format

### List view
After running `$TM list`, format the JSON as a table:

```
📋 Task Queue — <PROJECT_ROOT>
──────────────────────────────────────────────────────────
 ID  | TICKET     | STATUS              | TYPE | PRI | DEPENDS ON
─────|────────────|─────────────────────|──────|─────|──────────
 001 | CTR-1135   | ✅ done             | us   |  1  | —
 002 | CTR-1139   | 🔄 doing            | us   |  2  | CTR-1135
 003 | CTR-1156   | ⏳ waiting          | us   |  3  | —
 004 | CTR-1200   | 🆕 new              | us   |  4  | CTR-1139
──────────────────────────────────────────────────────────
Total: 4 tasks
```

Status icons: `🆕 new` · `⏳ waiting` · `🔄 doing` · `🔐 awaiting-user-approval` · `✅ done`

### Task card (get / next)
```
┌─────────────────────────────────────────────────┐
│  TICKET  CTR-1139                               │
│  STATUS  🔄 doing                               │
│  TYPE    us   PRI 2                             │
│  BRANCH  us/CTR-1139                            │
│  DEPENDS —                                      │
├─────────────────────────────────────────────────┤
│  PRD     docs/tasks/CTR-1139/PRD.md   ✅        │
│  PROMPT  docs/tasks/CTR-1139/PROMPT.md ✅       │
│  QUALITY docs/tasks/CTR-1139/QUALITY.md ✅      │
└─────────────────────────────────────────────────┘
```

For each artifact path, show ✅ if file exists, ❌ if missing.

---

## DONE_GUARD

Only transition a task to `done` via `/execute` — never directly via `/tasks done`.

If user runs `/tasks done <ticket>`:
1. Show current task summary (card format).
2. Warn: "Marcar como `done` deve ser feito via `/execute` após validação completa (E2E + QA + token de aprovação). Quer forçar mesmo assim?"
3. If user confirms → require exact token `APROVAR_EXEC_TASK_001`.
4. If token matches → `$TM set-status <id> done` + `$TM render-index`.
5. If token doesn't match → stop.

---

## Dependency check

When displaying `next`:
1. Run `$TM next`.
2. If the returned task has a `depends_on` field:
   - Run `$TM get <depends_on>` and check status.
   - If status ≠ `done` → **do not suggest this task**.
   - Show: "⚠️ `<TICKET>` aguarda `<depends_on>` (status: `<status>`). Nenhuma task disponível — conclua a dependência primeiro."
3. If no `depends_on` or dependency is `done` → show task card normally.

---

## Safety rules

- Never edit `index.json` directly.
- Never transition to `done` without exact token.
- Never show a blocked task as "next" — always filter by dependency status.
