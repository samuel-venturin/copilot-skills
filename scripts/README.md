# Shared scripts for Cursor / Copilot skills

Bundled so `npx github:samuel-venturin/copilot-skills install-cursor` works
without a pre-existing `~/.claude/scripts` folder.

Installed to `~/.cursor/scripts` by `install-cursor.js`.

| Script | Purpose |
|---|---|
| `task_manager.py` | Task queue index for interpret/execute |
| `spec-extractor.tool.py` | Extract fields from Jira XML / markdown specs |
| `jira_client.py` | Shared Jira Cloud client (reads `~/.cursor/agent-env/.env`) |
| `jira.tool.py` | CLI: myself, mine, sprint, get, search, transitions, transition, comment, attach |
| `workspace_paths.py` | Documents/copilot-workspace path helpers (ensure, resolve, meta, evidence) |

## Jira quick start

```powershell
python ~/.cursor/scripts/jira.tool.py myself
python ~/.cursor/scripts/jira.tool.py mine
python ~/.cursor/scripts/jira.tool.py sprint
python ~/.cursor/scripts/jira.tool.py get CTR-1234 --markdown --save ./specs/CTR-1234.md
python ~/.cursor/scripts/jira.tool.py transitions CTR-1234
python ~/.cursor/scripts/jira.tool.py transition CTR-1234 --to "In Development" --dry-run
python ~/.cursor/scripts/jira.tool.py comment CTR-1234 --body "Evidências anexadas."
python ~/.cursor/scripts/jira.tool.py attach CTR-1234 --files a.png,b.png
```

## Workspace quick start

```powershell
python ~/.cursor/scripts/workspace_paths.py root
python ~/.cursor/scripts/workspace_paths.py ensure CTR-1234 --repo C:\path\to\repo
python ~/.cursor/scripts/workspace_paths.py write-meta CTR-1234 --jira-updated "2026-01-01T00:00:00.000+0000" --repo C:\path\to\repo
```

Credentials live in `~/.cursor/agent-env/.env` — never commit tokens.
