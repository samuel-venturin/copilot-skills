---
id: IDEA-001
name: Playbook CLI test memory framework
description: Persist reusable test playbooks and validation status
applies_to: playwright-cli
status: draft
priority: high
owner: team
created_at: 2026-02-27T12:00:00Z
last_updated: 2026-02-27T12:00:00Z
---

# IDEA-001 — Playbook CLI test memory framework

## Revision Log (newest first)

### 2026-02-27T12:00:00Z — new-idea
#### Context
Need a reusable way for the agent to avoid re-discovering test flows every time.

#### Proposal
Create a test memory framework with:
1. feature index (status and history),
2. playbook per feature (steps + `data-test` selectors),
3. scripts to check existing coverage before running/creating new flow.

#### Expected behavior
- On first test of a feature, auto-create playbook + register in index.
- On next requests, consult index first and reuse existing playbook.
- Keep validation status: `validated`, `needs-improvement`, etc.

#### Acceptance criteria (draft)
- Agent always checks index before testing.
- Agent can generate/update playbook files.
- Agent can update status after each run.
- Evidence path is linked in playbook/index when available.

#### Open questions
- Should this framework live under `.github/skills` or a dedicated `.qa/` folder?
- Should status updates be automatic or confirmed by user each run?
- Should we keep one global index or one per domain (customer, tax, etc.)?

#### Next step
Design v1 file structure and implement a first end-to-end flow for tax exemptions.
