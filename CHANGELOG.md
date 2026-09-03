# Changelog

All notable changes to this repository are documented here. Versions follow
`package.json`'s `version` field. `update.js` reads this file to print a
summary of what's new whenever you update.

## [1.2.1]

- Fix: `update`, `uninstall`, and `schedule-check` now work via a plain
  `npx github:samuel-venturin/copilot-skills <subcommand>` invocation, with
  no clone required. Previously only `install` was reachable this way
  because `npx github:owner/repo` always resolves to the bin matching
  `package.json`'s `name` (`install.js`), so any extra arguments were just
  passed through to the installer and ignored. `install.js` now inspects its
  first positional argument and, if it matches `update`, `uninstall`, or
  `schedule-check`, dispatches to the matching sibling script instead
  (forwarding all remaining flags unchanged). An explicit `install` keyword
  is accepted as a no-op alias for the default install flow. Cloning the
  repo and running the scripts directly still works exactly as before.
- Add the missing `qa-test-tutorial` entry to `install.js`'s informational
  prerequisite-tools table (it depends on `playwright-cli`'s own tools,
  `node`/`npx`), which was left out when the skill was added in 1.2.0.

## [1.2.0]

- Add new skill `qa-test-tutorial`: writes a manual QA test tutorial for an
  already-implemented ticket and, by default, immediately executes it
  end-to-end with `playwright-cli` against the real dev environment.
  Evidence screenshots are always saved directly under the user's
  `Documents\<TICKET>-evidencias\` folder (never left only in a hard-to-find
  temporary/session location), and reruns keep prior investigation
  screenshots in a clearly named `historico-*` subfolder instead of mixing
  them with current evidence.
- `pr-maestro` now supports an optional `--how-to-test-file` argument (on
  both PR creation and template re-apply) that injects a "🧭 Como testar
  manualmente" section into the generated PR body, right before the
  checklist — intended to be filled from a `qa-test-tutorial` run.

## [1.1.0]

- Add `update.js`: updates all installed skills to the latest version and
  prints a summary of what changed.
- Add `schedule-check.js`: registers a daily background check (Task
  Scheduler on Windows, launchd on macOS, cron on Linux) that lets you know
  when a new version is available, without installing anything automatically.
- `install.js` now writes a manifest (`.copilot-skills-manifest.json`) in the
  target directory recording the installed version, timestamp, and skill list.

## [1.0.0]

- Add `uninstall.js`: removes skills previously installed by `install.js`,
  with `--dry-run`, `--only`, `--all`, `--yes`, `--keep-backups` flags.
- Add a `Contributing` section to the README documenting the `develop` →
  `main` branch-protected workflow.
- `install.js` now offers to auto-install missing core CLIs the skills
  depend on (`gh`, `copilot`, `python`, `dotnet`, `pnpm`) with the user's
  explicit consent — `wsl` stays fully optional and is never auto-installed.
- Initial zero-dependency Node.js installer (`install.js`), runnable via
  `npx github:samuel-venturin/copilot-skills` or after a manual clone.
- Initial import of the 12 Copilot CLI skills.
