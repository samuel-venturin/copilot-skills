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
| `pr-maestro` | Single-entry PR automation using Python tools for tagging, PR creation, and template application. Supports an optional `--how-to-test-file` to inject a manual-test tutorial into the PR body. |
| `qa-test-tutorial` | Writes a manual QA test tutorial for an already-implemented ticket and, by default, immediately executes it end-to-end with `playwright-cli` against the real dev environment, saving screenshot evidence straight to `Documents/<TICKET>-evidencias/`. |
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

## Uninstall

**Option A — no clone needed:**

```powershell
npx github:samuel-venturin/copilot-skills uninstall
```

**Option B — clone first, then run the script directly:**

```powershell
git clone https://github.com/samuel-venturin/copilot-skills.git
cd copilot-skills
node uninstall.js                          # removes this repo's skills from ~/.copilot/skills
node uninstall.js --dry-run                # preview what would be removed
node uninstall.js --only local-stack,tasks # remove just specific skills
node uninstall.js --target C:\custom\path  # uninstall from a custom target
node uninstall.js --yes                    # skip the confirmation prompt
node uninstall.js --all                    # also remove skills at the target that aren't in this repo
node uninstall.js --keep-backups           # don't delete this repo's _backup_* folders
node uninstall.js --help
```

All the same flags work with the `npx` form too, e.g.
`npx github:samuel-venturin/copilot-skills uninstall --dry-run --only local-stack,tasks`.

By default, `uninstall.js` only removes skill folders that exist in this repository —
any custom skill you added yourself, unrelated to this collection, is left untouched
unless you pass `--all`.

## Updating

Every install writes a small manifest (`.copilot-skills-manifest.json`) inside the
target directory recording the installed version and skill list. `update.js` uses it
to figure out what changed.

**Option A — no clone needed:**

```powershell
npx github:samuel-venturin/copilot-skills update
npx github:samuel-venturin/copilot-skills update --check-only
```

**Option B — clone first, then run the script directly:**

```powershell
git clone https://github.com/samuel-venturin/copilot-skills.git
cd copilot-skills
node update.js                 # check for updates, show what's new, and apply if you confirm
node update.js --check-only    # just report whether an update is available
node update.js --dry-run       # show what would be updated without changing anything
node update.js --yes           # skip the confirmation prompt
node update.js --target C:\custom\path
node update.js --help
```

`update.js` only touches the skills you already have installed (per the manifest) —
it won't add skills you never installed, and it prints the relevant `CHANGELOG.md`
entries (every version newer than the one you had) straight to the terminal before
applying anything.

## Daily update check (optional)

`schedule-check.js` registers a background task that runs once a day and tells you
if a new version is available — it only notifies, it never installs anything on its
own. Uses Task Scheduler on Windows, launchd on macOS, and cron on Linux.

**Option A — no clone needed:**

```powershell
npx github:samuel-venturin/copilot-skills schedule-check
```

**Option B — clone first, then run the script directly:**

```powershell
node schedule-check.js                  # schedule a daily check at 09:00
node schedule-check.js --time 18:30     # pick a different time
node schedule-check.js --target C:\custom\path
node schedule-check.js --remove         # unregister the daily check
node schedule-check.js --help
```

When an update is available you'll see a desktop notification (where supported) and a
line in `~/.copilot/skills-update-check.log`. Run `node update.js` yourself whenever
you're ready to apply it — this never updates anything without you running it.

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

## Contributing

`main` and `develop` are protected — direct pushes are disabled on both, all changes
go through a pull request.

- **`develop`** is the default/integration branch. New skills, fixes, and improvements
  are proposed here first, via a pull request from a feature branch.
- **`main`** always reflects the latest stable, released state. It's only updated via a
  pull request from `develop` (i.e. `develop` → `main`), once changes on `develop` are
  considered stable.

Workflow to propose a change:

```powershell
git clone https://github.com/samuel-venturin/copilot-skills.git
cd copilot-skills
git checkout develop
git checkout -b feature/my-improvement

# ...make your changes...

git add <files>
git commit -m "[FEAT]: describe the change"
git push -u origin feature/my-improvement
gh pr create --base develop --title "[FEAT]: describe the change" --body "..."
```

Then open the pull request against `develop` on GitHub (or via `gh pr create` as above)
and wait for it to be reviewed and merged. Once `develop` is stable, a separate pull
request from `develop` into `main` promotes it to the stable branch.
