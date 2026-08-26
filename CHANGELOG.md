# Changelog

All notable changes to this repository are documented here. Versions follow
`package.json`'s `version` field. `update.js` reads this file to print a
summary of what's new whenever you update.

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
