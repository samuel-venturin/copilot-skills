#!/usr/bin/env python3
"""
jira_client.py — shared Atlassian Cloud (Jira) helpers for copilot-skills.

Credentials load order (first hit wins per key):
  1) process environment
  2) %USERPROFILE%/.cursor/agent-env/.env  (or ~/.cursor/agent-env/.env)
  3) optional path from ATLASSIAN_ENV_FILE

Never prints token values.
"""

from __future__ import annotations

import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Optional


ENV_KEYS = (
    "ATLASSIAN_EMAIL",
    "ATLASSIAN_API_TOKEN",
    "ATLASSIAN_BASE_URL",
    "ATLASSIAN_CLOUD_ID",
)


def agent_env_path() -> Path:
    override = os.environ.get("ATLASSIAN_ENV_FILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".cursor" / "agent-env" / ".env"


def load_dotenv(path: Optional[Path] = None) -> dict[str, str]:
    path = path or agent_env_path()
    loaded: dict[str, str] = {}
    if not path.is_file():
        return loaded
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            loaded[key] = value
    return loaded


def resolve_config() -> dict[str, str]:
    file_vals = load_dotenv()
    cfg: dict[str, str] = {}
    for key in ENV_KEYS:
        cfg[key] = (os.environ.get(key) or file_vals.get(key) or "").strip()
    if cfg["ATLASSIAN_BASE_URL"]:
        cfg["ATLASSIAN_BASE_URL"] = cfg["ATLASSIAN_BASE_URL"].rstrip("/")
    return cfg


class JiraError(Exception):
    def __init__(self, message: str, status: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status = status
        self.body = body


class JiraClient:
    def __init__(self, email: str, token: str, base_url: str):
        if not email or not token or not base_url:
            raise JiraError(
                "Missing Atlassian credentials. Fill ~/.cursor/agent-env/.env "
                "(ATLASSIAN_EMAIL, ATLASSIAN_API_TOKEN, ATLASSIAN_BASE_URL)."
            )
        self.email = email
        self.token = token
        self.base_url = base_url.rstrip("/")
        auth = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
        self._headers = {
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    @classmethod
    def from_env(cls) -> "JiraClient":
        cfg = resolve_config()
        return cls(cfg["ATLASSIAN_EMAIL"], cfg["ATLASSIAN_API_TOKEN"], cfg["ATLASSIAN_BASE_URL"])

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urllib.parse.urlencode(query, doseq=True)}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=self._headers, method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
                if not raw:
                    return None
                return json.loads(raw)
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(err_body) if err_body else None
            except json.JSONDecodeError:
                parsed = err_body
            raise JiraError(f"Jira HTTP {e.code} on {method.upper()} {path}", status=e.code, body=parsed) from e
        except urllib.error.URLError as e:
            raise JiraError(f"Jira connection error: {e}") from e

    def myself(self) -> dict[str, Any]:
        return self.request("GET", "/rest/api/3/myself")

    def get_issue(self, key: str, *, expand: str = "renderedFields,names") -> dict[str, Any]:
        key = key.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", key):
            raise JiraError(f"Invalid issue key: {key}")
        return self.request(
            "GET",
            f"/rest/api/3/issue/{key}",
            query={
                "expand": expand,
                "fields": "summary,description,status,issuetype,priority,assignee,reporter,labels,components,created,updated,comment,attachment,parent,subtasks,issuelinks",
            },
        )

    def search(self, jql: str, *, max_results: int = 50, fields: Optional[str] = None) -> dict[str, Any]:
        return self.request(
            "GET",
            "/rest/api/3/search/jql",
            query={
                "jql": jql,
                "maxResults": max_results,
                "fields": fields
                or "summary,status,issuetype,priority,assignee,updated,created,labels",
            },
        )

    def search_legacy(self, jql: str, *, max_results: int = 50, fields: Optional[str] = None) -> dict[str, Any]:
        """Fallback for sites that still expose /rest/api/3/search."""
        return self.request(
            "GET",
            "/rest/api/3/search",
            query={
                "jql": jql,
                "maxResults": max_results,
                "fields": fields
                or "summary,status,issuetype,priority,assignee,updated,created,labels",
            },
        )

    def assigned_to_me(self, *, max_results: int = 50, include_done: bool = False) -> dict[str, Any]:
        jql = "assignee = currentUser()"
        if not include_done:
            # Prefer statusCategory so "Fechada"/"Cancelado" without resolution are excluded.
            jql += ' AND statusCategory != Done'
        jql += " ORDER BY updated DESC"
        try:
            return self.search(jql, max_results=max_results)
        except JiraError as e:
            # Some tenants still use the classic search endpoint.
            if e.status in (404, 410):
                return self.search_legacy(jql, max_results=max_results)
            raise


def adf_to_text(node: Any) -> str:
    """Best-effort Atlassian Document Format → plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "\n".join(adf_to_text(n) for n in node if n is not None).strip()
    if not isinstance(node, dict):
        return str(node)

    ntype = node.get("type")
    text = node.get("text") or ""
    content = node.get("content") or []

    if ntype == "text":
        return text
    if ntype == "hardBreak":
        return "\n"
    if ntype == "mention":
        return node.get("attrs", {}).get("text") or text or ""
    if ntype == "emoji":
        return node.get("attrs", {}).get("shortName") or ""
    if ntype in ("paragraph", "heading", "blockquote", "listItem", "panel"):
        inner = "".join(adf_to_text(c) for c in content)
        return inner + "\n"
    if ntype in ("bulletList", "orderedList"):
        lines = []
        for i, item in enumerate(content, 1):
            item_text = adf_to_text(item).strip()
            prefix = f"{i}. " if ntype == "orderedList" else "- "
            lines.append(prefix + item_text.replace("\n", "\n  "))
        return "\n".join(lines) + "\n"
    if ntype == "codeBlock":
        inner = "".join(adf_to_text(c) for c in content)
        return f"```\n{inner}\n```\n"
    if ntype == "rule":
        return "---\n"
    # generic
    return "".join(adf_to_text(c) for c in content)


def issue_to_markdown(issue: dict[str, Any]) -> str:
    fields = issue.get("fields") or {}
    key = issue.get("key") or ""
    summary = fields.get("summary") or ""
    status = (fields.get("status") or {}).get("name") or ""
    itype = (fields.get("issuetype") or {}).get("name") or ""
    priority = (fields.get("priority") or {}).get("name") or ""
    assignee = (fields.get("assignee") or {}).get("displayName") or "Unassigned"
    description = fields.get("description")
    desc_text = adf_to_text(description).strip() if description else ""
    rendered = (issue.get("renderedFields") or {}).get("description")
    if rendered and isinstance(rendered, str) and len(rendered) > len(desc_text):
        # keep ADF text preferred; rendered is HTML — skip unless ADF empty
        if not desc_text:
            desc_text = re.sub(r"<[^>]+>", "", rendered)

    lines = [
        "---",
        f"task: {key}",
        f"type: {itype}",
        f"status: {status}",
        f"priority: {priority}",
        f"assignee: {assignee}",
        f"description: Jira card imported via API",
        "source: jira-api",
        "---",
        "",
        f"# {key} — {summary}",
        "",
        f"- **Type:** {itype}",
        f"- **Status:** {status}",
        f"- **Priority:** {priority}",
        f"- **Assignee:** {assignee}",
        "",
        "## Description",
        "",
        desc_text or "_No description_",
        "",
    ]
    return "\n".join(lines)


def summarize_issue(issue: dict[str, Any]) -> dict[str, Any]:
    fields = issue.get("fields") or {}
    assignee = fields.get("assignee") or {}
    return {
        "key": issue.get("key"),
        "summary": fields.get("summary"),
        "status": (fields.get("status") or {}).get("name"),
        "issuetype": (fields.get("issuetype") or {}).get("name"),
        "priority": (fields.get("priority") or {}).get("name"),
        "assignee": assignee.get("displayName"),
        "assigneeAccountId": assignee.get("accountId"),
        "updated": fields.get("updated"),
        "created": fields.get("created"),
        "labels": fields.get("labels") or [],
        "url": None,  # filled by caller with base_url
    }
