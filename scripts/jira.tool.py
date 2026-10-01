#!/usr/bin/env python3
"""
jira.tool.py — CLI for Jira Cloud used by Cursor / Copilot skills.

Usage:
  python jira.tool.py myself
  python jira.tool.py mine [--max 50] [--include-done]
  python jira.tool.py get <ISSUE-KEY> [--save <path>] [--markdown]
  python jira.tool.py search --jql "..." [--max 50]

Credentials: ~/.cursor/agent-env/.env (ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN, ATLASSIAN_BASE_URL)

All successful responses are JSON on stdout. Errors: {"error": "..."} exit 1.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as `python scripts/jira.tool.py` from repo root
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from jira_client import (  # noqa: E402
    JiraClient,
    JiraError,
    issue_to_markdown,
    resolve_config,
    summarize_issue,
)


def _out(data: dict, indent: int = 2):
    payload = json.dumps(data, ensure_ascii=False, indent=indent)
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    sys.stdout.buffer.write((payload + "\n").encode("utf-8"))


def _err(msg: str, code: int = 1):
    payload = json.dumps({"error": msg}, ensure_ascii=False)
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    sys.stdout.buffer.write((payload + "\n").encode("utf-8"))
    sys.exit(code)


def cmd_myself(_: argparse.Namespace) -> None:
    client = JiraClient.from_env()
    me = client.myself()
    _out(
        {
            "success": True,
            "accountId": me.get("accountId"),
            "displayName": me.get("displayName"),
            "emailAddress": me.get("emailAddress"),
            "baseUrl": client.base_url,
            "envFileHint": str(Path.home() / ".cursor" / "agent-env" / ".env"),
        }
    )


def cmd_mine(args: argparse.Namespace) -> None:
    client = JiraClient.from_env()
    raw = client.assigned_to_me(max_results=args.max, include_done=args.include_done)
    issues = raw.get("issues") or raw.get("values") or []
    items = []
    for issue in issues:
        item = summarize_issue(issue)
        item["url"] = f"{client.base_url}/browse/{item['key']}"
        items.append(item)
    _out(
        {
            "success": True,
            "count": len(items),
            "includeDone": bool(args.include_done),
            "issues": items,
        }
    )


def cmd_get(args: argparse.Namespace) -> None:
    client = JiraClient.from_env()
    issue = client.get_issue(args.key)
    summary = summarize_issue(issue)
    summary["url"] = f"{client.base_url}/browse/{summary['key']}"
    md = issue_to_markdown(issue)
    result = {
        "success": True,
        "issue": summary,
        "markdown": md,
        "rawKey": issue.get("key"),
    }
    if args.save:
        path = Path(args.save)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(md if args.markdown or path.suffix.lower() in {".md", ".markdown"} else json.dumps(issue, ensure_ascii=False, indent=2), encoding="utf-8")
        result["savedTo"] = str(path.resolve())
    if args.markdown and not args.save:
        # Still JSON envelope; markdown field present
        pass
    _out(result)


def cmd_search(args: argparse.Namespace) -> None:
    client = JiraClient.from_env()
    try:
        raw = client.search(args.jql, max_results=args.max)
    except JiraError as e:
        if e.status in (404, 410):
            raw = client.search_legacy(args.jql, max_results=args.max)
        else:
            raise
    issues = raw.get("issues") or raw.get("values") or []
    items = []
    for issue in issues:
        item = summarize_issue(issue)
        item["url"] = f"{client.base_url}/browse/{item['key']}"
        items.append(item)
    _out({"success": True, "count": len(items), "jql": args.jql, "issues": items})


def main() -> None:
    parser = argparse.ArgumentParser(description="Jira Cloud tool for copilot-skills / Cursor")
    sub = parser.add_subparsers(dest="command", required=True)

    p_me = sub.add_parser("myself", help="Verify credentials / current user")
    p_me.set_defaults(func=cmd_myself)

    p_mine = sub.add_parser("mine", help="List issues assigned to current user")
    p_mine.add_argument("--max", type=int, default=50)
    p_mine.add_argument("--include-done", action="store_true")
    p_mine.set_defaults(func=cmd_mine)

    p_get = sub.add_parser("get", help="Fetch one issue by key")
    p_get.add_argument("key")
    p_get.add_argument("--save", help="Write markdown/JSON to this path")
    p_get.add_argument("--markdown", action="store_true", help="Prefer markdown when saving")
    p_get.set_defaults(func=cmd_get)

    p_search = sub.add_parser("search", help="Run JQL search")
    p_search.add_argument("--jql", required=True)
    p_search.add_argument("--max", type=int, default=50)
    p_search.set_defaults(func=cmd_search)

    args = parser.parse_args()
    # Soft config check for clearer errors
    cfg = resolve_config()
    if args.command != "myself":
        missing = [k for k in ("ATLASSIAN_EMAIL", "ATLASSIAN_API_TOKEN", "ATLASSIAN_BASE_URL") if not cfg.get(k)]
        if missing:
            _err(
                "Missing "
                + ", ".join(missing)
                + ". Fill ~/.cursor/agent-env/.env (see ~/.cursor/agent-env/README.md)."
            )
    try:
        args.func(args)
    except JiraError as e:
        payload = {"error": str(e)}
        if e.status is not None:
            payload["status"] = e.status
        if e.body is not None:
            payload["details"] = e.body
        try:
            sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8"))
        except Exception:
            print(json.dumps(payload, ensure_ascii=False))
        sys.exit(1)
    except Exception as e:  # noqa: BLE001
        _err(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
