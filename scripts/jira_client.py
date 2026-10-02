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

    def sprint_assigned_to_me(self, *, max_results: int = 50, include_done: bool = False) -> dict[str, Any]:
        jql = "assignee = currentUser() AND sprint in openSprints()"
        if not include_done:
            jql += " AND statusCategory != Done"
        jql += " ORDER BY priority ASC, updated DESC"
        try:
            return self.search(jql, max_results=max_results)
        except JiraError as e:
            if e.status in (404, 410):
                return self.search_legacy(jql, max_results=max_results)
            raise

    def get_transitions(self, key: str) -> list[dict[str, Any]]:
        key = _normalize_key(key)
        data = self.request("GET", f"/rest/api/3/issue/{key}/transitions")
        return list((data or {}).get("transitions") or [])

    def transition_issue(
        self,
        key: str,
        *,
        transition_id: Optional[str] = None,
        to_name: Optional[str] = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        key = _normalize_key(key)
        transitions = self.get_transitions(key)
        chosen: Optional[dict[str, Any]] = None
        if transition_id:
            tid = str(transition_id)
            chosen = next((t for t in transitions if str(t.get("id")) == tid), None)
            if not chosen:
                raise JiraError(f"Transition id {tid} not available for {key}")
        elif to_name:
            needle = to_name.strip().lower()
            chosen = next(
                (t for t in transitions if str(t.get("name") or "").strip().lower() == needle),
                None,
            )
            if not chosen:
                # partial match fallback
                chosen = next(
                    (t for t in transitions if needle in str(t.get("name") or "").strip().lower()),
                    None,
                )
            if not chosen:
                names = [t.get("name") for t in transitions]
                raise JiraError(f"No transition matching '{to_name}' for {key}. Available: {names}")
        else:
            raise JiraError("Provide transition_id or to_name")

        payload = {"transition": {"id": str(chosen["id"])}}
        if dry_run:
            return {"dryRun": True, "key": key, "transition": chosen, "payload": payload}
        self.request("POST", f"/rest/api/3/issue/{key}/transitions", body=payload)
        return {"key": key, "transition": chosen}

    def add_comment(self, key: str, body_text: str) -> dict[str, Any]:
        key = _normalize_key(key)
        adf = plain_text_to_adf(body_text)
        return self.request(
            "POST",
            f"/rest/api/3/issue/{key}/comment",
            body={"body": adf},
        )

    def attach_files(self, key: str, files: list[Path]) -> list[dict[str, Any]]:
        """Upload files in order via multipart. Returns list of attachment metadata."""
        key = _normalize_key(key)
        if not files:
            raise JiraError("No files to attach")
        results: list[dict[str, Any]] = []
        for path in files:
            path = Path(path)
            if not path.is_file():
                raise JiraError(f"File not found: {path}")
            results.append(self._upload_attachment(key, path))
        return results

    def _upload_attachment(self, key: str, path: Path) -> dict[str, Any]:
        boundary = f"----copilotBoundary{os.urandom(8).hex()}"
        filename = path.name
        file_bytes = path.read_bytes()
        # Guess content type lightly
        suffix = path.suffix.lower()
        ctype = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".pdf": "application/pdf",
            ".md": "text/markdown",
            ".txt": "text/plain",
        }.get(suffix, "application/octet-stream")

        body = bytearray()
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode("utf-8")
        )
        body.extend(f"Content-Type: {ctype}\r\n\r\n".encode("utf-8"))
        body.extend(file_bytes)
        body.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))

        url = f"{self.base_url}/rest/api/3/issue/{key}/attachments"
        headers = {
            "Authorization": self._headers["Authorization"],
            "Accept": "application/json",
            "X-Atlassian-Token": "no-check",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }
        req = urllib.request.Request(url, data=bytes(body), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                raw = resp.read().decode("utf-8")
                parsed = json.loads(raw) if raw else []
                # API returns a list of attachments
                if isinstance(parsed, list) and parsed:
                    return parsed[0]
                if isinstance(parsed, dict):
                    return parsed
                return {"filename": filename, "raw": parsed}
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                parsed_err = json.loads(err_body) if err_body else None
            except json.JSONDecodeError:
                parsed_err = err_body
            raise JiraError(
                f"Jira HTTP {e.code} on POST /rest/api/3/issue/{key}/attachments",
                status=e.code,
                body=parsed_err,
            ) from e
        except urllib.error.URLError as e:
            raise JiraError(f"Jira connection error: {e}") from e


def _normalize_key(key: str) -> str:
    key = key.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", key):
        raise JiraError(f"Invalid issue key: {key}")
    return key


def plain_text_to_adf(text: str) -> dict[str, Any]:
    """Convert plain text (paragraphs separated by blank lines) to minimal ADF."""
    paragraphs = re.split(r"\n\s*\n", (text or "").strip())
    content: list[dict[str, Any]] = []
    for para in paragraphs:
        lines = para.split("\n")
        nodes: list[dict[str, Any]] = []
        for i, line in enumerate(lines):
            if i:
                nodes.append({"type": "hardBreak"})
            if line:
                nodes.append({"type": "text", "text": line})
        if not nodes:
            nodes = [{"type": "text", "text": " "}]
        content.append({"type": "paragraph", "content": nodes})
    if not content:
        content = [{"type": "paragraph", "content": [{"type": "text", "text": " "}]}]
    return {"type": "doc", "version": 1, "content": content}


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
