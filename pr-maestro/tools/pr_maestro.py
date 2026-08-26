#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from _pr_helpers import (
    CommandError,
    build_template_body,
    current_branch,
    default_title,
    diff_data,
    open_pr_for_branch,
    parse_lcov_summary,
    print_json,
    run,
)

TOOLS_DIR = Path(__file__).resolve().parent
# Detect project root via git, falling back to TOOLS_DIR.parents[3] for non-symlink installs
try:
    import subprocess as _sp
    ROOT = Path(_sp.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
except Exception:
    ROOT = TOOLS_DIR.parents[3]
TAG_HELPER = ROOT / ".github/scripts/tag-release-helper.sh"
CONFIG_PATH = TOOLS_DIR / "config.json"


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

    default_create_tag = cfg_bool(config, "defaults", "createTag", False)
    default_create_or_update_pr = cfg_bool(config, "defaults", "createOrUpdatePr", True)
    default_draft = cfg_bool(config, "defaults", "draft", False)
    default_quality_gate = cfg_bool(config, "quality", "requirePassingTests", True)

    parser = argparse.ArgumentParser(description="Orchestrate tag + PR template + create/update PR.")
    parser.add_argument("--base", default=default_base)
    parser.add_argument("--bump", choices=["auto", "major", "minor", "patch"], default=default_bump)
    parser.add_argument(
        "--create-tag",
        action=argparse.BooleanOptionalAction,
        default=default_create_tag,
        help="Create/push semantic tag (default from config). Use --no-create-tag to disable.",
    )
    parser.add_argument(
        "--create-or-update-pr",
        action=argparse.BooleanOptionalAction,
        default=default_create_or_update_pr,
        help="Create or update PR flow (default from config). Use --no-create-or-update-pr to disable.",
    )
    parser.add_argument("--title", default=None)
    parser.add_argument(
        "--draft",
        action=argparse.BooleanOptionalAction,
        default=default_draft,
        help="Create PR as draft (default from config). Use --no-draft to disable.",
    )
    parser.add_argument(
        "--quality-gate",
        action=argparse.BooleanOptionalAction,
        default=default_quality_gate,
        help="Execute quality-gate commands before PR generation/update (default from config).",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def apply_runtime_config(config: dict) -> None:
    write_bytecode = cfg_bool(config, "python", "writeBytecode", False)

    if not write_bytecode:
        sys.dont_write_bytecode = True
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"


def parse_tag_helper_output(raw: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in raw.splitlines():
        if "=" in line and not line.startswith("COMMITS_"):
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def resolve_next_tag(bump: str) -> tuple[str, dict[str, str]]:
    output = run(["bash", str(TAG_HELPER)])
    parsed = parse_tag_helper_output(output)
    chosen = bump
    if chosen == "auto":
        chosen = parsed.get("RECOMMENDED_BUMP", "patch")
    key = {
        "major": "NEXT_MAJOR",
        "minor": "NEXT_MINOR",
        "patch": "NEXT_PATCH",
    }[chosen]
    return parsed[key], parsed


def ensure_gh_auth() -> None:
    proc = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
    if proc.returncode != 0:
        raise CommandError("GitHub CLI is not authenticated. Run: gh auth login")


def create_and_push_tag(tag: str, dry_run: bool) -> str:
    exists = run(["git", "tag", "--list", tag])
    if exists.strip() == tag:
        return "already_exists"
    if dry_run:
        return "dry_run"
    run(["git", "tag", tag])
    run(["git", "push", "origin", tag])
    return "created"


def run_quality_gate(config: dict, enabled: bool) -> dict:
    quality_section = config.get("quality", {}) if isinstance(config, dict) else {}
    commands = quality_section.get(
        "commands",
        [
            "pnpm coverage",
            "pnpm run typecheck",
            "pnpm run lint",
        ],
    )
    blocking_commands = quality_section.get("blockingCommands", ["pnpm coverage"])
    normalized_blocking_commands = [
        command for command in blocking_commands if isinstance(command, str) and command.strip()
    ]

    if not enabled:
        return {
            "enabled": False,
            "allPassed": True,
            "commands": [],
            "coverage": None,
        }

    results: list[dict] = []
    blocking_passed = True

    for command in commands:
        if not isinstance(command, str) or not command.strip():
            continue

        started = time.monotonic()
        is_windows = sys.platform == "win32"
        process = subprocess.run(
            shlex.split(command),
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=os.environ.copy(),
            shell=is_windows,
        )
        duration = round(time.monotonic() - started, 2)
        stdout = (process.stdout or "").strip()
        stderr = (process.stderr or "").strip()

        results.append(
            {
                "command": command,
                "exitCode": process.returncode,
                "durationSeconds": duration,
                "outputTail": "\n".join((stdout + "\n" + stderr).strip().splitlines()[-12:]).strip(),
            }
        )

        if process.returncode != 0 and command in normalized_blocking_commands:
            blocking_passed = False

    coverage = parse_lcov_summary(ROOT / "coverage/lcov.info")

    non_blocking_failures = [
        item
        for item in results
        if int(item.get("exitCode", 1)) != 0 and item.get("command") not in normalized_blocking_commands
    ]

    return {
        "enabled": True,
        "allPassed": blocking_passed,
        "blockingPassed": blocking_passed,
        "blockingCommands": normalized_blocking_commands,
        "nonBlockingFailures": non_blocking_failures,
        "commands": results,
        "coverage": coverage,
    }


def main() -> int:
    config = load_config()
    apply_runtime_config(config)

    args = parse_args(config)
    ensure_gh_auth()

    steps: list[dict[str, str]] = []
    tag_value = None

    quality_report = run_quality_gate(config, args.quality_gate)
    quality_status = "passed" if quality_report.get("allPassed", False) else "failed"
    steps.append(
        {
            "name": "quality-gate",
            "status": quality_status,
            "details": "Quality gate commands executed" if quality_report.get("enabled") else "Skipped by configuration",
        }
    )

    if quality_report.get("enabled") and not quality_report.get("blockingPassed", False):
        print_json(
            {
                "status": "failed",
                "tag": None,
                "pr": None,
                "steps": steps,
                "qualityGate": quality_report,
                "nextActions": "Fix failing blocking test commands before generating/updating PR.",
            }
        )
        return 1

    branch = current_branch()
    diff = diff_data(args.base)
    title = args.title or default_title(branch, diff.commits)
    body = build_template_body(
        args.base,
        branch,
        title,
        diff.commits,
        diff.files,
        quality_report=quality_report,
    )

    if args.create_tag:
        tag_value, tag_meta = resolve_next_tag(args.bump)
        tag_status = create_and_push_tag(tag_value, args.dry_run)
        steps.append(
            {
                "name": "create-tag",
                "status": tag_status,
                "details": f"resolved={tag_value}, recommended={tag_meta.get('RECOMMENDED_BUMP', 'n/a')}",
            }
        )

    pr_data = None
    if args.create_or_update_pr:
        existing = open_pr_for_branch(args.base, branch)
        if not existing:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tmp:
                tmp.write(body)
                tmp.flush()
                tmp_body = tmp.name

            create_cmd = [
                sys.executable,
                str(TOOLS_DIR / "pr_create_or_get.py"),
                "--base",
                args.base,
                "--title",
                title,
                "--body-file",
                tmp_body,
            ]
            if args.draft:
                create_cmd.append("--draft")
            if args.dry_run:
                create_cmd.append("--dry-run")

            created_json = json.loads(run(create_cmd))
            steps.append(
                {
                    "name": "push-pull-request",
                    "status": created_json.get("status", "unknown"),
                    "details": created_json.get("prUrl", "n/a"),
                }
            )
            pr_data = created_json
            pr_number = created_json.get("prNumber")
        else:
            pr_number = existing["number"]
            pr_data = {
                "status": "already_exists",
                "prNumber": existing["number"],
                "prUrl": existing["url"],
                "title": existing["title"],
            }

        if pr_number:
            apply_cmd = [
                sys.executable,
                str(TOOLS_DIR / "pr_template_apply.py"),
                "--base",
                args.base,
                "--pr-number",
                str(pr_number),
                "--title",
                title,
            ]

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as quality_tmp:
                json.dump(quality_report, quality_tmp, ensure_ascii=False)
                quality_tmp.flush()
                quality_report_file = quality_tmp.name

            apply_cmd.extend(["--quality-report-file", quality_report_file])
            if args.dry_run:
                apply_cmd.append("--dry-run")

            applied_json = json.loads(run(apply_cmd))
            steps.append(
                {
                    "name": "apply-pr-template",
                    "status": applied_json.get("status", "unknown"),
                    "details": applied_json.get("prUrl", "n/a"),
                }
            )
            pr_data = {
                "status": applied_json.get("status", pr_data.get("status") if pr_data else "unknown"),
                "prNumber": applied_json.get("prNumber", pr_data.get("prNumber") if pr_data else None),
                "prUrl": applied_json.get("prUrl", pr_data.get("prUrl") if pr_data else None),
                "title": applied_json.get("title", pr_data.get("title") if pr_data else title),
            }

    status = "success"
    if any(step.get("status") == "failed" for step in steps):
        status = "failed"

    print_json(
        {
            "status": status,
            "tag": tag_value,
            "pr": pr_data,
            "steps": steps,
            "qualityGate": quality_report,
            "nextActions": "Run without --dry-run to apply changes." if args.dry_run else "Done.",
        }
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print_json({"status": "failed", "error": str(exc)})
        raise SystemExit(1)
