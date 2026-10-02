---
name: qa-test-tutorial
description: Writes a manual QA test tutorial for an already-implemented ticket/feature and, by default, executes it with playwright-cli against the real dev environment. Correction-evidence upload to Jira is owned by fix-evidence (run that skill before this one).
---

# QA Test Tutorial Skill

Use this whenever the user asks for a manual QA tutorial/roteiro for a ticket/feature that has
**already been implemented**. Typical triggers (PT-BR): "faz um tutorial de como testar", "como o
QA pode testar isso", "passo a passo de teste manual", "gera o roteiro de teste pro QA".

**Preferred order with `dev-day`:** run **`fix-evidence` first** (success PNGs + optional Jira
attach), then this skill for the full QA tutorial.

This skill has **two phases that always run back-to-back by default** — Phase A (write) and
Phase B (execute + local screenshots). Skip Phase B only if the env is unreachable or the user
asks for text only.

## Ownership boundary

| Concern | Owner |
|---------|--------|
| Happy-path success proof + ordered Jira attach of correction evidence | **`fix-evidence`** |
| Full QA tutorial text + optional local tutorial screenshots | **`qa-test-tutorial`** (this skill) |

This skill **must not** call `$JIRA attach` / publish correction evidence. If the user asks to
upload fix screenshots to Jira, redirect them to `/fix-evidence` or `/dev-day evidence`.

## Non-negotiable security rule

**Never type, read, log, or store a password, token, or any credential.** SSO is completed
manually by the human. Drive the browser only after they confirm authentication.

## Phase A — Write the tutorial

### Mandatory investigation before writing a single line

1. **Identify the ticket.** Branch name, `specs/<TICKET>.md`, or ask.
2. **Confirm the real, shipped implementation** — git log/diff and merged PRs. **Never** base the
   tutorial only on planning docs (`Documents/copilot-workspace/.../PRD.md` or legacy
   `docs/tasks/<TICKET>/PRD.md`) — they are frequently stale vs what shipped.
3. **Locate every real entry point** via grep/view — never invent labels, endpoints, or URLs.
   Dev URL convention: `https://<repo-name>.dev.scansource.com.br` — confirm via
   `public/config.json` or docs.
4. Cover happy path, relevant variations, and at least one negative/guard case.

### Fixed output format

1. Title: `Tutorial: Testando a <funcionalidade> (<TICKET>)`.
2. "O que você vai testar" — one paragraph.
3. "Antes de começar" — users/roles/env.
4. Numbered steps (`## Passo N — <título>`) ending with `✅ **Resultado esperado**: ...`.
5. Negative/guard cases.
6. Optional "Verificação técnica".
7. Closing notes for non-obvious behavior.

### Anti-hallucination rule

Every quoted label, field, endpoint, message, or URL must be confirmed from code (or validated UI)
in this run.

## Phase B — Execute the tutorial (local evidence)

Continue from Phase A by default.

1. Discover/confirm test users (Applications Manager on **dev**, not local Keycloak seed). Never
   set/see passwords.
2. Open named `playwright-cli` sessions per role at confirmed URLs.
3. Pause for manual SSO; confirm via snapshot before driving.
4. Execute tutorial steps; screenshot at each "✅ Resultado esperado".
5. Save screenshots under Documents. Prefer the workspace evidence area when present:
   ```bash
   python ~/.cursor/scripts/workspace_paths.py evidence-dir <TICKET> --repo <PROJECT_ROOT>
   ```
   Use a subfolder `tutorial/` under that dir (e.g. `…/evidence/tutorial/01-….png`) so tutorial
   shots are not confused with `fix-evidence` files named `{TICKET}-evidencia-NN-….png`.
   Fallback: `%USERPROFILE%\Documents\<TICKET>-evidencias\tutorial\`.
6. Hand the final file list to the user. **Do not** upload to Jira from this skill. For
   correction-evidence publish, point to `/fix-evidence`.

### When to skip Phase B

Only when env/URLs unreachable or user asks for text only — say so explicitly.

### Risks to flag

- Users without email in IdP → notification paths may silently no-op.
- SSO cookies expire — re-auth before retry.
- Extra seed data needed → flag in Phase A.
