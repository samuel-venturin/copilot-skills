---
name: release-maestro
description: Single-entry release automation using Python tools for tag recommendation, tag creation, release notes generation and create/update release.
---

# Release Maestro Skill

Use this as the single skill for release automation when the user asks to:
- automate tag + release flow end-to-end;
- infer bump type from merged PR titles;
- create or update release in an idempotent workflow.

## Runtime model

All logic runs through Python scripts in:
- `~/.claude/skills/release-maestro/tools`

Central configuration lives in:
- `~/.claude/skills/release-maestro/tools/config.json`

`release_maestro.py` is the main entrypoint.

## Mandatory template

Release notes must always be rendered from:
- `~/.claude/skills/release-maestro/templates/TEMPALTE.md`

All placeholders in that template must be filled with real data collected during execution.
Do not publish release notes using an alternative template path when this file is available.

## Tools

- `release_maestro.py`: end-to-end orchestrator (recommended entrypoint)
- `tag_from_prs.py`: standalone Python tool to infer and optionally create a semantic tag from PR types in the release window

## Execution model (two-phase)

Phase 1 (analysis / suggestion):

```bash
python3 ~/.claude/skills/release-maestro/tools/release_maestro.py --base develop
```

Expected output status: `needs_confirmation` with:
- PR type distribution in the window since last tag;
- suggested bump;
- next tag candidate;
- proposed release title.

Phase 2 (confirmed execution):

```bash
python3 ~/.claude/skills/release-maestro/tools/release_maestro.py \
  --base develop \
  --bump minor \
  --title "v1.2.3 - clear release summary" \
  --confirm
```

## Bump policy

- FEAT-dominant PR set: suggest `minor`.
- Non-FEAT dominant PR set: suggest `patch`.
- Tie between top PR types: suggest `minor`.
- No merged PRs in release window: block execution.
- `major`/breaking must be explicitly chosen by user.

## Release behavior

- Generates release notes from `~/.claude/skills/release-maestro/templates/TEMPALTE.md`.
- Uses `.github/scripts/release-data.sh` and `.github/scripts/release-coverage.sh` as data sources.
- Creates release when missing, updates release when tag release already exists.

## Safety rules

- Never create/push tag without explicit confirmation (`--confirm`).
- Never publish release without explicit confirmation (`--confirm`).
- Never fabricate PR, commit, coverage, or release metrics.
- Keep output machine-readable (JSON) for deterministic chaining.
