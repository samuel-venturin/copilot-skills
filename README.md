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

## Install (first time on a new machine)

Requires [Node.js](https://nodejs.org) ≥ 18 (no other dependencies are installed).

**Option A — no clone needed:**

```powershell
npx github:samuel-venturin/copilot-skills
```

**Option B — clone first, then run the installer:**

```powershell
git clone https://github.com/samuel-venturin/copilot-skills.git
cd copilot-skills
node install.js
```

Both copy every skill into `~/.copilot/skills` (or `%USERPROFILE%\.copilot\skills` on Windows).
If a skill with the same name already exists there, it is backed up automatically
(`~/.copilot/skills/_backup_<timestamp>/<skill>`) before being replaced — nothing is
silently overwritten.

After copying the skills, the installer checks whether the core CLIs the skills
depend on are on `PATH`: **`gh`, `copilot`, `python`, `dotnet`, `pnpm`**. If any are
missing, it asks for permission before installing anything:

```
Missing tools: GitHub CLI (gh), Python (python/python3)
Install them now? [y/N]
```

- Answer `y` (or pass `--yes`/`-y` up front) and it installs the missing ones for you:
  - `gh` → `winget`/`choco` (Windows), `brew` (macOS/Linux), `apt-get`/`dnf` (Linux)
  - `copilot` → `npm install -g @github/copilot`
  - `python` → `winget`/`choco`/`brew`/`apt-get`/`dnf` depending on platform
  - `dotnet` → `winget`/`choco`/`brew`/`apt-get`/`dnf` depending on platform
  - `pnpm` → `npm install -g pnpm`
- Answer `n` (or run non-interactively without `--yes`) and it just prints the manual install
  links, without touching your system.
- Pass `--no-tools` to skip this step entirely.

**`wsl` is intentionally excluded** — it's only used by `local-stack` and stays 100%
optional; the installer never prompts for it or installs it.

It also prints an informational checklist of the other per-skill prerequisite tools
(`git`, `node`, `wsl`, ...) — these are only reported, never auto-installed.

Useful flags:

```powershell
node install.js --dry-run                  # preview without changing anything
node install.js --only local-stack,tasks   # install just specific skills
node install.js --target C:\custom\path    # install somewhere other than ~/.copilot/skills
node install.js --force                    # overwrite in place, no backup
node install.js --skip-existing            # never touch a skill that's already installed
node install.js --yes                      # auto-confirm installing missing core CLIs
node install.js --no-tools                 # never offer to install core CLIs
node install.js --help
```

## Manual copy (alternative)

If you prefer not to run any script:

```powershell
git clone https://github.com/samuel-venturin/copilot-skills.git
Copy-Item .\copilot-skills\* -Destination "$env:USERPROFILE\.copilot\skills" -Recurse -Force -Exclude install.js,package.json,README.md,.gitignore
```

## Notes

- Some skills (`local-stack`, `pr-maestro`, `release-maestro`, `refactor`, `testid-extractor`) include `tools/config.json` files with local paths and project-specific settings. Review and adjust these before reuse in a different environment.
- Runtime artifacts (logs, `__pycache__`, cached state) are excluded via `.gitignore` and are not versioned.
- This repository is personal and independent of any employer's GitHub organization.
