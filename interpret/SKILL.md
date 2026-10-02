---
name: interpret
description: Interpret a Jira issue and produce planning artifacts — PRD, PROMPT, QUALITY — under Documents/copilot-workspace. Prefers Jira API by ticket key; XML paste is legacy fallback only.
---

# /interpret — Task Interpreter

> `$TM` = `python ~/.cursor/scripts/task_manager.py`
> `$SE` = `python ~/.cursor/scripts/spec-extractor.tool.py`
> `$JIRA` = `python ~/.cursor/scripts/jira.tool.py`
> `$WS` = `python ~/.cursor/scripts/workspace_paths.py`
> All git commands run with `cwd = <PROJECT_ROOT>` (repo). Planning artifacts live under Documents (see `$WS`).

Input: `$ARGUMENTS` — ticket ID, `mine`, spec file path, or empty. Optionally `--in-background`, `--project <slug>`.

Flags:
- `--in-background` — create a git worktree for isolated execution. Default: **off**.
- `--project <slug>` — force Documents project slug when prefixes collide.

This command runs **entirely in foreground**. Do not dispatch background agents.

**Jira credentials**: `~/.cursor/agent-env/.env` → `ATLASSIAN_EMAIL`, `ATLASSIAN_API_TOKEN`, `ATLASSIAN_BASE_URL`.
Never ask the user to paste tokens in chat.

**Artifact root** (canonical):

```text
%USERPROFILE%\Documents\copilot-workspace\<project-slug>\<TICKET>\
  card.md  PRD.md  PROMPT.md  QUALITY.md  meta.json  evidence/
```

Resolve with `$WS ensure <TICKET> --repo <PROJECT_ROOT> [--project <slug>]`.  
Legacy `<PROJECT_ROOT>/docs/tasks/<TICKET>/` is read only as a migration fallback if Documents files are missing.

---

## Step 0 — Detect input mode

| Condition | Input mode |
|-----------|-----------|
| `$ARGUMENTS` looks like a ticket (e.g. `CTR-1200`) | `jira-fetch` — **default** |
| `$ARGUMENTS` is `mine` / `--mine` | `jira-mine` |
| `$ARGUMENTS` is a file path | `spec-file` |
| `$ARGUMENTS` empty AND conversation has raw Jira XML (`<rss` / `<item`) | `xml-paste` — **legacy fallback only** |
| `$ARGUMENTS` looks like a ticket AND user explicitly passed a local-only flag with existing `specs/<TICKET>.md` and no Jira creds | `ticket-file` — local markdown |
| None of the above | Ask for ticket key, `mine`, or (legacy) XML |

Prefer **Jira API** whenever a key is present. Do not require XML.

---

## Step 1 — Extract spec data

### If `jira-mine`:
1. `$JIRA mine --max 30` (and optionally `$JIRA sprint`).
2. Show compact table; ask which key (or stop if list-only).
3. Continue as `jira-fetch`.

### If `jira-fetch`:
1. `$WS ensure <TICKET> --repo <PROJECT_ROOT>`
2. `$JIRA get <TICKET> --markdown --save <ticketDir>/card.md`  
   Also mirror to `<PROJECT_ROOT>/specs/<TICKET>.md` for `$TM` / repo convenience.
3. On `error` → **stop** (remind agent-env on auth failures).
4. Run `$SE` on saved markdown when possible; if extractor needs XML and fails, use `issue.summary` + `markdown` from `$JIRA get` and continue.
5. Store `jiraUpdated` from `issue.updated` for meta later.
6. Continue to Step 2.

### If `xml-paste` (legacy):
1. Save validated XML to `<PROJECT_ROOT>/specs/<TICKET>.md` and copy summary markdown into `<ticketDir>/card.md`.
2. `$SE --xml "<xml_content>"`
3. Continue to Step 2.

### If `ticket-file` or `spec-file`:
1. Read markdown/XML from the file.
2. Prefer `$SE`; if `source: jira-api` frontmatter, treat body as spec without XML.
3. Continue to Step 2.

### Validate extractor output:
- `success: false` → **stop**.
- Empty `key` → **stop**.
- Empty `acceptance_criteria` → warn, continue.

Store: `key`, `type`, `summary`, `acceptance_criteria`, `test_cases`, `dod`, `jiraUpdated` (if any).

---

## Step 2 — IDEMPOTENCY_GUARD ⛔

```bash
$WS resolve <TICKET> --repo <PROJECT_ROOT>
# also: $WS is-fresh <TICKET> --jira-updated <jiraUpdated>   when jiraUpdated known
```

If **any** of Documents `PRD.md`, `PROMPT.md`, `QUALITY.md` exists:
1. Show paths + last-modified; if `is-fresh` is true, say interpret is still valid vs Jira.
2. Ask regenerate all / regenerate one / cancel.
3. Wait for choice. Cancel → stop.

If Documents missing but legacy `docs/tasks/<TICKET>/` exists, mention it and offer to regenerate into Documents.

---

## Step 3 — BRANCH_SETUP

### Infer branch name:

| Spec type | Branch prefix | Example |
|-----------|--------------|---------|
| `História` | `us/` | `us/CTR-1200` |
| `Tarefa` / `Sub-tarefa` | `us/task/` | `us/task/CTR-1200` |
| `Bug` / `Hotfix` / `Fix` / `bug` | `bug/` | `bug/CTR-1200` |
| `Chore` | `chore/` | `chore/CTR-1200` |

### If `--in-background` → WORKTREE mode:

```bash
WORKTREE_PATH=../<PROJECT_ROOT_BASENAME>-worktrees/<TICKET>
```

Reuse / recreate / cancel as before. Copy `.env` and `public/config.json` when creating.  
**Code** `PROJECT_ROOT` may become `WORKTREE_PATH`; **Documents paths stay on `$WS`** (never inside the worktree).

### If not `--in-background` → MAIN REPO mode:

Create local branch from `origin/develop` if missing. Documents still via `$WS`.

---

## Step 4 — PM_AMBIGUITY_GATE ⛔ BLOCKING

Unchanged analysis (scope split, missing UI, API contract, UX edges). Show `Ambiguidades restantes: N`.  
Exception: user says "pode assumir" → log under PRD `## Open Assumptions`.

---

## Step 5 — Write PRD

1. `prd_path` from `$WS resolve` → `prd`
2. Ensure layout: `$WS ensure <TICKET>`
3. Prefer `se-product-manager-advisor` when available; else write PRD from spec + resolved ambiguities.

Minimum PRD structure unchanged (Context, Scope, CAs, UX, Assumptions, Out of Scope).

---

## Step 6 — Write PROMPT

1. Read Documents `PRD.md`.
2. Write Documents `PROMPT.md`.
3. Header must reference the **Documents** PRD path from `$WS`.
4. Include branch, optional worktree path, impacted files, steps, tests, mocks, open questions.

---

## Step 7 — Write QUALITY

1. Prefer `qa-subagent` with Documents `prd` / `quality` paths; else write QUALITY from PRD.
2. Include CAs, CTs, DoD, traceability, gaps.

---

## Step 8 — Register meta + index

```bash
$WS write-meta <TICKET> --jira-updated <jiraUpdated> --repo <PROJECT_ROOT>
```

If `jiraUpdated` unknown (XML-only), still write meta with empty/omitted update and note source.

Optional `$TM` registration (paths point to Documents artifacts):

```bash
$TM add --spec <PROJECT_ROOT>/specs/<TICKET>.md --ticket <key> --type <type>
$TM set-field <id> prompt <prompt_path>
$TM set-field <id> quality <quality_path>
$TM set-field <id> prd <prd_path>
$TM set-field <id> branch <branch_name>
$TM set-status <id> waiting
$TM render-index
```

> Duplicate check: skip `$TM add`, update fields only.

---

## Step 9 — Report

```
✅ /interpret concluído para <TICKET>

  Branch    <branch_name>
  Worktree  <WORKTREE_PATH>   ← only if --in-background
  Workspace <ticketDir>
  PRD       <prd_path>
  PROMPT    <prompt_path>
  QUALITY   <quality_path>
  Status    waiting

Próximo passo: /execute <TICKET>  ou  /dev-day start <TICKET>
```

---

## Safety rules

- Never generate artifacts from memory — read PRD before PROMPT/QUALITY.
- Never overwrite without IDEMPOTENCY_GUARD.
- Never create worktree from a branch other than `origin/develop`.
- Never proceed if `$SE` returns `success: false` when XML mode required it.
- Never infer missing API contracts silently — ask in AMBIGUITY_GATE.
- Prefer Jira over XML; do not ask for XML when a key + credentials work.
