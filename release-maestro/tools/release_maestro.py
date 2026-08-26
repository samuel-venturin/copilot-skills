#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from _release_helpers import (
    CommandError,
    MergeGateResult,
    build_overview_non_technical,
    check_pr_merge_gate,
    collect_coverage_data,
    collect_release_data,
    commits_since_latest,
    count_pr_types,
    create_and_push_tag,
    create_or_update_release,
    detect_tag_window,
    ensure_gh_auth,
    fetch_tags_from_origin,
    git_tag_exists,
    merged_prs_from_commits,
    next_tag_for_bump,
    print_json,
    release_exists,
    render_release_notes,
    repo_name_with_owner,
    suggest_bump_from_pr_types,
)

TOOLS_DIR = Path(__file__).resolve().parent
SKILL_DIR = TOOLS_DIR.parent
CONFIG_PATH = TOOLS_DIR / "config.json"
RELEASE_TEMPLATE_PATH = SKILL_DIR / "templates" / "TEMPLATE.md"


def _detect_repo_root() -> Path:
    try:
        result = __import__("subprocess").run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(result.stdout.strip())
    except Exception:
        return Path.cwd()


ROOT = _detect_repo_root()
TMP_DIR = ROOT / ".github/.tmp"


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    raw = CONFIG_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {}


def cfg_bool(config: dict, section: str, key: str, fallback: bool) -> bool:
    value = config.get(section, {}).get(key, fallback)
    return value if isinstance(value, bool) else fallback


def cfg_str(config: dict, section: str, key: str, fallback: str) -> str:
    value = config.get(section, {}).get(key, fallback)
    return value if isinstance(value, str) and value.strip() else fallback


def parse_args(config: dict) -> argparse.Namespace:
    default_base = cfg_str(config, "defaults", "base", "develop")
    default_bump = cfg_str(config, "defaults", "bump", "auto")
    if default_bump not in {"auto", "major", "minor", "patch"}:
        default_bump = "auto"

    parser = argparse.ArgumentParser(description="Orchestrate semantic tag + release creation/update in one Python flow.")
    parser.add_argument("--base", default=default_base)
    parser.add_argument("--from-tag", default=None, help="Override latest tag detection (bypasses outlier logic).")
    parser.add_argument("--bump", choices=["auto", "major", "minor", "patch"], default=default_bump)
    parser.add_argument("--title", default=None)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--run-coverage",
        action=argparse.BooleanOptionalAction,
        default=cfg_bool(config, "release", "runCoverage", True),
        help="Run coverage collection script for release notes.",
    )
    return parser.parse_args()


def build_confirmation_payload(
    *,
    tag_window,
    prs: list[dict],
    type_counts: dict[str, int],
    suggested_bump: str,
    suggestion_reason: str,
    selected_bump: str,
    next_tag: str,
    proposed_title: str,
) -> dict:
    return {
        "status": "needs_confirmation",
        "latestTag": tag_window.latest_tag,
        "previousTag": tag_window.previous_tag,
        "range": tag_window.range_since_latest,
        "prCount": len(prs),
        "prTypeCounts": type_counts,
        "suggestedBump": suggested_bump,
        "suggestionReason": suggestion_reason,
        "selectedBump": selected_bump,
        "nextTag": next_tag,
        "proposedTitle": proposed_title,
        "nextAction": "Confirm bump/title and rerun with --confirm to create tag and create/update release.",
    }


def main() -> int:
    config = load_config()
    args = parse_args(config)

    ensure_gh_auth()
    owner_repo = repo_name_with_owner()

    if not RELEASE_TEMPLATE_PATH.exists():
        raise CommandError(f"Release template not found: {RELEASE_TEMPLATE_PATH}")

    fetch_tags_from_origin()
    tag_window = detect_tag_window(from_tag=getattr(args, "from_tag", None), base=args.base)

    # Resume detection: if the latest tag has no GitHub release, a prior
    # --confirm run likely created the tag but failed before finishing.
    # Switch to previous_tag..latest_tag so PRs are found correctly.
    resume_tag: str | None = None
    if tag_window.latest_tag != "v0.0.0" and not release_exists(tag_window.latest_tag):
        resume_tag = tag_window.latest_tag
        effective_range = (
            f"{tag_window.previous_tag}..{tag_window.latest_tag}"
            if tag_window.previous_tag
            else tag_window.latest_tag
        )
    else:
        effective_range = tag_window.range_since_latest

    commits = commits_since_latest(effective_range)
    prs = merged_prs_from_commits(owner_repo, commits)

    if not prs:
        print_json(
            {
                "status": "blocked",
                "reason": "no_prs_since_latest_tag",
                "latestTag": tag_window.latest_tag,
                "range": effective_range,
                "nextAction": "No merged PRs found in the release window. Flow is blocked by policy.",
            }
        )
        return 1

    type_counts = count_pr_types(prs)

    if resume_tag:
        next_tag = resume_tag
        selected_bump = "resume"
        suggested_bump = "resume"
        suggestion_reason = "resume_existing_tag_no_release"
    else:
        suggested_bump, suggestion_reason = suggest_bump_from_pr_types(type_counts)
        selected_bump = args.bump if args.bump != "auto" else suggested_bump
        next_tag = next_tag_for_bump(tag_window.latest_tag, selected_bump)

    proposed_title = args.title or f"{next_tag} - release updates"

    if not args.title:
        # Keeps title aligned with release-create style while still being deterministic.
        from _release_helpers import summarize_release_title

        proposed_title = summarize_release_title(next_tag, prs)

    # Block: target tag already has a tag AND a release — nothing to do.
    if not resume_tag and git_tag_exists(next_tag) and release_exists(next_tag):
        print_json(
            {
                "status": "blocked",
                "reason": "tag_and_release_already_exist",
                "tag": next_tag,
                "latestTag": tag_window.latest_tag,
                "range": effective_range,
                "nextAction": f"Tag {next_tag} and its release already exist. Nothing to do.",
            }
        )
        return 1

    if not args.confirm:
        payload = build_confirmation_payload(
            tag_window=tag_window,
            prs=prs,
            type_counts=type_counts,
            suggested_bump=suggested_bump,
            suggestion_reason=suggestion_reason,
            selected_bump=selected_bump,
            next_tag=next_tag,
            proposed_title=proposed_title,
        )
        if resume_tag:
            payload["status"] = "needs_confirmation_resume"
            payload["range"] = effective_range
            payload["nextAction"] = (
                f"Tag {resume_tag} exists but has no release. "
                "Rerun with --confirm to create the release."
            )
        print_json(payload)
        return 0

    # PR merge gate: all PRs in the window must be truly merged on GitHub
    # before a new tag is allowed to be created.
    gate = check_pr_merge_gate(owner_repo, prs)
    if not gate.passed:
        blocked = [p for p in gate.prs if p.get("gate") != "passed"]
        print_json({
            "status": "blocked",
            "reason": "pr_merge_gate_failed",
            "nextTag": next_tag,
            "blockedPrs": blocked,
            "nextAction": "The following PRs are not yet merged. Merge them before creating the tag.",
        })
        return 1

    tag_status = create_and_push_tag(
        next_tag,
        dry_run=args.dry_run,
        confirmed=True,
        target=f"origin/{args.base}",
    )
    release_previous_tag = tag_window.previous_tag if resume_tag else tag_window.latest_tag
    release_data, release_blocks = collect_release_data(
        last_tag=next_tag,
        previous_tag=release_previous_tag,
    )
    coverage_data = collect_coverage_data(args.run_coverage)
    final_title = args.title or proposed_title
    overview = build_overview_non_technical(prs, release_data)

    notes = render_release_notes(
        template_path=RELEASE_TEMPLATE_PATH,
        release_data=release_data,
        release_blocks=release_blocks,
        coverage_data=coverage_data,
        title=final_title,
        overview=overview,
    )

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    notes_path = TMP_DIR / f"release-notes-{next_tag}.md"
    notes_path.write_text(notes, encoding="utf-8")

    release_status, release_url = create_or_update_release(
        tag=next_tag,
        title=final_title,
        notes_file=notes_path,
        dry_run=args.dry_run,
    )

    print_json(
        {
            "status": "success",
            "latestTag": tag_window.latest_tag,
            "previousTag": tag_window.previous_tag,
            "range": effective_range,
            "prCount": len(prs),
            "prTypeCounts": type_counts,
            "suggestedBump": suggested_bump,
            "suggestionReason": suggestion_reason,
            "selectedBump": selected_bump,
            "tag": {
                "value": next_tag,
                "status": tag_status,
            },
            "release": {
                "tag": next_tag,
                "title": final_title,
                "status": release_status,
                "url": release_url,
                "notesFile": str(notes_path),
            },
            "nextActions": "Done." if not args.dry_run else "Run without --dry-run to apply changes.",
        }
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print_json({"status": "failed", "error": str(exc)})
        raise SystemExit(1)
