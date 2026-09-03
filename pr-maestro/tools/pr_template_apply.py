#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from _pr_helpers import (
    build_template_body,
    current_branch,
    default_title,
    diff_data,
    open_pr_for_branch,
    print_json,
    repo_name_with_owner,
    run,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply PR template to an existing pull request.")
    parser.add_argument("--pr-number", type=int, default=None)
    parser.add_argument("--base", default="develop")
    parser.add_argument("--title", default=None)
    parser.add_argument("--quality-report-file", default=None)
    parser.add_argument(
        "--how-to-test-file",
        default=None,
        help="Path to a Markdown file whose content is embedded as the 'Como testar manualmente' section.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output-body-file", default=None)
    return parser.parse_args()


def resolve_pr_number(base: str, explicit: int | None) -> int:
    if explicit:
        return explicit
    branch = current_branch()
    existing = open_pr_for_branch(base, branch)
    if not existing:
        raise RuntimeError(f"No open PR found for branch '{branch}' against '{base}'.")
    return int(existing["number"])


def main() -> int:
    args = parse_args()
    branch = current_branch()
    diff = diff_data(args.base)
    title = args.title or default_title(branch, diff.commits)
    quality_report = None

    if args.quality_report_file:
        quality_path = Path(args.quality_report_file)
        if quality_path.exists():
            quality_report = json.loads(quality_path.read_text(encoding="utf-8"))

    how_to_test_content = None
    if args.how_to_test_file:
        how_to_test_path = Path(args.how_to_test_file)
        if how_to_test_path.exists():
            how_to_test_content = how_to_test_path.read_text(encoding="utf-8")

    body = build_template_body(
        args.base,
        branch,
        title,
        diff.commits,
        diff.files,
        quality_report=quality_report,
        how_to_test=how_to_test_content,
    )
    pr_number = resolve_pr_number(args.base, args.pr_number)

    if args.output_body_file:
        Path(args.output_body_file).write_text(body, encoding="utf-8")

    if args.dry_run:
        print_json(
            {
                "status": "dry_run",
                "prNumber": pr_number,
                "title": title,
                "bodyPreview": body[:500],
            }
        )
        return 0

    owner_repo = repo_name_with_owner()
    payload = {"title": title, "body": body}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(payload, tmp, ensure_ascii=False)
        tmp.flush()
        payload_path = tmp.name

    run(
        [
            "gh",
            "api",
            f"repos/{owner_repo}/pulls/{pr_number}",
            "--method",
            "PATCH",
            "--input",
            payload_path,
            "--silent",
        ]
    )

    updated = json.loads(
        run(
            [
                "gh",
                "pr",
                "view",
                str(pr_number),
                "--json",
                "number,url,title",
            ]
        )
    )

    print_json(
        {
            "status": "updated",
            "prNumber": updated["number"],
            "prUrl": updated["url"],
            "title": updated["title"],
            "templateApplied": True,
            "method": "gh api PATCH",
        }
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print_json({"status": "failed", "error": str(exc)})
        raise SystemExit(1)
