#!/usr/bin/env python3
"""
local_stack.py — Gerenciador da stack local de desenvolvimento (ScanSource Brazil)

Usage:
    python local_stack.py status
    python local_stack.py start [service]
    python local_stack.py stop [service]
    python local_stack.py restart <service>
    python local_stack.py logs <service> [--lines N]
    python local_stack.py reset <service>   # stop + clear log + start
"""

import sys
import os
import json
import re
import subprocess
import time
import signal
import socket
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────────
SKILL_DIR = Path(__file__).parent
CONFIG_FILE = SKILL_DIR / "config.json"
STATE_FILE = SKILL_DIR / "state.json"
# Cache for auto-discovered, machine-specific paths (base_dir / wsl_home).
# Never versioned (see .gitignore) — regenerated per machine on first run.
RESOLVED_CACHE_FILE = SKILL_DIR / "resolved_env.json"

with open(CONFIG_FILE) as f:
    CFG = json.load(f)

LOG_DIR = SKILL_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def _load_resolved_cache() -> dict:
    if RESOLVED_CACHE_FILE.exists():
        try:
            return json.loads(RESOLVED_CACHE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_resolved_cache(cache: dict):
    RESOLVED_CACHE_FILE.write_text(json.dumps(cache, indent=2))


def _project_root_names() -> list:
    """Top-level project directory names referenced by dotnet/pnpm services in config.json."""
    names = []
    for svc in CFG.get("services", {}).values():
        if svc.get("type") in ("dotnet", "pnpm"):
            project = svc.get("project", "")
            root = re.split(r"[\\/]", project)[0]
            if root and root not in names:
                names.append(root)
    return names


def discover_base_dir() -> Path:
    """
    Resolve the local folder that contains all sibling project repos.

    Resolution order:
      1. LOCAL_STACK_BASE_DIR env var
      2. Explicit "base_dir" in config.json (manual override)
      3. Cached value in resolved_env.json (from a previous successful discovery)
      4. Auto-scan of "base_dir_search_roots" from config.json, picking the first
         root that contains every project folder referenced by the configured services
    """
    env_override = os.environ.get("LOCAL_STACK_BASE_DIR")
    if env_override and Path(env_override).is_dir():
        return Path(env_override)

    cfg_override = CFG.get("base_dir")
    if cfg_override and Path(cfg_override).is_dir():
        return Path(cfg_override)

    cache = _load_resolved_cache()
    cached = cache.get("base_dir")
    required = _project_root_names()
    if cached and all((Path(cached) / name).is_dir() for name in required):
        return Path(cached)

    for root in CFG.get("base_dir_search_roots", []):
        candidate = Path(os.path.expanduser(root))
        if candidate.is_dir() and all((candidate / name).is_dir() for name in required):
            cache["base_dir"] = str(candidate)
            _save_resolved_cache(cache)
            return candidate

    print(c(RED, "  ✗ Could not auto-discover the projects base directory."))
    print(c(YELLOW, f"    Looked for folders {required} under: {CFG.get('base_dir_search_roots', [])}"))
    print(c(YELLOW, "    Fix: set the LOCAL_STACK_BASE_DIR env var, or the \"base_dir\" field in config.json."))
    sys.exit(1)


def discover_wsl_home() -> str:
    """
    Resolve the WSL user's home directory (used to build compose_dir paths).

    Resolution order:
      1. LOCAL_STACK_WSL_HOME env var
      2. Explicit "wsl_home" in config.json (manual override)
      3. Cached value in resolved_env.json
      4. `wsl -- bash -c "echo $HOME"`
    """
    env_override = os.environ.get("LOCAL_STACK_WSL_HOME")
    if env_override:
        return env_override.rstrip("/")

    cfg_override = CFG.get("wsl_home")
    if cfg_override:
        return cfg_override.rstrip("/")

    cache = _load_resolved_cache()
    if cache.get("wsl_home"):
        return cache["wsl_home"].rstrip("/")

    try:
        r = subprocess.run(["wsl", "--", "bash", "-c", "echo $HOME"],
                            capture_output=True, text=True, timeout=15)
        home = r.stdout.strip()
        if home:
            cache["wsl_home"] = home
            _save_resolved_cache(cache)
            return home.rstrip("/")
    except Exception:
        pass

    print(c(YELLOW, "  [warn] Could not resolve WSL home via `wsl -- echo $HOME`; "
                     "falling back to /root. Set LOCAL_STACK_WSL_HOME to override."))
    return "/root"


BASE_DIR = discover_base_dir()

# Resolve compose_dir for docker-compose-wsl services from wsl_home + *_relative config,
# unless an absolute compose_dir was already provided explicitly (back-compat).
for _svc in CFG.get("services", {}).values():
    if _svc.get("type") == "docker-compose-wsl" and not _svc.get("compose_dir"):
        _relative = _svc.get("compose_dir_relative") or CFG.get("wsl_compose_dir_relative", "")
        if _relative:
            _svc["compose_dir"] = f"{discover_wsl_home()}/{_relative.lstrip('/')}"

# ── Colors ─────────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

def c(color, text): return f"{color}{text}{RESET}"

# ── State ──────────────────────────────────────────────────────────────────────
def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}

def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2))

# ── Process helpers ────────────────────────────────────────────────────────────
def is_pid_alive(pid: int) -> bool:
    """Check if a Windows process with given PID is alive."""
    if pid <= 0:
        return False
    try:
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH", "/FO", "CSV"],
            capture_output=True, text=True, timeout=5
        )
        return str(pid) in result.stdout
    except Exception:
        return False

def kill_pid(pid: int):
    """Kill a Windows process by PID."""
    try:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                       capture_output=True, timeout=10)
    except Exception:
        pass

def is_port_open(port: int) -> bool:
    """Check if a TCP port is listening using socket (tries both IPv4 and IPv6)."""
    for family, addr in [(socket.AF_INET, '127.0.0.1'), (socket.AF_INET6, '::1')]:
        try:
            s = socket.socket(family, socket.SOCK_STREAM)
            s.settimeout(0.5)
            result = s.connect_ex((addr, port))
            s.close()
            if result == 0:
                return True
        except Exception:
            pass
    return False


def http_ok(url: str) -> bool:
    """Return True if URL responds with 2xx."""
    if not url:
        return False
    try:
        req = urllib.request.urlopen(url, timeout=5)
        return req.status < 400
    except Exception:
        return False

# ── launch.json helpers ────────────────────────────────────────────────────────
def _strip_json_comments(text: str) -> str:
    """Strip single-line // comments from JSON5-like files (e.g. .vscode/launch.json)."""
    # Remove // comments that are not inside strings
    result = re.sub(r'(?m)(?<!:)(?<!https)(?<!http)\s*//[^\n]*', '', text)
    return result


def load_launch_json(path: str, workspace_folder: str) -> dict:
    """
    Parse a .vscode/launch.json and return the first configuration's env and cwd.
    Resolves ${workspaceFolder} to workspace_folder.
    Returns {"env": {...}, "cwd": "..."} or {} on failure.
    """
    try:
        raw = Path(path).read_text(encoding="utf-8")
        cleaned = _strip_json_comments(raw)
        data = json.loads(cleaned)
        configs = data.get("configurations", [])
        if not configs:
            return {}
        cfg = configs[0]
        env = cfg.get("env", {})
        cwd = cfg.get("cwd", "")
        # Resolve ${workspaceFolder}
        resolved_env = {k: v.replace("${workspaceFolder}", workspace_folder) for k, v in env.items()}
        resolved_cwd = cwd.replace("${workspaceFolder}", workspace_folder)
        return {"env": resolved_env, "cwd": resolved_cwd}
    except Exception as e:
        print(c(YELLOW, f"  [warn] Could not load launch.json at {path}: {e}"))
        return {}



def wsl_run(cmd: str, capture=True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["wsl", "--", "bash", "-c", cmd],
        capture_output=capture, text=True, timeout=60
    )

def docker_container_running(container: str) -> bool:
    try:
        r = wsl_run(f"docker inspect --format '{{{{.State.Running}}}}' {container} 2>/dev/null")
        return r.stdout.strip() == "true"
    except Exception:
        return False

# ── Service status ─────────────────────────────────────────────────────────────
SERVICE_STATUS_CACHE = {}

def get_service_status(name: str, svc: dict, state: dict) -> str:
    """Returns: running | degraded | stopped | unknown"""
    stype = svc.get("type", "")
    port = svc.get("port")
    health_url = svc.get("health_url")

    if stype == "docker-compose-wsl":
        # Check if mongo container is running
        running = docker_container_running("fullproject-mongo-1")
        return "running" if running else "stopped"

    # Check saved PID
    pid = state.get(name, {}).get("pid", 0)
    pid_alive = is_pid_alive(pid) if pid else False

    # Check port
    port_open = is_port_open(port) if port else None

    if port_open:
        # Port open: if health_url defined, use it to confirm; otherwise, assume running
        if health_url:
            return "running" if http_ok(health_url) else "degraded"
        return "running"

    if pid_alive:
        return "degraded"  # PID alive but port not open yet

    return "stopped"


def status_icon(status: str) -> str:
    return {
        "running":  c(GREEN,  "●"),
        "degraded": c(YELLOW, "◑"),
        "stopped":  c(RED,    "○"),
        "unknown":  c(DIM,    "?"),
    }.get(status, c(DIM, "?"))


# ── Start service ──────────────────────────────────────────────────────────────
def start_infra(name: str, svc: dict, state: dict) -> bool:
    """Start Docker infra via WSL compose, mongo-only filter."""
    compose_dir = svc["compose_dir"]
    print(f"  {c(CYAN, '→')} Starting Docker infra (mongo)...", end=" ", flush=True)

    if docker_container_running("fullproject-mongo-1"):
        print(c(GREEN, "already running"))
        return True

    r = wsl_run(f"cd '{compose_dir}' && docker-compose up -d mongo 2>&1")
    if r.returncode == 0:
        time.sleep(2)
        if docker_container_running("fullproject-mongo-1"):
            print(c(GREEN, "started ✓"))
            return True

    print(c(YELLOW, "retrying docker start..."))
    wsl_run(f"docker start fullproject-mongo-1 2>&1", capture=True)
    time.sleep(2)
    if docker_container_running("fullproject-mongo-1"):
        print(c(GREEN, "started ✓"))
        return True

    print(c(RED, "FAILED"))
    return False


def start_dotnet(name: str, svc: dict, state: dict) -> bool:
    """Start a .NET service as a background Windows process."""
    project = BASE_DIR / svc["project"]
    log_file = LOG_DIR / f"{name}.log"
    port = svc.get("port")
    health_url = svc.get("health_url")

    if port and is_port_open(port):
        print(c(GREEN, f"already running on :{port}"))
        return True

    print(f"  {c(CYAN, '→')} Starting {name} on :{port}...", end=" ", flush=True)

    # Build env: start from OS env, then apply launch.json, then config.json overrides
    env = os.environ.copy()

    launch_json_path = svc.get("launch_json")
    if launch_json_path:
        # Derive workspaceFolder as the repo root (parent of the .vscode dir)
        workspace_folder = str(BASE_DIR / Path(launch_json_path).parts[0])
        launch_cfg = load_launch_json(str(BASE_DIR / launch_json_path), workspace_folder)
        if launch_cfg.get("env"):
            env.update(launch_cfg["env"])

    # config.json "env" acts as explicit overrides (highest priority)
    env.update(svc.get("env", {}))

    with open(log_file, "w") as lf:
        proc = subprocess.Popen(
            ["dotnet", "run", "--project", str(project)],
            env=env,
            stdout=lf,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )

    state[name] = {"pid": proc.pid, "started_at": datetime.now().isoformat()}
    save_state(state)

    # Wait for health
    deadline = time.time() + 60
    while time.time() < deadline:
        time.sleep(3)
        if port and is_port_open(port):
            print(c(GREEN, f"up ✓  (pid {proc.pid})"))
            return True
        if not is_pid_alive(proc.pid):
            print(c(RED, f"CRASHED — check logs: {log_file}"))
            return False

    print(c(YELLOW, f"timeout waiting for :{port} — check logs: {log_file}"))
    return False


def start_pnpm(name: str, svc: dict, state: dict) -> bool:
    """Start pnpm dev server."""
    project_dir = BASE_DIR / svc["project"]
    log_file = LOG_DIR / f"{name}.log"
    port = svc.get("port")

    if port and is_port_open(port):
        print(c(GREEN, f"already running on :{port}"))
        return True

    print(f"  {c(CYAN, '→')} Starting {name} on :{port}...", end=" ", flush=True)

    with open(log_file, "w") as lf:
        proc = subprocess.Popen(
            ["pnpm", "dev"],
            cwd=str(project_dir),
            stdout=lf,
            stderr=subprocess.STDOUT,
            shell=True,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        )

    state[name] = {"pid": proc.pid, "started_at": datetime.now().isoformat()}
    save_state(state)

    deadline = time.time() + 180
    while time.time() < deadline:
        time.sleep(4)
        if port and is_port_open(port):
            print(c(GREEN, f"up ✓  (pid {proc.pid})"))
            return True
        if not is_pid_alive(proc.pid):
            print(c(RED, f"CRASHED — check logs: {log_file}"))
            return False

    print(c(YELLOW, f"timeout waiting for :{port} — check logs: {log_file}"))
    return False


def start_service(name: str, svc: dict, state: dict) -> bool:
    stype = svc.get("type", "")
    optional = svc.get("optional", False)

    try:
        if stype == "docker-compose-wsl":
            ok = start_infra(name, svc, state)
        elif stype == "dotnet":
            ok = start_dotnet(name, svc, state)
        elif stype == "pnpm":
            ok = start_pnpm(name, svc, state)
        else:
            print(c(YELLOW, f"  Unknown type '{stype}' for {name}"))
            return False
    except Exception as e:
        print(c(RED, f"  ERROR starting {name}: {e}"))
        ok = False

    if not ok and optional:
        print(c(YELLOW, f"  {name} is optional — continuing anyway"))
        return True

    return ok


# ── Stop service ───────────────────────────────────────────────────────────────
def stop_service(name: str, svc: dict, state: dict):
    stype = svc.get("type", "")
    port = svc.get("port")

    print(f"  {c(CYAN, '→')} Stopping {name}...", end=" ", flush=True)

    if stype == "docker-compose-wsl":
        wsl_run("docker stop fullproject-mongo-1 2>/dev/null")
        print(c(GREEN, "stopped ✓"))
        return

    # Kill by saved PID
    pid = state.get(name, {}).get("pid", 0)
    if pid and is_pid_alive(pid):
        kill_pid(pid)

    # Also kill by port (in case started outside this tool)
    if port and is_port_open(port):
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | "
                 f"Select-Object -ExpandProperty OwningProcess -Unique | "
                 f"ForEach-Object {{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}"],
                capture_output=True, text=True, timeout=10
            )
        except Exception:
            pass

    # Verify
    time.sleep(1)
    if port and is_port_open(port):
        print(c(YELLOW, "port still open — may need manual kill"))
    else:
        print(c(GREEN, "stopped ✓"))

    if name in state:
        del state[name]
        save_state(state)


# ── Commands ───────────────────────────────────────────────────────────────────
def cmd_status():
    state = load_state()
    services = CFG["services"]

    print(f"\n{c(BOLD, '  Local Stack — Service Status')}")
    print(f"  {'─' * 52}")
    print(f"  {'SERVICE':<12} {'STATUS':<12} {'PORT':<8} {'PID':<8} {'STARTED'}")
    print(f"  {'─' * 52}")

    any_down = False
    for name in CFG["start_order"]:
        svc = services[name]
        status = get_service_status(name, svc, state)
        icon = status_icon(status)
        port = svc.get("port", "—")
        pid = state.get(name, {}).get("pid", "—")
        started = state.get(name, {}).get("started_at", "—")
        if started != "—":
            started = started[11:16]  # HH:MM

        optional_tag = c(DIM, " (opt)") if svc.get("optional") else ""
        status_text = c(GREEN, "running") if status == "running" else \
                      c(YELLOW, "degraded") if status == "degraded" else \
                      c(RED, "stopped")

        print(f"  {icon} {name:<10} {status_text:<20} {str(port):<8} {str(pid):<8} {started}{optional_tag}")

        if status == "stopped" and not svc.get("optional"):
            any_down = True

    print(f"  {'─' * 52}")
    if any_down:
        print(f"\n  {c(YELLOW, '⚠')}  Run: {c(CYAN, 'python local_stack.py start')} to bring everything up\n")
    else:
        print(f"\n  {c(GREEN, '✓')}  All required services running\n")


def cmd_start(target: str = None):
    state = load_state()
    services = CFG["services"]
    order = CFG["start_order"]

    if target:
        if target not in services:
            print(c(RED, f"Unknown service: {target}"))
            print(f"Available: {', '.join(order)}")
            sys.exit(1)
        targets = [target]
    else:
        targets = order

    print(f"\n{c(BOLD, '  Starting services...')}\n")

    for name in targets:
        if name not in services:
            continue
        svc = services[name]
        current = get_service_status(name, svc, state)
        if current == "running":
            port = svc.get("port", "")
            print(f"  {status_icon('running')} {c(BOLD, name):<14} {c(GREEN, 'already running')}" +
                  (f" :{port}" if port else ""))
            continue

        ok = start_service(name, svc, state)
        state = load_state()  # reload after potential save in start_*
        if not ok:
            print(c(RED, f"\n  ✗ Failed to start {name}. Stopping here."))
            break

    print()
    cmd_status()


def cmd_stop(target: str = None):
    state = load_state()
    services = CFG["services"]
    order = list(reversed(CFG["start_order"]))

    if target:
        if target not in services:
            print(c(RED, f"Unknown service: {target}"))
            sys.exit(1)
        targets = [target]
    else:
        targets = order

    print(f"\n{c(BOLD, '  Stopping services...')}\n")
    for name in targets:
        if name not in services:
            continue
        stop_service(name, services[name], state)

    print()
    cmd_status()


def cmd_restart(target: str):
    if not target:
        print(c(RED, "Usage: python local_stack.py restart <service>"))
        sys.exit(1)
    state = load_state()
    services = CFG["services"]
    if target not in services:
        print(c(RED, f"Unknown service: {target}"))
        sys.exit(1)

    print(f"\n{c(BOLD, f'  Restarting {target}...')}\n")
    stop_service(target, services[target], state)
    time.sleep(2)
    state = load_state()
    start_service(target, services[target], state)
    print()
    cmd_status()


def cmd_reset(target: str):
    """Stop + clear log + start."""
    if not target:
        print(c(RED, "Usage: python local_stack.py reset <service>"))
        sys.exit(1)
    state = load_state()
    services = CFG["services"]
    if target not in services:
        print(c(RED, f"Unknown service: {target}"))
        sys.exit(1)

    log_file = LOG_DIR / f"{target}.log"
    print(f"\n{c(BOLD, f'  Resetting {target}...')}\n")
    stop_service(target, services[target], state)
    if log_file.exists():
        log_file.unlink()
        print(f"  {c(DIM, f'Log cleared: {log_file}')}")
    time.sleep(2)
    state = load_state()
    start_service(target, services[target], state)
    print()
    cmd_status()


def cmd_logs(target: str, lines: int = 50):
    if not target:
        print(c(RED, "Usage: python local_stack.py logs <service> [--lines N]"))
        sys.exit(1)
    log_file = LOG_DIR / f"{target}.log"
    if not log_file.exists():
        print(c(YELLOW, f"No log file found for {target}: {log_file}"))
        return

    content = log_file.read_text(errors="replace").splitlines()
    tail = content[-lines:]
    print(f"\n{c(BOLD, f'  Logs — {target}')} {c(DIM, f'(last {lines} lines)')}\n{'─'*60}")
    for line in tail:
        print(f"  {line}")
    print("─"*60 + "\n")


# ── Entry point ────────────────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(0)

    cmd = args[0].lower()
    rest = args[1:]

    # Parse --lines flag for logs
    lines = 50
    if "--lines" in rest:
        idx = rest.index("--lines")
        try:
            lines = int(rest[idx + 1])
            rest = [x for i, x in enumerate(rest) if i != idx and i != idx + 1]
        except (IndexError, ValueError):
            pass

    target = rest[0] if rest else None

    if cmd == "status":
        cmd_status()
    elif cmd == "start":
        cmd_start(target)
    elif cmd == "stop":
        cmd_stop(target)
    elif cmd == "restart":
        cmd_restart(target)
    elif cmd == "reset":
        cmd_reset(target)
    elif cmd == "logs":
        cmd_logs(target, lines)
    else:
        print(c(RED, f"Unknown command: {cmd}"))
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
