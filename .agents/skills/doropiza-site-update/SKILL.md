---
name: doropiza-site-update
description: ドロピザのONE PIECE考察Markdownを追記・新規作成したあと、その内容を考察アーカイブサイト https://doropiza.vercel.app に反映して本番公開するときに使う。「ドロピザの考察を更新したからサイトに反映して」「考察増やした」「ドロピザサイト更新して」「考察アーカイブを最新にして」などで発動する。考察ファイルを触った直後や、サイトの表示件数が実際の本数と食い違っているという話が出たときも、明示的に頼まれていなくてもこのスキルを使うこと。プロジェクトは /Users/motoki/Desktop/GitHub/05_知識・考察ストック/doropiza。
---

# ドロピザ考察アーカイブサイトの更新

考察Markdownを追記したあと、静的サイト用のデータを再生成して本番（Vercel）へ公開するまでの手順。

- プロジェクト: `/Users/motoki/Desktop/GitHub/05_知識・考察ストック/doropiza`
- 本番URL: https://doropiza.vercel.app
- 考察の原稿: リポジトリ直下の `ドロピザ考察NNN-NNN.md`（30本ごとに1ファイル）
- サイトが読むデータ: `site/data/entries-data.js`（`window.ENTRIES` に全件のHTMLを埋め込んだ生成物）

サイトは `site/` 以下の素の静的ファイルだけで動く。ビルドステップは無く、**唯一の生成物が `entries-data.js`** なので、更新作業の本質は「Markdownから生成物を作り直して push する」だけ。

## 手順

### 1. 何が変わったかを掴む

```bash
cd "/Users/motoki/Desktop/GitHub/05_知識・考察ストック/doropiza"
git status --short
```

新規ファイル（`??`）と追記されたファイル（` M`）の両方を見る。ユーザーは「新しいファイルを足した」と言いつつ、既存ファイルの末尾にも書き足していることがよくある。どちらも自動で拾われるので特別な操作は要らないが、後で件数を報告するために何が動いたかは把握しておく。

### 2. データを再生成する

```bash
python3 scripts/generate_entries_data.py
```

`ドロピザ考察*.md` を全部読み直して `site/data/entries-data.js` を作り直し、ついでに `site/index.html` の meta description にある本数も実件数へ同期する。出力される `(N entries)` が新しい総件数なので控えておく。

差分ではなく毎回全件を作り直す設計なので、どのファイルが変わったかをスクリプトに教える必要はない。

### 3. テストを通す

```bash
python3 scripts/test_generate_entries_data.py
```

`ALL TESTS PASSED` を確認する。pytestは入っていないので、ファイルを直接実行する（`python3 -m pytest` は失敗する）。

このテスト群は見出しパースの単体テストに加えて、**コーパス全体を走査する回帰テスト**を含んでいる。特に重要なのが、`[00:13]` のような再生位置タイムスタンプが「ラベル: 本文」のコロンと誤認されて `…[00` と `13]` に分断されていないかの検査。新しい考察に変わった書式の行が混ざると、ここで初めて壊れが露見する。落ちたら push せず、`plain_block_to_html()` の判定を見直す。

### 4. 新規分のタグを確認する

タグは `tags.json` のキーワード辞書との単純マッチで自動付与される。新しい考察に辞書外のキャラや題材（新章のキャラ、新しい元ネタなど）が出てくると、**タグが付かないか、的外れなタグだけが付く**。件数が増えたときは新規エントリのタグを覗いておく。

```bash
python3 -c "
import json
s = open('site/data/entries-data.js', encoding='utf-8').read()
data = json.loads(s[len('window.ENTRIES = '):].rstrip().rstrip(';'))
for e in data[-8:]:
    print(e.get('number'), '|', e['title'][:40], '|', e.get('tags'))
"
```

明らかに拾えていない題材があればユーザーに知らせ、`tags.json` に語を足すか聞く。辞書を直したら手順2からやり直す。

### 5. 件数を見せて公開の可否を聞く

push すると本番サイトが即座に書き換わるので、ここで一度だけ止まる。報告する内容は「更新前→更新後の件数」「新規何件」「テストの結果」の3点で足りる。

> 214件 → 221件（新規7件）、テスト46件パスです。本番に反映してよいですか？

### 6. コミットして push する

```bash
git add -A
git commit -m "feat: 考察NNN-NNNをサイトに反映（旧件数→新件数）"
git push origin main
```

Vercelのプロジェクトは Root Directory が `site` に設定済みで、`main` への push で自動デプロイが走る。**`npx vercel --prod` を手で叩く必要はない**（環境によっては権限で弾かれる）。デプロイは静的配信なので数十秒で終わる。

### 7. 本番に届いたか確かめる

見た目のスクショより、配信されているファイルがローカルの生成物と同一かを見るのが確実。

```bash
curl -s https://doropiza.vercel.app/data/entries-data.js -o /tmp/dep.js
shasum -a 256 /tmp/dep.js site/data/entries-data.js
curl -s https://doropiza.vercel.app/ | grep -o "考察[0-9]*本"
```

2つのハッシュが一致し、本数が手順2の件数と合っていれば完了。ハッシュが違ううちはデプロイがまだ進行中なので、少し置いてもう一度取る。それでも合わなければ `npx vercel ls doropiza` でデプロイの状態を見る。

## 落とし穴

**テストがリポジトリの実ファイルを書き換えないか。** `test_main_handles_no_md_files` は `REPO_ROOT` を一時ディレクトリに差し替えて `main()` を呼ぶ。`main()` の中で書き込み先を「モジュール定数」から取ると、差し替えが効かず本物の `site/index.html` を「考察0本」に潰して、そのまま本番へ出る事故が起きた。生成スクリプトに書き込み処理を足すときは、**パスを必ず `REPO_ROOT` から都度導出する**こと。`test_main_does_not_touch_the_real_index_html` がこの回帰を見張っている。

**macOSのファイル名の正規化。** `find_md_files()` は濁点の分解（NFD）と結合（NFC）の両方の「ドロピザ」にマッチするようになっている。Finderやアプリ経由で作られたファイル名はNFDになることがあり、素朴なglobだと取りこぼす。件数が期待より少ないときはここを疑う。

**タイムスタンプ付きの行の扱い。** 行末の `[00:47]` は本文から切り離されて `<span class="ts">` になり、句点を含まない短い行なら動画内の小見出し（`h4.sec-sub`）として扱われる。原稿の書き方が変わって意図しない見た目になったら、`plain_block_to_html()` の判定順序を読むのが早い。

## 表示を直したくなったら

データではなく見た目の話（カードの並び、モーダル、検索・タグ絞り込み）は `site/style.css` と `site/app.js` を直接編集する。この場合も反映は同じで、push すれば自動デプロイされる。モバイル幅の確認は Playwright で 390px 前後にリサイズして見るのが早い。
