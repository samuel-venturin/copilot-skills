---
name: execute
description: Execute a planned task end-to-end, using specific sub-skills for each step of the workflow. This is the main execution command that orchestrates the entire process from identifying the task to final approval.
---

# /execute — Task Executor

> `$TM` = `python3 ~/.claude/scripts/task_manager.py`
> All commands run with `cwd = <PROJECT_ROOT>`.

Input: `$ARGUMENTS` — ticket ID, "next", "resume"/"continua", or empty (defaults to resume).

This command runs **entirely in foreground**. Do not dispatch Caio or any subagent in background.

---

## Workflow Overview

This skill orchestrates task execution through 8 sequential phases, each implemented as a sub-skill:

1. **Phase 1 (`/execute-validate`)** — Validation (Steps 0-3)
   - Identify ticket
   - Check dependencies, artifacts, and status

2. **Phase 2 (`/execute-setup`)** — Worktree Setup (Step 4)
   - Locate or create worktree

3. **Phase 3 (`/execute-tdd-red`)** — Test-First TDD-RED (Step 5)
    - Write all unit and E2E tests in failing state
    - Tests document expected behavior (from QUALITY.md)
    - E2E must live under `\<WORKTREE_PATH\>/e2e/tests/\<dominio\>`
    - NO implementation yet — tests only

4. **Phase 4 (`/execute-transition`)** — Status Transition (Step 6)
    - Transition task to `doing` only
    - Carry `e2e_domain_path` + `e2e_target_specs` to implementation

5. **Phase 5 (`/execute-implementation`)** — GREEN Loop (Step 7)
   - Implement in loop: test -> fix -> retest until GREEN
   - Never modify tests without explicit user authorization

6. **Phase 6 (`/execute-code-review`)** — Code Review (Step 8)
   - Rigorous validation against DRY, SOLID, FP, Clean Code, Project Standards
   - Caio acts as strict code reviewer
   - Decision: APPROVED / NEEDS_IMPROVEMENT / REJECTED

7. **Phase 7 (`/execute-qa-validation`)** — QA Revalidation Gate (Step 9-10)
    - Re-run tests after code review
    - Re-run ticket E2E targets from `\<WORKTREE_PATH\>/e2e/tests/\<dominio\>`
    - GREEN -> continue; FAIL -> generate report and stop

8. **Phase 8 (`/execute-approve`)** — Approval (Steps 11-13)
   - Await user approval
   - Transition to `done`
   - Cleanup

---

## Execution Flow

### Phase 1: INVOKE `/execute-validate <TICKET>`

```bash
/execute-validate <TICKET>
```

This phase:
- Maps `$ARGUMENTS` to ticket (Step 0)
- Validates dependencies (Step 1)
- Validates artifacts (Step 2)
- Checks task status and offers resume mode (Step 3)

**Expected output:**
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

If validation fails → **STOP**. Display error message from validate phase and do not proceed.

---

### Phase 2: INVOKE `/execute-setup <TICKET>`

```bash
/execute-setup <TICKET>
```

This phase:
- Locates existing worktree or creates new one (Step 4)
- Copies `.env` and `public/config.json` to maintain consistency

**Expected output:**
```json
{
  "ticket": "<TICKET>",
  "setup_passed": true,
  "worktree_path": "<WORKTREE_PATH>",
  "status": "created | existing"
}
```

If setup fails → **STOP**. Display error message from setup phase and do not proceed.

---

### Phase 3: INVOKE `/execute-tdd-red <TICKET>`

```bash
/execute-tdd-red <TICKET>
```

This phase:
- Reads `QUALITY.md` and extracts all unit/E2E/regression test cases
- Dispatches João to write tests first (RED phase), before any implementation
- Defines `e2e_domain_path` and `e2e_target_specs` in `\<WORKTREE_PATH\>/e2e/tests/\<dominio\>`
- Validates 100% QUALITY.md coverage and confirms tests are failing as expected
- **CRITICAL:** This is **foreground-only** — wait for TDD-RED completion before proceeding

**Expected output:**
```json
{
  "ticket": "<TICKET>",
  "tdd_red_passed": true,
  "unit_tests_count": 0,
  "e2e_tests_count": 0,
  "regression_tests_count": 0,
  "all_tests_failing": true,
  "quality_md_coverage": "100%",
  "ready_for_implementation": true,
  "e2e_domain_path": "<WORKTREE_PATH>/e2e/tests/<dominio>",
  "e2e_target_specs": ["<WORKTREE_PATH>/e2e/tests/<dominio>/<flow>.spec.ts"]
}
```

If RED state is not confirmed or QUALITY.md coverage is incomplete → **STOP**. Do not proceed.

---

### Phase 4: INVOKE `/execute-transition <TICKET>`

```bash
/execute-transition <TICKET>
```

This phase:
- Transitions task status to `doing` only
- Does not implement code and does not run QA gates

**Expected output:**
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

If transition fails → **STOP**.

---

### Phase 5: INVOKE `/execute-implementation <TICKET>`

```bash
/execute-implementation <TICKET>
```

This phase:
- Executes implementation loop: test -> fix production code -> retest
- Repeats until all tests are GREEN
- Runs ticket E2E targets from `e2e_domain_path/e2e_target_specs` only
- Never alters tests without explicit user authorization
- **CRITICAL:** foreground-only

**Expected output:**
```json
{
  "ticket": "<TICKET>",
  "implementation_passed": true,
  "tests_status": "all_passing (GREEN)",
  "tests_passing": 0,
  "tests_failing": 0,
  "test_change_requested": false,
  "ready_for_code_review": true
}
```

If tests fail or test changes are required without user authorization → **STOP**.

---

### Phase 6: INVOKE `/execute-code-review <TICKET>`

```bash
/execute-code-review <TICKET>
```

This phase:
- Performs strict code review (DRY, SOLID, FP, Clean Code, `<WORKTREE_PATH>/AGENTS.md`)
- Returns severity-based violations and recommendation
- **CRITICAL:** foreground-only

**Expected output:**
```json
{
  "ticket": "<TICKET>",
  "code_review_passed": true,
  "recommendation": "APPROVED | NEEDS_IMPROVEMENT | REJECTED",
  "overall_code_review_score": 85,
  "violations_total": 0,
  "critical_violations": 0
}
```

If recommendation is `REJECTED` → **STOP**.

---

### Phase 7: INVOKE `/execute-qa-validation <TICKET>`

```bash
/execute-qa-validation <TICKET>
```

This phase:
- Re-runs validation tests after code review
- Uses E2E targets from `\<WORKTREE_PATH\>/e2e/tests/\<dominio\>` only
- If GREEN: allows final user approval
- If FAIL: generates `docs/tasks/<TICKET>/QA_VALIDATION_REPORT.json` and stops for manual continuation

**Expected output:**
```json
{
  "ticket": "<TICKET>",
  "qa_validation_passed": true,
  "tests_status": "all_passing (GREEN)",
  "ready_for_user_approval": true
}
```

If `qa_validation_passed = false` → **STOP** and hand off to user with generated report.

---

### Phase 8: INVOKE `/execute-approve <TICKET>`

```bash
/execute-approve <TICKET>
```

This phase:
- Transitions task to `awaiting-user-approval`
- Presents execution summary to user
- Awaits exact approval token: `APROVAR_EXEC_TASK_001`
- Transitions to `done`
- Offers optional cleanup

**Expected output:**
```json
{
  "ticket": "<TICKET>",
  "status": "done",
  "approval_timestamp": "<ISO-8601>",
  "prompt_cleaned": true | false
}
```

If approval fails → **STOP**. Ask user to retry with correct token.

---

## Safety Rules

- **Foreground-only execution** — all phases are synchronous, never dispatch subskills in background
- **Sequential flow** — do not skip or reorder phases
- Never skip DEPENDENCY_GUARD — do not execute if dependency is not `done`
- Never skip ARTIFACT_GUARD — do not execute without PRD + PROMPT + QUALITY
- Never skip TDD_RED — tests must be written/executed in RED state before implementation
- Never skip TRANSITION — task must enter `doing` before implementation
- Never skip GREEN_CHECK — implementation phase must make tests pass before code-review
- Never modify tests during implementation without explicit user authorization
- Never skip CODE_REVIEW — code quality validation is mandatory before user approval
- Never skip QA_VALIDATION — tests must be re-run after code-review before user approval
- Never use protocolo djalma — only automations under `<WORKTREE_PATH>/e2e/tests/<dominio>`
- QA validation failures must generate `docs/tasks/<TICKET>/QA_VALIDATION_REPORT.json` and stop
- CODE_REVIEW with REJECTED recommendation blocks approval completely
- CODE_REVIEW with NEEDS_IMPROVEMENT allows user override (tracked for accountability)
- Never delete `PRD.md`, `QUALITY.md`, or `docs/ux/` — only cleanup `PROMPT.md` if user confirms
- If any phase fails or returns `passed: false` → STOP immediately and display the error
- If Caio is unavailable (agent not found) → stop and inform user
