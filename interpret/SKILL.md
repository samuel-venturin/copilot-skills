---
name: interpret
description: Interpret a Jira spec and produce planning artifacts — PRD, PROMPT, QUALITY. Triggered automatically when XML is pasted.
---

# /interpret — Task Interpreter

> `$TM` = `python3 ~/.claude/scripts/task_manager.py`
> `$SE` = `python3 ~/.claude/scripts/spec-extractor.tool.py`
> All commands run with `cwd = <PROJECT_ROOT>`.

Input: `$ARGUMENTS` — ticket ID, spec file path, or empty (XML already in conversation context). Optionally followed by `--in-background` flag.

Flags:
- `--in-background` — create a git worktree for isolated execution (background agent mode). Default: **off** (work in main repo).

This command runs **entirely in foreground**. Do not dispatch background agents.

---

## Step 0 — Detect input mode

Determine the spec source from `$ARGUMENTS` and conversation context:

| Condition | Input mode |
|-----------|-----------|
| `$ARGUMENTS` is empty AND conversation contains raw XML (starts with `<`, has `<rss`/`<item`) | `xml-paste` — use XML from conversation |
| `$ARGUMENTS` looks like a ticket (e.g. `CTR-1200`) | `ticket-file` — look for `specs/CTR-1200.md` |
| `$ARGUMENTS` is a file path | `spec-file` — use the file directly |
| None of the above | Ask: "Cole o XML do Jira ou informe o ticket/arquivo do spec." |

---

## Step 1 — Extract spec data

### If input mode is `xml-paste`:
1. Save validated XML to `<PROJECT_ROOT>/specs/<TICKET>.md` (create `specs/` with `mkdir -p` if needed), using this template:
   ```markdown
   ---
   task: <ticket>
   type: <type>
   description: Jira card importado via XML
   ---

   # Tarefa:

   ```xml
   <original XML here>
   ```
   ```
2. Run: `$SE --xml "<xml_content>"`
3. Continue to Step 2.

### If input mode is `ticket-file` or `spec-file`:
1. Read the XML block from the spec file.
2. Run: `$SE --xml "<xml_block>"`
3. Continue to Step 2.

### Validate extractor output:
- `success: false` or error → **stop**, show error to user.
- `key` is empty → **stop**: "Ticket key not found in XML."
- `acceptance_criteria` is empty → warn: "CAs not extracted — check spec format." (but continue).

Store extracted data: `key`, `type`, `summary`, `acceptance_criteria`, `test_cases`, `dod`.

---

## Step 2 — IDEMPOTENCY_GUARD ⛔

Check if planning artifacts already exist for this ticket:

```bash
ls <PROJECT_ROOT>/docs/tasks/<TICKET>/
```

If **any** of `PRD.md`, `PROMPT.md`, or `QUALITY.md` exists:
1. Show which files exist with their last-modified dates.
2. Ask:
   > "Os artefatos de planejamento para `<TICKET>` já existem:
   > - PRD.md (modificado: <date>)
   > - PROMPT.md (modificado: <date>)
   > - QUALITY.md (modificado: <date>)
   >
   > O que deseja fazer?
   > (a) Regenerar tudo — sobrescrever os artefatos existentes
   > (b) Regenerar somente [especifique qual]
   > (c) Cancelar — manter os artefatos existentes"
3. Wait for user choice before continuing.
4. If user chooses (c) → stop.

---

## Step 3 — BRANCH_SETUP

### Infer branch name (MUST match branch naming contract):

| Spec type | Branch prefix | Example |
|-----------|--------------|---------|
| `História` | `us/` | `us/CTR-1200` |
| `Tarefa` / `Sub-tarefa` | `us/task/` | `us/task/CTR-1200` |
| `Bug` / `Hotfix` / `Fix` / `bug` | `bug/` | `bug/CTR-1200` |
| `Chore` | `chore/` | `chore/CTR-1200` |

### If `--in-background` flag is present → WORKTREE mode:

```bash
WORKTREE_PATH=../<PROJECT_ROOT_BASENAME>-worktrees/<TICKET>
ls $WORKTREE_PATH 2>/dev/null
```

If worktree **already exists**:
1. Show: git log --oneline -5 and `git status` inside the worktree.
2. Ask:
   > "A worktree `<WORKTREE_PATH>` já existe com as seguintes alterações: [show status].
   > (a) Reuse — continuar usando esta worktree
   > (b) Delete e recriar — apagar a worktree e criar nova a partir de `origin/develop`
   > (c) Cancelar"
3. If (a) → skip worktree creation. Redefine PROJECT_ROOT = WORKTREE_PATH.
4. If (b) → `git worktree remove <WORKTREE_PATH> --force`, then create new (see below).
5. If (c) → stop.

If worktree **does not exist**:
```bash
cd <PROJECT_ROOT>
git fetch origin
git worktree add $WORKTREE_PATH -b <branch_name> origin/develop
[ -f <PROJECT_ROOT>/.env ] && cp <PROJECT_ROOT>/.env $WORKTREE_PATH/.env
[ -f <PROJECT_ROOT>/public/config.json ] && cp <PROJECT_ROOT>/public/config.json $WORKTREE_PATH/public/config.json
```

**From this point forward, `PROJECT_ROOT = WORKTREE_PATH`.**

### If `--in-background` flag is NOT present → MAIN REPO mode (default):

Only create the branch if it doesn't already exist:
```bash
cd <PROJECT_ROOT>
git fetch origin
git branch <branch_name> origin/develop 2>/dev/null || true
```

**`PROJECT_ROOT` stays as the main repo. `WORKTREE_PATH` is not set.**

---

## Step 4 — PM_AMBIGUITY_GATE ⛔ BLOCKING

Analyze the extracted spec data for ambiguities. Do not skip. Do not proceed until count = 0.

Check for:

**A. Scope split (frontend vs backend)**
- If spec contains CAs tagged as "Backend" or referencing server-side behavior:
  > "Este spec inclui [N] CAs de backend. Estamos num projeto frontend. Devo:
  > (a) Escopar apenas frontend
  > (b) Incluir backend como sub-tarefa separada
  > (c) Manter escopo fullstack"

**B. Referenced UI elements that may not exist**
- Scan `app/pages/`, `app/components/`, `app/stores/` for each UI element mentioned (tabs, screens, sections).
- If not found:
  > "O spec menciona '[elemento]' mas não encontrei no codebase. Devo:
  > (a) Criar como parte desta task
  > (b) Assumir que existe com outro nome (especifique)
  > (c) Ignorar este elemento"

**C. Missing API contract**
- If spec references an API call without URL, method, or payload:
  > "Não há contrato de API definido para [ação]. Você tem esse contrato, ou devo registrar como questão aberta no PRD?"

**D. Unclear UX edge cases**
- If spec has CAs with undefined behavior for edge scenarios (navigation, errors, empty states):
  - List each and ask for the expected behavior.

Show counter after each answer: `Ambiguidades restantes: N`

Exception: if user says "pode assumir" → proceed but log all open assumptions in PRD under `## Open Assumptions`.

---

## Step 5 — Write PRD

1. Compute: `prd_path = <PROJECT_ROOT>/docs/tasks/<TICKET>/PRD.md`
2. Run `mkdir -p <PROJECT_ROOT>/docs/tasks/<TICKET>/`
3. If `se-product-manager-advisor` is available → dispatch with:
   - full spec content, extracted spec data, resolved ambiguities
   - `prd_output_path: <prd_path>`
   - Instruction: "Operate in Task Interpreter Integration Mode. All ambiguities resolved — see context. Do NOT ask new questions. Write PRD directly to prd_output_path."
   - Wait for completion. Verify file written.
4. If agent not available or file not written after retry → write PRD directly from spec data + resolved context.

PRD structure (minimum):
```
# PRD — <TICKET>: <summary>
## Context / Problem
## Scope (frontend | backend | fullstack)
## Acceptance Criteria (normalized CAxx list)
## UX Reference (if UX docs exist)
## Open Assumptions (if any)
## Out of Scope
```

---

## Step 6 — Write PROMPT

1. Read PRD from `<PROJECT_ROOT>/docs/tasks/<TICKET>/PRD.md`.
2. Write `<PROJECT_ROOT>/docs/tasks/<TICKET>/PROMPT.md`.

PROMPT must start with:
```
> PRD reference: <PROJECT_ROOT>/docs/tasks/<TICKET>/PRD.md
> Read this file before executing any step below.
```

PROMPT must include:
- Task scope summary (1 paragraph)
- Branch: `<branch_name>`
- Worktree path: `<WORKTREE_PATH>` *(only if `--in-background` was used; omit otherwise)*
- Impacted files / layers (with confidence: High / Medium / Low)
- Implementation steps — one step per file/action (what / where / how)
- Test strategy (unit / integration / E2E)
- Mock plan (if API contract is missing)
- Open questions (if any)

---

## Step 7 — Write QUALITY

1. If `qa-subagent` is available → dispatch with:
   - `prd_path: <PROJECT_ROOT>/docs/tasks/<TICKET>/PRD.md`
   - `quality_output_path: <PROJECT_ROOT>/docs/tasks/<TICKET>/QUALITY.md`
   - Instruction: "Operate in Task Interpreter Integration Mode. Read the PRD. Write QUALITY.md."
   - Wait for completion. Verify file written.
2. If agent not available or file not written after retry → write QUALITY directly from PRD.

QUALITY must include:
- Normalized CAs (`CA01`…)
- Normalized CTs grouped: positive / negative / error (`CT01`…)
- Definition of Done checklist
- Traceability matrix (CA → CT → files)
- Quality gaps (CAs without clear CT)

---

## Step 8 — Register in index

Run from `PROJECT_ROOT = WORKTREE_PATH`:

```bash
$TM add --spec <PROJECT_ROOT>/specs/<TICKET>.md --ticket <key> --type <type>
$TM set-field <id> prompt <PROJECT_ROOT>/docs/tasks/<TICKET>/PROMPT.md
$TM set-field <id> quality <PROJECT_ROOT>/docs/tasks/<TICKET>/QUALITY.md
$TM set-field <id> prd <PROJECT_ROOT>/docs/tasks/<TICKET>/PRD.md
$TM set-field <id> branch <branch_name>
$TM set-status <id> waiting
$TM render-index
```

> If spec is already indexed (duplicate check): skip `$TM add`, update fields only.

---

## Step 9 — Report

Show final summary:
```
✅ /interpret concluído para <TICKET>

  Branch    <branch_name>
  Worktree  <WORKTREE_PATH>  ← only shown when --in-background was used
  PRD       docs/tasks/<TICKET>/PRD.md
  PROMPT    docs/tasks/<TICKET>/PROMPT.md
  QUALITY   docs/tasks/<TICKET>/QUALITY.md
  Status    waiting

  Ambiguidades resolvidas: <N>
  Assumptions abertas: <N> (ver PRD § Open Assumptions)

Próximo passo: /execute <TICKET>
```

---

## Safety rules

- Never generate artifacts from memory or summaries — always read PRD file before writing PROMPT/QUALITY.
- Never overwrite existing artifacts without confirming with user first (IDEMPOTENCY_GUARD).
- Never create a worktree from a branch other than `origin/develop`.
- Never proceed if `$SE` returns `success: false`.
- Never infer missing API contracts silently — ask in AMBIGUITY_GATE.
