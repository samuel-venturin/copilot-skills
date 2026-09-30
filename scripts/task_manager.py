#!/usr/bin/env python3
"""
task_manager.py
CLI for reading and writing the task-interpreter index.json.

All writes go through this tool — agents never edit index.json directly.
All output is JSON to stdout unless --pretty is used for render-index.

Usage:
    python3 ~/.claude/scripts/task_manager.py list [--status=<status>] [--type=<type>]
    python3 ~/.claude/scripts/task_manager.py next
    python3 ~/.claude/scripts/task_manager.py get <id>
    python3 ~/.claude/scripts/task_manager.py add --spec=<path> [--ticket=<ticket>] [--type=<type>] [--priority=<n>] [--name=<name>] [--depends-on=<ticket-or-id>]
    python3 ~/.claude/scripts/task_manager.py set-status <id> <status>
    python3 ~/.claude/scripts/task_manager.py set-field <id> <field> <value>
    python3 ~/.claude/scripts/task_manager.py render-index
    python3 ~/.claude/scripts/task_manager.py sync-specs [--specs-dir=<dir>]
    python3 ~/.claude/scripts/task_manager.py register [--name=<project-name>]
    python3 ~/.claude/scripts/task_manager.py global-list [--status=<status>]

Settable fields (set-field): branch, prompt, quality, prd, ticket, priority, name, type, depends_on

Exit codes:
    0 = success
    1 = error (JSON {"error": "..."} on stdout)
"""
import sys
import os
import json
import argparse
import datetime
import re

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_SKILL_DIR = os.path.dirname(_SCRIPT_DIR)
# workspace root = current working directory (where the agent runs the command)
# This allows the script to work both from a project repo and globally.
_WORKSPACE_ROOT = os.getcwd()
_SPECS_DIR  = os.path.join(_WORKSPACE_ROOT, "specs")
_TASKS_DIR  = os.path.join(_WORKSPACE_ROOT, "docs", "tasks")
_INDEX_PATH = os.path.join(_TASKS_DIR, "index.json")
_INDEX_MD   = os.path.join(_TASKS_DIR, "index.md")

# Global registry — lives in the skill dir (not in any project)
_REGISTRY_PATH = os.path.join(_SKILL_DIR, "registry.json")

VALID_STATUSES = ["new", "waiting", "doing", "awaiting-user-approval", "done"]
VALID_TYPES = ["us", "bug", "task"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _out(data: dict, indent: int = 2):
    print(json.dumps(data, ensure_ascii=False, indent=indent))

def _err(msg: str, code: int = 1):
    print(json.dumps({"error": msg}, ensure_ascii=False))
    sys.exit(code)

def _today() -> str:
    return datetime.date.today().isoformat()

def _load_index() -> dict:
    if not os.path.isfile(_INDEX_PATH):
        _err(f"index.json not found at: {_INDEX_PATH}\nRun 'task_manager.py register' to initialize this project.")
    try:
        with open(_INDEX_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        _err(f"index.json is malformed (JSONDecodeError): {e}")
    except OSError as e:
        _err(f"Could not read index.json: {e}")

def _save_index(data: dict):
    try:
        os.makedirs(_TASKS_DIR, exist_ok=True)
        with open(_INDEX_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as e:
        _err(f"Could not write index.json: {e}")

def _next_id(tasks: list) -> str:
    if not tasks:
        return "001"
    max_id = max(int(t["id"]) for t in tasks if str(t["id"]).isdigit())
    return str(max_id + 1).zfill(3)

def _find_task(tasks: list, id_or_name: str) -> dict | None:
    for t in tasks:
        if str(t["id"]) == str(id_or_name) or t.get("name") == id_or_name or t.get("ticket") == id_or_name:
            return t
    return None

def _dependency_satisfied(task: dict, all_tasks: list) -> bool:
    dep = task.get("depends_on")
    if not dep:
        return True
    dep_task = _find_task(all_tasks, dep)
    if not dep_task:
        return True  # dependency not found in index — don't block
    return dep_task.get("status") == "done"

def _priority_sort_key(task: dict):
    status_order = {s: i for i, s in enumerate(VALID_STATUSES)}
    p = task.get("priority") or 999
    return (status_order.get(task.get("status", "new"), 0), p)

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_list(args):
    idx = _load_index()
    tasks = idx["tasks"]
    if args.status:
        tasks = [t for t in tasks if t.get("status") == args.status]
    if args.type:
        tasks = [t for t in tasks if t.get("type") == args.type]
    _out({"tasks": tasks, "count": len(tasks)})


def cmd_next(args):
    idx = _load_index()
    all_tasks = idx["tasks"]
    active_statuses = ["doing", "waiting", "new"]
    candidates = [t for t in all_tasks if t.get("status") in active_statuses]
    if not candidates:
        _out({"next": None, "message": "No queued tasks found."})
        return
    # Priority: doing first, then waiting, then new; within group, lower priority number wins
    doing = [t for t in candidates if t.get("status") == "doing"]
    if doing:
        by_priority = sorted(doing, key=lambda t: t.get("priority") or 999)
        _out({"next": by_priority[0], "source": "doing"})
        return
    waiting = [t for t in candidates if t.get("status") == "waiting" and _dependency_satisfied(t, all_tasks)]
    if waiting:
        by_priority = sorted(waiting, key=lambda t: t.get("priority") or 999)
        _out({"next": by_priority[0], "source": "waiting"})
        return
    new_tasks = [t for t in candidates if t.get("status") == "new" and _dependency_satisfied(t, all_tasks)]
    if new_tasks:
        by_priority = sorted(new_tasks, key=lambda t: t.get("priority") or 999)
        _out({"next": by_priority[0], "source": "new"})
        return
    # All candidates blocked by unmet dependencies
    blocked = [t for t in candidates if not _dependency_satisfied(t, all_tasks)]
    _out({"next": None, "message": f"All {len(blocked)} queued task(s) are blocked by unmet dependencies.", "blocked": blocked})


def cmd_get(args):
    idx = _load_index()
    task = _find_task(idx["tasks"], args.id)
    if not task:
        _err(f"Task not found: {args.id}")
    _out({"task": task})


def cmd_add(args):
    if not args.spec:
        _err("--spec is required")
    os.makedirs(_TASKS_DIR, exist_ok=True)
    os.makedirs(_SPECS_DIR, exist_ok=True)
    idx = _load_index()
    tasks = idx["tasks"]

    # Prevent duplicate spec
    existing = next((t for t in tasks if t.get("spec") == args.spec), None)
    if existing:
        _err(f"Spec already indexed as task {existing['id']} (status: {existing['status']})")

    # Infer name from spec path if not provided
    name = args.name
    if not name:
        basename = os.path.basename(args.spec)
        name = re.sub(r"\.md$", "", basename)

    # Infer type from ticket or argument
    task_type = args.type or "us"

    new_task = {
        "id": _next_id(tasks),
        "name": name,
        "spec": args.spec,
        "ticket": args.ticket or None,
        "type": task_type,
        "priority": int(args.priority) if args.priority else len(tasks) + 1,
        "status": "new",
        "branch": None,
        "prompt": None,
        "quality": None,
        "prd": None,
        "depends_on": args.depends_on or None,
        "createdAt": _today(),
        "updatedAt": _today(),
    }
    tasks.append(new_task)
    _save_index(idx)
    _out({"ok": True, "task": new_task})


def cmd_set_status(args):
    if args.status not in VALID_STATUSES:
        _err(f"Invalid status '{args.status}'. Valid values: {VALID_STATUSES}")
    idx = _load_index()
    task = _find_task(idx["tasks"], args.id)
    if not task:
        _err(f"Task not found: {args.id}")
    old_status = task["status"]
    task["status"] = args.status
    task["updatedAt"] = _today()
    _save_index(idx)
    _out({"ok": True, "id": task["id"], "from": old_status, "to": args.status})


def cmd_set_field(args):
    ALLOWED_FIELDS = ["branch", "prompt", "quality", "prd", "ticket", "priority", "name", "type", "depends_on"]
    if args.field not in ALLOWED_FIELDS:
        _err(f"Field '{args.field}' is not settable. Allowed: {ALLOWED_FIELDS}")
    idx = _load_index()
    task = _find_task(idx["tasks"], args.id)
    if not task:
        _err(f"Task not found: {args.id}")
    value = args.value
    if args.field == "priority":
        try:
            value = int(value)
        except ValueError:
            _err("priority must be an integer")
    task[args.field] = value
    task["updatedAt"] = _today()
    _save_index(idx)
    _out({"ok": True, "id": task["id"], "field": args.field, "value": value})


def cmd_sync_specs(args):
    """Scan specs dir and add any unindexed spec as status=new."""
    specs_dir = args.specs_dir or _SPECS_DIR
    if not os.path.isdir(specs_dir):
        _err(f"specs dir not found: {specs_dir}")
    idx = _load_index()
    tasks = idx["tasks"]
    indexed_specs = {t["spec"] for t in tasks}
    added = []
    for fname in sorted(os.listdir(specs_dir)):
        if not fname.endswith(".md"):
            continue
        rel_path = os.path.join(specs_dir, fname)
        if rel_path in indexed_specs:
            continue
        name = re.sub(r"\.md$", "", fname)
        new_task = {
            "id": _next_id(tasks),
            "name": name,
            "spec": rel_path,
            "ticket": None,
            "type": "us",
            "priority": len(tasks) + 1,
            "status": "new",
            "branch": None,
            "prompt": None,
            "quality": None,
            "prd": None,
            "depends_on": None,
            "createdAt": _today(),
            "updatedAt": _today(),
        }
        tasks.append(new_task)
        added.append(new_task)
    if added:
        _save_index(idx)
    _out({"ok": True, "added": len(added), "tasks_added": added})


def cmd_render_index(args):
    """Regenerate index.md from index.json."""
    idx = _load_index()
    tasks = idx["tasks"]
    lines = [
        "# Task Interpreter Index",
        "",
        "This file is auto-generated by `task_manager.py render-index`. Do not edit manually.",
        "",
        "| id | name | path | ticket | type | priority | status | depends_on |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for t in tasks:
        ticket = t.get("ticket") or "-"
        priority = t.get("priority") or "-"
        depends_on = t.get("depends_on") or "-"
        lines.append(
            f"| {t['id']} | {t['name']} | {t['spec']} | {ticket} | {t.get('type','-')} | {priority} | {t['status']} | {depends_on} |"
        )
    lines += [
        "",
        "## Status legend",
        "",
        "- `new`: spec detected but not planned yet.",
        "- `waiting`: planned, waiting to start execution.",
        "- `doing`: currently in execution.",
        "- `awaiting-user-approval`: implementation complete; waiting exact user approval token before `done`.",
        "- `done`: finished and validated.",
        "",
    ]
    try:
        os.makedirs(_TASKS_DIR, exist_ok=True)
        with open(_INDEX_MD, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except OSError as e:
        _err(f"Could not write index.md: {e}")
    _out({"ok": True, "path": _INDEX_MD, "tasks": len(tasks)})


# ---------------------------------------------------------------------------
# Registry helpers
# ---------------------------------------------------------------------------

def _load_registry() -> list:
    if not os.path.isfile(_REGISTRY_PATH):
        return []
    try:
        with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        _err(f"registry.json is malformed (JSONDecodeError): {e}")
    except OSError as e:
        _err(f"Could not read registry.json: {e}")

def _save_registry(data: list):
    try:
        os.makedirs(os.path.dirname(_REGISTRY_PATH), exist_ok=True)
        with open(_REGISTRY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
    except OSError as e:
        _err(f"Could not write registry.json: {e}")


def cmd_register(args):
    """Register the current project in the global registry."""
    name = args.name or os.path.basename(_WORKSPACE_ROOT)
    index_path = _INDEX_PATH

    # Initialize index.json if it doesn't exist yet
    if not os.path.isfile(index_path):
        os.makedirs(_TASKS_DIR, exist_ok=True)
        _save_index({"tasks": []})

    registry = _load_registry()
    existing = next((r for r in registry if r["path"] == index_path), None)
    if existing:
        existing["name"] = name
        _save_registry(registry)
        _out({"ok": True, "action": "updated", "project": name, "path": index_path})
    else:
        registry.append({"name": name, "path": index_path, "root": _WORKSPACE_ROOT})
        _save_registry(registry)
        _out({"ok": True, "action": "registered", "project": name, "path": index_path})


def cmd_global_list(args):
    """List tasks from all registered projects."""
    registry = _load_registry()
    if not registry:
        _out({"projects": [], "total": 0, "message": "No projects registered. Run 'register' in each project first."})
        return

    all_tasks = []
    errors = []
    for entry in registry:
        idx_path = entry["path"]
        if not os.path.isfile(idx_path):
            errors.append({"project": entry["name"], "error": f"index not found: {idx_path}"})
            continue
        try:
            with open(idx_path, "r", encoding="utf-8") as f:
                idx = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            errors.append({"project": entry["name"], "error": str(e)})
            continue
        tasks = idx.get("tasks", [])
        if args.status:
            tasks = [t for t in tasks if t.get("status") == args.status]
        for t in tasks:
            t["_project"] = entry["name"]
            t["_root"] = entry.get("root", "")
        all_tasks.extend(tasks)

    all_tasks.sort(key=lambda t: (
        VALID_STATUSES.index(t["status"]) if t["status"] in VALID_STATUSES else 99,
        t.get("priority") or 999
    ))

    _out({
        "projects": len(registry),
        "total": len(all_tasks),
        "errors": errors,
        "tasks": all_tasks,
    })


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="task_manager.py — task-interpreter index CLI")
    sub = parser.add_subparsers(dest="command")

    # list
    p_list = sub.add_parser("list")
    p_list.add_argument("--status", help="Filter by status")
    p_list.add_argument("--type", help="Filter by type")

    # next
    sub.add_parser("next")

    # get
    p_get = sub.add_parser("get")
    p_get.add_argument("id")

    # add
    p_add = sub.add_parser("add")
    p_add.add_argument("--spec", required=True)
    p_add.add_argument("--ticket")
    p_add.add_argument("--type", choices=VALID_TYPES)
    p_add.add_argument("--priority")
    p_add.add_argument("--name")
    p_add.add_argument("--depends-on", dest="depends_on", help="Ticket or task ID this task depends on")

    # set-status
    p_ss = sub.add_parser("set-status")
    p_ss.add_argument("id")
    p_ss.add_argument("status", choices=VALID_STATUSES)

    # set-field
    p_sf = sub.add_parser("set-field")
    p_sf.add_argument("id")
    p_sf.add_argument("field")
    p_sf.add_argument("value")

    # sync-specs
    p_sync = sub.add_parser("sync-specs")
    p_sync.add_argument("--specs-dir")

    # render-index
    sub.add_parser("render-index")

    # register
    p_reg = sub.add_parser("register")
    p_reg.add_argument("--name", help="Project name (defaults to workspace folder name)")

    # global-list
    p_gl = sub.add_parser("global-list")
    p_gl.add_argument("--status", help="Filter by status across all projects")

    args = parser.parse_args()

    dispatch = {
        "list": cmd_list,
        "next": cmd_next,
        "get": cmd_get,
        "add": cmd_add,
        "set-status": cmd_set_status,
        "set-field": cmd_set_field,
        "sync-specs": cmd_sync_specs,
        "render-index": cmd_render_index,
        "register": cmd_register,
        "global-list": cmd_global_list,
    }

    if not args.command or args.command not in dispatch:
        parser.print_help()
        sys.exit(1)

    try:
        dispatch[args.command](args)
    except SystemExit:
        raise
    except Exception as e:
        print(json.dumps({"error": f"Unexpected error: {e}"}, ensure_ascii=False))
        sys.exit(1)


if __name__ == "__main__":
    main()
