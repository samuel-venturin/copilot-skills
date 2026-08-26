---
name: local-stack
description: "Gerencia a stack local de desenvolvimento. Invocado com /local-stack [comando] [servico]. Comandos: status, start, stop, restart, reset, logs. Servicos: infra, domain, tasks, bff, frontend."
---

# Local Stack Skill

## Trigger

This skill is invoked when the user types `/local-stack` followed by an optional command and service name.

```
/local-stack               -> status (default)
/local-stack status        -> show all services
/local-stack start         -> start all services in order
/local-stack start bff     -> start one service
/local-stack stop          -> stop all services
/local-stack stop frontend -> stop one service
/local-stack restart bff   -> stop + start (use after code change)
/local-stack reset domain  -> stop + clear log + start
/local-stack logs bff      -> last 50 lines of logs
/local-stack logs bff 100  -> last N lines
```

## Agent dispatch instructions

**Step 1 - Parse the user message** to extract command and optional service:

| User says | command | service arg |
|-----------|---------|-------------|
| `/local-stack` | `status` | (none) |
| `/local-stack status` | `status` | (none) |
| `/local-stack start` | `start` | (none) |
| `/local-stack start bff` | `start` | `bff` |
| `/local-stack stop` | `stop` | (none) |
| `/local-stack stop bff` | `stop` | `bff` |
| `/local-stack restart domain` | `restart` | `domain` |
| `/local-stack reset domain` | `reset` | `domain` |
| `/local-stack logs bff` | `logs` | `bff` |
| `/local-stack logs bff 100` | `logs` | `bff --lines 100` |

**Step 2 - Build and run the command via powershell:**

```
SCRIPT = <this skill's directory>\tools\local_stack.py   # e.g. ~/.copilot/skills/local-stack/tools/local_stack.py

python <SCRIPT> <command> [service] [--lines N]
```

- Use `initial_wait: 120` for start / restart / reset
- Use `initial_wait: 15` for status / stop / logs

**Step 3 - Relay the output as-is.** The script formats its own output.

## Services

| Name | Type | Port | Optional | Environment |
|------|------|------|----------|-------------|
| `infra` | Docker/WSL (MongoDB) | 27017 | **Yes** (domain/bff use remote DB via Azure) | — |
| `domain` | .NET | 5000 | No | `Development` + Azure App Config (from launch.json) |
| `tasks` | .NET | 6000 | Yes | `Local` + `ASPNETCORE_URLS=http://+:8082` (from launch.json) |
| `bff` | .NET | 7000 | No | `Development` + Azure App Config (from launch.json) |
| `frontend` | pnpm | 3000 | No | — |

Start order: `infra -> domain -> tasks -> bff -> frontend`

## Path auto-discovery

`base_dir` (folder containing all sibling project repos) and `wsl_home` (WSL user home,
used to build `compose_dir` for the `infra` service) are **auto-discovered at runtime** —
no machine-specific absolute paths are hardcoded in `config.json`.

Resolution order for both:
1. Env var override (`LOCAL_STACK_BASE_DIR`, `LOCAL_STACK_WSL_HOME`)
2. Explicit value in `config.json` (`base_dir`, `wsl_home`)
3. Cached value in `tools/resolved_env.json` (created on first successful discovery, gitignored)
4. Auto-scan: `base_dir` is found by checking `base_dir_search_roots` in `config.json`
   (e.g. `~/Documents/GitHub`, `~/GitHub`, `~/repos`, ...) for a folder containing all
   project directories referenced by the configured services. `wsl_home` is resolved via
   `wsl -- bash -c "echo $HOME"`.

If auto-discovery fails (e.g. repos live outside all search roots), set `LOCAL_STACK_BASE_DIR`
env var or add the correct path directly to `config.json`.

## Notes

- `tasks` is optional - may fail locally due to missing config, that is expected
- `infra` is optional - domain and bff connect to remote MongoDB via Azure App Configuration; start infra only if you need a local MongoDB (e.g. for the `tasks` service or local seeding)
- Env vars are loaded from each service's `.vscode/launch.json` automatically; `config.json "env"` acts as an explicit override with highest priority
- `frontend` requires `public/config.json` with `BASE_URL: http://localhost:7000`
- Logs: `<this skill's directory>\logs\<service>.log`
- State/PIDs: `<this skill's directory>\tools\state.json`
- **Prerequisite**: internet/VPN access to `app-configuration-zeusdev-001.azconfig.io` for domain and bff
