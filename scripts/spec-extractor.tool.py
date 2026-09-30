#!/usr/bin/env python3
"""
spec-extractor.tool.py
Extrai e normaliza dados de specs markdown (Jira RSS XML ou markdown puro)
para uso pelo task-interpreter.

Uso:
    python3 spec-extractor.tool.py <spec-markdown-file>

Output (stdout):
    JSON { "success": true, "source": "xml"|"markdown", "data": { ... } }
    JSON { "error": "mensagem" }  (exit 1 em caso de erro)

Dependências opcionais (requirements.txt):
    lxml>=5.0, beautifulsoup4>=4.12
    Sem elas, usa xml.etree.ElementTree + html.parser da stdlib.
"""
import sys
import os
import re
import json

# ---------------------------------------------------------------------------
# Detecção de dependências opcionais
# ---------------------------------------------------------------------------

try:
    from lxml import etree as lxml_etree
    _HAS_LXML = True
except ImportError:
    _HAS_LXML = False
    import xml.etree.ElementTree as ET

try:
    from bs4 import BeautifulSoup
    _HAS_BS4 = True
except ImportError:
    _HAS_BS4 = False
    from html.parser import HTMLParser


# ---------------------------------------------------------------------------
# HTML → seções (bs4 preferido, stdlib fallback)
# ---------------------------------------------------------------------------

def _html_sections_bs4(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    sections = {"_intro": []}
    current = "_intro"
    heading_tags = {"h1", "h2", "h3", "h4"}
    for el in soup.children:
        tag = getattr(el, "name", None)
        if tag in heading_tags:
            current = el.get_text(strip=True)
            sections.setdefault(current, [])
        else:
            text = el.get_text(separator="\n").strip() if hasattr(el, "get_text") else str(el).strip()
            if text:
                sections.setdefault(current, []).append(text)
    return {k: "\n".join(v).strip() for k, v in sections.items() if any(v)}


if not _HAS_BS4:
    class _SectionParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self._cur = "_intro"
            self._sections = {"_intro": []}
            self._buf = []
            self._h = {"h1", "h2", "h3", "h4"}
            self._in_h = False
            self._hbuf = []
            self._ldepth = 0
            self._ocounters = []

        def handle_starttag(self, tag, attrs):
            tag = tag.lower()
            if tag in self._h:
                self._flush(); self._in_h = True; self._hbuf = []
            elif tag == "ul": self._ldepth += 1
            elif tag == "ol": self._ldepth += 1; self._ocounters.append(0)
            elif tag == "li":
                self._flush()
                if self._ocounters:
                    self._ocounters[-1] += 1
                    self._buf.append("  " * (self._ldepth - 1) + f"{self._ocounters[-1]}. ")
                else:
                    self._buf.append("  " * (self._ldepth - 1) + "- ")
            elif tag in ("br", "hr"): self._buf.append("\n")

        def handle_endtag(self, tag):
            tag = tag.lower()
            if tag in self._h:
                h = "".join(self._hbuf).strip(); self._in_h = False
                self._flush(); self._cur = h; self._sections.setdefault(h, [])
            elif tag in ("ul", "ol"):
                self._ldepth -= 1
                if self._ocounters and tag == "ol": self._ocounters.pop()
                self._flush()
            elif tag == "li": self._flush()
            elif tag in ("p", "div"): self._flush(); self._buf.append("\n")

        def handle_data(self, data):
            if self._in_h: self._hbuf.append(data)
            else: self._buf.append(data)

        def _flush(self):
            t = "".join(self._buf).strip()
            if t: self._sections.setdefault(self._cur, []).append(t)
            self._buf = []

        def get_sections(self):
            self._flush()
            return {k: "\n".join(v).strip() for k, v in self._sections.items() if any(v)}


def _html_to_sections(html: str) -> dict:
    if _HAS_BS4:
        return _html_sections_bs4(html)
    p = _SectionParser()
    p.feed(html)
    return p.get_sections()


def _html_to_text(html: str) -> str:
    return "\n".join(_html_to_sections(html).values())


# ---------------------------------------------------------------------------
# Mapeamento seções → campos normalizados
# ---------------------------------------------------------------------------

_SECTION_MAP = {
    "acceptance_criteria": [
        r"crit[eé]rios de aceite",
        r"acceptance criteria",
        r"^CA\d+",
        r"crit[eé]rios de aceite\s*[–-]",
        r"fluxo positivo",
        r"fluxo negativo",
        r"fluxo de erro",
    ],
    "test_cases": [
        r"casos de teste",
        r"test cases",
        r"testes positivos",
        r"testes negativos",
        r"testes de erro",
        r"^CT\d+",
    ],
    "definition_of_ready": [
        r"definition of ready",
        r"\bdor\b",
        r"defini[çc][aã]o de pronto para desenvolvimento",
        r"pronto para desenvolvimento",
    ],
    "definition_of_done": [
        r"definition of done",
        r"\bdod\b",
        r"defini[çc][aã]o de (conclu[íi]do|feito|pronto)",
        r"pronto para entrega",
    ],
    "user_story": [
        r"hist[óo]ria de usu[áa]rio",
        r"user story",
    ],
    "steps_to_reproduce": [
        r"como reproduzir",
        r"steps to reproduce",
    ],
    "expected_behavior": [
        r"comportamento esperado",
        r"expected behavior",
        r"resultado esperado",
    ],
    "actual_behavior": [
        r"resultado atual",
        r"comportamento (atual|observado)",
        r"actual (result|behavior)",
        r"observed behavior",
    ],
    "identified_scenario": [
        r"cen[áa]rio identificado",
        r"identified scenario",
    ],
    "impact": [
        r"impacto",
        r"impact",
    ],
}


def _map_sections(raw: dict) -> dict:
    result = {k: "" for k in _SECTION_MAP}
    result["other_sections"] = {}
    for heading, content in raw.items():
        if heading == "_intro":
            result["intro"] = content
            continue
        matched = False
        for field, patterns in _SECTION_MAP.items():
            for pat in patterns:
                if re.search(pat, heading, re.IGNORECASE):
                    result[field] = (result[field] + "\n\n" + content).strip() if result[field] else content
                    matched = True
                    break
            if matched:
                break
        if not matched:
            result["other_sections"][heading] = content
    return {k: v for k, v in result.items() if v or k in _SECTION_MAP}


# ---------------------------------------------------------------------------
# XML parsing
# ---------------------------------------------------------------------------

def _sanitize_xml(xml_str: str) -> str:
    """Escapa & soltos e deduplica atributos HTML embutidos no XML."""
    xml_str = re.sub(r"&(?!(?:amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)", "&amp;", xml_str)

    def _dedupe(m):
        seen = set()
        def _rep(am):
            name = am.group(1).lower()
            if name in seen: return ""
            seen.add(name); return am.group(0)
        return re.sub(r'\s+([\w-]+)=(?:"[^"]*"|\'[^\']*\')', _rep, m.group(0))

    return re.sub(r"<[a-zA-Z][^>]*>", _dedupe, xml_str)


def _parse_xml_root(xml_str: str):
    if _HAS_LXML:
        parser = lxml_etree.XMLParser(recover=True, encoding="utf-8")
        root = lxml_etree.fromstring(xml_str.encode("utf-8"), parser=parser)
        return root, "lxml"
    xml_str = _sanitize_xml(xml_str)
    return ET.fromstring(xml_str), "stdlib"


def _find(el, path):
    return el.find(path)

def _findall(el, path):
    return el.findall(path)

def _t(el, default="") -> str:
    if el is None: return default
    return (el.text or "").strip()


def _inner_html(el) -> str:
    if el is None: return ""
    if _HAS_LXML:
        parts = [el.text or ""]
        for child in el:
            parts.append(lxml_etree.tostring(child, encoding="unicode", method="html"))
        return "".join(parts)
    html = ET.tostring(el, encoding="unicode", method="html")
    tag = el.tag
    return re.sub(rf"^<{tag}[^>]*>|</{tag}>$", "", html).strip()


def _extract_customfields(item) -> dict:
    customs = {}
    for cf in _findall(item, ".//customfield"):
        name_el = _find(cf, "customfieldname")
        if name_el is None or not _t(name_el): continue
        name = _t(name_el)
        vals = [_t(v) for v in _findall(cf, ".//customfieldvalue") if _t(v)]
        if vals:
            customs[name] = "\n".join(vals)
    return customs


def _parse_item(item) -> dict:
    data = {}
    for f in ("key", "summary", "type", "priority", "status", "assignee",
              "reporter", "created", "updated", "link", "environment", "resolution"):
        data[f] = _t(_find(item, f))

    proj = _find(item, "project")
    if proj is not None:
        data["project"] = {"name": _t(proj), "key": proj.get("key", "")}

    parent = _find(item, "parent")
    if parent is not None:
        data["parent"] = _t(parent)

    data["labels"] = [_t(l) for l in _findall(item, ".//label") if _t(l)]
    data["subtasks"] = [_t(s) for s in _findall(item, ".//subtask") if _t(s)]

    desc_html = _inner_html(_find(item, "description"))
    if desc_html:
        raw = _html_to_sections(desc_html)
        data.update(_map_sections(raw))
        data["description_text"] = _html_to_text(desc_html)
    else:
        data["description_text"] = ""

    customs = _extract_customfields(item)
    data["custom_fields"] = customs

    # Preferir Acceptance Criteria do customfield se mais completo
    for cf_name, cf_val in customs.items():
        if re.search(r"acceptance criteria|crit[eé]rios de aceite", cf_name, re.IGNORECASE):
            parsed = _html_to_text(cf_val) if "<" in cf_val else cf_val
            if parsed and len(parsed) > len(data.get("acceptance_criteria", "")):
                data["acceptance_criteria"] = parsed

    return data


# ---------------------------------------------------------------------------
# Fallback: spec markdown puro (sem bloco XML)
# ---------------------------------------------------------------------------

def _parse_markdown_spec(content: str) -> dict:
    data = {k: "" for k in ("key", "summary", "type", "priority", "status",
                             "assignee", "reporter", "created", "updated", "link")}
    title = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title:
        data["summary"] = title.group(1).strip()

    raw = {}
    heading_re = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
    matches = list(heading_re.finditer(content))
    for i, m in enumerate(matches):
        heading = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        sec = content[start:end]
        sec = re.sub(r"^#{1,4}\s+.+$", "", sec, flags=re.MULTILINE)
        sec = re.sub(r"^[-_]{3,}$", "", sec, flags=re.MULTILINE).strip()
        if sec:
            raw[heading] = sec

    data.update(_map_sections(raw))
    return data


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _read_spec(md_path: str):
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
    xml_blocks = re.findall(r"```xml\s*(.*?)```", content, re.DOTALL)
    return (xml_blocks[0] if xml_blocks else None), content


def _process(xml_str, md_content):
    """Core parse logic shared by all input modes."""
    if xml_str:
        root, backend = _parse_xml_root(xml_str)
        item = root.find(".//item")
        if item is None:
            raise ValueError("Elemento <item> não encontrado no XML.")
        data = _parse_item(item)
        data["_meta"] = {"source": "xml", "xml_parser": backend,
                         "lxml": _HAS_LXML, "bs4": _HAS_BS4}
        print(json.dumps({"success": True, "source": "xml", "data": data},
                          ensure_ascii=False, indent=2))
    else:
        data = _parse_markdown_spec(md_content)
        data["_meta"] = {"source": "markdown", "xml_parser": None,
                         "lxml": _HAS_LXML, "bs4": _HAS_BS4}
        print(json.dumps({"success": True, "source": "markdown", "data": data},
                          ensure_ascii=False, indent=2))


def main():
    """
    Supported modes:
        spec-extractor.tool.py <file.md>           — file mode (original)
        spec-extractor.tool.py --stdin             — reads markdown or XML from stdin
        spec-extractor.tool.py --xml "<rss>...</>" — raw XML string passed as argument
    """
    import argparse
    parser = argparse.ArgumentParser(description="spec-extractor.tool.py")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("file", nargs="?", help="Path to spec markdown file")
    group.add_argument("--stdin", action="store_true", help="Read spec content from stdin")
    group.add_argument("--xml", metavar="XML_STRING", help="Raw XML string to parse directly")
    args = parser.parse_args()

    try:
        # ── Mode 1: file path (original behaviour) ──────────────────────────
        if args.file:
            if not os.path.isfile(args.file):
                print(json.dumps({"error": f"Arquivo não encontrado: {args.file}"}))
                sys.exit(1)
            xml_str, md_content = _read_spec(args.file)
            _process(xml_str, md_content)

        # ── Mode 2: stdin ────────────────────────────────────────────────────
        elif args.stdin:
            content = sys.stdin.read()
            # Detect if raw XML was piped directly (starts with < and contains <rss or <item)
            stripped = content.strip()
            if stripped.startswith("<") and re.search(r"<(rss|item|channel)\b", stripped):
                _process(stripped, "")
            else:
                # Treat as markdown (may contain ```xml blocks)
                xml_blocks = re.findall(r"```xml\s*(.*?)```", content, re.DOTALL)
                xml_str = xml_blocks[0] if xml_blocks else None
                _process(xml_str, content)

        # ── Mode 3: inline --xml argument ────────────────────────────────────
        elif args.xml:
            _process(args.xml.strip(), "")

        else:
            parser.print_help()
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
