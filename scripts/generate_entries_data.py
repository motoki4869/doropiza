#!/usr/bin/env python3
"""ドロピザ考察*.md を全件パースし、site/data/entries-data.js を再生成する。
考察を追記した際は、このスクリプトを再実行してentries-data.jsをコミットし直す想定。
"""
import fnmatch
import json
import re
import unicodedata
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


# 「[00:13]」「[01:23:27]」のような動画内の再生位置
TIMESTAMP_RE = re.compile(r"\[\d{1,2}:\d{2}(?::\d{2})?\]")
TRAILING_TIMESTAMP_RE = re.compile(r"\s*(\[\d{1,2}:\d{2}(?::\d{2})?\])\s*$")
# タイムスタンプ内のコロンを一時的に置き換える文字。本文には現れない制御文字を使う
TS_COLON_MASK = "\x00"


def mask_timestamp_colons(text: str) -> str:
    """タイムスタンプ内のコロンを隠す。

    「ラベル: 本文」の判定に使う正規表現が、[00:13]のコロンを
    区切りとして拾ってしまうのを防ぐ。文字数は変えないので、
    見出し判定の長さチェックにも影響しない。
    """
    return TIMESTAMP_RE.sub(lambda m: m.group(0).replace(":", TS_COLON_MASK), text)


def unmask_timestamp_colons(text: str) -> str:
    return text.replace(TS_COLON_MASK, ":")


def plain_block_to_html(stripped: str) -> str:
    """Markdown記法を持たない1行を、内容から構造を推定してHTML化する。

    ドロピザの本文はMarkdown記法をほとんど使わず、
    「概要」「1. 見出し」「ラベル: 本文」といった書式を
    プレーンテキストで表現している。そのまま<p>にすると
    全てが同じ見た目の段落になり読みづらいため、
    ここで見出し・ラベル付き項目を判別して意味的なタグを付ける。
    """
    # 行末のタイムスタンプは見出し判定の邪魔になるので一度切り離し、最後に付け直す
    m_ts = TRAILING_TIMESTAMP_RE.search(stripped)
    timestamp = ""
    if m_ts:
        timestamp = f'<span class="ts">{m_ts.group(1)}</span>'
        stripped = stripped[: m_ts.start()]
        if not stripped:
            # 行がタイムスタンプだけだった場合。見出しにはしない
            return f"<p>{timestamp}</p>"

    masked = mask_timestamp_colons(stripped)

    def emit(text: str) -> str:
        return inline(unmask_timestamp_colons(text))

    # 「1. 最終章へのカウントダウン」のような番号付き見出し
    m = re.match(r"^(\d+)[.．]\s*(.+)$", masked)
    if m and "。" not in masked and len(masked) < 60:
        return f'<h4 class="sec-num"><span class="num">{emit(m.group(1))}</span>{emit(m.group(2))}{timestamp}</h4>'

    # 「名前の由来:」のように行末がコロンで終わる小見出し
    m = re.match(r"^([^:：]{2,30})[:：]$", masked)
    if m:
        return f'<h4 class="sec-sub">{emit(m.group(1))}{timestamp}</h4>'

    # 「物語の終焉に向けたペース: 尾田先生は〜」のようなラベル付き項目
    m = re.match(r"^([^:：]{2,30})[:：]\s*(.+)$", masked)
    if m and not m.group(2).startswith("//"):
        return f'<p class="term-item"><span class="term">{emit(m.group(1))}</span>{emit(m.group(2))}{timestamp}</p>'

    # 「CP9の動物モチーフとカリファの例外性 [00:00]」のように、
    # 再生位置を伴う短い行は本文ではなく動画内の小見出し
    if timestamp and "。" not in masked:
        return f'<h4 class="sec-sub">{emit(masked)}{timestamp}</h4>'

    # 「概要」「この動画が伝えたかったこと」のような独立したセクション見出し
    if len(masked) <= 24 and "。" not in masked and "、" not in masked:
        return f'<h3 class="sec">{emit(masked)}</h3>'

    return f"<p>{emit(masked)}{timestamp}</p>"


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
            hashes, text = len(m.group(1)), m.group(2)
            if hashes == 3:
                # 「### 1. タイトル」は既存記事の「1. タイトル」(プレーンテキスト)と
                # 同じ丸数字バッジ見出しに、番号なしなら独立見出し(概要等)に揃える
                num_m = re.match(r"^(\d+)[.．]\s*(.+)$", text)
                if num_m:
                    out.append(
                        f'<h4 class="sec-num"><span class="num">{inline(num_m.group(1))}</span>{inline(num_m.group(2))}</h4>'
                    )
                else:
                    out.append(f'<h3 class="sec">{inline(text)}</h3>')
            elif hashes == 4:
                # 「#### 小見出し」は既存記事の「小見出し:」と同じ扱いに揃える
                out.append(f'<h4 class="sec-sub">{inline(text)}</h4>')
            else:
                level = 2 if hashes == 1 else min(hashes + 1, 4)
                out.append(f"<h{level}>{inline(text)}</h{level}>")
            i += 1
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            list_buf.append(stripped[2:].strip())
            i += 1
            continue

        flush_list()
        out.append(plain_block_to_html(stripped))
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


def find_md_files(repo_root: Path) -> list:
    # macOSのファイルシステムはファイル名をNFD（濁点等が分解された形）で
    # 保持することがあり、ソースコード中のNFCなグロブパターンでは
    # 一部のファイルがマッチしないことがある。ここではファイル名を
    # NFCに正規化してから比較することで、オンディスクの正規化形式に
    # 依存せず確実に全ファイルを検出する。
    pattern = unicodedata.normalize("NFC", MD_GLOB)
    matched = [
        p for p in repo_root.iterdir()
        if p.is_file() and fnmatch.fnmatch(unicodedata.normalize("NFC", p.name), pattern)
    ]
    return sorted(matched, key=lambda p: unicodedata.normalize("NFC", p.name))


def build_entries(file_paths: list, tags_dict: dict) -> list:
    entries = []
    for file_path in file_paths:
        text = file_path.read_text(encoding="utf-8")
        for idx, (heading, body) in enumerate(split_entries(text), start=1):
            if not body.strip():
                print(f"WARNING: 本文が空のためスキップ: {file_path.name} - {heading}")
                continue
            number, title = parse_heading(heading)
            entries.append({
                "id": make_entry_id(file_path.stem, idx),
                "number": number,
                "title": title,
                "sourceFile": unicodedata.normalize("NFC", file_path.name),
                "tags": match_tags(f"{heading}\n{body}", tags_dict),
                "html": md_to_html(body),
            })
    return entries


def write_entries_js(entries: list, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    js = "window.ENTRIES = " + json.dumps(entries, ensure_ascii=False, indent=2) + ";\n"
    out_path.write_text(js, encoding="utf-8")


def update_meta_description(count: int, index_path: Path) -> bool:
    """index.htmlのmeta descriptionにある本数を実際の件数に合わせる。

    考察を追加するたびに手で直すと必ず食い違うので、生成時に同期する。
    """
    if not index_path.exists():
        return False
    html = index_path.read_text(encoding="utf-8")
    updated = re.sub(r"考察\d+本", f"考察{count}本", html, count=1)
    if updated == html:
        return False
    index_path.write_text(updated, encoding="utf-8")
    return True


def main():
    tags_dict = load_tags(TAGS_FILE)
    entries = build_entries(find_md_files(REPO_ROOT), tags_dict)
    write_entries_js(entries, OUT_FILE)
    print(f"generated {OUT_FILE} ({len(entries)} entries)")
    # REPO_ROOTから毎回導出する。テストがREPO_ROOTを差し替えたときに
    # 実リポジトリのindex.htmlを書き換えてしまうのを防ぐため。
    index_file = REPO_ROOT / "site" / "index.html"
    if update_meta_description(len(entries), index_file):
        print(f"updated meta description in {index_file}")


if __name__ == "__main__":
    main()
