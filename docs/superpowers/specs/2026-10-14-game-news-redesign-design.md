---
created: 2026-10-14
status: draft
---

# Game News 作り直し 設計メモ

## 目的

- 今は自分用（スマホで毎日チェック）。最終的には一般公開のサイトにしたい。
- PCでもスマホでも見やすくする。
- ニュースとセール情報を、1時間ごとに自動で更新する。
- お金はかけない（GitHub Actions 公開リポジトリ枠 + Vercel Hobby）。

## 現状の問題（2026-10-14 時点で確認したもの）

| # | 問題 | 根拠 |
|---|------|------|
| 1 | Vercel の公開サイトが 10/04 のデータのまま止まっている | リポジトリの `news.json` は 10/14 10:33 更新。公開サイトには今の `fetch_news.py` にないカテゴリ（PS公式、電ファミ・話題など）が表示されている。原因は未確認（Vercel API が 403 で見られなかった）。bot コミットでデプロイされていない可能性が高い |
| 2 | RSS ニュースが1件も取れていない | `item.find('title') or ...` が、子要素のない Element を False 扱いして None になる。最新の `news.json` はEpicとSteamの12件だけ |
| 3 | 毎時になっていない | コミット間隔は4〜7時間。GitHub の schedule は毎時0分が混みやすく、遅延・スキップされる。ニュースが取れず差分がない回はコミットされない |
| 4 | お気に入りが外れる | ID に Python の `hash()` を使っている。実行ごとに値が変わる（PYTHONHASHSEED のランダム化） |
| 5 | 日時が全部同じ | `pubDate` に取得時刻を入れている |
| 6 | 「セール速報」の誤判定 | タイトルのキーワードだけで判定している（例：「Garage Sale」の記事） |
| 7 | 本番で Tailwind の CDN 版を使っている | `cdn.tailwindcss.com` は開発用。表示が遅い |
| 8 | XSS の危険 | 外部のタイトルや URL をエスケープせずに `innerHTML` に入れている |

## 全体の流れ

```
GitHub Actions（cron: 17 * * * *、手動実行あり）
  1. py -m fetcher        … 全ソースを収集して news.json を作る
  2. pytest               … 失敗したら公開しない
  3. news.json をコミット・push（前回データとして使う）
  4. vercel deploy --prod … 静的ファイルを直接公開
```

- Vercel の Git 連携による自動デプロイは `vercel.json` の `git.deploymentEnabled: false` で止める（二重デプロイを防ぐ）。
- GitHub Secrets に `VERCEL_TOKEN`、`VERCEL_ORG_ID`、`VERCEL_PROJECT_ID` を登録する（ユーザーが設定する）。
- コミットメッセージに `[skip ci]` は付けない（Actions はそもそも bot の push では再実行されない）。

## ディレクトリ構成

```
fetcher/
  __main__.py   … エントリポイント（py -m fetcher）
  main.py       … 全ソースを呼ぶ → 前回データとマージ → news.json を書く
  common.py     … HTTP取得（リトライ・タイムアウト）、固定ID生成、日時処理、翻訳
  rss.py        … ニュース（RSS / Atom）
  steam.py      … Steam セール
  epic.py       … Epic 無料配布（今週・来週）
  psstore.py    … PS Store セール
  eshop.py      … Nintendo eShop セール
tests/
  fixtures/     … 各ソースの実レスポンスを保存したサンプル
  test_*.py
public/
  index.html, style.css, app.js, news.json
vercel.json
requirements.txt / requirements-dev.txt
```

各ソースは `fetch() -> list[dict]` という同じ形の関数を持つ。取得（HTTP）と解析（parse）は別の関数に分けて、解析はサンプルデータでテストできるようにする。

## データ形式（news.json）

```json
{
  "updated_at": "2026-10-14T10:17:00+09:00",
  "sources": [
    {"id": "steam", "ok": true, "count": 30, "error": null, "last_success": "2026-10-14T10:17:00+09:00"}
  ],
  "news": [
    {
      "id": "n_<sha1(link)の先頭12文字>",
      "title": "…", "title_original": "…（翻訳したときだけ）",
      "link": "https://…", "summary": "…（120文字まで）",
      "source": "AUTOMATON", "region": "jp | global | official",
      "platforms": ["PS5"], "image": "https://… | null",
      "published_at": "ISO 8601", "first_seen": "ISO 8601",
      "translated": false
    }
  ],
  "deals": [
    {
      "id": "d_<store>_<商品ID>",
      "store": "steam | epic | ps | eshop",
      "title": "…", "link": "https://…", "image": "https://… | null",
      "price_original": 8778, "price_sale": 2633, "discount": 70,
      "is_free": false, "upcoming": false,
      "starts_at": "ISO 8601 | null", "ends_at": "ISO 8601 | null"
    }
  ]
}
```

- 日時はすべて ISO 8601（JST）で持ち、表示の整形は画面側でやる。
- `published_at` が取れない記事は `first_seen` を使う。
- ニュースは新しい順に最大200件、72時間より古いものは捨てる。
- セールは `ends_at` を過ぎたものを捨てる。

## 収集元

### ニュース（RSS）

今の16フィードを引き継ぐ。各フィード最新15件。`region` は今の `category` と `default_platform` から決める（ハード公式3つは `official`）。

- 海外記事のタイトルは翻訳する。今の非公式 Google 翻訳エンドポイントを使い続けるが、失敗したら原文のまま出す。翻訳結果は ID ごとに前回データから再利用して、同じ記事を毎時翻訳しない。
- 画像は `media:content`、`enclosure`、`media:thumbnail` の順に探す。なければ null。
- XML は標準ライブラリの `xml.etree` ではなく `defusedxml` で読む（外部 XML を安全に読むため）。

### セール

| ストア | 方法 | 確度 |
|--------|------|------|
| Steam | `api/featuredcategories`（specials）＋ `storesearch` の specials。終了日時は `discount_expiration` | 今動いている |
| Epic | `freeGamesPromotions`。今週の無料（`promotionalOffers`）と来週の無料（`upcomingPromotionalOffers`）。リンクは `catalogNs.mappings` の pageSlug を優先 | 今動いている |
| PS Store | セール一覧ページの HTML に埋め込まれた JSON（Next.js / Apollo の状態データ）を読む | **未確認**。実装の最初に試す |
| Nintendo eShop | 任天堂の検索サイトが使っている検索 API をセール条件で呼ぶ | **未確認**。実装の最初に試す |

PS Store と eShop は、試して取れなかった場合はそのストアを外して、ユーザーに相談する（それらしいデータで埋めない）。

## エラー時の動き

- ソースごとに try/except し、結果を `sources` に記録する。
- 失敗したソースは、前回の `news.json` にあるそのソースのデータを使い回す。ただし `last_success` から24時間までで、それを過ぎたら消す。
- 全ソースが失敗したときは `news.json` を書き換えず、終了コード1で終わる（空のサイトを公開しない）。
- HTTP はタイムアウト10秒、1回だけリトライ。User-Agent はブラウザに似せる。

## 画面（A. ダッシュボード型）

- 外部の CSS フレームワークは使わない。素の HTML / CSS / JS（ビルドなし）。
- ダーク基調。色は CSS 変数で管理する。
- **PC（900px以上）**：左にニュース一覧、右にセール欄の2カラム。セール欄は縦にスクロールしても上に貼り付いたまま。
- **スマホ**：1カラム。ヘッダー下のタブで「ニュース / セール」を切り替える。
- ニュース：サムネイル＋タイトル＋出典＋相対時刻（「2時間前」）。絞り込みは「すべて / 国内 / 海外 / 公式」。海外の翻訳記事には「翻訳」ラベルを付け、原題をツールチップで見られる。
- セール：ストアの切り替え（すべて / Steam / Epic / PS / Switch）、並べ替え（割引率順 / 終了が近い順）。無料配布は一番上に固定。「来週の無料」は別の見出しで出す。
- 検索（ニュースとセールの両方が対象）とお気に入り（localStorage）。
- ヘッダーに「最終更新：◯分前」。3時間以上古いときは警告色にする。取得に失敗しているソースがあれば小さく表示する。
- 文字列はすべて `textContent` で入れる（`innerHTML` に外部データを入れない）。リンクは `http(s)` のものだけ許可する。
- 画像は `loading="lazy"`。読み込みに失敗したらプレースホルダーにする。

## テスト

- `pytest` で各ソースの parse 関数をサンプルデータでテストする（ネットワークに出ない）。
- `main` のマージ処理（前回データの使い回し、72時間・24時間ルール、全滅時に書き込まない）をテストする。
- 固定 ID が実行ごとに変わらないことをテストする。
- 画面は、ローカルで静的サーバーを立ててブラウザで PC 幅とスマホ幅を確認する。
- 最後に Actions を手動実行し、Vercel の公開サイトが更新されるのを確認する。

## やらないこと

- 独自ドメイン、広告、アカウント機能、プッシュ通知。
- 過去記事のアーカイブページ。
- もう1つのサイトの修正（Game News が終わってから別に扱う）。
