#!/usr/bin/env python3
"""
workspace_paths.py — Documents/copilot-workspace helpers for copilot-skills.

Layout:
  %USERPROFILE%/Documents/copilot-workspace/
    projects.json
    state/index.json
    <project-slug>/<TICKET>/
      card.md, PRD.md, PROMPT.md, QUALITY.md, meta.json
      evidence/ + manifest.json

CLI:
  python workspace_paths.py root
  python workspace_paths.py resolve <TICKET> [--project <slug>] [--repo <path>]
  python workspace_paths.py ensure <TICKET> [--project <slug>] [--repo <path>]
  python workspace_paths.py evidence-dir <TICKET> [--project <slug>]
  python workspace_paths.py write-meta <TICKET> --jira-updated <ISO> [--project <slug>]
  python workspace_paths.py is-fresh <TICKET> --jira-updated <ISO> [--project <slug>]
  python workspace_paths.py set-project <slug> --repo <path> [--prefixes CTR,XYZ]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


TICKET_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$", re.IGNORECASE)


def workspace_root() -> Path:
    override = os.environ.get("COPILOT_WORKSPACE")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / "Documents" / "copilot-workspace").resolve()


def projects_path(root: Optional[Path] = None) -> Path:
    return (root or workspace_root()) / "projects.json"


def state_index_path(root: Optional[Path] = None) -> Path:
    return (root or workspace_root()) / "state" / "index.json"


def load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def normalize_ticket(ticket: str) -> str:
    ticket = ticket.strip().upper()
    if not TICKET_RE.match(ticket):
        raise ValueError(f"Invalid ticket key: {ticket}")
    return ticket


def slugify_project(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name.strip().lower()).strip("-")
    return s or "project"


def load_projects(root: Optional[Path] = None) -> dict[str, Any]:
    return load_json(projects_path(root), {"projects": {}})


def save_projects(data: dict[str, Any], root: Optional[Path] = None) -> None:
    save_json(projects_path(root), data)


def infer_prefix(ticket: str) -> str:
    return normalize_ticket(ticket).split("-", 1)[0]


def resolve_project_slug(
    ticket: str,
    *,
    project: Optional[str] = None,
    repo: Optional[str] = None,
    root: Optional[Path] = None,
) -> str:
    if project:
        return slugify_project(project)

    data = load_projects(root)
    projects = data.get("projects") or {}
    prefix = infer_prefix(ticket)

    # Match by prefix list
    matches = []
    for slug, info in projects.items():
        prefixes = [str(p).upper() for p in (info.get("prefixes") or [])]
        if prefix in prefixes:
            matches.append(slug)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise ValueError(
            f"Ambiguous project for {ticket}: {matches}. Pass --project <slug>."
        )

    # Match by repo path
    if repo:
        repo_path = str(Path(repo).expanduser().resolve())
        for slug, info in projects.items():
            mapped = info.get("repo")
            if mapped and str(Path(mapped).expanduser().resolve()) == repo_path:
                return slug
        # register new
        slug = slugify_project(Path(repo).name)
        set_project(slug, repo=repo_path, prefixes=[prefix], root=root)
        return slug

    # Fallback: use ticket prefix as slug
    return slugify_project(prefix.lower())


def set_project(
    slug: str,
    *,
    repo: str,
    prefixes: Optional[list[str]] = None,
    root: Optional[Path] = None,
) -> dict[str, Any]:
    slug = slugify_project(slug)
    data = load_projects(root)
    projects = data.setdefault("projects", {})
    entry = projects.get(slug) or {}
    entry["repo"] = str(Path(repo).expanduser().resolve())
    if prefixes is not None:
        entry["prefixes"] = [p.strip().upper() for p in prefixes if p.strip()]
    elif "prefixes" not in entry:
        entry["prefixes"] = []
    projects[slug] = entry
    save_projects(data, root)
    return entry


def ticket_dir(
    ticket: str,
    *,
    project: Optional[str] = None,
    repo: Optional[str] = None,
    root: Optional[Path] = None,
) -> Path:
    ticket = normalize_ticket(ticket)
    slug = resolve_project_slug(ticket, project=project, repo=repo, root=root)
    return (root or workspace_root()) / slug / ticket


def evidence_dir(
    ticket: str,
    *,
    project: Optional[str] = None,
    repo: Optional[str] = None,
    root: Optional[Path] = None,
) -> Path:
    return ticket_dir(ticket, project=project, repo=repo, root=root) / "evidence"


def artifact_paths(
    ticket: str,
    *,
    project: Optional[str] = None,
    repo: Optional[str] = None,
    root: Optional[Path] = None,
) -> dict[str, str]:
    base = ticket_dir(ticket, project=project, repo=repo, root=root)
    return {
        "ticketDir": str(base),
        "card": str(base / "card.md"),
        "prd": str(base / "PRD.md"),
        "prompt": str(base / "PROMPT.md"),
        "quality": str(base / "QUALITY.md"),
        "meta": str(base / "meta.json"),
        "evidenceDir": str(base / "evidence"),
        "manifest": str(base / "evidence" / "manifest.json"),
    }


def ensure_ticket_layout(
    ticket: str,
    *,
    project: Optional[str] = None,
    repo: Optional[str] = None,
    root: Optional[Path] = None,
) -> dict[str, str]:
    paths = artifact_paths(ticket, project=project, repo=repo, root=root)
    Path(paths["ticketDir"]).mkdir(parents=True, exist_ok=True)
    Path(paths["evidenceDir"]).mkdir(parents=True, exist_ok=True)
    return paths


def read_meta(ticket: str, **kwargs) -> dict[str, Any]:
    paths = artifact_paths(ticket, **kwargs)
    return load_json(Path(paths["meta"]), {})


def write_meta(
    ticket: str,
    *,
    jira_updated: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
    **kwargs,
) -> dict[str, Any]:
    paths = ensure_ticket_layout(ticket, **kwargs)
    meta = load_json(Path(paths["meta"]), {})
    now = datetime.now(timezone.utc).isoformat()
    if jira_updated is not None:
        meta["jiraUpdated"] = jira_updated
    meta["interpretedAt"] = now
    meta["verified"] = bool(jira_updated)
    if extra:
        meta.update(extra)
    save_json(Path(paths["meta"]), meta)
    _update_state_index(normalize_ticket(ticket), meta, paths)
    return meta


def is_fresh(ticket: str, *, jira_updated: str, **kwargs) -> bool:
    meta = read_meta(ticket, **kwargs)
    stored = (meta.get("jiraUpdated") or "").strip()
    return bool(stored) and stored == (jira_updated or "").strip()


def _update_state_index(ticket: str, meta: dict[str, Any], paths: dict[str, str]) -> None:
    root = workspace_root()
    index_path = state_index_path(root)
    index = load_json(index_path, {"tickets": {}})
    tickets = index.setdefault("tickets", {})
    tickets[ticket] = {
        "jiraUpdated": meta.get("jiraUpdated"),
        "interpretedAt": meta.get("interpretedAt"),
        "verified": meta.get("verified"),
        "ticketDir": paths["ticketDir"],
        "hasPrd": Path(paths["prd"]).is_file(),
        "hasPrompt": Path(paths["prompt"]).is_file(),
        "hasQuality": Path(paths["quality"]).is_file(),
        "evidenceCount": len(list(Path(paths["evidenceDir"]).glob("*.png")))
        if Path(paths["evidenceDir"]).is_dir()
        else 0,
    }
    save_json(index_path, index)


def write_evidence_manifest(
    ticket: str,
    entries: list[dict[str, Any]],
    **kwargs,
) -> Path:
    paths = ensure_ticket_layout(ticket, **kwargs)
    manifest = {
        "ticket": normalize_ticket(ticket),
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "entries": entries,
    }
    path = Path(paths["manifest"])
    save_json(path, manifest)
    return path


def _out(data: dict) -> None:
    payload = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    sys.stdout.buffer.write((payload + "\n").encode("utf-8"))


def _err(msg: str, code: int = 1) -> None:
    _out({"error": msg})
    sys.exit(code)


def main() -> None:
    parser = argparse.ArgumentParser(description="Documents/copilot-workspace path helpers")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("root").set_defaults(func=lambda _: _out({"success": True, "root": str(workspace_root())}))

    p_res = sub.add_parser("resolve", help="Resolve artifact paths for a ticket")
    p_res.add_argument("ticket")
    p_res.add_argument("--project")
    p_res.add_argument("--repo")
    p_res.set_defaults(
        func=lambda a: _out(
            {
                "success": True,
                "project": resolve_project_slug(a.ticket, project=a.project, repo=a.repo),
                **artifact_paths(a.ticket, project=a.project, repo=a.repo),
            }
        )
    )

    p_ens = sub.add_parser("ensure", help="Create ticket layout dirs")
    p_ens.add_argument("ticket")
    p_ens.add_argument("--project")
    p_ens.add_argument("--repo")
    p_ens.set_defaults(
        func=lambda a: _out(
            {
                "success": True,
                "project": resolve_project_slug(a.ticket, project=a.project, repo=a.repo),
                **ensure_ticket_layout(a.ticket, project=a.project, repo=a.repo),
            }
        )
    )

    p_ev = sub.add_parser("evidence-dir", help="Ensure and print evidence directory")
    p_ev.add_argument("ticket")
    p_ev.add_argument("--project")
    p_ev.add_argument("--repo")
    p_ev.set_defaults(
        func=lambda a: _out(
            {
                "success": True,
                "evidenceDir": str(
                    ensure_ticket_layout(a.ticket, project=a.project, repo=a.repo)["evidenceDir"]
                ),
            }
        )
    )

    p_wm = sub.add_parser("write-meta", help="Write meta.json after interpret")
    p_wm.add_argument("ticket")
    p_wm.add_argument("--jira-updated", required=True)
    p_wm.add_argument("--project")
    p_wm.add_argument("--repo")
    p_wm.set_defaults(
        func=lambda a: _out(
            {
                "success": True,
                "meta": write_meta(
                    a.ticket,
                    jira_updated=a.jira_updated,
                    project=a.project,
                    repo=a.repo,
                ),
            }
        )
    )

    p_if = sub.add_parser("is-fresh", help="Compare meta.jiraUpdated to current")
    p_if.add_argument("ticket")
    p_if.add_argument("--jira-updated", required=True)
    p_if.add_argument("--project")
    p_if.add_argument("--repo")
    p_if.set_defaults(
        func=lambda a: _out(
            {
                "success": True,
                "fresh": is_fresh(
                    a.ticket,
                    jira_updated=a.jira_updated,
                    project=a.project,
                    repo=a.repo,
                ),
                "meta": read_meta(a.ticket, project=a.project, repo=a.repo),
            }
        )
    )

    p_sp = sub.add_parser("set-project", help="Register project slug → repo mapping")
    p_sp.add_argument("slug")
    p_sp.add_argument("--repo", required=True)
    p_sp.add_argument("--prefixes", default="", help="Comma-separated ticket prefixes")
    p_sp.set_defaults(
        func=lambda a: _out(
            {
                "success": True,
                "slug": slugify_project(a.slug),
                "project": set_project(
                    a.slug,
                    repo=a.repo,
                    prefixes=[p for p in a.prefixes.split(",") if p.strip()],
                ),
            }
        )
    )

    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as e:  # noqa: BLE001
        _err(str(e))


if __name__ == "__main__":
    main()
