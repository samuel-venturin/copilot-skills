#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


def _detect_repo_root() -> Path:
    """Detect git repository root from current working directory."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True,
        )
        return Path(result.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


ROOT = _detect_repo_root()
SEMVER_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
KNOWN_TYPES = {"FEAT", "FIX", "CHORE", "DOCS", "TEST", "REFACTOR", "PERF", "CI"}


class CommandError(RuntimeError):
    pass


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
    if check and proc.returncode != 0:
        raise CommandError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\\n{stderr or stdout}"
        )
    return stdout


def try_run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
    return proc.returncode, stdout, stderr


def print_json(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def repo_name_with_owner() -> str:
    out = run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    if "/" not in out:
        raise CommandError("Could not determine owner/repo from gh cli.")
    return out


def ensure_gh_auth() -> None:
    rc, _, _ = try_run(["gh", "auth", "status"])
    if rc != 0:
        raise CommandError("GitHub CLI is not authenticated. Run: gh auth login")


def fetch_tags_from_origin() -> None:
    """Sync tags from origin before any tag-based logic runs.

    Without this, ``git for-each-ref refs/tags/...`` only sees locally cached
    tags and can miss tags created by CI or other teammates since the last fetch.
    """
    run(["git", "fetch", "--tags", "origin"], check=False)


@dataclass
class TagWindow:
    latest_tag: str
    previous_tag: str | None
    outlier_detected: bool
    range_since_latest: str


def _parse_semver(tag: str) -> tuple[int, int, int] | None:
    match = SEMVER_RE.match(tag.strip())
    if not match:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _list_tags_by_creation_date() -> list[str]:
    """Return semver tags sorted by creation date, most recent first.

    Uses ``git for-each-ref --sort=-creatordate`` which respects the actual
    timestamp the tag object (or the tagged commit for lightweight tags) was
    created — independent of the semver number, so accidental high-number tags
    never shadow the real latest release.
    """
    tags_raw = run([
        "git", "for-each-ref",
        "--sort=-creatordate",
        "--format=%(refname:short)",
        "refs/tags/v*.*.*",
    ])
    return [line.strip() for line in tags_raw.splitlines() if _parse_semver(line.strip())]


def detect_tag_window(from_tag: str | None = None, base: str | None = None) -> TagWindow:
    range_tip = f"origin/{base}" if base else "HEAD"

    if from_tag:
        parsed = _parse_semver(from_tag)
        if not parsed:
            raise CommandError(f"--from-tag value is not a valid semver tag: {from_tag}")
        # For the previous-tag lookup, use creation-date order as well
        tags_by_date = _list_tags_by_creation_date()
        try:
            idx = tags_by_date.index(from_tag)
            previous_tag = tags_by_date[idx + 1] if (idx + 1) < len(tags_by_date) else None
        except ValueError:
            previous_tag = None
        return TagWindow(
            latest_tag=from_tag,
            previous_tag=previous_tag,
            outlier_detected=False,
            range_since_latest=f"{from_tag}..{range_tip}",
        )

    # Sort by creation date (most recently created tag first).
    # This is intentional: the last tag that was actually created is always the
    # correct baseline, regardless of its semver number — avoids picking up
    # accidental high-number tags (e.g. v11.x) over real ones (e.g. v1.65.x).
    tags = _list_tags_by_creation_date()

    if not tags:
        return TagWindow(
            latest_tag="v0.0.0",
            previous_tag=None,
            outlier_detected=False,
            range_since_latest=range_tip,
        )

    latest_tag = tags[0]
    previous_tag = tags[1] if len(tags) > 1 else None

    return TagWindow(
        latest_tag=latest_tag,
        previous_tag=previous_tag,
        outlier_detected=False,
        range_since_latest=f"{latest_tag}..{range_tip}",
    )


def next_tag_for_bump(latest_tag: str, bump: str) -> str:
    parsed = _parse_semver(latest_tag)
    if not parsed:
        raise CommandError(f"Invalid semantic tag: {latest_tag}")

    major, minor, patch = parsed
    if bump == "major":
        return f"v{major + 1}.0.0"
    if bump == "minor":
        return f"v{major}.{minor + 1}.0"
    if bump == "patch":
        return f"v{major}.{minor}.{patch + 1}"

    raise CommandError(f"Unsupported bump type: {bump}")


def commits_since_latest(range_since_latest: str) -> list[dict[str, str]]:
    if range_since_latest == "HEAD":
        log_out = run(["git", "log", "--pretty=format:%H|%s", "HEAD"])
    else:
        log_out = run(["git", "log", "--pretty=format:%H|%s", range_since_latest])

    result: list[dict[str, str]] = []
    for line in log_out.splitlines():
        if "|" not in line:
            continue
        commit_hash, subject = line.split("|", 1)
        commit_hash = commit_hash.strip()
        subject = subject.strip()
        if commit_hash:
            result.append({"sha": commit_hash, "subject": subject})
    return result


def _parse_pr_type_from_title(title: str) -> str | None:
    tokens = re.findall(r"\[([^\]]+)\]", title)
    normalized = [token.strip().upper() for token in tokens if token.strip()]

    for token in normalized:
        if token in KNOWN_TYPES:
            return token

    for token in normalized:
        if "-" in token:
            continue
        if token.isalpha() and 2 <= len(token) <= 10:
            return token

    return None


def merged_prs_from_commits(owner_repo: str, commits: list[dict[str, str]]) -> list[dict]:
    seen_numbers: set[int] = set()
    result: list[dict] = []

    for item in commits:
        sha = item.get("sha", "").strip()
        if not sha:
            continue

        rc, stdout, stderr = try_run(
            [
                "gh",
                "api",
                f"repos/{owner_repo}/commits/{sha}/pulls",
                "--method",
                "GET",
                "-H",
                "Accept: application/vnd.github+json",
            ]
        )
        if rc != 0:
            message = stderr or stdout
            raise CommandError(f"Could not list PRs for commit {sha}: {message}")

        payload = json.loads(stdout or "[]")
        if not isinstance(payload, list):
            continue

        for pr in payload:
            if not isinstance(pr, dict):
                continue
            number = pr.get("number")
            if not isinstance(number, int) or number in seen_numbers:
                continue

            merged_at = pr.get("merged_at")
            if not merged_at:
                continue

            title = str(pr.get("title") or "").strip()
            pr_type = _parse_pr_type_from_title(title)
            result.append(
                {
                    "number": number,
                    "title": title,
                    "url": pr.get("html_url"),
                    "mergedAt": merged_at,
                    "type": pr_type or "UNKNOWN",
                }
            )
            seen_numbers.add(number)

    result.sort(key=lambda item: str(item.get("mergedAt", "")))
    return result


def count_pr_types(prs: list[dict]) -> dict[str, int]:
    counts = Counter(str(item.get("type") or "UNKNOWN").upper() for item in prs)
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def suggest_bump_from_pr_types(type_counts: dict[str, int]) -> tuple[str, str]:
    if not type_counts:
        raise CommandError("No PR type data available.")

    top_count = max(type_counts.values())
    top_types = sorted([kind for kind, count in type_counts.items() if count == top_count])

    if len(top_types) > 1:
        return "minor", "tie_between_top_types"

    top_type = top_types[0]
    if top_type == "FEAT":
        return "minor", "feat_dominant"

    return "patch", "non_feat_dominant"


def git_tag_exists(tag: str) -> bool:
    existing = run(["git", "tag", "--list", tag])
    return existing.strip() == tag


@dataclass
class MergeGateResult:
    passed: bool
    prs: list[dict]


def check_pr_merge_gate(owner_repo: str, prs: list[dict]) -> MergeGateResult:
    """Verify every PR in the release window is truly merged on GitHub.

    Each entry is re-verified via ``gh pr view`` regardless of what the git log
    says — a closed-but-not-merged PR could appear in the commit graph if the
    branch was force-pushed or cherry-picked.

    Gate rules:
    - PR state must be ``MERGED`` (not ``OPEN`` or ``CLOSED``).
    - If all PRs pass → ``MergeGateResult.passed = True``.
    - If any PR is not yet merged → ``passed = False`` with details.
    """
    results: list[dict] = []
    all_passed = True

    for pr in prs:
        number = pr.get("number")
        if not isinstance(number, int):
            continue

        rc, out, err = try_run([
            "gh", "pr", "view", str(number),
            "--repo", owner_repo,
            "--json", "number,title,state,mergedAt,url",
        ])

        if rc != 0:
            results.append({
                "pr": number,
                "title": pr.get("title", ""),
                "gate": "error",
                "reason": err or out,
            })
            all_passed = False
            continue

        data = json.loads(out or "{}")
        state = str(data.get("state") or "").upper()
        merged_at = data.get("mergedAt")
        is_merged = state == "MERGED" and bool(merged_at)

        results.append({
            "pr": number,
            "title": data.get("title", pr.get("title", "")),
            "url": data.get("url", pr.get("url", "")),
            "state": state,
            "mergedAt": merged_at,
            "gate": "passed" if is_merged else "blocked",
        })

        if not is_merged:
            all_passed = False

    return MergeGateResult(passed=all_passed, prs=results)


def create_and_push_tag(tag: str, *, dry_run: bool, confirmed: bool, target: str | None = None) -> str:
    if git_tag_exists(tag):
        return "already_exists"

    if not confirmed:
        return "needs_confirmation"

    if dry_run:
        return "dry_run"

    cmd = ["git", "tag", tag]
    if target:
        cmd.append(target)
    run(cmd)
    run(["git", "push", "origin", tag])
    return "created"


def parse_kv_and_blocks(raw: str) -> tuple[dict[str, str], dict[str, list[str]]]:
    scalars: dict[str, str] = {}
    blocks: dict[str, list[str]] = {}

    current_block: str | None = None
    current_lines: list[str] = []

    for line in raw.splitlines():
        if line.endswith("_START"):
            current_block = line[: -len("_START")]
            current_lines = []
            continue

        if line.endswith("_END") and current_block and line == f"{current_block}_END":
            blocks[current_block] = current_lines[:]
            current_block = None
            current_lines = []
            continue

        if current_block is not None:
            current_lines.append(line)
            continue

        if "=" in line:
            key, value = line.split("=", 1)
            scalars[key.strip()] = value.strip()

    return scalars, blocks


def _find_bash() -> str:
    """Find the best bash for the current platform (prefer Git Bash on Windows)."""
    if sys.platform == "win32":
        git_bash = Path("C:/Program Files/Git/bin/bash.exe")
        if git_bash.exists():
            return str(git_bash)
    return "bash"


def _run_bash_script(script_path: Path, cwd: Path | None = None, env: dict[str, str] | None = None) -> str:
    """Run a bash script, normalizing CRLF line endings for WSL/Linux bash compatibility."""
    import os
    content = script_path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    merged_env = {**os.environ, **(env or {})}
    proc = subprocess.run(
        [_find_bash()],
        input=content.encode("utf-8"),
        cwd=str(cwd or ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=merged_env,
    )
    stdout = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
    stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
    if proc.returncode != 0:
        raise CommandError(
            f"Script failed ({proc.returncode}): {script_path.name}\n{stderr or stdout}"
        )
    return stdout


def collect_release_data(last_tag: str | None = None, previous_tag: str | None = None) -> tuple[dict[str, str], dict[str, list[str]]]:
    env: dict[str, str] = {}
    if last_tag:
        env["RELEASE_LAST_TAG"] = last_tag
    if previous_tag:
        env["RELEASE_PREVIOUS_TAG"] = previous_tag
    output = _run_bash_script(ROOT / ".github/scripts/release-data.sh", env=env)
    return parse_kv_and_blocks(output)


def collect_coverage_data(run_coverage: bool) -> dict[str, str]:
    if not run_coverage:
        return {
            "COVERAGE_LINES": "skipped",
            "COVERAGE_HIT": "0",
            "COVERAGE_FOUND": "0",
        }

    output = _run_bash_script(ROOT / ".github/scripts/release-coverage.sh")
    scalars, _ = parse_kv_and_blocks(output)
    return {
        "COVERAGE_LINES": scalars.get("COVERAGE_LINES", "unknown"),
        "COVERAGE_HIT": scalars.get("COVERAGE_HIT", "0"),
        "COVERAGE_FOUND": scalars.get("COVERAGE_FOUND", "0"),
    }


def summarize_release_title(tag: str, prs: list[dict], max_len: int = 100) -> str:
    default_summary = "release updates"
    summary = default_summary

    if prs:
        top = prs[-1]
        title = str(top.get("title") or "").strip()
        normalized = re.sub(r"\s+", " ", title)
        normalized = re.sub(r"\[[^\]]+\]", "", normalized).strip(" -:")
        if normalized:
            summary = normalized.lower()

    composed = f"{tag} - {summary}"
    if len(composed) <= max_len:
        return composed

    room = max(1, max_len - (len(tag) + 3))
    return f"{tag} - {summary[:room].rstrip()}"


def build_overview_non_technical(prs: list[dict], release_data: dict[str, str]) -> str:
    commit_count = release_data.get("COMMIT_COUNT", "0")
    contributor_count = release_data.get("AUTHOR_COUNT", "0")
    file_count = release_data.get("FILE_COUNT", "0")

    if prs:
        feat_count = sum(1 for item in prs if str(item.get("type", "")).upper() == "FEAT")
        if feat_count > 0:
            return (
                f"This release adds user-facing improvements and functional updates. "
                f"It consolidates {commit_count} commits from {contributor_count} contributors "
                f"with coordinated changes across {file_count} files."
            )

    return (
        f"This release delivers maintenance and reliability improvements. "
        f"It packages {commit_count} commits from {contributor_count} contributors "
        f"touching {file_count} files."
    )


def render_release_notes(
    *,
    template_path: Path,
    release_data: dict[str, str],
    release_blocks: dict[str, list[str]],
    coverage_data: dict[str, str],
    title: str,
    overview: str,
) -> str:
    template = template_path.read_text(encoding="utf-8")

    replacements = {
        "TAG": release_data.get("LAST_TAG", "n/a"),
        "TITLE": title,
        "PREVIOUS_TAG": release_data.get("PREVIOUS_TAG", "none"),
        "FIRST_COMMIT_AT": release_data.get("FIRST_COMMIT_AT", "n/a"),
        "LAST_COMMIT_AT": release_data.get("LAST_COMMIT_AT", "n/a"),
        "TIME_WINDOW_HOURS": release_data.get("TIME_WINDOW_HOURS", "0"),
        "COMMIT_COUNT": release_data.get("COMMIT_COUNT", "0"),
        "AUTHOR_COUNT": release_data.get("AUTHOR_COUNT", "0"),
        "FILE_COUNT": release_data.get("FILE_COUNT", "0"),
        "COMPLEXITY_SCORE": release_data.get("COMPLEXITY_SCORE", "0"),
        "COMPLEXITY_BOMBS": release_data.get("COMPLEXITY_BOMBS", "💣"),
        "COVERAGE_LINES": coverage_data.get("COVERAGE_LINES", "unknown"),
        "COVERAGE_HIT": coverage_data.get("COVERAGE_HIT", "0"),
        "COVERAGE_FOUND": coverage_data.get("COVERAGE_FOUND", "0"),
        "OVERVIEW": overview,
        "AUTHORS_LIST": "\n".join(release_blocks.get("AUTHORS", ["- n/a"])),
        "COMMITS_LIST": "\n".join(release_blocks.get("COMMITS", ["- n/a"])),
        "FILES_LIST": "\n".join(release_blocks.get("FILES", ["- n/a"])),
    }

    output = template
    for key, value in replacements.items():
        output = output.replace(f"{{{{{key}}}}}", value)

    return output


def release_exists(tag: str) -> bool:
    rc, _, _ = try_run(["gh", "release", "view", tag, "--json", "url"])
    return rc == 0


def create_or_update_release(*, tag: str, title: str, notes_file: Path, dry_run: bool) -> tuple[str, str]:
    exists = release_exists(tag)

    if dry_run:
        status = "would_update" if exists else "would_create"
        return status, f"https://github.com/{repo_name_with_owner()}/releases/tag/{tag}"

    if exists:
        run([
            "gh",
            "release",
            "edit",
            tag,
            "--title",
            title,
            "--notes-file",
            str(notes_file),
        ])
        status = "updated"
    else:
        run([
            "gh",
            "release",
            "create",
            tag,
            "--title",
            title,
            "--notes-file",
            str(notes_file),
        ])
        status = "created"

    url = run(["gh", "release", "view", tag, "--json", "url", "--jq", ".url"])
    return status, url


def split_command(command: str) -> list[str]:
    return shlex.split(command)
