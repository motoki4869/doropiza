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
