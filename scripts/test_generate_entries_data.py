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
