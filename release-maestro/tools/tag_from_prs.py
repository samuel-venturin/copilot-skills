#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json

from _release_helpers import (
    CommandError,
    commits_since_latest,
    count_pr_types,
    create_and_push_tag,
    detect_tag_window,
    ensure_gh_auth,
    merged_prs_from_commits,
    next_tag_for_bump,
    print_json,
    repo_name_with_owner,
    suggest_bump_from_pr_types,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Infer release bump from PR title types since last tag and optionally create/push a new tag."
    )
    parser.add_argument("--bump", choices=["auto", "major", "minor", "patch"], default="auto")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ensure_gh_auth()

    owner_repo = repo_name_with_owner()
    tag_window = detect_tag_window()
    commits = commits_since_latest(tag_window.range_since_latest)
    prs = merged_prs_from_commits(owner_repo, commits)

    if not prs:
        print_json(
            {
                "status": "blocked",
                "reason": "no_prs_since_latest_tag",
                "latestTag": tag_window.latest_tag,
                "range": tag_window.range_since_latest,
                "message": "No merged PRs were found since the latest tag. Release flow is blocked by policy.",
            }
        )
        return 1

    type_counts = count_pr_types(prs)
    suggested_bump, reason = suggest_bump_from_pr_types(type_counts)

    selected_bump = args.bump if args.bump != "auto" else suggested_bump
    next_tag = next_tag_for_bump(tag_window.latest_tag, selected_bump)

    if not args.confirm:
        print_json(
            {
                "status": "needs_confirmation",
                "latestTag": tag_window.latest_tag,
                "previousTag": tag_window.previous_tag,
                "range": tag_window.range_since_latest,
                "prCount": len(prs),
                "prTypeCounts": type_counts,
                "suggestedBump": suggested_bump,
                "suggestionReason": reason,
                "selectedBump": selected_bump,
                "nextTag": next_tag,
                "nextAction": "Confirm bump and rerun with --confirm to create and push the tag.",
            }
        )
        return 0

    tag_status = create_and_push_tag(next_tag, dry_run=args.dry_run, confirmed=True)

    print_json(
        {
            "status": "success",
            "latestTag": tag_window.latest_tag,
            "range": tag_window.range_since_latest,
            "prTypeCounts": type_counts,
            "suggestedBump": suggested_bump,
            "selectedBump": selected_bump,
            "tag": {
                "value": next_tag,
                "status": tag_status,
            },
        }
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print_json({"status": "failed", "error": str(exc)})
        raise SystemExit(1)
