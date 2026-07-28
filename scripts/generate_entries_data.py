#!/usr/bin/env python3
"""ドロピザ考察*.md を全件パースし、site/data/entries-data.js を再生成する。
考察を追記した際は、このスクリプトを再実行してentries-data.jsをコミットし直す想定。
"""
import json
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MD_GLOB = "ドロピザ考察*.md"
TAGS_FILE = REPO_ROOT / "tags.json"
OUT_FILE = REPO_ROOT / "site" / "data" / "entries-data.js"


def parse_heading(heading_text: str) -> tuple:
    stripped = heading_text.strip()
    m = re.match(r"^(\d+)\.\s*(.+)$", stripped)
    if m:
        return m.group(1), m.group(2).strip()
    return None, stripped


def split_entries(md_text: str) -> list:
    lines = md_text.split("\n")
    heading_idx = [i for i, line in enumerate(lines) if line.startswith("## ")]
    entries = []
    for pos, start in enumerate(heading_idx):
        end = heading_idx[pos + 1] if pos + 1 < len(heading_idx) else len(lines)
        heading = lines[start][3:].strip()
        body = "\n".join(lines[start + 1:end]).strip()
        entries.append((heading, body))
    return entries


def make_entry_id(file_stem: str, index: int) -> str:
    m = re.search(r"(\d{3}-\d{3})", file_stem)
    range_part = m.group(1) if m else file_stem
    return f"{range_part}_{index:03d}"


def inline(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    return text


def parse_table(lines: list) -> str:
    rows = [l.strip() for l in lines if l.strip().startswith("|")]
    rows = [r for r in rows if not re.fullmatch(r"\|[\s:\-|]+\|?", r)]
    cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
    if not cells:
        return ""
    head, *body = cells
    out = ['<table class="rpt-table">', "<thead><tr>"]
    out += [f"<th>{inline(c)}</th>" for c in head]
    out.append("</tr></thead><tbody>")
    for row in body:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out = []
    i = 0
    list_buf: list = []

    def flush_list():
        if list_buf:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in list_buf) + "</ul>")
            list_buf.clear()

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            flush_list()
            i += 1
            continue

        if stripped == "---":
            flush_list()
            out.append("<hr>")
            i += 1
            continue

        if stripped.startswith("|"):
            flush_list()
            table_lines = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            out.append(parse_table(table_lines))
            continue

        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            flush_list()
            level = 2 if len(m.group(1)) == 1 else min(len(m.group(1)) + 1, 4)
            out.append(f"<h{level}>{inline(m.group(2))}</h{level}>")
            i += 1
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            list_buf.append(stripped[2:].strip())
            i += 1
            continue

        flush_list()
        out.append(f"<p>{inline(stripped)}</p>")
        i += 1

    flush_list()
    return "\n".join(out)


def load_tags(tags_path: Path) -> dict:
    if not tags_path.exists():
        return {}
    return json.loads(tags_path.read_text(encoding="utf-8"))


def match_tags(text: str, tags_dict: dict) -> list:
    matched = [name for name, keywords in tags_dict.items() if any(kw in text for kw in keywords)]
    return matched if matched else ["未分類"]
