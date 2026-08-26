#!/usr/bin/env python3
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from _pr_helpers import CommandError, current_branch, open_pr_for_branch, print_json, run


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create PR if missing, otherwise return existing PR metadata.")
    parser.add_argument("--base", default="develop")
    parser.add_argument("--head", default=None)
    parser.add_argument("--title", required=True)
    parser.add_argument("--body", default=None)
    parser.add_argument("--body-file", default=None)
    parser.add_argument("--draft", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    head = args.head or current_branch()

    if not args.body and not args.body_file:
        raise CommandError("Either --body or --body-file is required.")

    existing = open_pr_for_branch(args.base, head)
    if existing:
        print_json(
            {
                "status": "already_exists",
                "prNumber": existing["number"],
                "prUrl": existing["url"],
                "title": existing["title"],
                "baseBranch": args.base,
                "headBranch": head,
            }
        )
        return 0

    if args.dry_run:
        print_json(
            {
                "status": "dry_run",
                "prNumber": None,
                "prUrl": None,
                "title": args.title,
                "baseBranch": args.base,
                "headBranch": head,
            }
        )
        return 0

    run(["git", "push", "-u", "origin", head])

    body_file_path = args.body_file
    cleanup = None
    if not body_file_path:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8")
        tmp.write(args.body or "")
        tmp.flush()
        tmp.close()
        body_file_path = tmp.name
        cleanup = Path(body_file_path)

    cmd = [
        "gh",
        "pr",
        "create",
        "--base",
        args.base,
        "--head",
        head,
        "--title",
        args.title,
        "--body-file",
        body_file_path,
    ]
    if args.draft:
        cmd.append("--draft")

    pr_url = run(cmd)
    created = open_pr_for_branch(args.base, head)

    if cleanup and cleanup.exists():
        cleanup.unlink(missing_ok=True)

    print_json(
        {
            "status": "created",
            "prNumber": created["number"] if created else None,
            "prUrl": pr_url.strip() if pr_url else (created["url"] if created else None),
            "title": created["title"] if created else args.title,
            "baseBranch": args.base,
            "headBranch": head,
        }
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print_json({"status": "failed", "error": str(exc)})
        raise SystemExit(1)
