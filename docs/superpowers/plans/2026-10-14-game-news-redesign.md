# Game News 作り直し Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ニュースと4ストアのセールを毎時自動で集めて Vercel に直接公開する、ダッシュボード型のサイトに作り直す。

**Architecture:** `fetcher/` パッケージ（ソースごとに1ファイル、取得と解析を分離）が `public/news.json` を作る。GitHub Actions が毎時17分に実行し、テスト → コミット → `vercel deploy --prebuilt --prod` で公開。画面は `public/` の素の HTML / CSS / JS。

**Tech Stack:** Python 3.12（標準ライブラリ + `defusedxml`）、pytest、素の HTML/CSS/JS、GitHub Actions、Vercel CLI。

**Spec:** `docs/superpowers/specs/2026-10-14-game-news-redesign-design.md`

## Global Constraints

- 日時はすべて JST の ISO 8601 文字列（例 `2026-10-14T10:17:00+09:00`）。
- ID は `hashlib.sha1` ベースで、実行ごとに変わらないこと。Python の `hash()` は使わない。
- ニュースは最大200件・72時間以内。セールは `ends_at` を過ぎたら捨てる。失敗ソースの使い回しは `last_success` から24時間まで。
- 全ソース失敗時は `news.json` を書き換えず終了コード1。
- HTTP はタイムアウト10秒・リトライ1回。
- 画面に外部データを入れるときは `textContent` / 属性代入のみ。リンクは `http:` / `https:` のみ許可。
- 外部 CSS フレームワークなし。CDN の Tailwind は削除。
- 依存パッケージは `defusedxml` だけ（テスト用に `pytest`）。

## Review Focus

1. RSS の `<title>` が CDATA / 子要素なし / Atom の `<link href>` のどれでも取れること（今回の全滅バグの再発防止）→ Task 2 のテスト。
2. 価格が「無料」「¥0」や割引率0%のときに deal として出さない（Epic 無料配布だけ例外）→ Task 3〜6 のテスト。
3. 前回の `news.json` が存在しない・壊れている初回実行でも落ちない → Task 7 のテスト。
4. タイトルに `<img onerror>` のような HTML が入っても画面で実行されない → Task 8 の手動確認。
5. `published_at` が未来日時や解析不能な RSS → `first_seen` で代用し、並び順が壊れない → Task 2 / 7 のテスト。

---

### Task 1: 土台（common.py とテスト環境）

**Files:**
- Create: `fetcher/__init__.py`（空）, `fetcher/common.py`, `requirements.txt`（`defusedxml==0.7.1`）, `requirements-dev.txt`（`-r requirements.txt` と `pytest==8.3.3`）, `pytest.ini`（`testpaths = tests`）, `tests/__init__.py`, `tests/test_common.py`, `.gitignore`（`__pycache__/`, `.pytest_cache/`, `.vercel/`）

**Interfaces:**
- Produces:
  - `JST: timezone`（+9h）
  - `now_jst() -> datetime`
  - `to_iso(dt: datetime) -> str` … JST に変換して秒まで（`isoformat(timespec="seconds")`）
  - `parse_date(value: str | None) -> datetime | None` … RFC 822（`email.utils.parsedate_to_datetime`）と ISO 8601（末尾 `Z` 対応）を受ける。失敗は None。タイムゾーンなしは UTC とみなす
  - `stable_id(prefix: str, key: str) -> str` … `f"{prefix}_{sha1(key).hexdigest()[:12]}"`
  - `http_get(url: str, headers: dict | None = None, timeout: int = 10) -> bytes` … ブラウザ風 User-Agent を既定で付与、例外時に1回だけ再試行、2回目の例外はそのまま送出
  - `clean_text(html: str | None, limit: int | None = None) -> str` … タグ除去、`html.unescape`、空白の連続を1つに、limit で切る

- [ ] **Step 1: テストを書く** — `tests/test_common.py`
  - `test_stable_id_is_deterministic`: `stable_id("n", "https://a/1") == stable_id("n", "https://a/1")` かつ `len == 14`、別キーなら別 ID
  - `test_parse_date_rfc822`: `parse_date("Tue, 14 Oct 2026 01:00:00 GMT")` を `to_iso` すると `"2026-10-14T10:00:00+09:00"`
  - `test_parse_date_iso_z`: `"2026-10-14T01:00:00Z"` → 同上
  - `test_parse_date_bad`: `parse_date("not a date") is None`、`parse_date(None) is None`
  - `test_clean_text`: `clean_text("<p>A&amp;B\n  C</p>", 3) == "A&B"`
- [ ] **Step 2: 失敗を確認** — `py -m pytest tests/test_common.py -v` → ImportError
- [ ] **Step 3: `fetcher/common.py` を実装**
- [ ] **Step 4: 通過を確認** — 同コマンドで 5 passed
- [ ] **Step 5: コミット** — `feat: fetcher の共通処理を追加`

### Task 2: ニュース（rss.py）

**Files:**
- Create: `fetcher/rss.py`, `tests/test_rss.py`, `tests/fixtures/rss_sample.xml`, `tests/fixtures/atom_sample.xml`

**Interfaces:**
- Consumes: Task 1 の `http_get`, `parse_date`, `stable_id`, `clean_text`, `to_iso`
- Produces:
  - `FEEDS: list[dict]` … 今の `fetch_news.py` の16件をそのまま移す。キーは `url`, `source`, `region`（`jp` / `global` / `official`）, `platform`（任意）。任天堂公式・PlayStation Blog・Xbox Wire Japan が `official`
  - `parse_feed(xml: bytes, feed: dict, limit: int = 15) -> list[dict]` … news 項目（spec のデータ形式。`first_seen` と `translated` / `title_original` は付けない）
  - `fetch(feed: dict) -> list[dict]` … `parse_feed(http_get(feed["url"]), feed)`
  - `detect_platforms(text: str, default: str | None) -> list[str]` … 今の `PLATFORM_KEYWORDS` を移す。ただし `"pc"` は単語境界で判定（`re.search(r"\bpc\b")`）。空なら `[]`

要素の探し方は `find()` の結果を `is not None` で判定する（`or` でつながない）。名前空間は RSS2 / Atom / `media` を見る。画像は `media:content@url` → `media:thumbnail@url` → `enclosure@url`（type が image/*）→ 説明文中の最初の `<img src>`。XML は `defusedxml.ElementTree.fromstring`。

- [ ] **Step 1: フィクスチャを作る** — `rss_sample.xml`: 3記事（CDATA タイトル、`<media:content>` 画像あり、pubDate なし の各1件）。`atom_sample.xml`: 2記事（`<link href>`、`<updated>`）
- [ ] **Step 2: テストを書く** — `tests/test_rss.py`
  - `test_parse_rss_gets_all_items`: 3件取れて、1件目の `title` が CDATA の中身、`image` が media の URL
  - `test_parse_rss_missing_pubdate`: pubDate なしの記事は `published_at is None`
  - `test_parse_atom_link_href`: Atom の `link` が href の値、`published_at` が `<updated>` を JST にしたもの
  - `test_id_from_link`: `id == stable_id("n", link)`
  - `test_detect_platforms_pc_word`: `detect_platforms("New PC port", None) == ["PC"]`、`detect_platforms("topcoat", None)` に `"PC"` を含まない（今のコードは部分一致なので含んでしまう）
- [ ] **Step 3: 失敗を確認** — `py -m pytest tests/test_rss.py -v`
- [ ] **Step 4: `fetcher/rss.py` を実装**
- [ ] **Step 5: 通過を確認**
- [ ] **Step 6: 実フィードで確認** — `py -c "from fetcher import rss; [print(f['source'], len(rss.fetch(f))) for f in rss.FEEDS]"`。0件や例外のフィードは URL を調べて、移転していれば直し、廃止なら FEEDS から外してユーザーに報告
- [ ] **Step 7: コミット** — `feat: RSS ニュース取得を作り直し（全件スキップのバグ修正）`

### Task 3: Steam（steam.py）

**Files:**
- Create: `fetcher/steam.py`, `tests/test_steam.py`, `tests/fixtures/steam_search.html`, `tests/fixtures/steam_featured.json`

**Interfaces:**
- Produces:
  - `SEARCH_URL = "https://store.steampowered.com/search/results/?specials=1&cc=jp&l=japanese&count=50&infinite=1&filter=topsellers"`（JSON の `results_html` を使う）
  - `FEATURED_URL = "https://store.steampowered.com/api/featuredcategories/?cc=jp&l=japanese"`
  - `parse_search(results_html: str) -> list[dict]` … `html.parser.HTMLParser` で `a.search_result_row` ごとに `data-ds-appid`, `.title`, `data-discount`, `.discount_original_price`, `.discount_final_price` を読む
  - `parse_expirations(featured: dict) -> dict[int, int]` … `specials.items` の `id → discount_expiration`
  - `fetch() -> list[dict]` … deal 項目。`id = f"d_steam_{appid}"`, `link = f"https://store.steampowered.com/app/{appid}/"`, `image = f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"`, `ends_at` は expirations にあれば変換、なければ None。featured 取得の失敗は無視して検索結果だけで返す

- [ ] **Step 1: フィクスチャ保存** — 上の2つの URL の実レスポンスを保存（search は `results_html` の中身だけを .html に）
- [ ] **Step 2: テストを書く**
  - `test_parse_search_reads_prices`: フィクスチャから1件以上、すべて `discount > 0` かつ `price_sale < price_original`。Street Fighter 6（1364780）があれば `discount == 60`, `price_original == 4990`, `price_sale == 1996`
  - `test_parse_search_skips_no_discount`: discount 0 の行を足した最小 HTML で、その行は出ない
  - `test_parse_expirations`: フィクスチャの1件目の id が dict に入っている
- [ ] **Step 3: 失敗を確認 → Step 4: 実装 → Step 5: 通過を確認**
- [ ] **Step 6: コミット** — `feat: Steam セール取得を検索結果ベースに変更`

### Task 4: Epic（epic.py）

**Files:**
- Create: `fetcher/epic.py`, `tests/test_epic.py`, `tests/fixtures/epic_free.json`

**Interfaces:**
- Produces:
  - `parse(data: dict, now: datetime) -> list[dict]` … `promotionalOffers` の有効期間内で `discountPercentage == 0`（= 無料）のものを `is_free=True, upcoming=False`、`upcomingPromotionalOffers` の同条件を `upcoming=True`。`price_original` は `price.totalPrice.originalPrice // 100`（JPY は minor unit 0 なら割らない — `currencyInfo.decimals` を見る）、`price_sale = 0`, `discount = 100`。`id = f"d_epic_{el['id']}"`。リンクは `catalogNs.mappings[0].pageSlug` → `offerMappings[0].pageSlug` → `productSlug` の順で `https://store.epicgames.com/ja/p/{slug}`、どれもなければ `https://store.epicgames.com/ja/free-games`。画像は `OfferImageWide` → `DieselStoreFrontWide` → `Thumbnail`
  - `fetch() -> list[dict]`

- [ ] **Step 1: フィクスチャ保存**（`freeGamesPromotions?locale=ja&country=JP&allowCountries=JP`）
- [ ] **Step 2: テストを書く**
  - `test_current_free`: `now` を今日の JST にして、現在の無料タイトル（10/14 時点では「Out of Sight」「TerraScape」）が `is_free and not upcoming`、`ends_at` が `2026-10-16T00:00:00+09:00`
  - `test_upcoming`: upcoming が1件以上なら `upcoming=True` で `starts_at` がある（フィクスチャに無ければ最小 dict を自作してテスト）
  - `test_ignores_paid_discount`: `discountPercentage` が 0 でないオファーだけの要素は出ない
- [ ] **Step 3〜5: 失敗確認 → 実装 → 通過確認**
- [ ] **Step 6: コミット** — `feat: Epic 無料配布（今週・来週）取得`

### Task 5: PS Store（psstore.py）

**Files:**
- Create: `fetcher/psstore.py`, `tests/test_psstore.py`, `tests/fixtures/ps_category.json`

**Interfaces:**
- Produces:
  - `CATEGORY_ID = "3f772501-f6f8-49b7-abac-874a88ca4897"`（「すべてのセール」, localizedKeyId `cat.gma.AllDeals`）
  - `QUERY_HASH = "88c0b9a1273c6d320c51cd73e390924e21ae28bf09f01cde8b84b1034b16cd03"`（`categoryGridRetrieve`）
  - `build_url(offset: int, size: int) -> str` … `https://web.np.playstation.com/api/graphql/v1/op?operationName=categoryGridRetrieve&variables=…&extensions=…`（JSON を `urllib.parse.quote`）
  - `parse_price(text: str | None) -> int | None` … `"¥8,470"` → 8470、`"無料"` や None → None
  - `parse(data: dict) -> list[dict]` … `data.categoryGridRetrieve.products`。`price.isTiedToSubscription` が true のもの、`discountText` が無いもの、価格が取れないものは除外。`discount` は `discountText` の数字。`id = f"d_ps_{product.id}"`, `link = f"https://store.playstation.com/ja-jp/product/{product.id}"`, 画像は media の `MASTER` → `GAMEHUB_COVER_ART` → 最初の IMAGE。`ends_at = None`
  - `fetch(limit: int = 60) -> list[dict]` … size=30 で2ページ。ヘッダーに `x-psn-store-locale-override: ja-JP`

- [ ] **Step 1: フィクスチャ保存**（size=10）
- [ ] **Step 2: テストを書く**
  - `test_parse_price`: `parse_price("¥8,470") == 8470`, `parse_price("無料") is None`
  - `test_parse_products`: フィクスチャから1件以上、全件 `0 < discount < 100`、`price_sale < price_original`
  - `test_skips_subscription_price`: `isTiedToSubscription: true` の最小 product は出ない
- [ ] **Step 3〜5: 失敗確認 → 実装 → 通過確認**
- [ ] **Step 6: コミット** — `feat: PS Store セール取得`

### Task 6: Nintendo eShop（eshop.py）

**Files:**
- Create: `fetcher/eshop.py`, `tests/test_eshop.py`, `tests/fixtures/eshop_search.json`

**Interfaces:**
- Produces:
  - `SEARCH_URL = "https://search.nintendo.jp/nintendo_soft/search.json?opt_sshow=1&opt_osale=1&limit=100&page={page}"`
  - `parse(data: dict, now: datetime) -> list[dict]` … `result.items` のうち `sale_flg == "1"` かつ `sprice < price` かつ `sedate` が未来のもの。`discount = round((1 - sprice / price) * 100)`。`ends_at` は `sedate`（`"YYYY-MM-DD HH:MM:SS"`、JST）、`starts_at` は `ssdate`。`id = f"d_eshop_{nsuid}"`, `link = f"https://store-jp.nintendo.com/item/software/D{nsuid}"`, `image = f"https://img-eshop.cdn.nintendo.net/i/{iurl}.jpg"`（iurl が無ければ None）。同じ `nsuid` の重複は除く
  - `fetch(pages: int = 3, limit: int = 60) -> list[dict]` … 3ページ読んで割引率の高い順に `limit` 件

- [ ] **Step 1: フィクスチャ保存**（limit=50）
- [ ] **Step 2: テストを書く**
  - `test_parse_only_sale_items`: 全件 `price_sale < price_original`、`ends_at` が `now` より後
  - `test_discount_rounding`: price=2860, sprice=2574 の最小 item で `discount == 10`
  - `test_expired_sale_dropped`: `sedate` が過去の item は出ない
- [ ] **Step 3〜5: 失敗確認 → 実装 → 通過確認**
- [ ] **Step 6: 実 URL で確認** — `py -c "from fetcher import eshop; print(len(eshop.fetch()))"` が 1 以上。リンクを1つブラウザで開いて商品ページになるか確認（ならなければ URL 形式を直す）
- [ ] **Step 7: コミット** — `feat: Nintendo eShop セール取得`

### Task 7: まとめ処理（main.py / translate）

**Files:**
- Create: `fetcher/main.py`, `fetcher/__main__.py`（`main()` を呼んで `sys.exit` に渡す）, `fetcher/translate.py`, `tests/test_main.py`

**Interfaces:**
- Consumes: Task 2〜6 の `fetch`
- Produces:
  - `translate.to_japanese(text: str) -> str | None` … 今の Google 翻訳エンドポイントを使う。英字5文字以上を含まなければ None（翻訳不要）、失敗も None
  - `SOURCES: list[tuple[str, Callable[[], list[dict]]]]` … `("rss:<source名>", …)` を各フィード、`("steam", …)`, `("epic", …)`, `("ps", …)`, `("eshop", …)`
  - `load_previous(path: Path) -> dict` … 無い・壊れているときは `{"news": [], "deals": [], "sources": []}`
  - `merge(results: dict[str, list[dict] | Exception], previous: dict, now: datetime) -> dict` … 純粋関数（ネットワークなし）。やること：
    - 成功ソースは新データを採用。失敗ソースは前回の `sources` の `last_success` が24時間以内なら前回データ（`source`/`store` が一致する項目）を残す
    - news: 前回にある ID は `first_seen` と翻訳結果を引き継ぐ。新規は `first_seen = now`。`published_at` が None か `now` より未来なら `first_seen` を使う。72時間より古いものを捨て、`published_at` の新しい順に200件
    - deals: `ends_at` が過去のものを捨てる。並びは store ごとに元の順
    - `sources`: `{"id", "ok", "count", "error", "last_success"}`
  - `apply_translations(news: list[dict]) -> None` … `region == "global"` かつ `translated` キーがまだ無い記事だけ `to_japanese` を呼ぶ。成功したら `title_original` に原文、`title` を訳、`translated=True`。1回の実行で最大40件
  - `main(path: Path = Path("public/news.json")) -> int` … 全ソースを `concurrent.futures.ThreadPoolExecutor(max_workers=8)` で実行 → `merge` → `apply_translations` → 書き込み。全ソース失敗なら書かずに 1

- [ ] **Step 1: テストを書く** — `tests/test_main.py`（`merge` と `load_previous` だけを対象。ネットワークなし）
  - `test_failed_source_reuses_previous_within_24h` / `test_failed_source_dropped_after_24h`
  - `test_first_seen_kept_for_known_article`
  - `test_future_published_at_falls_back_to_first_seen`
  - `test_old_news_dropped_after_72h` と `test_news_capped_at_200`
  - `test_expired_deal_dropped`
  - `test_load_previous_missing_or_broken`（存在しないパスと `"{"` だけのファイル）
  - `test_main_all_failed_returns_1`: `SOURCES` を全部例外を投げる関数に monkeypatch し、`tmp_path` のファイルが作られず戻り値 1
- [ ] **Step 2: 失敗確認 → Step 3: 実装 → Step 4: 通過確認** — `py -m pytest -v` で全テスト通過
- [ ] **Step 5: 実行して確認** — `py -m fetcher` が終了コード0で、`public/news.json` の `sources` に ok=false があれば理由を確認・報告
- [ ] **Step 6: コミット** — `feat: 収集結果のマージと news.json 出力`

### Task 8: 画面（public/）

**Files:**
- Create: `public/index.html`, `public/style.css`, `public/app.js`, `.claude/launch.json`（`py -m http.server 8000 --directory public`）
- Delete: ルートの `index.html`, `news.json`, `fetch_news.py`, `src`（空ファイル）

**Interfaces:**
- Consumes: Task 7 の `public/news.json` の形

決めていること（spec の「画面」をそのまま実装）：
- 900px 以上は2カラム（`grid-template-columns: minmax(0, 1.7fr) minmax(320px, 1fr)`）、セール欄は `position: sticky`。未満はタブ切り替え。
- 色は `:root` の CSS 変数。ダークのみ。フォントは `"Noto Sans JP", system-ui`（Google Fonts）。
- 相対時刻：1分未満「たった今」、60分未満「◯分前」、24時間未満「◯時間前」、それ以上「M/D」。
- ヘッダーの更新時刻が180分以上前なら警告色。`sources` に ok=false があれば「一部の取得に失敗：◯◯」を小さく表示。
- お気に入りは `localStorage` キー `gamefeed_favs_v2`（ID 形式が変わるので旧キーは使わない）。読み書きは try/catch。
- 要素は `document.createElement` と `textContent` で組む。`safeUrl(u)` は `new URL(u)` の protocol が http/https のときだけ返し、他は `"#"`。
- 画像の `onerror` でプレースホルダー（CSS の背景色だけのブロック）に差し替え。

- [ ] **Step 1: 3ファイルを書く**
- [ ] **Step 2: ローカルで表示** — `.claude/launch.json` から preview を起動し、PC 幅（1280px）とスマホ幅（375px）でスクリーンショット確認。確認項目：2カラム / タブ切り替え、ストア切り替え、並べ替え、検索、お気に入りの付け外しと再読み込み後の保持、Epic 無料が先頭
- [ ] **Step 3: XSS 確認** — `news.json` のコピーで1件のタイトルを `<img src=x onerror=alert(1)>` にして表示し、文字のまま出ること（確認後に戻す）
- [ ] **Step 4: 古いファイルを削除してコミット** — `feat: ダッシュボード型の画面に作り直し`

### Task 9: 自動更新とデプロイ

**Files:**
- Modify: `.github/workflows/auto_update.yml`（全面書き換え）
- Create: `vercel.json`, `README.md`（書き換え：構成、手動実行、Secrets の説明）

**決めていること：**
- `vercel.json`: `{"git": {"deploymentEnabled": false}, "buildCommand": "", "outputDirectory": "public", "cleanUrls": true}`
- workflow:
  - `on: schedule: cron "17 * * * *"` と `workflow_dispatch`、`concurrency: {group: update, cancel-in-progress: false}`、`permissions: contents: write`
  - steps: `actions/checkout@v4` → `actions/setup-python@v5`（`3.12`、pip キャッシュ）→ `pip install -r requirements-dev.txt` → `pytest -q` → `python -m fetcher` → `public/news.json` に差分があればコミット・push（`git pull --rebase` してから）→ `npm i -g vercel@latest` → `vercel pull --yes --environment=production --token=$VERCEL_TOKEN` → `vercel build --prod --token=…` → `vercel deploy --prebuilt --prod --token=…`
  - env: `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` を Secrets から
  - デプロイは差分の有無に関係なく毎回実行（更新時刻表示のため news.json は毎回変わる）
- Vercel の値：`VERCEL_ORG_ID = team_zCUQoOGAXe4r1pBay8I8ukiI`, `VERCEL_PROJECT_ID = prj_xQnhBPEoKgGiTsX2slU4LLPFevtw`（今日 Vercel API で確認済み）。`VERCEL_TOKEN` はユーザーが vercel.com/account/tokens で発行して GitHub Secrets に登録する

- [ ] **Step 1: ファイルを書く**
- [ ] **Step 2: YAML の文法確認** — `py -c "import yaml"` が無ければスキップし、目視で確認
- [ ] **Step 3: コミット** — `ci: 毎時17分に収集して Vercel に直接デプロイ`
- [ ] **Step 4: ユーザー作業の案内** — Secrets 3つの登録手順を伝える。push と main へのマージはユーザーの確認後
- [ ] **Step 5: 本番確認（push 後）** — Actions を手動実行 → 成功 → `https://game-news-smoky.vercel.app/` の更新時刻が数分以内になっていることをブラウザで確認
