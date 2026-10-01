# Shared scripts for Cursor / Copilot skills

Bundled so `npx github:samuel-venturin/copilot-skills install-cursor` works
without a pre-existing `~/.claude/scripts` folder.

Installed to `~/.cursor/scripts` by `install-cursor.js`.

| Script | Purpose |
|---|---|
| `task_manager.py` | Task queue index for interpret/execute |
| `spec-extractor.tool.py` | Extract fields from Jira XML / markdown specs |
| `jira_client.py` | Shared Jira Cloud client (reads `~/.cursor/agent-env/.env`) |
| `jira.tool.py` | CLI: `myself`, `mine`, `get <KEY>`, `search --jql ...` |

## Jira quick start

```powershell
python ~/.cursor/scripts/jira.tool.py myself
python ~/.cursor/scripts/jira.tool.py mine
python ~/.cursor/scripts/jira.tool.py get CTR-1234 --markdown --save ./specs/CTR-1234.md
```

Credentials live in `~/.cursor/agent-env/.env` — never commit tokens.
