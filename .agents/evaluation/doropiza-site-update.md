# doropiza-site-update

方針は`~/.agents/docs/skills_policy.md`。このスキルを直す前に読み、失敗が起きたら先にここへケースを足す。

## 合格基準

- 考察のmdをすべて読み直して`site/data/entries-data.js`を作り直し、`site/index.html`のmeta descriptionの本数を実件数に合わせる。
- `python3 scripts/test_generate_entries_data.py`で`ALL TESTS PASSED`を確かめる（pytestは使わない）。落ちたらpushしない。
- pushの前に一度だけ止まり、「更新前→更新後の件数」「新規何件」「テストの結果」を伝えて承認を得る。
- push後、本番の内容が手元と一致するまで確かめる。

## テストケース

- 新しい考察が7本増えた → 「214件 → 221件（新規7件）、テストN件パスです。本番に反映してよいですか？」の形で止まる。
- `[00:13]`のような再生位置を含む行がある → 「ラベル: 本文」と誤認して分断しない（回帰テストで検出）。
- 濁点が分解された（NFD）ファイル名の考察 → 取りこぼさない。

## 過去の失敗

- **2026-07-28**（`74ca688`で修正）：テスト`test_main_handles_no_md_files`が書き込み先をモジュール定数から取っていたため、本物の`site/index.html`を「考察0本」に書き潰し、そのまま本番へ出た。→ パスを`REPO_ROOT`から都度導出するようにし、`test_main_does_not_touch_the_real_index_html`で見張っている。

## 確認コマンド

```sh
python3 -B scripts/test_generate_entries_data.py
```
