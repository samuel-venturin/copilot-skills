---
name: execute-implementation
description: Implement in a GREEN loop (run tests, fix code, rerun) until all tests pass. Never alter tests without explicit user authorization.
---

# /execute-implementation — GREEN Loop Phase

> `$TM` = `python3 ~/.claude/scripts/task_manager.py`

Input (from `/execute-transition` + prior outputs):
- `$TICKET`
- `$WORKTREE_PATH`
- `$PROMPT_PATH`, `$PRD_PATH`, `$QUALITY_PATH`
- `$RESUME_MODE`
- `$TEST_FILES_CREATED` — tests created in TDD-RED
- `$E2E_DOMAIN_PATH` — `<WORKTREE_PATH>/e2e/tests/<dominio>`
- `$E2E_TARGET_SPECS` — targeted E2E specs created in TDD-RED

---

## Step 6 — CAIO_IMPLEMENTATION_LOOP

Dispatch Caio to implement the feature with strict looping:

1. Run targeted tests (unit + e2e from TDD-RED)
2. Analyze failures
3. Fix production code
4. Re-run tests
5. Repeat until GREEN (`tests_failing = 0`)

**Critical rule:** never modify test files unless user explicitly authorizes.

Context:

```
ticket:              <TICKET>
project_root:        <WORKTREE_PATH>
prompt_path:         <PROMPT_PATH>
prd_path:            <PRD_PATH>
quality_path:        <QUALITY_PATH>
agents_md_path:      <WORKTREE_PATH>/AGENTS.md
e2e_docs_path:       <WORKTREE_PATH>/e2e/docs/
e2e_domain_path:     <WORKTREE_PATH>/e2e/tests/<dominio>
e2e_target_specs:    [<WORKTREE_PATH>/e2e/tests/<dominio>/<flow>.spec.ts]
test_files_created:  [<paths>]
resume_mode:         "continue" | "restart"
```

Dispatch instruction:

> "Você é o Caio. Execute a implementação em loop GREEN para `<TICKET>`.
>
> Regras obrigatórias:
> - Leia PRD, PROMPT, QUALITY, `<WORKTREE_PATH>/AGENTS.md` e `<WORKTREE_PATH>/e2e/docs/`.
> - Faça loop: testar -> corrigir código de produção -> retestar, até ficar GREEN.
> - Execute E2E somente via `<WORKTREE_PATH>/e2e/tests/<dominio>` (`e2e_target_specs`).
> - **NUNCA altere testes sem autorização explícita do usuário.**
> - Se detectar que alteração de teste é necessária, pare e solicite autorização.
> - Não apague/reescreva código sem conflito explícito com PROMPT.
> - Protocolo djalma é proibido.
>
> Retorne JSON:
> ```json
> {
>   \"ticket\": \"<TICKET>\",
>   \"implementation_passed\": true/false,
>   \"tests_status\": \"all_passing (GREEN) | failing | blocked_waiting_user_auth\",
>   \"tests_passing\": <number>,
>   \"tests_failing\": <number>,
>   \"loops_executed\": <number>,
>   \"test_change_requested\": true/false,
>   \"test_change_reason\": \"<when requested>\",
>   \"execution_summary\": {
>     \"scope\": \"frontend | backend | fullstack\",
>     \"agents_dispatched\": [],
>     \"code_review_rounds\": <number>,
>     \"ux_review\": \"approved | skipped\",
>     \"qa_verdict\": \"approved | rejected\"
>   },
>   \"ready_for_code_review\": true/false
> }
> ```"

Wait for Caio result in foreground.

---

## ✅ SUCCESS PATH

Proceed only when:
- `implementation_passed = true`
- `tests_status = all_passing (GREEN)`
- `tests_failing = 0`
- `ready_for_code_review = true`

Then:

```json
{
  "ticket": "<TICKET>",
  "implementation_passed": true,
  "tests_status": "all_passing (GREEN)",
  "ready_for_code_review": true
}
```

**Proceed to next phase: `/execute-code-review`**

---

## ⛔ BLOCKED/FAILURE PATH

If `tests_status = blocked_waiting_user_auth` or `test_change_requested = true`:
- Stop and ask user authorization explicitly before any test modifications.

If tests remain failing:
- Stop and return failure details for user decision.

---

## Safety rules

- Foreground-only.
- Never alter tests without explicit user authorization.
- Always reference `<WORKTREE_PATH>/AGENTS.md` and `<WORKTREE_PATH>/e2e/docs/` as source of truth.
- Run E2E from `<WORKTREE_PATH>/e2e/tests/<dominio>` targets only.
