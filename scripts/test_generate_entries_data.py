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


def run():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    run()
