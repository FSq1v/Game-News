# Game News

国内外のゲームニュースと、Steam・Epic・PS Store・Nintendo eShop のセール情報を1時間ごとに自動でまとめるサイトです。

公開先：https://game-news-smoky.vercel.app/

## 仕組み

```
GitHub Actions（毎時17分）
  → pytest
  → python -m fetcher   … 全ソースを集めて public/news.json を作る
  → news.json をコミット（前回データとして使う）
  → vercel deploy --prebuilt --prod
```

- `fetcher/` … 収集処理。ソースごとに1ファイル（`rss.py` `steam.py` `epic.py` `psstore.py` `eshop.py`）。`main.py` が全部を呼んで前回データとマージする
- `public/` … サイト本体（`index.html` `style.css` `app.js`）とデータ（`news.json`）
- `tests/` … 各ソースの解析とマージ処理のテスト。外部サイトにはつながない

あるソースの取得に失敗しても、ほかのソースは普通に更新されます。失敗したソースは最後に成功してから24時間まで前回のデータを出し、画面のヘッダーに「一部の取得に失敗」と表示します。

## 手元で動かす

```bash
py -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
.venv\Scripts\python -m fetcher
py -m http.server 8000 --directory public
```

## 初回だけ必要な設定

GitHub のリポジトリの Settings → Secrets and variables → Actions に、次の3つを登録します。

| 名前 | 値 |
|------|----|
| `VERCEL_TOKEN` | https://vercel.com/account/tokens で発行したトークン |
| `VERCEL_ORG_ID` | Vercel のチーム ID（`team_` で始まる） |
| `VERCEL_PROJECT_ID` | Vercel のプロジェクト ID（`prj_` で始まる） |

`vercel.json` で Vercel の Git 連携による自動デプロイは止めています（Actions から直接デプロイするため）。

## 取得元が壊れたとき

- PS Store は公式 API がなく、ストアのページが内部で使っている GraphQL を呼んでいます。取れなくなったら、PS Store の「すべてのセール」ページをブラウザの開発者ツールで開き、`categoryGridRetrieve` の `sha256Hash` を `fetcher/psstore.py` の `QUERY_HASH` に入れ直してください。
- Nintendo eShop は任天堂の検索サイトの API（`search.nintendo.jp`）を使っています。
- 海外記事のタイトル翻訳は非公式の Google 翻訳エンドポイントです。失敗したときは原文のまま表示します。
