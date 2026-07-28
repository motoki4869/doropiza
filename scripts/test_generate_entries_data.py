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
    html = ged.md_to_html("これは最初の段落です。\n\nこれは次の段落です。")
    assert html == "<p>これは最初の段落です。</p>\n<p>これは次の段落です。</p>"


def test_md_to_html_bold_inline():
    html = ged.md_to_html("これは**重要**です。")
    assert html == "<p>これは<strong>重要</strong>です。</p>"


def test_md_to_html_list():
    html = ged.md_to_html("- 項目1\n- 項目2")
    assert html == "<ul><li>項目1</li><li>項目2</li></ul>"


def test_list_label_colon_inside_bold():
    assert ged.list_label("**「D」の真の意味:**") == "「D」の真の意味"


def test_list_label_colon_outside_bold():
    assert ged.list_label("**「D」の真の意味**:") == "「D」の真の意味"


def test_list_label_full_width_colon():
    assert ged.list_label("**ラベル：**") == "ラベル"


def test_list_label_bold_without_colon_is_not_a_label():
    # 太字だけでコロンが無い項目は、ただの強調された箇条書き項目であってラベルではない
    assert ged.list_label("**重要な項目**") is None


def test_list_label_plain_item_is_not_a_label():
    assert ged.list_label("ふつうの項目") is None


def test_md_to_html_list_with_label_becomes_label_and_ul():
    md = "- **「D」の真の意味:**\n- ダイバーシティ（多様性）の意味を持つ\n- 差別された種族全般を指す"
    html = ged.md_to_html(md)
    assert html == (
        '<p class="list-label">「D」の真の意味</p>\n'
        "<ul><li>ダイバーシティ（多様性）の意味を持つ</li><li>差別された種族全般を指す</li></ul>"
    )


def test_md_to_html_list_without_label_is_unaffected():
    html = ged.md_to_html("- 項目1\n- 項目2")
    assert html == "<ul><li>項目1</li><li>項目2</li></ul>"


def test_md_to_html_label_only_list_has_no_trailing_ul():
    html = ged.md_to_html("- **単独ラベル:**")
    assert html == '<p class="list-label">単独ラベル</p>'


def test_md_to_html_numbered_h3_becomes_sec_num_heading():
    """新しい原稿ファイルは「1. 見出し」をプレーンテキストではなく
    Markdown見出し(### 1. 見出し)で書くようになった。既存記事の
    番号付き見出しと同じ丸数字バッジのスタイルに揃える。"""
    html = ged.md_to_html("### 1. 導入部分")
    assert html == '<h4 class="sec-num"><span class="num">1</span>導入部分</h4>'


def test_md_to_html_non_numbered_h3_becomes_sec_heading():
    html = ged.md_to_html("### この動画が伝えたかったこと")
    assert html == '<h3 class="sec">この動画が伝えたかったこと</h3>'


def test_md_to_html_h4_becomes_sec_sub_heading():
    html = ged.md_to_html("#### 人工の森とレッドラインの真実")
    assert html == '<h4 class="sec-sub">人工の森とレッドラインの真実</h4>'


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


def test_main_updates_meta_description_count():
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "ドロピザ考察001-030.md").write_text(
            "## 1. サンプルA\n本文です。\n\n## 2. サンプルB\n本文です。\n", encoding="utf-8"
        )
        tags_file = d / "tags.json"
        tags_file.write_text("{}", encoding="utf-8")
        out_file = d / "site" / "data" / "entries-data.js"
        index_file = d / "site" / "index.html"
        index_file.parent.mkdir(parents=True, exist_ok=True)
        index_file.write_text(
            '<meta name="description" content="考察999本を検索できる。">', encoding="utf-8"
        )

        original = (ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE)
        ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE = d, tags_file, out_file
        try:
            ged.main()
        finally:
            ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE = original

        assert "考察2本" in index_file.read_text(encoding="utf-8")


def test_main_does_not_touch_the_real_index_html():
    """main()はREPO_ROOT配下だけを書き換える。

    INDEX_FILEをモジュール定数にしていたとき、REPO_ROOTだけ差し替えた
    テストが実リポジトリのindex.htmlを「考察0本」に書き潰した回帰がある。
    """
    real_index = Path(__file__).resolve().parent.parent / "site" / "index.html"
    before = real_index.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        tags_file = d / "tags.json"
        tags_file.write_text("{}", encoding="utf-8")

        original = (ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE)
        ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE = d, tags_file, d / "out.js"
        try:
            ged.main()
        finally:
            ged.REPO_ROOT, ged.TAGS_FILE, ged.OUT_FILE = original

    assert real_index.read_text(encoding="utf-8") == before


def test_plain_block_numbered_line_becomes_section_heading():
    html = ged.plain_block_to_html("1. 最終章へのカウントダウンとワノ国後の展開")
    assert html == (
        '<h4 class="sec-num"><span class="num">1</span>'
        "最終章へのカウントダウンとワノ国後の展開</h4>"
    )


def test_plain_block_numbered_sentence_stays_paragraph():
    # 句点を含む長い文は見出しではなく本文として扱う
    line = "1. これは実際には本文であり、句点を含むため見出しではありません。"
    assert ged.plain_block_to_html(line) == f"<p>{line}</p>"


def test_plain_block_labeled_line_becomes_term_item():
    html = ged.plain_block_to_html("物語の終焉に向けたペース: 尾田先生は2019年時点で言及した。")
    assert html == (
        '<p class="term-item"><span class="term">物語の終焉に向けたペース</span>'
        "尾田先生は2019年時点で言及した。</p>"
    )


def test_plain_block_full_width_colon_is_supported():
    html = ged.plain_block_to_html("捕縛のタイミング：カイドウを倒した後に消耗する。")
    assert '<span class="term">捕縛のタイミング</span>' in html


def test_plain_block_trailing_colon_becomes_subheading():
    assert ged.plain_block_to_html("名前の由来:") == '<h4 class="sec-sub">名前の由来</h4>'


def test_plain_block_short_standalone_line_becomes_section():
    assert ged.plain_block_to_html("この動画が伝えたかったこと") == (
        '<h3 class="sec">この動画が伝えたかったこと</h3>'
    )


def test_plain_block_normal_sentence_stays_paragraph():
    line = "本動画は、人気漫画『ONE PIECE』のワノ国編終了後の展開を考察する内容です。"
    assert ged.plain_block_to_html(line) == f"<p>{line}</p>"


def test_plain_block_url_is_not_treated_as_label():
    line = "詳しくは https://example.com/page を参照してください。"
    assert ged.plain_block_to_html(line) == f"<p>{line}</p>"


def test_plain_block_preserves_inline_bold():
    html = ged.plain_block_to_html("結論: **ルフィ**が鍵を握る。")
    assert "<strong>ルフィ</strong>" in html


def test_md_to_html_applies_plain_block_structure():
    html = ged.md_to_html("概要\n本動画は考察を行う内容です。\n\n1. 最初の論点")
    assert '<h3 class="sec">概要</h3>' in html
    assert "<p>本動画は考察を行う内容です。</p>" in html
    assert '<h4 class="sec-num">' in html


def test_plain_block_trailing_timestamp_becomes_subheading():
    # 実データで373行が「ラベル: 本文」と誤判定されていた形
    html = ged.plain_block_to_html("CP9の動物モチーフとカリファの例外性 [00:00]")
    assert html == '<h4 class="sec-sub">CP9の動物モチーフとカリファの例外性<span class="ts">[00:00]</span></h4>'


def test_plain_block_hour_length_timestamp_is_supported():
    html = ged.plain_block_to_html("保守派（盾）とリベラル派（剣） [01:21:24]")
    assert html == '<h4 class="sec-sub">保守派（盾）とリベラル派（剣）<span class="ts">[01:21:24]</span></h4>'


def test_plain_block_timestamp_colon_is_not_a_label_separator():
    # タイムスタンプが行頭近くにあっても区切りとして拾わない
    html = ged.plain_block_to_html("[00:13] が示すのは、物語の折り返し地点である。")
    assert 'class="term"' not in html
    assert "[00:13]" in html


def test_plain_block_sentence_with_trailing_timestamp_stays_paragraph():
    line = "くまは「暴君」と恐れられていたが、実際は誰よりも人々を救った聖者であった。 [00:30]"
    html = ged.plain_block_to_html(line)
    assert html.startswith("<p>")
    assert '<span class="ts">[00:30]</span></p>' in html


def test_plain_block_label_keeps_its_trailing_timestamp():
    html = ged.plain_block_to_html("祖父：ピンゾロ [06:07]")
    assert '<span class="term">祖父</span>ピンゾロ' in html
    assert '<span class="ts">[06:07]</span>' in html


def test_plain_block_timestamp_only_line_stays_paragraph():
    html = ged.plain_block_to_html("[02:30]")
    assert html == '<p><span class="ts">[02:30]</span></p>'


def test_mask_timestamp_colons_preserves_length():
    text = "見出し [01:21:24] の続き"
    assert len(ged.mask_timestamp_colons(text)) == len(text)
    assert ged.unmask_timestamp_colons(ged.mask_timestamp_colons(text)) == text


def test_no_entry_splits_a_timestamp_across_label_and_body():
    """実データ全件で、タイムスタンプがラベルと本文に分断されていないこと。

    373行が壊れていた回帰なので、個別ケースではなくコーパス全体で検証する。
    """
    import re

    for path in ged.find_md_files(ged.REPO_ROOT):
        html = ged.md_to_html(path.read_text(encoding="utf-8"))
        # 「…[00</span>」のようにラベル末尾がタイムスタンプ途中で切れていないか
        assert not re.search(r"\[\d{1,2}</span>", html), path.name


def run():
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
        print(f"OK: {t.__name__}")
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    run()
