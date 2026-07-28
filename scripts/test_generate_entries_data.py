#!/usr/bin/env python3
import json
import sys
import tempfile
import unicodedata
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


def test_find_md_files_sorted_by_name():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "ドロピザ考察031-060.md").write_text("", encoding="utf-8")
        (d / "ドロピザ考察001-030.md").write_text("", encoding="utf-8")
        files = ged.find_md_files(d)
        assert [f.name for f in files] == ["ドロピザ考察001-030.md", "ドロピザ考察031-060.md"]


def test_find_md_files_detects_nfd_filenames():
    # macOS上のファイルシステムはファイル名をNFD（濁点等が分解された形）で
    # 保持することがある。ここでは実際にNFD形式のファイル名でファイルを
    # 作成し、find_md_filesがNFC/NFDどちらの表記でもマッチできることを
    # 検証する（実データで119/214件しか検出できなかった回帰を防ぐテスト）。
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        nfc_name = unicodedata.normalize("NFC", "ドロピザ考察001-030.md")
        nfd_name = unicodedata.normalize("NFD", "ドロピザ考察031-060.md")
        assert nfc_name != nfd_name  # 前提: 実際にバイト表現が異なること

        (d / nfc_name).write_text("", encoding="utf-8")
        (d / nfd_name).write_text("", encoding="utf-8")

        files = ged.find_md_files(d)
        normalized_names = [unicodedata.normalize("NFC", f.name) for f in files]
        assert normalized_names == [
            "ドロピザ考察001-030.md",
            "ドロピザ考察031-060.md",
        ]


def test_build_entries_normalizes_source_file_to_nfc():
    # build_entriesが格納するsourceFileも、find_md_filesが検出した元の
    # ファイル名の正規化形式（NFC/NFD）に関わらずNFCに統一されることを検証する。
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        nfd_name = unicodedata.normalize("NFD", "ドロピザ考察031-060.md")
        (d / nfd_name).write_text("## 1. サンプル\n本文です。\n", encoding="utf-8")

        entries = ged.build_entries(ged.find_md_files(d), {})
        assert len(entries) == 1
        assert entries[0]["sourceFile"] == "ドロピザ考察031-060.md"
        assert unicodedata.is_normalized("NFC", entries[0]["sourceFile"])


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


def run():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    run()
