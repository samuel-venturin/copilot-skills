---
name: qa-test-tutorial
description: Writes a manual QA test tutorial for an already-implemented ticket/feature and, by default, immediately executes it end-to-end with playwright-cli against the real dev environment, capturing screenshot evidence to attach to the Jira US.
---

# QA Test Tutorial Skill

Use this as the single skill whenever the user asks for a manual test tutorial/roteiro for a
ticket or feature that has **already been implemented and merged** (not a plan for future work).
Typical triggers (PT-BR): "faz um tutorial de como testar", "como o QA pode testar isso", "passo a
passo de teste manual", "gera o roteiro de teste pro QA", "escreve como se fosse um tutorial".

This skill has **two phases that always run back-to-back by default** — Phase A (write) and
Phase B (execute + evidence). Do not stop after Phase A waiting for a second request; only skip
Phase B if the dev environment is unreachable or the user explicitly asks for text only (e.g. "só
escreve o tutorial, não precisa rodar agora").

## Non-negotiable security rule (applies to both phases, especially Phase B)

**Never type, read, log, or store a password, token, or any credential — for any user, in any
step.** All SSO/login steps must be completed manually by the human, in the browser window opened
by `playwright-cli`. The skill only drives the browser **after** the human confirms the session is
authenticated. This rule cannot be relaxed by convenience.

## Phase A — Write the tutorial

### Mandatory investigation before writing a single line

1. **Identify the ticket.** Use the current branch name, `specs/<TICKET>.md` (present in most
   repos), or ask the user if ambiguous.
2. **Confirm the real, shipped implementation** — read git log/diff and merged PRs in every
   repository involved. **Never** base the tutorial only on planning docs
   (`docs/tasks/<TICKET>/PRD.md`, `PROMPT.md`) — these are frequently stale relative to what
   actually shipped (confirmed pattern in this codebase: CTR-1616's docs described a superseded
   Kafka-contract approach that was never implemented).
3. **Locate every real entry point** via grep/view in the source code — never invent or assume:
   - UI button labels, field names, dialog copy (e.g. confirmed via
     `TaskDetailsDialog.vue`: "Aprovar"/"Recusar", a required "Observações" field on reject only).
   - API endpoints/DTOs (controllers).
   - **Dev environment URLs** — this ecosystem follows the convention
     `https://<repo-name>.dev.scansource.com.br` (e.g. `customers-manager-ui.dev.scansource.com.br`,
     `tasks-manager-ui.dev.scansource.com.br`). Confirm each URL from `public/config.json` or repo
     docs before using it — never guess a URL without at least one supporting reference.
4. Cover, whenever applicable: the main happy path, relevant variations (with/without an optional
   field, different document/veredict types, etc.), and at least one negative/guard case (who
   should NOT be affected, a state that should NOT trigger the behavior).

### Fixed output format

1. Title: `Tutorial: Testando a <funcionalidade> (<TICKET>)`.
2. Section "O que você vai testar" — one paragraph, plain language.
3. Section "Antes de começar" — prerequisites: how many test users/roles are needed, what access
   each one needs, which environment.
4. Numbered steps (`## Passo N — <título>`), each with sub-steps and a closing line
   `✅ **Resultado esperado**: ...`.
5. Negative/guard cases, in the same step format.
6. Optional section "Verificação técnica" (DevTools/logs) when it adds real value.
7. Closing note for any non-obvious behavior (e.g. a precondition that causes silent no-op rather
   than an error).

### Anti-hallucination rule

Every button label, field name, endpoint, message, or URL quoted in the tutorial must have been
confirmed by grep/view against the real code in this run (or reused from an already-validated
investigation earlier in the same session). Never assume a label by convention alone.

## Phase B — Execute the tutorial and capture evidence (always, by default)

As soon as Phase A produces the tutorial, immediately continue into Phase B using that same
tutorial as the execution script. Do not wait for a separate request.

### Steps

1. **Discover/confirm the test users the tutorial needs** (however many roles it requires — e.g.
   2 for CTR-1616: a requester and an approver/analyst). Use the **Applications Manager**
   (`applications-manager-ui`, real dev environment — not the local Keycloak seed some repos ship
   under `keycloak/realm.json`, which is local-only and unrelated to dev) to locate existing users
   in the right group, or — with the user's explicit confirmation — create new ones. The skill may
   fill non-sensitive fields (name, email, group) but must never set/see a password; the human sets
   credentials directly in the browser if a user needs to be created.
2. **Open one named `playwright-cli` session per user/role** (e.g. `-s=userA`, `-s=userB`) at the
   dev URLs identified in Phase A.
3. **Pause and ask the human to complete SSO login manually** in each opened window before the
   skill drives any further interaction in that session. Confirm the authenticated state (e.g. via
   `playwright-cli snapshot`) before proceeding.
4. **Execute every step of the Phase A tutorial, in order**, taking a
   `playwright-cli screenshot --filename=...` at each "✅ Resultado esperado" checkpoint (and at any
   other transition worth documenting).
5. **Save all screenshots directly under the user's `Documents` folder**, never only in the
   session workspace — the session workspace (`files/<TICKET>-evidencias/`) is temporary/hard to
   find, and the user should never have to go hunting for the evidence. Use:
   `$env:USERPROFILE\Documents\<TICKET>-evidencias\` (Windows) — resolve `$env:USERPROFILE`
   explicitly, never hardcode a username. Use sequential, descriptive filenames that mirror the
   tutorial steps (e.g. `01-solicitacao-enviada.png`, `02-task-recusada.png`,
   `03-notificacao-sino.png`). If a prior/partial run already left evidence in the session
   workspace, copy or move it into this same `Documents` folder so everything ends up in one place.
   When redoing a run to fix incorrect evidence, keep any genuinely historical/investigation
   screenshots (e.g. proving a bug that was later fixed) in a clearly named subfolder (e.g.
   `historico-investigacao-<assunto>/`) so they aren't confused with the current, correct evidence.
6. **Hand the final file list to the user** at the end, with the full `Documents` path spelled out,
   ready to attach manually to the Jira US — this skill has no direct Jira access to attach files
   itself.

### When to skip Phase B

Only when the dev environment/URLs are not reachable (e.g. no VPN), or the user explicitly asks for
the tutorial text only. In either case, say so explicitly instead of silently skipping it.

### Risks to flag during Phase B

- If a test user has no email configured in Keycloak, email/notification-dependent behavior will
  silently no-op — verify this before relying on it as a test signal.
- SSO session cookies expire; if a step fails due to an expired session, ask the human to redo the
  manual login for that specific session before retrying.
- If the tutorial depends on additional seed data beyond the test users (e.g. a specific pending
  record), flag this during Phase A so it can be prepared before Phase B starts.
