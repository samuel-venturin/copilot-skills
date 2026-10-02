---
name: fix-evidence
description: Capture ordered success-evidence screenshots for an implemented ticket (playwright-cli or Cursor browser), save named PNGs under Documents/copilot-workspace, and optionally upload them to Jira in order. Runs after execute and before qa-test-tutorial.
---

# /fix-evidence — Success evidence for a fix/feature

> `$JIRA` = `python ~/.cursor/scripts/jira.tool.py`
> `$WS` = `python ~/.cursor/scripts/workspace_paths.py`
> Browser driver: **`playwright-cli` by default**; Cursor integrated browser is an equivalent fallback (same contract: navigate → pause on SSO → interact → screenshot).

Use this skill when the user (or `dev-day`) asks to **prove the correction works**, capture screenshots, and attach them to the Jira card — **before** `/qa-test-tutorial`.

Input: `$ARGUMENTS` — issue key (e.g. `CTR-1851`). Optional `--project <slug>`, `--no-publish`.

## Non-negotiable security rule

**Never type, read, log, or store a password, token, or any credential.** SSO/login is completed manually by the human. Drive the browser only after the human confirms the session is authenticated.

## Responsibility boundary

| Skill | Owns |
|-------|------|
| `fix-evidence` | Happy-path success proof + named PNGs + optional ordered Jira `attach` + short comment |
| `qa-test-tutorial` | Full QA manual tutorial (write + optional re-run). Does **not** own correction-evidence upload |

---

## Step 0 — Resolve ticket + workspace

1. Require a ticket key in `$ARGUMENTS`. If missing, ask for it.
2. Resolve paths:
   ```bash
   $WS ensure <TICKET> [--project <slug>] [--repo <PROJECT_ROOT>]
   ```
3. Prefer acceptance criteria from:
   - `$WS resolve` → `quality` (`QUALITY.md`) when present
   - else git diff / merged PR for what actually shipped
   - **Do not** trust stale PRD alone
4. Confirm UI entry points and **dev URL** from code/`public/config.json` (same convention as qa-test-tutorial: `https://<repo>.dev.scansource.com.br` when applicable).

---

## Step 1 — Happy-path only

Build a **short success script** (not the full QA tutorial):

- Only the primary happy path that proves the fix/feature works.
- Numbered milestones suitable for screenshots (aim 3–8 shots).
- Skip exhaustive negative/guard cases (those belong in `qa-test-tutorial`).

For each milestone define:

- `NN` — `01`, `02`, …
- `slug` — kebab-case short label (e.g. `lista`, `detalhe-aprovado`)
- Expected success signal visible on screen

---

## Step 2 — Browser session

1. Open the app with `playwright-cli` (or Cursor browser).
2. **Pause** and ask the user to complete SSO; wait for explicit confirmation.
3. Confirm authenticated state via snapshot before continuing.
4. Execute milestones in order. On each success checkpoint:
   - Take a screenshot
   - Save under the evidence dir from `$WS evidence-dir <TICKET>`:
     ```text
     {TICKET}-evidencia-{NN}-{slug}.png
     ```
     Example: `CTR-1851-evidencia-01-lista.png`
5. If a milestone **fails**:
   - Stop the success pipeline
   - Report what failed + optional failure screenshot named `…-FALHA-…png` (not uploaded as “correção ok”)
   - **Do not** call Jira `attach` / success comment

---

## Step 3 — Write `manifest.json`

After all success shots are saved, write:

```json
{
  "ticket": "<TICKET>",
  "createdAt": "<ISO-8601>",
  "entries": [
    {
      "order": 1,
      "filename": "<TICKET>-evidencia-01-<slug>.png",
      "path": "<absolute-path>",
      "title": "<short caption>",
      "capturedAt": "<ISO-8601>"
    }
  ]
}
```

Path: `<ticketDir>/evidence/manifest.json` (from `$WS resolve`).

Show the user the ordered file list with full paths.

---

## Step 4 — Publish to Jira (ask first)

Unless `--no-publish` was passed:

> "Evidências de sucesso salvas em `<evidenceDir>`. Publicar no Jira `<TICKET>` agora? (sim/não)"

If **no** → stop after local save; return paths.

If **yes**:

1. Build comma-separated file list **in manifest order**:
   ```bash
   $JIRA attach <TICKET> --files path1.png,path2.png,...
   ```
2. Post a short comment:
   ```text
   Evidências de sucesso — correção validada

   1. <filename> — <title>
   2. ...
   ```
   via `$JIRA comment <TICKET> --body-file <temp.txt>` (or `--body`).

3. Report attachment IDs + browse URL from tool JSON.

---

## Step 5 — Handoff

Return a compact summary for `dev-day` / the user:

```json
{
  "ticket": "<TICKET>",
  "evidenceDir": "<path>",
  "manifest": "<path>",
  "files": ["..."],
  "published": true|false,
  "attachments": []
}
```

Next suggested step: `/qa-test-tutorial <TICKET>` or `dev-day tutorial <TICKET>`.

---

## Safety rules

- Never upload on failure.
- Never invent UI labels — confirm from code or live UI.
- Never put secrets in screenshots captions/comments.
- Prefer renaming/moving screenshots into the evidence dir over leaving them only in session temp folders.
