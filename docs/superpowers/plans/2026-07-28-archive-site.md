# ドロピザ考察アーカイブサイト Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `doropiza`リポジトリ直下の`ドロピザ考察*.md`（12ファイル・約214件の考察）を、フリーワード検索とタグ絞り込みでブラウジングできる自分用サイトにし、Vercelにデプロイする。

**Architecture:** `scripts/generate_entries_data.py`が12個の`ドロピザ考察*.md`を全件パースし、`## `見出し単位で1考察＝1エントリに分割、`tags.json`の辞書と照合してタグを自動付与し、`site/data/entries-data.js`（`window.ENTRIES = [...]`）として書き出す。フロントは静的HTML/CSS/JSのみで、`entries-data.js`をクライアントサイドで読み込み、カード一覧・フリーワード検索・タグ絞り込み・タップで全文モーダル表示を行う。サーバーサイド処理やビルドステップは持たない。

**Tech Stack:** Python 3（標準ライブラリのみ）、Vanilla JS（依存パッケージなし）、Vercel（静的ホスティングのみ、Serverless Functionは使わない）。

## Global Constraints

- `ドロピザ考察*.md`の内容は変更しない。読み取り専用の情報源として扱う。
- `generate_entries_data.py`は実行のたびに全`ドロピザ考察*.md`を読み直し、`site/data/entries-data.js`を丸ごと上書きする（差分計算はしない）。
- 新規に外部パッケージ（pip/npm）は追加しない。Python標準ライブラリとVanilla JSのみを使う。
- サイトは公開URL・認証なし（ai_news/investmentと同じ運用）。
- Vercelプロジェクトは`doropiza`リポジトリに新規作成し、Root Directoryを`site`に設定する。

---

### Task 1: `generate_entries_data.py` — 見出しパース・ID生成（純粋関数）

**Files:**
- Create: `scripts/generate_entries_data.py`
- Create: `scripts/test_generate_entries_data.py`
- Test: `scripts/test_generate_entries_data.py`（`python3 scripts/test_generate_entries_data.py`で実行）

**Interfaces:**
- Produces: `parse_heading(heading_text: str) -> tuple[str|None, str]`、`split_entries(md_text: str) -> list[tuple[str, str]]`、`make_entry_id(file_stem: str, index: int) -> str`
- Task 4の`build_entries`はこの3関数を組み合わせて使う。

- [ ] **Step 1: 失敗するテストを書く**

`scripts/test_generate_entries_data.py`を新規作成する：

```python
#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_entries_data as ged  # noqa: E402


def test_parse_heading_with_number():
    assert ged.parse_heading("302. ゲッコー・モリアの真実") == ("302", "ゲッコー・モリアの真実")


def test_parse_heading_without_number():
    result = ged.parse_heading("転: ONE PIECEにおける革命軍の正体")
    assert result == (None, "転: ONE PIECEにおける革命軍の正体")


def test_parse_heading_strips_whitespace():
    assert ged.parse_heading("  1.   タイトル  ") == ("1", "タイトル")


def test_split_entries_two_headings():
    md = "## 1. タイトルA\n本文A1行目\n本文A2行目\n\n## 2. タイトルB\n本文B\n"
    entries = ged.split_entries(md)
    assert len(entries) == 2
    assert entries[0][0] == "1. タイトルA"
    assert "本文A1行目" in entries[0][1]
    assert "本文A2行目" in entries[0][1]
    assert entries[1][0] == "2. タイトルB"
    assert entries[1][1] == "本文B"


def test_split_entries_last_entry_runs_to_eof():
    md = "## 1. タイトルA\n本文A\n"
    entries = ged.split_entries(md)
    assert len(entries) == 1
    assert entries[0][1] == "本文A"


def test_split_entries_no_heading_returns_empty():
    assert ged.split_entries("見出しのない本文だけ\n") == []


def test_make_entry_id():
    assert ged.make_entry_id("ドロピザ考察301-330", 2) == "301-330_002"


def test_make_entry_id_pads_index():
    assert ged.make_entry_id("ドロピザ考察001-030", 12) == "001-030_012"


def run():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    run()
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 scripts/test_generate_entries_data.py`
Expected: `ModuleNotFoundError: No module named 'generate_entries_data'`（`scripts/generate_entries_data.py`が存在しないため）

- [ ] **Step 3: 最小実装を書く**

`scripts/generate_entries_data.py`を新規作成する：

```python
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
```

- [ ] **Step 4: テストを実行して成功を確認する**

Run: `python3 scripts/test_generate_entries_data.py`
Expected: `ALL TESTS PASSED`

- [ ] **Step 5: コミット**

```bash
git add scripts/generate_entries_data.py scripts/test_generate_entries_data.py
git commit -m "$(cat <<'EOF'
feat: 考察md見出しパース用の純粋関数を追加

## 見出し単位でエントリを分割し、番号付き/番号なし見出しを判別するparse_heading・split_entries・ファイル内出現順から一意IDを作るmake_entry_idを実装。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GpPNJpKXZykuk4XUPJoSFM
EOF
)"
```

---

### Task 2: `generate_entries_data.py` — Markdown→HTML変換（ai_newsから移植）

**Files:**
- Modify: `scripts/generate_entries_data.py`
- Modify: `scripts/test_generate_entries_data.py`
- Test: `scripts/test_generate_entries_data.py`

**Interfaces:**
- Produces: `inline(text: str) -> str`、`parse_table(lines: list) -> str`、`md_to_html(md: str) -> str`
- Task 4の`build_entries`はエントリ本文（Task 1の`split_entries`が返すbody）をこの`md_to_html`でHTML化する。

- [ ] **Step 1: 失敗するテストを書く**

`scripts/test_generate_entries_data.py`の`def run():`の直前に追記する：

```python
def test_inline_bold():
    assert ged.inline("**強調**テキスト") == "<strong>強調</strong>テキスト"


def test_md_to_html_single_paragraph():
    assert ged.md_to_html("ただの文章です。") == "<p>ただの文章です。</p>"


def test_md_to_html_multiple_paragraphs():
    html = ged.md_to_html("段落1\n\n段落2")
    assert html == "<p>段落1</p>\n<p>段落2</p>"


def test_md_to_html_bold_inline():
    html = ged.md_to_html("これは**重要**です。")
    assert html == "<p>これは<strong>重要</strong>です。</p>"


def test_md_to_html_list():
    html = ged.md_to_html("- 項目1\n- 項目2")
    assert html == "<ul><li>項目1</li><li>項目2</li></ul>"


def test_md_to_html_table():
    md = "| a | b |\n|---|---|\n| 1 | 2 |"
    html = ged.md_to_html(md)
    assert '<table class="rpt-table">' in html
    assert "<th>a</th>" in html
    assert "<td>1</td>" in html
```

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 scripts/test_generate_entries_data.py`
Expected: `AttributeError: module 'generate_entries_data' has no attribute 'inline'`

- [ ] **Step 3: 最小実装を書く**

`scripts/generate_entries_data.py`の`make_entry_id`関数の後に追記する（ai_news/scripts/generate_reports_data.pyの同名関数と同一の実装）：

```python
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
```

- [ ] **Step 4: テストを実行して成功を確認する**

Run: `python3 scripts/test_generate_entries_data.py`
Expected: `ALL TESTS PASSED`

- [ ] **Step 5: コミット**

```bash
git add scripts/generate_entries_data.py scripts/test_generate_entries_data.py
git commit -m "$(cat <<'EOF'
feat: 考察本文のMarkdown→HTML変換をai_newsから移植

ai_news/scripts/generate_reports_data.pyのinline/parse_table/md_to_htmlをそのまま移植し、考察本文を段落・強調・箇条書き・表を備えたHTMLへ変換できるようにした。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GpPNJpKXZykuk4XUPJoSFM
EOF
)"
```

---

### Task 3: タグ辞書ファイル作成＋タグマッチング

**Files:**
- Create: `tags.json`
- Modify: `scripts/generate_entries_data.py`
- Modify: `scripts/test_generate_entries_data.py`
- Test: `scripts/test_generate_entries_data.py`

**Interfaces:**
- Produces: `load_tags(tags_path: Path) -> dict`、`match_tags(text: str, tags_dict: dict) -> list[str]`
- Task 4の`build_entries`は`load_tags(TAGS_FILE)`で辞書を読み込み、各エントリの見出し＋本文に対して`match_tags`を呼ぶ。

- [ ] **Step 1: `tags.json`を作成する**

リポジトリ直下（`scripts/`と同階層）に`tags.json`を新規作成する。214件のタイトルを分析して抽出した主要キャラ・テーマの初期辞書：

```json
{
  "ルフィ/ニカ": ["ルフィ", "ニカ", "ゴムゴムの実", "ヒトヒトの実"],
  "イム様/世界政府": ["イム様", "世界政府", "五老星", "天竜人"],
  "黒ひげ海賊団": ["黒ひげ", "マーシャル・D・ティーチ", "ロックス"],
  "モンキー家/革命軍": ["モンキー家", "ドラゴン", "革命軍", "ガープ"],
  "空白の100年/古代史": ["空白の100年", "ゴッドバレー", "古代兵器"],
  "ジョイボーイ": ["ジョイボーイ", "ポーネグリフ"],
  "麦わらの一味": ["ゾロ", "サンジ", "ナミ", "ウソップ", "ロビン", "フランキー", "ブルック", "ジンベエ", "麦わら"],
  "サボ/エース": ["サボ", "エース"],
  "シャンクス/ロジャー": ["シャンクス", "ロジャー"],
  "エルバフ編": ["エルバフ"],
  "ワノ国編": ["ワノ国"],
  "海軍": ["海軍", "クザン", "大将"],
  "四皇/大海賊時代": ["四皇", "大船団", "海賊王"],
  "バーソロミュー・くま/ボニー": ["くま", "ボニー"],
  "ゲッコー・モリア": ["モリア"],
  "悪魔の実": ["悪魔の実"],
  "神話・宗教モデル": ["神話", "宗教"],
  "実在の歴史・世界遺産": ["世界遺産", "実在する"],
  "他作品": ["推しの子", "アイシールド21", "ポケモン", "ディズニー"]
}
```

タグ名・キーワードは今後この`tags.json`を直接編集するだけで拡張できる（スクリプト・サイト側の変更は不要）。

- [ ] **Step 2: 失敗するテストを書く**

`scripts/test_generate_entries_data.py`の`def run():`の直前に追記する：

```python
def test_match_tags_single_match():
    tags_dict = {"ルフィ/ニカ": ["ルフィ", "ニカ"], "黒ひげ海賊団": ["黒ひげ"]}
    assert ged.match_tags("ルフィが食べた実の正体", tags_dict) == ["ルフィ/ニカ"]


def test_match_tags_multiple_matches():
    tags_dict = {"ルフィ/ニカ": ["ルフィ"], "黒ひげ海賊団": ["黒ひげ"]}
    result = ged.match_tags("ルフィと黒ひげの因縁", tags_dict)
    assert set(result) == {"ルフィ/ニカ", "黒ひげ海賊団"}


def test_match_tags_no_match_returns_unclassified():
    tags_dict = {"ルフィ/ニカ": ["ルフィ"]}
    assert ged.match_tags("無関係な文章", tags_dict) == ["未分類"]


def test_load_tags_missing_file_returns_empty_dict():
    assert ged.load_tags(Path("/tmp/does_not_exist_tags_test.json")) == {}


def test_load_tags_reads_real_file():
    tags_dict = ged.load_tags(ged.TAGS_FILE)
    assert "ルフィ/ニカ" in tags_dict
    assert "ルフィ" in tags_dict["ルフィ/ニカ"]
```

（テストファイル冒頭に`from pathlib import Path`を追加する）

- [ ] **Step 3: テストを実行して失敗を確認する**

Run: `python3 scripts/test_generate_entries_data.py`
Expected: `AttributeError: module 'generate_entries_data' has no attribute 'load_tags'`

- [ ] **Step 4: 最小実装を書く**

`scripts/generate_entries_data.py`の`md_to_html`関数の後に追記する：

```python
def load_tags(tags_path: Path) -> dict:
    if not tags_path.exists():
        return {}
    return json.loads(tags_path.read_text(encoding="utf-8"))


def match_tags(text: str, tags_dict: dict) -> list:
    matched = [name for name, keywords in tags_dict.items() if any(kw in text for kw in keywords)]
    return matched if matched else ["未分類"]
```

- [ ] **Step 5: テストを実行して成功を確認する**

Run: `python3 scripts/test_generate_entries_data.py`
Expected: `ALL TESTS PASSED`

- [ ] **Step 6: コミット**

```bash
git add tags.json scripts/generate_entries_data.py scripts/test_generate_entries_data.py
git commit -m "$(cat <<'EOF'
feat: キャラ/テーマのタグ辞書と自動タグ付けを追加

tags.jsonにキャラクター・テーマ19項目のキーワード辞書を定義し、見出し+本文から部分一致でタグを自動付与するmatch_tagsを実装。未一致は「未分類」タグを付与する。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GpPNJpKXZykuk4XUPJoSFM
EOF
)"
```

---

### Task 4: `generate_entries_data.py` — main()配線と実データ生成

**Files:**
- Modify: `scripts/generate_entries_data.py`
- Modify: `scripts/test_generate_entries_data.py`
- Create: `site/data/entries-data.js`（実行結果として生成・コミット）
- Test: `scripts/test_generate_entries_data.py`

**Interfaces:**
- Consumes: Task 1の`split_entries`・`parse_heading`・`make_entry_id`、Task 2の`md_to_html`、Task 3の`load_tags`・`match_tags`
- Produces: `find_md_files(repo_root: Path) -> list[Path]`、`build_entries(file_paths: list, tags_dict: dict) -> list[dict]`、`write_entries_js(entries: list, out_path: Path)`、`main()`
- `site/data/entries-data.js`のスキーマ: `window.ENTRIES = [{id, number, title, sourceFile, tags, html}, ...]`。Task 5・Task 6・Task 7のフロントはこのスキーマをそのまま読む。

- [ ] **Step 1: 失敗するテストを書く**

`scripts/test_generate_entries_data.py`の先頭に`import tempfile`を追加し、`def run():`の直前に追記する：

```python
def test_find_md_files_sorted_by_name():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "ドロピザ考察031-060.md").write_text("", encoding="utf-8")
        (d / "ドロピザ考察001-030.md").write_text("", encoding="utf-8")
        files = ged.find_md_files(d)
        assert [f.name for f in files] == ["ドロピザ考察001-030.md", "ドロピザ考察031-060.md"]


def test_build_entries_basic():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "ドロピザ考察001-030.md").write_text(
            "## 1. ルフィの正体\nルフィは**ニカ**である。\n\n"
            "## 転: 黒ひげの謎\n黒ひげ海賊団の真実。\n",
            encoding="utf-8",
        )
        tags_dict = {"ルフィ/ニカ": ["ルフィ", "ニカ"], "黒ひげ海賊団": ["黒ひげ"]}
        entries = ged.build_entries(ged.find_md_files(d), tags_dict)

        assert len(entries) == 2
        assert entries[0]["id"] == "001-030_001"
        assert entries[0]["number"] == "1"
        assert entries[0]["title"] == "ルフィの正体"
        assert entries[0]["sourceFile"] == "ドロピザ考察001-030.md"
        assert entries[0]["tags"] == ["ルフィ/ニカ"]
        assert "<strong>ニカ</strong>" in entries[0]["html"]

        assert entries[1]["id"] == "001-030_002"
        assert entries[1]["number"] is None
        assert entries[1]["title"] == "転: 黒ひげの謎"
        assert entries[1]["tags"] == ["黒ひげ海賊団"]


def test_build_entries_skips_empty_body():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "ドロピザ考察001-030.md").write_text(
            "## 1. 空の考察\n\n## 2. 中身あり\n本文。\n", encoding="utf-8"
        )
        entries = ged.build_entries(ged.find_md_files(d), {})
        assert len(entries) == 1
        assert entries[0]["title"] == "中身あり"


def test_write_entries_js_and_main():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "ドロピザ考察001-030.md").write_text("## 1. サンプル\n本文です。\n", encoding="utf-8")
        tags_file = d / "tags.json"
        tags_file.write_text("{}", encoding="utf-8")
        out_file = d / "site" / "data" / "entries-data.js"

        original = (ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE)
        ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE = d, tags_file, out_file
        try:
            ged.main()
        finally:
            ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE = original

        content = out_file.read_text(encoding="utf-8")
        assert content.startswith("window.ENTRIES = ")
        json_text = content[len("window.ENTRIES = "):].strip()
        if json_text.endswith(";"):
            json_text = json_text[:-1]
        data = json.loads(json_text)
        assert len(data) == 1
        assert data[0]["title"] == "サンプル"


def test_main_handles_no_md_files():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        tags_file = d / "tags.json"
        tags_file.write_text("{}", encoding="utf-8")
        out_file = d / "site" / "data" / "entries-data.js"

        original = (ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE)
        ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE = d, tags_file, out_file
        try:
            ged.main()
        finally:
            ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE = original

        content = out_file.read_text(encoding="utf-8")
        assert "window.ENTRIES = []" in content
```

（テストファイル先頭のimportに`import json`を追加する）

- [ ] **Step 2: テストを実行して失敗を確認する**

Run: `python3 scripts/test_generate_entries_data.py`
Expected: `AttributeError: module 'generate_entries_data' has no attribute 'find_md_files'`

- [ ] **Step 3: 最小実装を書く**

`scripts/generate_entries_data.py`の末尾に追記する：

```python
def find_md_files(repo_root: Path) -> list:
    return sorted(repo_root.glob(MD_GLOB))


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
                "sourceFile": file_path.name,
                "tags": match_tags(f"{heading}\n{body}", tags_dict),
                "html": md_to_html(body),
            })
    return entries


def write_entries_js(entries: list, out_path: Path):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    js = "window.ENTRIES = " + json.dumps(entries, ensure_ascii=False, indent=2) + ";\n"
    out_path.write_text(js, encoding="utf-8")


def main():
    tags_dict = load_tags(TAGS_FILE)
    entries = build_entries(find_md_files(REPO_ROOT), tags_dict)
    write_entries_js(entries, OUT_FILE)
    print(f"generated {OUT_FILE} ({len(entries)} entries)")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: テストを実行して成功を確認する**

Run: `python3 scripts/test_generate_entries_data.py`
Expected: `ALL TESTS PASSED`

- [ ] **Step 5: 実データに対して実行し、生成物を確認する**

Run: `python3 scripts/generate_entries_data.py`
Expected: `generated .../site/data/entries-data.js (214 entries)`（本文が空のエントリがあればスキップされるため件数は多少前後してよい）

Run: `python3 -c "
import json, pathlib
text = pathlib.Path('site/data/entries-data.js').read_text(encoding='utf-8')
data = json.loads(text[len('window.ENTRIES = '):].strip().rstrip(';'))
print(len(data))
print(data[0]['id'], data[0]['number'], data[0]['title'], data[0]['tags'])
print([e for e in data if e['number'] is None][:2])
"`
Expected: エラーなくJSONとしてパースでき、件数・先頭エントリの内容・番号なしエントリのサンプルが表示される

- [ ] **Step 6: コミット**

```bash
git add scripts/generate_entries_data.py scripts/test_generate_entries_data.py site/data/entries-data.js
git commit -m "$(cat <<'EOF'
feat: main()配線と初回entries-data.js生成

12個のドロピザ考察*.mdを全件パースしsite/data/entries-data.jsを生成するmain()を実装。実データに対して実行し初回生成物をコミット。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GpPNJpKXZykuk4XUPJoSFM
EOF
)"
```

---

### Task 5: 静的フロント骨格（カード一覧表示のみ）

**Files:**
- Create: `site/index.html`
- Create: `site/style.css`
- Create: `site/app.js`
- Create: `site/images/doropiza.png`（既存`images/doropiza.png`のコピー）

**Interfaces:**
- Consumes: `site/data/entries-data.js`（Task 4の出力）の`window.ENTRIES`
- Produces: DOM要素`#card-grid`, `#entry-count`。Task 6・Task 7はこれらのidと、Task 5で定義するカードのマークアップ構造（`.entry-card[data-id]`）をそのまま使う。

- [ ] **Step 1: ロゴ画像をsite配下にコピーする**

Vercelは`site/`をRoot Directoryとしてデプロイするため、`site/`の外にあるファイルは配信されない。ヘッダーに使うロゴをコピーする：

Run: `mkdir -p site/images && cp images/doropiza.png site/images/doropiza.png`

- [ ] **Step 2: `site/index.html`を作成する**

```html
<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>ドロピザ考察アーカイブ</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="ドロピザのONE PIECE考察約210本をフリーワード検索・タグ絞り込みで探せる自分用アーカイブ。">
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="site-header">
  <img src="images/doropiza.png" alt="ドロピザ" class="logo">
  <div class="header-text">
    <h1>ドロピザ考察アーカイブ</h1>
    <p id="entry-count" class="entry-count"></p>
  </div>
</header>
<main>
  <div id="card-grid" class="card-grid"></div>
</main>
<script src="data/entries-data.js"></script>
<script src="app.js"></script>
</body>
</html>
```

- [ ] **Step 3: `site/style.css`を作成する（宝地図テーマ）**

```css
:root {
  --parchment: #f0e0bd;
  --parchment-dark: #e2cd9c;
  --ink: #2b1d0e;
  --gold: #c9962c;
  --wine: #7a1f2b;
  --sea: #2b5a63;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Hiragino Mincho ProN", "Yu Mincho", serif;
  color: var(--ink);
  background:
    radial-gradient(ellipse at 20% 0%, rgba(255, 255, 255, 0.25), transparent 60%),
    radial-gradient(ellipse at 80% 100%, rgba(122, 31, 43, 0.08), transparent 55%),
    linear-gradient(160deg, var(--parchment) 0%, var(--parchment-dark) 100%);
  min-height: 100vh;
}
.site-header {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-bottom: 3px double var(--gold);
}
.logo { height: 56px; width: auto; }
.header-text h1 {
  margin: 0;
  font-size: 1.3rem;
  color: var(--wine);
  letter-spacing: 0.04em;
}
.entry-count { margin: 2px 0 0; font-size: 0.85rem; color: var(--ink); opacity: 0.7; }
main { padding: 20px 24px 60px; }
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
.entry-card {
  position: relative;
  background: rgba(255, 250, 235, 0.75);
  border: 1px solid var(--gold);
  border-radius: 6px;
  padding: 16px 16px 14px;
  cursor: pointer;
  box-shadow: 2px 3px 0 rgba(43, 29, 14, 0.12);
  transition: transform 0.1s ease;
}
.entry-card:hover, .entry-card:focus-visible { transform: translateY(-2px); }
.entry-card .badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--wine);
  color: var(--parchment);
  font-size: 0.8rem;
  font-weight: 700;
  margin-bottom: 8px;
}
.entry-card h2 {
  margin: 0 0 10px;
  font-size: 1rem;
  line-height: 1.5;
  color: var(--ink);
}
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.tag {
  font-size: 0.72rem;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--sea);
  color: #fdf6e3;
}
.source { font-size: 0.72rem; opacity: 0.6; }
```

- [ ] **Step 4: `site/app.js`を作成する**

```js
(function () {
  const grid = document.getElementById("card-grid");
  const countEl = document.getElementById("entry-count");
  const entries = window.ENTRIES || [];

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderCards(list) {
    grid.innerHTML = list
      .map(
        (e) => `
      <div class="entry-card" tabindex="0" role="button" data-id="${e.id}">
        ${e.number ? `<div class="badge">${escapeHtml(e.number)}</div>` : ""}
        <h2>${escapeHtml(e.title)}</h2>
        <div class="tags">${e.tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}</div>
        <div class="source">${escapeHtml(e.sourceFile)}</div>
      </div>`
      )
      .join("");
  }

  countEl.textContent = `全${entries.length}件`;
  renderCards(entries);
})();
```

- [ ] **Step 5: ブラウザで手動確認する**

Run: `cd site && python3 -m http.server 8000`
ブラウザで`http://localhost:8000`を開き、以下を確認する：
- ヘッダーにドロピザのロゴと「全214件」前後の件数が表示される
- カードが一覧表示され、番号バッジ（あるもののみ）・タイトル・タグ・出典ファイル名が読める
- 羊皮紙風の背景色になっている
Expected: 上記が崩れずに表示される。確認できたら`Ctrl+C`でサーバーを停止する。

- [ ] **Step 6: コミット**

```bash
git add site/index.html site/style.css site/app.js site/images/doropiza.png
git commit -m "$(cat <<'EOF'
feat: 考察アーカイブサイトの静的フロント骨格を追加

entries-data.jsを読み込みカードグリッドを描画する最小構成のindex.html/style.css/app.jsを、宝地図テーマで追加。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GpPNJpKXZykuk4XUPJoSFM
EOF
)"
```

---

### Task 6: カードタップ→モーダル全文表示

**Files:**
- Modify: `site/index.html`
- Modify: `site/style.css`
- Modify: `site/app.js`

**Interfaces:**
- Consumes: Task 5の`entries`配列、DOM要素`#card-grid`
- Produces: `openModal(id: string)`、`closeModal()`、DOM要素`#modal`, `#modal-close`。Task 7はこれらをそのまま使い、フィルタ後のリストに対して同じ`openModal`を呼ぶ。

- [ ] **Step 1: `site/index.html`の`<main>`の後、`<script>`の前にモーダルのマークアップを追加する**

`old_string`:
```html
</main>
<script src="data/entries-data.js"></script>
```

`new_string`:
```html
</main>
<div id="modal" class="modal" hidden>
  <div class="modal-backdrop"></div>
  <div class="modal-body">
    <button id="modal-close" class="modal-close" aria-label="閉じる">×</button>
    <div id="modal-number" class="modal-number"></div>
    <h2 id="modal-title"></h2>
    <div id="modal-tags" class="tags"></div>
    <div id="modal-content" class="modal-content"></div>
  </div>
</div>
<script src="data/entries-data.js"></script>
```

- [ ] **Step 2: `site/style.css`の末尾にモーダルのスタイルを追記する**

```css
.modal { position: fixed; inset: 0; z-index: 50; }
.modal[hidden] { display: none; }
.modal-backdrop { position: absolute; inset: 0; background: rgba(43, 29, 14, 0.55); }
.modal-body {
  position: relative;
  max-width: 720px;
  margin: 40px auto;
  max-height: calc(100vh - 80px);
  overflow-y: auto;
  background: #fdf6e3;
  border: 2px solid var(--gold);
  border-radius: 8px;
  padding: 28px 28px 32px;
}
.modal-close {
  position: sticky;
  top: 0;
  float: right;
  border: none;
  background: none;
  font-size: 1.6rem;
  color: var(--ink);
  cursor: pointer;
}
.modal-number {
  clear: both;
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  background: var(--wine);
  color: var(--parchment);
  font-size: 0.8rem;
  margin-bottom: 8px;
}
#modal-title { margin: 0 0 10px; color: var(--wine); }
.modal-content { line-height: 1.9; }
.modal-content p { margin: 0 0 1em; }
```

- [ ] **Step 3: `site/app.js`を以下の内容に置き換える**

```js
(function () {
  const grid = document.getElementById("card-grid");
  const countEl = document.getElementById("entry-count");
  const entries = window.ENTRIES || [];

  const modal = document.getElementById("modal");
  const modalBackdrop = modal.querySelector(".modal-backdrop");
  const modalClose = document.getElementById("modal-close");
  const modalNumber = document.getElementById("modal-number");
  const modalTitle = document.getElementById("modal-title");
  const modalTags = document.getElementById("modal-tags");
  const modalContent = document.getElementById("modal-content");

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderCards(list) {
    grid.innerHTML = list
      .map(
        (e) => `
      <div class="entry-card" tabindex="0" role="button" data-id="${e.id}">
        ${e.number ? `<div class="badge">${escapeHtml(e.number)}</div>` : ""}
        <h2>${escapeHtml(e.title)}</h2>
        <div class="tags">${e.tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}</div>
        <div class="source">${escapeHtml(e.sourceFile)}</div>
      </div>`
      )
      .join("");
  }

  function openModal(id) {
    const entry = entries.find((e) => e.id === id);
    if (!entry) return;
    modalNumber.textContent = entry.number ? `No.${entry.number}` : "";
    modalNumber.style.display = entry.number ? "inline-block" : "none";
    modalTitle.textContent = entry.title;
    modalTags.innerHTML = entry.tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("");
    modalContent.innerHTML = entry.html;
    modal.removeAttribute("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    modal.setAttribute("hidden", "");
    document.body.style.overflow = "";
  }

  grid.addEventListener("click", (e) => {
    const card = e.target.closest(".entry-card");
    if (card) openModal(card.dataset.id);
  });
  grid.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const card = e.target.closest(".entry-card");
    if (card) {
      e.preventDefault();
      openModal(card.dataset.id);
    }
  });

  modalClose.addEventListener("click", closeModal);
  modalBackdrop.addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.hasAttribute("hidden")) closeModal();
  });

  countEl.textContent = `全${entries.length}件`;
  renderCards(entries);
})();
```

- [ ] **Step 4: ブラウザで手動確認する**

Run: `cd site && python3 -m http.server 8000`
ブラウザで`http://localhost:8000`を開き、以下を確認する：
- カードをクリックするとモーダルが開き、番号（あれば）・タイトル・タグ・全文が表示される
- ×ボタン、背景クリック、Escapeキーのいずれでもモーダルが閉じる
- 別のカードをクリックすると別のエントリの内容に切り替わる
Expected: 上記全てが動作する。確認できたら`Ctrl+C`でサーバーを停止する。

- [ ] **Step 5: コミット**

```bash
git add site/index.html site/style.css site/app.js
git commit -m "$(cat <<'EOF'
feat: カードタップで考察全文をモーダル表示する

entry-card クリックでentries-data.jsの該当エントリのhtmlをモーダルに表示。×/背景クリック/Escapeで閉じる操作を実装。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GpPNJpKXZykuk4XUPJoSFM
EOF
)"
```

---

### Task 7: フリーワード検索＋タグ絞り込みチップ

**Files:**
- Modify: `site/index.html`
- Modify: `site/style.css`
- Modify: `site/app.js`

**Interfaces:**
- Consumes: Task 6の`entries`, `renderCards(list)`, `openModal(id)`
- Produces: なし（末端のUI機能）

- [ ] **Step 1: `site/index.html`の`<main>`内、`#card-grid`の前に検索・タグUIを追加する**

`old_string`:
```html
<main>
  <div id="card-grid" class="card-grid"></div>
</main>
```

`new_string`:
```html
<main>
  <div class="controls">
    <input id="search" type="search" class="search-input" placeholder="キーワードで検索（例: イム様）">
    <div id="tag-filters" class="tag-filters"></div>
  </div>
  <div id="card-grid" class="card-grid"></div>
</main>
```

- [ ] **Step 2: `site/style.css`の末尾に検索・タグフィルタのスタイルを追記する**

```css
.controls { margin-bottom: 18px; }
.search-input {
  width: 100%;
  max-width: 420px;
  padding: 10px 14px;
  font-size: 0.95rem;
  border: 1px solid var(--gold);
  border-radius: 999px;
  background: rgba(255, 250, 235, 0.85);
  color: var(--ink);
  margin-bottom: 10px;
}
.search-input:focus { outline: 2px solid var(--wine); outline-offset: 1px; }
.tag-filters { display: flex; flex-wrap: wrap; gap: 8px; }
.tag-filter-chip {
  font-size: 0.78rem;
  padding: 4px 12px;
  border-radius: 999px;
  border: 1px solid var(--sea);
  background: transparent;
  color: var(--sea);
  cursor: pointer;
}
.tag-filter-chip.active { background: var(--gold); border-color: var(--gold); color: var(--ink); font-weight: 700; }
```

- [ ] **Step 3: `site/app.js`を以下の内容に置き換える**

```js
(function () {
  const grid = document.getElementById("card-grid");
  const countEl = document.getElementById("entry-count");
  const searchInput = document.getElementById("search");
  const tagFilters = document.getElementById("tag-filters");
  const entries = window.ENTRIES || [];

  const modal = document.getElementById("modal");
  const modalBackdrop = modal.querySelector(".modal-backdrop");
  const modalClose = document.getElementById("modal-close");
  const modalNumber = document.getElementById("modal-number");
  const modalTitle = document.getElementById("modal-title");
  const modalTags = document.getElementById("modal-tags");
  const modalContent = document.getElementById("modal-content");

  const state = { query: "", activeTags: new Set() };

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  const searchText = new Map(
    entries.map((e) => [e.id, `${e.title} ${e.html.replace(/<[^>]*>/g, " ")}`])
  );

  function allTags() {
    const set = new Set();
    entries.forEach((e) => e.tags.forEach((t) => set.add(t)));
    return Array.from(set).sort((a, b) => a.localeCompare(b, "ja"));
  }

  function filteredEntries() {
    return entries.filter((e) => {
      const matchesQuery = !state.query || searchText.get(e.id).includes(state.query);
      const matchesTags =
        state.activeTags.size === 0 || Array.from(state.activeTags).every((t) => e.tags.includes(t));
      return matchesQuery && matchesTags;
    });
  }

  function renderCards(list) {
    grid.innerHTML = list
      .map(
        (e) => `
      <div class="entry-card" tabindex="0" role="button" data-id="${e.id}">
        ${e.number ? `<div class="badge">${escapeHtml(e.number)}</div>` : ""}
        <h2>${escapeHtml(e.title)}</h2>
        <div class="tags">${e.tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("")}</div>
        <div class="source">${escapeHtml(e.sourceFile)}</div>
      </div>`
      )
      .join("");
  }

  function renderTagFilters() {
    tagFilters.innerHTML = allTags()
      .map(
        (t) => `<button type="button" class="tag-filter-chip${state.activeTags.has(t) ? " active" : ""}" data-tag="${escapeHtml(t)}">${escapeHtml(t)}</button>`
      )
      .join("");
  }

  function update() {
    const list = filteredEntries();
    countEl.textContent = `全${entries.length}件中 ${list.length}件表示`;
    renderCards(list);
  }

  function openModal(id) {
    const entry = entries.find((e) => e.id === id);
    if (!entry) return;
    modalNumber.textContent = entry.number ? `No.${entry.number}` : "";
    modalNumber.style.display = entry.number ? "inline-block" : "none";
    modalTitle.textContent = entry.title;
    modalTags.innerHTML = entry.tags.map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("");
    modalContent.innerHTML = entry.html;
    modal.removeAttribute("hidden");
    document.body.style.overflow = "hidden";
  }

  function closeModal() {
    modal.setAttribute("hidden", "");
    document.body.style.overflow = "";
  }

  searchInput.addEventListener("input", (e) => {
    state.query = e.target.value.trim();
    update();
  });

  tagFilters.addEventListener("click", (e) => {
    const chip = e.target.closest(".tag-filter-chip");
    if (!chip) return;
    const tag = chip.dataset.tag;
    if (state.activeTags.has(tag)) {
      state.activeTags.delete(tag);
    } else {
      state.activeTags.add(tag);
    }
    renderTagFilters();
    update();
  });

  grid.addEventListener("click", (e) => {
    const card = e.target.closest(".entry-card");
    if (card) openModal(card.dataset.id);
  });
  grid.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const card = e.target.closest(".entry-card");
    if (card) {
      e.preventDefault();
      openModal(card.dataset.id);
    }
  });

  modalClose.addEventListener("click", closeModal);
  modalBackdrop.addEventListener("click", closeModal);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !modal.hasAttribute("hidden")) closeModal();
  });

  renderTagFilters();
  update();
})();
```

- [ ] **Step 4: ブラウザで手動確認する**

Run: `cd site && python3 -m http.server 8000`
ブラウザで`http://localhost:8000`を開き、以下を確認する：
- 検索欄に「イム様」等キャラ名を入力すると、該当する考察のみカードが絞り込まれ、件数表示（「全214件中 N件表示」）が更新される
- タグチップをクリックすると該当タグを持つカードのみに絞り込まれ、チップがハイライトされる。複数タグを選ぶとAND条件で絞り込まれる
- 検索とタグ絞り込みを併用しても正しく絞り込まれる
- 検索欄を空にする／全タグを解除すると全カードに戻る
- 絞り込み後のカードをタップしてもモーダルが正しく開く
Expected: 上記全てが動作する。確認できたら`Ctrl+C`でサーバーを停止する。

- [ ] **Step 5: コミット**

```bash
git add site/index.html site/style.css site/app.js
git commit -m "$(cat <<'EOF'
feat: フリーワード検索とタグ絞り込みチップを追加

タイトル+本文プレーンテキストに対するフリーワード検索と、タグチップのAND条件絞り込みをクライアントサイドで実装。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GpPNJpKXZykuk4XUPJoSFM
EOF
)"
```

---

### Task 8: ファビコン一式作成

**Files:**
- Create: `site/favicon-32.png`
- Create: `site/favicon-16.png`
- Create: `site/apple-touch-icon.png`
- Modify: `site/index.html`

**Interfaces:**
- Consumes: `site/images/doropiza.png`（Task 5でコピー済み）

- [ ] **Step 1: macOS標準の`sips`コマンドでアイコン画像を生成する**

Run:
```bash
sips -z 32 32 site/images/doropiza.png --out site/favicon-32.png
sips -z 16 16 site/images/doropiza.png --out site/favicon-16.png
sips -z 180 180 site/images/doropiza.png --out site/apple-touch-icon.png
```
Expected: 3つのPNGファイルがエラーなく生成される（元画像が正方形でないため縦横比は多少潰れるが、個人用ツールのため許容する）

- [ ] **Step 2: `site/index.html`の`<head>`にファビコンのリンクを追加する**

`old_string`:
```html
<link rel="stylesheet" href="style.css">
</head>
```

`new_string`:
```html
<link rel="stylesheet" href="style.css">
<link rel="icon" type="image/png" sizes="32x32" href="favicon-32.png">
<link rel="icon" type="image/png" sizes="16x16" href="favicon-16.png">
<link rel="apple-touch-icon" href="apple-touch-icon.png">
</head>
```

- [ ] **Step 3: ブラウザで確認する**

Run: `cd site && python3 -m http.server 8000`
ブラウザで`http://localhost:8000`を開き、ブラウザタブにファビコンが表示されることを確認する。確認できたら`Ctrl+C`でサーバーを停止する。

- [ ] **Step 4: コミット**

```bash
git add site/favicon-32.png site/favicon-16.png site/apple-touch-icon.png site/index.html
git commit -m "$(cat <<'EOF'
feat: ドロピザロゴからファビコン一式を生成

images/doropiza.pngからsips でfavicon(16/32px)・apple-touch-iconを書き出し、index.htmlに反映。

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01GpPNJpKXZykuk4XUPJoSFM
EOF
)"
```

---

### Task 9: Vercelへのデプロイ

**Files:**
- なし（Vercelダッシュボード操作＋デプロイ後の疎通確認）

**Interfaces:**
- Consumes: これまでの全タスクの成果物（`site/`配下一式）

- [ ] **Step 1: リポジトリをGitHubにpushする**

Run: `git push origin main`
Expected: エラーなくpushが完了する

- [ ] **Step 2:（ユーザー操作）Vercelで新規プロジェクトを作成する**

Vercelダッシュボードで以下を行う：
1. 「Add New Project」→ GitHubの`doropiza`リポジトリをImport
2. 「Root Directory」を`site`に設定
3. Framework Presetは「Other」のままでよい（ビルドコマンド不要、静的ファイルのみ）
4. 「Deploy」を実行する

- [ ] **Step 3: デプロイ後の疎通確認をする**

Run（`<url>`は実際のデプロイURLに置き換える）:
```bash
curl -s https://<url>/data/entries-data.js | head -c 200
```
Expected: `window.ENTRIES = [` から始まるJSが返る（HTTP 200）

- [ ] **Step 4: ブラウザで最終確認する**

デプロイURLをブラウザで開き、以下を確認する：
- カード一覧・件数表示が表示される
- フリーワード検索・タグ絞り込みが機能する
- カードタップでモーダルが開き全文が読める
- ファビコンが表示される

Expected: ここまでの全ステップが確認できれば実装完了。
