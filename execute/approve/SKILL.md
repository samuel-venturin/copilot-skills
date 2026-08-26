---
name: execute-approve
description: Present execution summary and await user approval. Steps 7-9 of execute workflow.
---

# /execute-approve — Approval & Completion Phase

> `$TM` = `python3 ~/.claude/scripts/task_manager.py`

Input (from `/execute-qa-validation` output):
- `$TICKET` — task ID
- `$EXECUTION_SUMMARY` — Caio's JSON summary
- `$READY_FOR_USER_APPROVAL` — boolean

---

## Step 7 — Transition to `awaiting-user-approval`

```bash
$TM set-status <TICKET> awaiting-user-approval
$TM render-index
```

Confirm:
> "✅ Task `<TICKET>` transitioned to `awaiting-user-approval`."

---

## Step 8 — APPROVAL_GATE

Present execution summary to user (formatted clearly):

```
✅ Execução concluída por Caio — <TICKET>

  Escopo:               <scope>
  Agentes acionados:    <agents_dispatched>
  API contract:         <api_contract_found>
  Componentes Atena:    <atena_ui_components_used>
  Code reviews:         <code_review_rounds>
  UX review:            <ux_review>
  QA verdict:           <qa_verdict>

Para aprovar e marcar como done, forneça o token exato:
  APROVAR_EXEC_TASK_001
```

**Wait for the exact token `APROVAR_EXEC_TASK_001`.** Do not accept variants, paraphrases, or similar text.

If user provides anything other than the exact token:
> "Token inválido. Forneça exatamente: `APROVAR_EXEC_TASK_001`"

---

## Step 9 — DONE_TRANSITION

After receiving exact token `APROVAR_EXEC_TASK_001`:

```bash
$TM set-status <TICKET> done
$TM render-index
```

Confirm:
> "✅ Task `<TICKET>` marcada como done."

---

## Cleanup Phase (Optional)

Ask:
> "Deseja limpar os artefatos temporários de `<PROJECT_ROOT>/docs/tasks/<TICKET>/`?
>
> - PROMPT.md seria removido
> - PRD.md e QUALITY.md seriam mantidos (artefatos versionados)
> - docs/ux/ nunca é removido"

If user confirms:
```bash
rm <PROJECT_ROOT>/docs/tasks/<TICKET>/PROMPT.md
```

Confirm:
> "✅ PROMPT.md removido. PRD.md e QUALITY.md mantidos."

If user declines:
> "✅ Cleanup skipped. Todos os artefatos mantidos."

---

## ✅ COMPLETION

Return final result:

```json
{
  "ticket": "<TICKET>",
  "status": "done",
  "approval_timestamp": "<ISO-8601>",
  "prompt_cleaned": true/false
}
```

---

## Safety rules

- Never accept token variants. **Only exact match: `APROVAR_EXEC_TASK_001`**
- Never skip transition to `awaiting-user-approval` — always gate approval properly.
- Never delete `PRD.md`, `QUALITY.md`, or `docs/ux/`.
- Only delete `PROMPT.md` if explicitly confirmed by user.
