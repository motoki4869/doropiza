![ドロピザ](./images/doropiza.png)

# doropiza

ONE PIECEの考察（ドロピザ考察001-030.md〜391以降）をアーカイブし、静的サイトとして閲覧できるようにしたリポジトリ。

## 公開URL

https://doropiza.vercel.app

## 構成

- `ドロピザ考察NNN-NNN.md` — 考察本文の原稿（30本ごとに1ファイル、リポジトリ直下）
- `site/` — 公開用の静的サイト（Vercel、Root Directoryが`site`に設定済み）
- `site/data/entries-data.js` — サイトが読む唯一の生成物（`window.ENTRIES` に全件のHTMLを埋め込み）
- `scripts/generate_entries_data.py` — 考察Markdown全件から `entries-data.js` を作り直すスクリプト
- `scripts/test_generate_entries_data.py` — 見出しパースの単体テスト＋コーパス全体の回帰テスト
- `tags.json` — タグ自動付与用のキーワード辞書（考察本文とのキーワード単純マッチ）

## `entries-data.js` の生成フロー

1. 考察Markdownを追記・新規作成する
2. `python3 scripts/generate_entries_data.py` を実行 → `site/data/entries-data.js` と `site/index.html` のmeta description本数を再生成
3. `python3 scripts/test_generate_entries_data.py` で `ALL TESTS PASSED` を確認（pytestではなく直接実行）
4. `git add -A && git commit && git push origin main` → Vercelが自動デプロイ

## 反映手順

考察を追記したら **`doropiza-site-update` スキル**（`.claude/skills/doropiza-site-update/SKILL.md`）を使うのが基本。件数確認・タグ確認・本番反映後のハッシュ照合まで含めた手順が定義されている。

手動で行う場合は上記「`entries-data.js` の生成フロー」の1〜4を実行する。

## `tags.json` の役割

考察本文とのキーワード単純マッチでタグを自動付与する辞書。新章のキャラや新しい元ネタなど辞書外の題材が出てくるとタグが付かない・的外れになるため、件数が増えたときは新規エントリのタグを確認し、必要なら辞書に語を追加する。