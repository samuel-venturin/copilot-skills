#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[4]
# Override with git-detected root when running via symlink
try:
    import subprocess as _sp
    _git_root = _sp.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()
    if _git_root:
        ROOT = Path(_git_root)
except Exception:
    pass


class CommandError(RuntimeError):
    pass


def run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
    )
    if check and proc.returncode != 0:
        raise CommandError(
            f"Command failed ({proc.returncode}): {' '.join(cmd)}\\n{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return (proc.stdout or "").strip()


def try_run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "").strip(), (proc.stderr or "").strip()


def current_branch() -> str:
    return run(["git", "rev-parse", "--abbrev-ref", "HEAD"])


def repo_name_with_owner() -> str:
    out = run(["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"])
    if "/" not in out:
        raise CommandError("Could not determine owner/repo from gh cli.")
    return out


def infer_ticket(branch: str, commits: Iterable[str] | None = None) -> str:
    branch_match = re.search(r"([A-Z]+-\d+)", branch)
    if branch_match:
        return branch_match.group(1)

    if commits:
        for subject in commits:
            commit_match = re.search(r"\[([A-Z]+-\d+)\]", subject)
            if commit_match:
                return commit_match.group(1)

    return "TODO-TICKET"


def infer_type_from_commits(commits: list[str]) -> str:
    weights = {
        "FEAT": 0,
        "FIX": 0,
        "REFAC": 0,
        "TEST": 0,
        "DOCS": 0,
        "CHORE": 0,
    }
    for item in commits:
        match = re.search(r"\[[A-Z]+-\d+\]\[([A-Z]+)\]", item)
        if match and match.group(1) in weights:
            weights[match.group(1)] += 1

    if weights["FEAT"] > 0:
        return "FEAT"
    if weights["FIX"] > 0:
        return "FIX"

    dominant = max(weights.items(), key=lambda kv: kv[1])
    return dominant[0] if dominant[1] > 0 else "CHORE"


def default_title(branch: str, commits: list[str]) -> str:
    import re as _re
    ticket = infer_ticket(branch, commits)
    change_type = infer_type_from_commits(commits)

    # Try to read task description from docs/tasks/<TICKET>/PROMPT.md
    prompt_path = ROOT / "docs" / "tasks" / ticket / "PROMPT.md"
    if prompt_path.exists():
        for line in prompt_path.read_text(encoding="utf-8").splitlines():
            # Match: # PROMPT — CTR-XXXX: <description>
            m = _re.match(r"^#\s+PROMPT\s+[-—]+\s+[A-Z]+-\d+[:\s]+(.+)$", line.strip())
            if m:
                return f"[{ticket}][{change_type}]: {m.group(1).strip()}"

    # Fallback: try PRD.md title
    prd_path = ROOT / "docs" / "tasks" / ticket / "PRD.md"
    if prd_path.exists():
        for line in prd_path.read_text(encoding="utf-8").splitlines():
            m = _re.match(r"^#\s+(?:PRD[:\s]+)?(.+?)\s+[-—]+\s+[A-Z]+-\d+", line.strip())
            if m:
                return f"[{ticket}][{change_type}]: {m.group(1).strip()}"

    return f"[{ticket}][{change_type}]: update pull request changelog"


@dataclass
class DiffData:
    commits: list[str]
    files: list[str]


def diff_data(base: str) -> DiffData:
    commits_output = run(["git", "log", "--oneline", "--no-merges", f"origin/{base}..HEAD"]) if _has_origin_base(base) else run(["git", "log", "--oneline", "--no-merges", f"{base}..HEAD"])
    files_output = run(["git", "diff", "--name-only", f"{base}...HEAD"])

    commits = [line.strip() for line in commits_output.splitlines() if line.strip()]
    files = [line.strip() for line in files_output.splitlines() if line.strip()]
    return DiffData(commits=commits, files=files)


def _has_origin_base(base: str) -> bool:
    rc, _, _ = try_run(["git", "rev-parse", "--verify", f"origin/{base}"])
    return rc == 0


def filter_main_files(files: list[str]) -> list[str]:
    excluded_suffixes = (
        ".md",
        ".txt",
        ".lock",
        ".yaml",
        ".yml",
        ".json",
    )
    excluded_prefixes = (
        ".github/",
        "specs/",
        "dev_docs/",
        "coverage/",
        "logs/",
        "playwright-evidence/",
    )

    main = [
        path
        for path in files
        if not path.endswith(excluded_suffixes) and not path.startswith(excluded_prefixes)
    ]
    return main[:12]


def detect_areas(files: list[str]) -> list[str]:
    areas: list[str] = []
    rules = [
        ("app/pages/auxiliary_registries/tax/", "Tax exemption pages and user flow"),
        ("app/components/tax-exemption-type/", "Tax exemption form components"),
        ("app/composables/tax-exemptions/", "Tax exemption composables and repositories"),
        ("app/contracts/", "API contracts and schemas"),
        ("app/models/", "Domain models and mappers"),
        ("app/services/", "HTTP layer and service integration"),
        ("app/stores/", "Store behavior and state handling"),
        ("i18n/locales/", "Localization and translated labels"),
        (".github/skills/pr-maestro/", "Automation tooling for PR operations"),
        ("specs/e2e/", "E2E playbook definitions"),
    ]

    for prefix, label in rules:
        if any(file_path.startswith(prefix) for file_path in files):
            areas.append(label)

    if not areas:
        areas.append("General codebase maintenance and alignment")

    return areas[:3]


def summarize_commits(commits: list[str]) -> list[str]:
    if not commits:
        return ["No new commits were detected against the selected base branch."]

    commit_count = len(commits)
    inferred_type = infer_type_from_commits(commits)

    summary = [
        f"Included {commit_count} commit(s) from the current branch diff.",
        f"Dominant change profile inferred from commits: `{inferred_type}`.",
    ]

    if any("municip" in commit.lower() or "uf" in commit.lower() or "tax" in commit.lower() for commit in commits):
        summary.append("Captured tax exemption flow updates, including UF/municipality related behavior changes.")
    else:
        summary.append("Captured branch updates and synchronized PR narrative with repository standards.")

    return summary


def collect_test_evidence_from_commits(commits: list[str]) -> str:
    lowered = " ".join(commits).lower()

    if "test" in lowered or "__tests__" in lowered:
        return "Includes test-related commits in branch history"

    return "No explicit test execution evidence captured by automation run"


def _format_percentage(hit: int, total: int) -> str:
    if total <= 0:
        return "N/A"
    return f"{(hit / total) * 100:.2f}%"


def parse_lcov_summary(lcov_path: Path) -> dict[str, str] | None:
    if not lcov_path.exists():
        return None

    lf = lh = fnf = fnh = brf = brh = 0

    for raw_line in lcov_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if line.startswith("LF:"):
            lf += int(line[3:] or 0)
        elif line.startswith("LH:"):
            lh += int(line[3:] or 0)
        elif line.startswith("FNF:"):
            fnf += int(line[4:] or 0)
        elif line.startswith("FNH:"):
            fnh += int(line[4:] or 0)
        elif line.startswith("BRF:"):
            brf += int(line[4:] or 0)
        elif line.startswith("BRH:"):
            brh += int(line[4:] or 0)

    return {
        "lines": _format_percentage(lh, lf),
        "functions": _format_percentage(fnh, fnf),
        "branches": _format_percentage(brh, brf),
        "statements": _format_percentage(lh, lf),
    }


def build_tests_and_coverage_sections(
    quality_report: dict | None,
    commits: list[str],
) -> tuple[list[str], list[str], list[str]]:
    if not quality_report:
        tests_lines = [
            f"- [ ] `pnpm coverage` ({collect_test_evidence_from_commits(commits)})",
            "- [ ] `pnpm run typecheck`",
            "- [ ] `pnpm run lint`",
            "- Result summary:",
            "  - No automated quality gate execution data was provided for this run.",
        ]
        coverage_lines = [
            "- Coverage command was not executed by automation in this run.",
        ]
        return tests_lines, coverage_lines, []

    command_results: list[dict] = quality_report.get("commands", [])
    result_by_command = {
        item.get("command", ""): item
        for item in command_results
        if isinstance(item, dict)
    }

    def checkbox(command: str) -> str:
        result = result_by_command.get(command)
        if not result:
            return "[ ]"
        return "[x]" if int(result.get("exitCode", 1)) == 0 else "[ ]"

    tests_lines = [
        f"- {checkbox('pnpm coverage')} `pnpm coverage`",
        f"- {checkbox('pnpm run typecheck')} `pnpm run typecheck`",
        f"- {checkbox('pnpm run lint')} `pnpm run lint`",
        "- Result summary:",
    ]

    blocking_passed = bool(quality_report.get("blockingPassed", quality_report.get("allPassed", False)))
    blocking_commands = quality_report.get("blockingCommands", ["pnpm coverage"])
    blocking_display = ", ".join(blocking_commands) if isinstance(blocking_commands, list) else "pnpm coverage"

    if blocking_passed:
        tests_lines.append(f"  - Blocking test command(s) passed: {blocking_display}.")
    else:
        failed = [
            item.get("command", "unknown")
            for item in command_results
            if int(item.get("exitCode", 1)) != 0
        ]
        tests_lines.append(f"  - Blocking test command(s) failed: {', '.join(failed) if failed else 'unknown' }.")

    non_blocking_failures = quality_report.get("nonBlockingFailures", [])
    attention_notes: list[str] = []
    if isinstance(non_blocking_failures, list) and non_blocking_failures:
        attention_notes.append("Attention required (non-blocking quality failures):")
        for failure in non_blocking_failures:
            command = str(failure.get("command", "unknown"))
            output_tail = str(failure.get("outputTail", "")).strip()
            reason_line = output_tail.splitlines()[0].strip() if output_tail else "No output available"
            attention_notes.append(f"{command}: {reason_line}")
            if output_tail:
                for detail_line in output_tail.splitlines()[:2]:
                    cleaned = detail_line.strip()
                    if cleaned:
                        attention_notes.append(f"{command} detail: {cleaned}")

    coverage = quality_report.get("coverage")
    if isinstance(coverage, dict):
        coverage_lines = [
            f"- Lines: {coverage.get('lines', 'N/A')}",
            f"- Statements: {coverage.get('statements', 'N/A')}",
            f"- Functions: {coverage.get('functions', 'N/A')}",
            f"- Branches: {coverage.get('branches', 'N/A')}",
        ]
    else:
        coverage_lines = [
            "- Coverage artifact not found after `pnpm coverage` execution.",
        ]

    return tests_lines, coverage_lines, attention_notes


def build_risk_notes(files: list[str]) -> list[str]:
    notes: list[str] = []

    if len(files) >= 30:
        notes.append("Large diff scope; review by domain area is recommended before merge.")

    if any(path.startswith("app/services/") or path.startswith("app/contracts/") for path in files):
        notes.append("Integration contract changes may impact backend compatibility assumptions.")

    if any(path.startswith(".github/skills/pr-maestro/") for path in files):
        notes.append("Automation scripts were updated; validate workflow behavior in dry-run before release automation.")

    if not notes:
        notes.append("No critical risks identified by heuristic scan of changed paths.")

    return notes[:3]


def build_template_body(
    base: str,
    branch: str,
    title: str,
    commits: list[str],
    files: list[str],
    quality_report: dict | None = None,
) -> str:
    ticket = infer_ticket(branch, commits)
    main_files = filter_main_files(files)
    first_commits = commits[:10]
    repo_name = repo_name_with_owner().split("/")[-1] if "/" in repo_name_with_owner() else repo_name_with_owner()

    summary_lines = [f"- {line}" for line in summarize_commits(commits)]
    summary_lines.append(f"- Synced content from diff against `{base}` with ticket `{ticket}`.")

    areas = detect_areas(files)
    risk_notes = build_risk_notes(files)
    tests_lines, coverage_lines, attention_notes = build_tests_and_coverage_sections(quality_report, commits)
    risk_notes.extend(attention_notes)

    commits_lines = [
        f"{idx + 1}. `{line.split()[0]}` — `{' '.join(line.split()[1:])}`"
        for idx, line in enumerate(first_commits)
    ]
    if not commits_lines:
        commits_lines = ["1. `N/A` — `No commits detected for selected range`"]

    files_lines = [f"- `{path}`" for path in (main_files or ["N/A"]) ]

    body = [
        "# 📘 PR Changelog — `" + repo_name + "`",
        "",
        "## 🗓️ Date",
        date.today().isoformat(),
        "",
        "## 🎫 Ticket",
        ticket,
        "",
        "## ✅ Summary of work completed",
        *summary_lines,
        "",
        "---",
        "",
        "## 🧩 Commits in this PR",
        *commits_lines,
        "",
        "---",
        "",
        "## 🔧 Technical details",
        "",
        f"### 1) `{areas[0]}`",
        "- Primary scope concentrated in this area based on changed paths.",
        "- Behavior and integration narrative aligned to current branch diff.",
        "",
        f"### 2) `{areas[1] if len(areas) > 1 else 'Supporting domain updates'}`",
        "- Secondary scope reflects supporting code and data flow adjustments.",
        "- Preserves consistency between implementation and contract expectations.",
        "",
        f"### 3) `{areas[2] if len(areas) > 2 else 'Quality and operability'}`",
        "- Documents impact in a reviewer-friendly structure tied to real changes.",
        "- Maintains explicit evidence semantics without fabricating command results.",
        "",
        "---",
        "",
        "## 🧪 Tests",
        *tests_lines,
        "",
        "---",
        "",
        "## 📊 Coverage",
        *coverage_lines,
        "",
        "---",
        "",
        "## 📂 Main files impacted",
        *files_lines,
        "",
        "---",
        "",
        "## ⚠️ Notes / Risks",
        *[f"- {note}" for note in risk_notes],
        "",
        "## 🧾 Checklist",
        "- [ ] I tested the main flow manually",
        "- [ ] I added/updated automated tests as needed",
        "- [ ] I kept changes scoped and backward-compatible (or documented breaking changes)",
    ]

    return "\n".join(body).strip() + "\n"


def open_pr_for_branch(base: str, head: str) -> dict | None:
    output = run(
        [
            "gh",
            "pr",
            "list",
            "--base",
            base,
            "--head",
            head,
            "--state",
            "open",
            "--json",
            "number,url,title",
            "--limit",
            "1",
        ]
    )
    data = json.loads(output or "[]")
    return data[0] if data else None


def print_json(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
