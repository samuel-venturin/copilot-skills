---
name: execute-qa-validation
description: Re-run validation tests after code review. If GREEN, proceed to user approval; otherwise generate report and stop for manual continuation.
---

# /execute-qa-validation — Final QA Validation Phase

> `$TM` = `python3 ~/.claude/scripts/task_manager.py`

Input (from `/execute-code-review` + previous phases):
- `$TICKET`
- `$WORKTREE_PATH`
- `$TEST_FILES_CREATED`
- `$EXECUTION_SUMMARY`
- `$CODE_REVIEW_PASSED`
- `$E2E_DOMAIN_PATH` — `<WORKTREE_PATH>/e2e/tests/<dominio>`
- `$E2E_TARGET_SPECS` — targeted E2E specs for this ticket

---

## Step 9 — Re-run QA validation tests

Run tests again (full final gate):

```bash
cd <WORKTREE_PATH>
pnpm test --run
pnpm e2e:headed -- <WORKTREE_PATH>/e2e/tests/<dominio>/<flow>.spec.ts
```

Use `<WORKTREE_PATH>/AGENTS.md` and `<WORKTREE_PATH>/e2e/docs/` as source of truth for execution rules.
Do not use protocolo djalma.

---

## Step 10 — Decision Gate

If all tests are GREEN:

```json
{
  "ticket": "<TICKET>",
  "qa_validation_passed": true,
  "tests_status": "all_passing (GREEN)",
  "ready_for_user_approval": true
}
```

**Proceed to next phase: `/execute-approve`**

If any test fails:
- Generate report file:

```bash
mkdir -p <WORKTREE_PATH>/docs/tasks/<TICKET>
```

Write JSON report at:
- `<WORKTREE_PATH>/docs/tasks/<TICKET>/QA_VALIDATION_REPORT.json`

Minimum report payload:

```json
{
  "ticket": "<TICKET>",
  "qa_validation_passed": false,
  "generated_at": "<ISO-8601>",
  "tests_status": "failing",
  "unit_test_failures": [ "...summary..." ],
  "e2e_test_failures": [ "...summary..." ],
  "next_action": "Manual continuation required by user"
}
```

Then stop and notify user:
> "⛔ QA validation failed. Report generated at `docs/tasks/<TICKET>/QA_VALIDATION_REPORT.json`.  
> Processo interrompido para continuidade manual."

---

## Safety rules

- Foreground-only.
- Never proceed to `/execute-approve` unless `qa_validation_passed = true`.
- If failing, always generate `QA_VALIDATION_REPORT.json` and stop.
- E2E gate must execute ticket targets inside `<WORKTREE_PATH>/e2e/tests/<dominio>`.
