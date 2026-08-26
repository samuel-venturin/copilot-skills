# Copilot Skills

Personal collection of [GitHub Copilot CLI](https://github.com/github/copilot-cli) skills used across projects.

This repository mirrors the skills normally kept in `~/.copilot/skills/`.

## Skills

| Skill | Description |
|---|---|
| `commit-changes` | Commit changes using atomic commits following a defined commit convention. Runs required checks, stages selectively, and creates well-formed commits. Never pushes automatically. |
| `execute` | Execute a planned task end-to-end, using specific sub-skills for each step of the workflow (setup, tdd-red, implementation, code-review, qa-validation, approve, transition, validate). |
| `ideas-notes` | Consult and update persistent idea notes for automation/testing workflows. |
| `interpret` | Interpret a Jira spec and produce planning artifacts — PRD, PROMPT, QUALITY. |
| `local-stack` | Manage a local development stack (start/stop/restart/reset/logs) across infra, domain, tasks, bff, and frontend services. |
| `playwright-cli` | Automate browser interactions for web testing, form filling, screenshots, and data extraction. |
| `pr-maestro` | Single-entry PR automation using Python tools for tagging, PR creation, and template application. |
| `refactor` | Single-entry refactoring automation with Python tools for code analysis, spec generation, and guided refactoring (dead code removal, simplification, naming, clean code, pattern conformance). |
| `release-maestro` | Single-entry release automation for tag recommendation, tag creation, release notes generation, and release create/update. |
| `tasks` | Manage a task queue — list, next, inspect, set dependencies, and transition status. |
| `testid-extractor` | Extract `data-testid` attributes from pages and generate a reference map for E2E tests. |
| `update-error-catalog` | Sync error codes from a backend error catalog to frontend i18n localization files. |

## Usage

Clone or copy the contents of this repo into your local `~/.copilot/skills/` directory (or your agent's equivalent skills folder) to make these skills available.

```powershell
git clone https://github.com/samuel-venturin/copilot-skills.git
Copy-Item .\copilot-skills\* -Destination "$env:USERPROFILE\.copilot\skills" -Recurse -Force
```

## Notes

- Some skills (`local-stack`, `pr-maestro`, `release-maestro`, `refactor`, `testid-extractor`) include `tools/config.json` files with local paths and project-specific settings. Review and adjust these before reuse in a different environment.
- Runtime artifacts (logs, `__pycache__`, cached state) are excluded via `.gitignore` and are not versioned.
- This repository is personal and independent of any employer's GitHub organization.
