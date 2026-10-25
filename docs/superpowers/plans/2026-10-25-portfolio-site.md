# ゲーム＋AI ニュースサイト（ポートフォリオ版） 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Game-News を、ゲームと AI のニュースフィードと手書きのまとめ記事を載せた、スマホで読みやすい Astro 製の静的サイトにする。

**Architecture:** 収集は今の Python（`fetcher/`）が `data/news.json` を書く。まとめは手元の `scripts/sync_digests.py` が Obsidian から `src/content/digest/` に変換して取り込む。Astro がビルドのときに両方を読んで `dist/` を作り、GitHub Actions が毎時 Vercel にデプロイする。ブラウザの JS は、フィードの絞り込み・検索・お気に入り・タブ・並べ替えだけ（フレームワークなしの TypeScript）。

**Tech Stack:** Python 3.12 / pytest、Node 22 LTS、Astro 5、@astrojs/sitemap、@astrojs/rss、satori + @resvg/resvg-js（OGP 画像）、vitest、linkinator、GitHub Actions、Vercel Hobby

**Spec:** `docs/superpowers/specs/2026-10-25-portfolio-site-design.md`

## Global Constraints

- 公開 URL は `https://game-news-smoky.vercel.app` のまま。`astro.config.mjs` の `site` にこれを入れる。
- 費用ゼロ（GitHub Actions の公開リポジトリ枠 + Vercel Hobby）。有料の API やサービスは使わない。
- 外から来た文字列は必ずエスケープして出す。`set:html` と `innerHTML` は使わない。リンクは `http:` と `https:` だけ通す（それ以外は `#`）。
- 記事の本文は取り込まない。出すのはタイトル、要約（120 字まで）、リンクだけ。
- 「自分への影響：」の行は公開物に一切出さない。Obsidian の元ノートは読むだけで、書き換えない。
- スマホ（幅 375px）から作る。899px 以下は 1 カラム、900px 以上は 2 カラム。タップできるところは 44px 以上。
- 色は `src/styles/tokens.css` の CSS 変数だけで指定する。`prefers-color-scheme: dark` でダークに切り替える。Web フォントは画面には読み込まない（OGP 画像の生成だけで使う）。
- `prefers-reduced-motion: reduce` のときは動きを止める。
- サイト名は `src/site.ts` の `SITE_NAME` 1 か所だけで決める。ほかのファイルに直接書かない。
- お気に入りの保存キーは今と同じ `gamefeed_favs_v2` を使う（今のお気に入りを消さないため）。
- UI の文言は日本語。決まり文句や中身のないカタカナ語は使わない（ユーザーの CLAUDE.md のとおり）。
- コマンドは PowerShell で動く書き方にする。Python は `.venv\Scripts\python` で動かす。
- `git push`、PR の作成、Vercel の設定変更、フォントなどファイルのダウンロードは、そのたびにユーザーの確認を取る。

## Review Focus

1. **AI ニュースがゲームニュースに押し出される**：今の `NEWS_MAX = 200` は全ジャンル合わせた件数。ゲームのソースは 13 個あるので、AI が 0 件近くになりうる。→ ジャンルごとに 150 件までにする（Task 1 `test_cap_is_per_genre`）。
2. **`genre` のない前回データ**：デプロイ後の最初の実行では、前回の `news.json` に `genre` がない。24 時間の使い回しで出てくる古い項目が `/game` にも `/ai` にも出ない、という事態になる。→ `genre` がない項目は `"game"` として扱う（Task 1 `test_previous_item_without_genre_becomes_game`）。
3. **「自分への影響」の書き方の揺れ**：行頭の空白、全角コロン／半角コロン、`**自分への影響**：` のような太字、その下にぶら下がる字下げした行。→ どれも消す。ぶら下がる行も一緒に消す（Task 2 `test_strips_impact_variants`）。
4. **危ない文字列が入ったタイトルや URL**：`<script>` を含むタイトル、`javascript:` のリンク、画像 URL。→ 文字として出す、`#` に置き換える（Task 4 `safeUrl` のテスト、Task 5 のビルド結果の確認）。
5. **`data/news.json` がない、または壊れている**：→ ビルドは通る。まとめ記事は出る。フィードには「ニュースを読み込めませんでした」と出る（Task 4 `loadNews` のテスト）。

---

## ファイルの地図

| ファイル | 役割 |
|----------|------|
| `fetcher/rss.py` | `FEEDS` に `genre` を足し、AI のソースを足す。`parse_feed` が `genre` を付ける |
| `fetcher/main.py` | 出力先を `data/news.json` に。ジャンルごとの上限。`genre` がない前回データの扱い |
| `scripts/sync_digests.py` | Obsidian のまとめを公開用の Markdown に変換する |
| `tests/test_sync_digests.py`、`tests/fixtures/digests/` | 上のテスト |
| `package.json`、`astro.config.mjs`、`tsconfig.json`、`vitest.config.ts` | Astro・vitest の設定 |
| `src/site.ts` | `SITE_NAME`、`SITE_DESCRIPTION`、`SITE_URL` |
| `src/content.config.ts` | `digest` コレクションのスキーマ |
| `src/lib/news.ts` | `news.json` の型、読み込み、ジャンルで分ける |
| `src/lib/format.ts` | `safeUrl`、`relativeTime`、`formatEnd`、`yen` |
| `src/lib/filter.ts` | フィードの絞り込みの判定（純粋関数） |
| `src/lib/*.test.ts` | vitest |
| `src/styles/tokens.css`、`src/styles/global.css` | 色・文字・余白のトークンと土台 |
| `src/layouts/Base.astro` | head（title、description、OGP、canonical）、ヘッダー、フッター |
| `src/components/` | `SiteHeader`、`SiteFooter`、`NewsCard`、`NewsFeed`、`DealCard`、`FreeCard`、`DealsPanel`、`FeedStatus`、`DigestCard`、`Toc` |
| `src/scripts/feed.ts` | フィードの画面操作（DOM の出し入れ、localStorage） |
| `src/pages/` | `index`、`game`、`ai`、`digest/index`、`digest/[slug]`、`about`、`404`、`rss.xml.ts`、`og/[slug].png.ts`、`og/site.png.ts` |
| `src/lib/og.ts`、`src/assets/fonts/` | OGP 画像の生成と、そのためのフォント |
| `.github/workflows/auto_update.yml`、`.github/workflows/ci.yml` | 毎時の更新、PR のときの確認 |
| `vercel.json`、`.claude/launch.json`、`.gitignore`、`README.md` | 設定と説明 |
| 削除：`public/index.html`、`public/app.js`、`public/style.css`、`public/news.json` | Astro 版に置き換わる |

---

### Task 0: 準備（ユーザーの作業あり）

**Files:** なし

- [ ] **Step 1: ユーザーに Node 22 LTS を入れてもらう**

今の Node は v14.16.0 で、Astro 5 は動かない。ユーザーに確認を取ってから、次のどちらかで入れてもらう。

```powershell
winget install OpenJS.NodeJS.LTS
```

- [ ] **Step 2: 入ったか確かめる**

新しい PowerShell で `node -v` を実行する。Expected: `v22.` で始まる。`npm -v` は 10 以上。

---

### Task 1: AI ニュースの収集（ジャンルとジャンルごとの上限）

**Files:**
- Modify: `fetcher/rss.py`（`FEEDS`、`parse_feed`）
- Modify: `fetcher/main.py`（`OUTPUT`、`NEWS_MAX`、`merge`）
- Test: `tests/test_rss.py`、`tests/test_main.py`

**Interfaces:**
- Produces: `data/news.json` の各ニュースに `genre: "game" | "ai"`。`sources` の各項目にも `genre`（RSS は `FEEDS` の値、セールのソースは `"game"`）。`/about` のソース一覧はこれを使う。トップレベルのキー（`updated_at` `sources` `news` `deals`）は今のまま。`fetcher.main.OUTPUT == Path("data/news.json")`。`fetcher.main.NEWS_MAX_PER_GENRE == 150`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_rss.py` に足す：

```python
def test_genre_from_feed():
    items = parse_feed((FIX / "rss_sample.xml").read_bytes(), dict(FEED, genre="ai"))
    assert all(i["genre"] == "ai" for i in items)

def test_genre_defaults_to_game():
    assert all(i["genre"] == "game" for i in rss_items())

def test_every_feed_has_known_genre():
    from fetcher.rss import FEEDS
    assert {f.get("genre", "game") for f in FEEDS} <= {"game", "ai"}
    assert any(f.get("genre") == "ai" for f in FEEDS)
```

`tests/test_main.py` に足す（`news()` の初期値に `"genre": "game"` を足す）：

```python
def test_cap_is_per_genre(monkeypatch):
    monkeypatch.setattr(m, "NEWS_MAX_PER_GENRE", 2)
    game = [news(i, hours_ago=1) for i in range(5)]
    ai = [news(f"a{i}", source="AI src", hours_ago=10, genre="ai") for i in range(3)]
    out = m.merge({"rss:AUTOMATON": game, "rss:AI src": ai}, m.empty_data(), NOW)
    genres = [n["genre"] for n in out["news"]]
    assert genres.count("game") == 2 and genres.count("ai") == 2

def test_previous_item_without_genre_becomes_game():
    old = news(1, first_seen=to_iso(NOW))
    del old["genre"]
    out = m.merge({"rss:AUTOMATON": RuntimeError("x")}, previous([old]), NOW)
    assert out["news"][0]["genre"] == "game"

def test_source_status_has_genre(monkeypatch):
    monkeypatch.setattr(m, "SOURCE_GENRES", {"rss:AI src": "ai"})
    out = m.merge({"rss:AI src": [], "steam": RuntimeError("x")}, m.empty_data(), NOW)
    assert {s["id"]: s["genre"] for s in out["sources"]} == {"rss:AI src": "ai", "steam": "game"}
```

- [ ] **Step 2: 失敗することを確かめる**

Run: `.venv\Scripts\python -m pytest tests/test_rss.py tests/test_main.py -v`
Expected: 上の 6 つが FAIL（`KeyError: 'genre'` や件数の不一致）

- [ ] **Step 3: 実装する**

- `parse_feed` が `"genre": feed.get("genre", "game")` を付ける。
- `main.py`：`SOURCE_GENRES = {f"rss:{f['source']}": f.get("genre", "game") for f in rss.FEEDS}` を足し、`merge` が作るソースの状態に `"genre": SOURCE_GENRES.get(source_id, "game")` を入れる。`OUTPUT = Path("data/news.json")`。`NEWS_MAX` を消して `NEWS_MAX_PER_GENRE = 150` にする。`merge` の中で `n.setdefault("genre", "game")` をしてから、並べ替えたあと、ジャンルごとに先頭 150 件を残す（新しい順は保つ）。モジュールの docstring の `public/news.json` も直す。

- [ ] **Step 4: 通ることを確かめる**

Run: `.venv\Scripts\python -m pytest -q`
Expected: 全部 PASS

- [ ] **Step 5: AI のフィードの URL を実際に確かめる**

次の候補を 1 つずつ `fetcher.rss.fetch` に渡して、何件取れたかと、一番新しい記事の日付を出す。このときの Python は使い捨ての `-c` で動かす。

| source | url | region |
|--------|-----|--------|
| ITmedia AI+ | `https://rss.itmedia.co.jp/rss/2.0/aiplus.xml` | jp |
| Publickey | `https://www.publickey1.jp/atom.xml` | jp |
| OpenAI | `https://openai.com/news/rss.xml` | official |
| Anthropic | 公式の RSS があるか探す。なければ外す | official |
| Google AI | `https://blog.google/technology/ai/rss/` | official |
| The Verge AI | `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml` | global |
| TechCrunch AI | `https://techcrunch.com/category/artificial-intelligence/feed/` | global |

取れたもの（1 件以上取れて、一番新しい記事が 30 日以内）だけを、`FEEDS` の最後に `# --- AI ---` のコメントを付けて、`"genre": "ai"` 付きで足す。外したものと、その理由（HTTP エラー、0 件、更新が止まっている）は、コミットメッセージに書く。

- [ ] **Step 6: 本番と同じように動かす**

Run: `.venv\Scripts\python -m fetcher`
Expected: 各ソースの件数が出て、`data/news.json` ができる。中に `"genre": "ai"` の項目がある。

- [ ] **Step 7: コミット**

`public/news.json` を `git mv` で `data/news.json` に移したうえで、生成し直したものをコミットする。

```powershell
git add fetcher tests data/news.json
git commit -m "feat(fetcher): AI ニュースのソースを足し、ジャンルごとに上限をかける"
```

---

### Task 2: まとめ記事の取り込みスクリプト

**Files:**
- Create: `scripts/__init__.py`（空）、`scripts/sync_digests.py`
- Create: `tests/fixtures/digests/2026-10-14_ニュースまとめ.md`、`tests/fixtures/digests/2026-10-14_ニュースまとめ_2.md`、`tests/fixtures/digests/broken.md`
- Test: `tests/test_sync_digests.py`

**Interfaces:**
- Produces:
  - `convert(text: str) -> tuple[str, int]`：公開用の Markdown と、取り除いた行の数を返す。プロパティが読めなければ `ValueError`。
  - `output_name(source_name: str) -> str`：`2026-10-14_ニュースまとめ.md` → `2026-10-14.md`、`..._2.md` → `2026-10-14-2.md`。
  - `sync(src: Path, dest: Path) -> list[str]`：画面に出す報告の行を返す。
  - `python -m scripts.sync_digests [--src PATH] [--dest PATH]`。`--src` の初期値は環境変数 `DIGEST_SRC`（どちらもなければエラー終了。例：`<保管庫>\30_ニュース`）、`--dest` の初期値は `src/content/digest`。
  - 出力のプロパティ：`title`（本文の最初の `# ` の行）、`date`（`created`）、`period`（あれば）、`tags`（リスト）。Task 3 のスキーマと同じ名前にする。

- [ ] **Step 1: テスト用のノートを作る**

`tests/fixtures/digests/2026-10-14_ニュースまとめ.md`：本物と同じ形（`created` `type` `period` `tags` のプロパティ、`# ニュースまとめ（2026-10-14）`、`## AI`、`### 見出し`、本文、箇条書き）で 2 記事分。中に次のものを入れる。
- `- 自分への影響：Web開発で…`
- `  - 自分への影響: 半角コロン`（字下げあり）
- `- **自分への影響**：太字` と、その下の字下げした `  - 続きの行`
- `- 出典：Google公式ブログ（2026-10-13） https://blog.google/a`
- `[[2026-10-14_Game Newsサイトの作り直し]]` と `[[Unity 6のLTSとサポート期間|Unity 6 の LTS]]`
- `- 第三者の検証は確認できなかった。`（残るべき注記）

`_2.md` は最小限のノート。`broken.md` は `created` がないノート。

- [ ] **Step 2: 失敗するテストを書く**

```python
def test_strips_impact_variants():
    out, removed = convert(SAMPLE)
    assert "自分への影響" not in out
    assert "続きの行" not in out
    assert removed == 4  # 3 種類の行 + ぶら下がる 1 行

def test_keeps_notes_and_body():
    out, _ = convert(SAMPLE)
    assert "- 第三者の検証は確認できなかった。" in out

def test_wikilinks_become_plain_text():
    out, _ = convert(SAMPLE)
    assert "[[" not in out
    assert "2026-10-14_Game Newsサイトの作り直し" in out and "Unity 6 の LTS" in out

def test_source_line_becomes_link():
    out, _ = convert(SAMPLE)
    assert "- 出典：[Google公式ブログ（2026-10-13）](https://blog.google/a)" in out

def test_frontmatter_is_converted():
    out, _ = convert(SAMPLE)
    fm = out.split("---")[1]
    assert "title: ニュースまとめ（2026-10-14）" in fm
    assert "date: 2026-10-14" in fm and "period:" in fm and "tags:" in fm
    assert "type:" not in fm and "created:" not in fm

def test_h1_removed_from_body():  # タイトルはレイアウトが出すので本文からは消す
    body = convert(SAMPLE)[0].split("---", 2)[2]
    assert not any(line.startswith("# ") for line in body.splitlines())

def test_output_name():
    assert output_name("2026-10-14_ニュースまとめ.md") == "2026-10-14.md"
    assert output_name("2026-10-14_ニュースまとめ_2.md") == "2026-10-14-2.md"

def test_sync_skips_broken_and_reports(tmp_path):
    report = sync(FIX, tmp_path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["2026-10-14-2.md", "2026-10-14.md"]
    assert any("broken.md" in line and "created" in line for line in report)
    assert any("2026-10-14.md" in line and "4" in line for line in report)

def test_sync_reports_overwrite(tmp_path):
    sync(FIX, tmp_path)
    (tmp_path / "2026-10-14.md").write_text("old", encoding="utf-8")
    assert any("上書き" in line for line in sync(FIX, tmp_path))
```

- [ ] **Step 3: 失敗することを確かめる**

Run: `.venv\Scripts\python -m pytest tests/test_sync_digests.py -v`
Expected: `ModuleNotFoundError: scripts.sync_digests`

- [ ] **Step 4: 実装する**

プロパティは YAML ライブラリを足さずに、`key: value` と `tags: [a, b]` の 2 つの形だけを読む（保管庫のテンプレートがこの形なので）。「自分への影響」の判定は、行頭の空白、`- `、`**` を取った残りが `自分への影響` で始まるかどうかで行う。その行より深く字下げされた、すぐ後に続く行も消す。出典の行は `^(\s*- 出典：)(.+?)\s+(https?://\S+)$` を `\1[\2](\3)` にする。出力のプロパティは、`title` を必ずダブルクォートで囲んで書く（`：` や `#` が入っても壊れないように）。

- [ ] **Step 5: 通ることを確かめる**

Run: `.venv\Scripts\python -m pytest -q`
Expected: 全部 PASS

- [ ] **Step 6: 本物の保管庫で動かして、出力を見る**

Run: `.venv\Scripts\python -m scripts.sync_digests`
Expected: `src/content/digest/2026-10-14.md` ができて、「取り除いた行: N」と出る。N は、元のノートで `(Select-String -Path "<保管庫>\30_ニュース\2026-10-14_ニュースまとめ.md" -Pattern "自分への影響").Count` が返す数と同じ（ぶら下がる行がなければ）。`Select-String -Path src/content/digest/*.md -Pattern "自分への影響"` が何も返さない。出力の Markdown を開いて、出典がリンクになっていることを目で確かめる。

- [ ] **Step 7: コミット**

```powershell
git add scripts tests src/content/digest
git commit -m "feat: Obsidian のまとめを公開用に変換して取り込むスクリプトを足す"
```

---

### Task 3: Astro の土台とデザインのトークン

**Files:**
- Create: `package.json`、`astro.config.mjs`、`tsconfig.json`、`vitest.config.ts`、`src/site.ts`、`src/content.config.ts`、`src/styles/tokens.css`、`src/styles/global.css`、`src/layouts/Base.astro`、`src/components/SiteHeader.astro`、`src/components/SiteFooter.astro`、`src/pages/404.astro`、`src/pages/index.astro`（仮）、`public/favicon.svg`
- Modify: `vercel.json`、`.gitignore`、`.claude/launch.json`
- Delete: `public/index.html`、`public/app.js`、`public/style.css`

**Interfaces:**
- Produces:
  - `src/site.ts`：`export const SITE_NAME: string`、`export const SITE_DESCRIPTION: string`、`export const SITE_URL = "https://game-news-smoky.vercel.app"`。
  - `Base.astro` の props：`{ title?: string; description?: string; ogImage?: string; article?: { publishedTime: string } }`。`title` がないときは `SITE_NAME` だけ、あるときは `` `${title} | ${SITE_NAME}` ``。`ogImage` の初期値は `/og/site.png`（Task 8 で作る）。`<slot />` を `<main id="main">` に入れる。先頭に「本文へ移動」のスキップリンクを置く。
  - `digest` コレクション：`title: string`、`date: Date`（`z.coerce.date()`）、`period?: string`、`tags: string[]`（初期値 `[]`）。slug はファイル名（`2026-10-14`、`2026-10-14-2`）。
  - npm scripts：`dev`、`build`（`astro check && astro build`）、`preview`、`test`（`vitest run`）、`check:links`（`linkinator dist --recurse --skip "^https?://"`）。
  - CSS 変数（`tokens.css`）：`--bg` `--surface` `--text` `--text-muted` `--border` `--accent` `--accent-text` `--game` `--ai` `--radius` `--space-1`〜`--space-6` `--font-sans` `--font-size-*`。ゲームと AI を見分けるために `--game` と `--ai` の 2 色を持つ。

- [ ] **Step 1: サイト名を決める**

ユーザーに候補を出して選んでもらう。候補：「PLAYLOG」（遊びと記録）、「Signal」（ゲームと AI の信号を拾う）、「Two Screens」（ゲームと AI の 2 つの画面）。ほかの案でもいい。決まった名前を `SITE_NAME` に入れる。`SITE_DESCRIPTION` は「国内外のゲームと AI のニュースを 1 時間ごとに自動で集め、週ごとのまとめ記事を添えて届けるサイト。」をもとに、ユーザーと一緒に決める。

- [ ] **Step 2: パッケージを入れる**

```powershell
npm init -y
npm install astro @astrojs/sitemap @astrojs/rss @astrojs/check typescript
npm install -D vitest linkinator
```

`package.json` は `"type": "module"`、`"private": true`、`"engines": { "node": ">=22" }` にする。`package-lock.json` もコミットする。

- [ ] **Step 3: 設定と土台を書く**

- `astro.config.mjs`：`site: SITE_URL`、`integrations: [sitemap()]`。`build.format` は初期値（`directory`）のままにする（`/digest/2026-10-14/index.html` として出るので、Vercel の設定なしで `/digest/2026-10-14` が開ける。前に `cleanUrls` でトップが 404 になったので、URL を書き換える設定は使わない）。
- `vercel.json`：`{ "git": { "deploymentEnabled": false }, "framework": "astro", "buildCommand": "npm run build", "outputDirectory": "dist" }`。
- `.gitignore`：`node_modules/`、`dist/`、`.astro/` を足す。
- `.claude/launch.json`：`npm run dev`（ポート 4321）に変える。
- `tokens.css`：未 push の Apple 風リデザインのコミット `73517b7` の `public/style.css`（`git show 73517b7:public/style.css`）の色と文字を出発点にして、ダークの値を足す。文字と背景の組み合わせはすべてコントラスト 4.5:1 以上にする。
- `SiteHeader`：ロゴ（`SITE_NAME`）と、`/game` `/ai` `/digest` `/about` へのナビ。今いるページに `aria-current="page"`。スマホでは横にスクロールできるタブ型のナビ（ハンバーガーメニューは使わない）。
- `SiteFooter`：出典の扱いについての 1 文と `/about` へのリンク。
- `404.astro`：短い説明とトップへのリンク。

- [ ] **Step 4: ビルドが通ることを確かめる**

Run: `npm run build`
Expected: エラーなしで終わり、`dist/index.html`、`dist/404.html`、`dist/sitemap-index.xml` ができる。

- [ ] **Step 5: 見た目を確かめる**

`npm run dev` を動かし、ブラウザのペインで幅 375px とデスクトップ、ライトとダークの 4 通りのスクリーンショットを撮る。横スクロールが出ないこと（`document.documentElement.scrollWidth <= innerWidth`）を確かめる。

- [ ] **Step 6: コミット**

```powershell
git add -A
git commit -m "feat: Astro の土台、デザインのトークン、共通レイアウトを作る"
```

---

### Task 4: データの読み込みと、表示に使う関数

**Files:**
- Create: `src/lib/news.ts`、`src/lib/format.ts`、`src/lib/filter.ts`
- Test: `src/lib/news.test.ts`、`src/lib/format.test.ts`、`src/lib/filter.test.ts`

**Interfaces:**
- Produces:
  - `news.ts`：型 `NewsItem`、`Deal`、`SourceStatus`、`NewsData`（`news.json` の項目そのまま。`NewsItem.genre: "game" | "ai"`）。`loadNews(path?: string): NewsData & { error: boolean }`。初期値は `data/news.json`。ファイルがない、JSON が壊れている、`news` が配列でない、のどれでも `{ updated_at: null, sources: [], news: [], deals: [], error: true }` を返して、例外は投げない。`byGenre(items: NewsItem[], genre: "game" | "ai"): NewsItem[]`（`genre` がなければ `"game"` として扱う）。`failedSources(sources): string[]`（`rss:` を取った名前）。
  - `format.ts`：`safeUrl(value: string | null | undefined): string`、`relativeTime(iso: string, now: Date): string`、`formatEnd(iso: string | null): string`、`yen(n: number): string`。動きは今の `public/app.js` のものと同じにする。
  - `filter.ts`：`type FeedState = { region: "all" | "jp" | "global" | "official" | "fav"; query: string; favs: Set<string> }`、`matchesNews(item: Pick<NewsItem, "id" | "title" | "title_original" | "source" | "region">, state: FeedState): boolean`。`type DealState = { store: "all" | "steam" | "epic" | "ps" | "eshop"; query: string }`、`matchesDeal(...)`。`sortDeals<T extends Pick<Deal, "discount" | "price_sale" | "ends_at">>(deals: T[], sort: "default" | "discount" | "ending" | "price"): T[]`。

- [ ] **Step 1: 失敗するテストを書く**

```ts
// format.test.ts
test("safeUrl は http(s) だけ通す", () => {
  expect(safeUrl("https://a.jp/x")).toBe("https://a.jp/x");
  expect(safeUrl("javascript:alert(1)")).toBe("#");
  expect(safeUrl("data:text/html,x")).toBe("#");
  expect(safeUrl(null)).toBe("#");
  expect(safeUrl("not a url")).toBe("#");
});
test("relativeTime", () => {
  const now = new Date("2026-10-25T12:00:00+09:00");
  expect(relativeTime("2026-10-25T11:59:30+09:00", now)).toBe("たった今");
  expect(relativeTime("2026-10-25T11:15:00+09:00", now)).toBe("45分前");
  expect(relativeTime("2026-10-25T09:00:00+09:00", now)).toBe("3時間前");
  expect(relativeTime("2026-10-22T09:00:00+09:00", now)).toBe("10/22");
  expect(relativeTime("broken", now)).toBe("");
});
test("yen", () => expect(yen(12800)).toBe("¥12,800"));

// news.test.ts
test("ファイルがないときは error: true で空", () => {
  const d = loadNews("does/not/exist.json");
  expect(d).toMatchObject({ error: true, news: [], deals: [], sources: [] });
});
test("壊れた JSON でも例外を投げない", () => {
  const p = join(mkdtempSync(join(tmpdir(), "news-")), "news.json");
  writeFileSync(p, "{");
  expect(loadNews(p)).toMatchObject({ error: true, news: [] });
});
test("news が配列でなければ error", () => {
  const p = join(mkdtempSync(join(tmpdir(), "news-")), "news.json");
  writeFileSync(p, JSON.stringify({ news: "x" }));
  expect(loadNews(p).error).toBe(true);
});
test("byGenre は genre がない項目を game にする", () => {
  const items = [{ id: "a", genre: "ai" }, { id: "b" }, { id: "c", genre: "game" }] as NewsItem[];
  expect(byGenre(items, "game").map((n) => n.id)).toEqual(["b", "c"]);
  expect(byGenre(items, "ai").map((n) => n.id)).toEqual(["a"]);
});
test("failedSources", () => {
  expect(failedSources([{ id: "rss:Kotaku", ok: false }, { id: "steam", ok: true }] as SourceStatus[]))
    .toEqual(["Kotaku"]);
});

// filter.test.ts
const base = { region: "all", query: "", favs: new Set<string>() } as FeedState;
const item = { id: "n1", title: "Claude の新モデル", title_original: "New Claude model", source: "The Verge AI", region: "global" };
test("地域の絞り込み", () => {
  expect(matchesNews(item, { ...base, region: "global" })).toBe(true);
  expect(matchesNews(item, { ...base, region: "jp" })).toBe(false);
});
test("お気に入り", () => {
  expect(matchesNews(item, { ...base, region: "fav" })).toBe(false);
  expect(matchesNews(item, { ...base, region: "fav", favs: new Set(["n1"]) })).toBe(true);
});
test("検索は原題と出典にも当たる。大文字小文字は区別しない", () => {
  expect(matchesNews(item, { ...base, query: "new claude" })).toBe(true);
  expect(matchesNews(item, { ...base, query: "verge" })).toBe(true);
  expect(matchesNews(item, { ...base, query: "unity" })).toBe(false);
});
test("sortDeals の ending は終了日なしを最後にする", () => {
  const d = [{ discount: 10, price_sale: 100, ends_at: null }, { discount: 50, price_sale: 500, ends_at: "2026-10-26T00:00:00+09:00" }];
  expect(sortDeals(d, "ending")[0].discount).toBe(50);
  expect(sortDeals(d, "discount")[0].discount).toBe(50);
  expect(sortDeals(d, "price")[0].discount).toBe(10);
  expect(sortDeals(d, "default")).toEqual(d);
});
```

- [ ] **Step 2: 失敗することを確かめる**

Run: `npm test`
Expected: import できずに FAIL

- [ ] **Step 3: 実装する**

`loadNews` は `node:fs` の `readFileSync` を使う（ビルドのときだけ動く）。`query` は、呼ぶ側で `trim().toLowerCase()` した値が渡ってくる前提にする。

- [ ] **Step 4: 通ることを確かめる**

Run: `npm test`
Expected: 全部 PASS

- [ ] **Step 5: コミット**

```powershell
git add src/lib
git commit -m "feat: news.json の読み込みと、表示・絞り込みの関数を足す"
```

---

### Task 5: `/game` と `/ai` のフィード

**Files:**
- Create: `src/components/NewsCard.astro`、`src/components/NewsFeed.astro`、`src/components/DealCard.astro`、`src/components/FreeCard.astro`、`src/components/DealsPanel.astro`、`src/components/FeedStatus.astro`、`src/scripts/feed.ts`、`src/pages/game.astro`、`src/pages/ai.astro`

**Interfaces:**
- Consumes: Task 4 の `loadNews`、`byGenre`、`failedSources`、`safeUrl`、`formatEnd`、`yen`、`matchesNews`、`matchesDeal`、`sortDeals`。
- Produces:
  - `NewsFeed.astro` の props：`{ items: NewsItem[]; label: string; limit?: number; showControls?: boolean }`。`showControls` が false のとき（トップページで使う）は、絞り込みと検索を出さない。
  - `FeedStatus.astro` の props：`{ updatedAt: string | null; failed: string[]; error: boolean }`。
  - カードの HTML はサーバーで全部作る。`feed.ts` は、カードに付けた `data-id` `data-region` `data-search`（タイトル・原題・出典を小文字でつないだ文字列）と、セールの `data-store` `data-discount` `data-price` `data-ends`（ミリ秒、なければ空）を読んで、`hidden` を付け外しするだけ。カードを作り直さない。
  - 相対時刻は、サーバーでは `<time datetime>` に日時だけを入れる。表示の文字（「3時間前」）は `feed.ts` が `relativeTime` で入れて、1 分ごとに更新する。JS がないときは `M/D HH:mm` を出しておく。

- [ ] **Step 1: カードとフィードを作る**

- `NewsCard`：サムネイル（`loading="lazy"`、`width`/`height` を指定して表示のずれを防ぐ。画像がない・読み込めないときは出典名を入れたプレースホルダー）、タイトル、出典、時刻、翻訳バッジ（`translated` のとき。`title` 属性に原題）、お気に入りボタン（`aria-pressed`、44px、見えないラベル「〜をお気に入りに追加」）。リンクは `safeUrl`、`target="_blank" rel="noopener noreferrer"`。
- `NewsFeed`：絞り込みのチップ（すべて・国内・海外・公式・お気に入り。`role="group"`、`aria-pressed`）、検索（`type="search"`、`<label>` 付き）、一覧、0 件のときの文言（今の `app.js` の文言を使う）。
- `DealsPanel`：無料配布のカード、ストアのチップ、並べ替えの `<select>`、セールの一覧。`/game` だけで使う。
- `FeedStatus`：「最終更新 〜」、失敗したソースの名前。`error` のときは「ニュースを読み込めませんでした」。最終更新から 180 分を超えたら目立たせる（今の `STALE_MINUTES`）。

- [ ] **Step 2: ページを作る**

- `/game`：見出し、`FeedStatus`、「ニュース」「セール」のタブ（`role="tablist"`、矢印キーで移動）。900px 以上ではタブを出さずに 2 カラムで両方出す（今と同じ）。
- `/ai`：見出し、`FeedStatus`、`NewsFeed` だけ。
- 両方とも `description` を指定する。

- [ ] **Step 3: `feed.ts` を書く**

絞り込みの判定は `filter.ts` だけを使う。localStorage の読み書きは try/catch で囲む（プライベートモードでも動くように）。お気に入りの保存キーは `gamefeed_favs_v2`。

- [ ] **Step 4: ビルドして、危ない文字列が文字のまま出ることを確かめる**

`data/news.json` を一時的に退避して、`<script>alert(1)</script>` というタイトルと、`javascript:alert(1)` のリンクを持つ項目を 1 つだけ入れた `news.json` で `npm run build` を実行する。`dist/game.html` に `&lt;script&gt;` が含まれ、`href="javascript:` が含まれないことを `Select-String` で確かめる。確かめたら `git checkout data/news.json` で元に戻す。

- [ ] **Step 5: 画面で確かめる**

`npm run dev` でブラウザのペインを使い、幅 375px で：チップを押すと絞り込まれる、検索で絞り込まれる、☆ を押してから「お気に入り」で出る、再読み込みしても ☆ が残る、セールの並べ替えが効く、Tab キーだけでここまで全部操作できる。を確かめて、スクリーンショットを撮る。

- [ ] **Step 6: コミット**

```powershell
git add src
git commit -m "feat: ゲームと AI のフィードのページを作る"
```

---

### Task 6: まとめ記事のページと RSS 配信

**Files:**
- Create: `src/components/DigestCard.astro`、`src/components/Toc.astro`、`src/pages/digest/index.astro`、`src/pages/digest/[slug].astro`、`src/pages/rss.xml.ts`、`src/styles/prose.css`

**Interfaces:**
- Consumes: Task 3 の `digest` コレクション、`Base.astro`。
- Produces: `DigestCard.astro` の props：`{ entry: CollectionEntry<"digest">; headings: string[]; featured?: boolean }`。`headings` は h3 の文字列（記事の見出し）。Task 7 のトップページで `featured` を使う。`src/lib/digest.ts` に `getDigests(): Promise<{ entry; headings: string[] }[]>`（新しい順）を置く。見出しは `render(entry)` が返す `headings` から `depth === 3` のものを取る。

- [ ] **Step 1: 一覧と記事のページを作る**

- `/digest`：新しい順。カードには日付、対象期間、タグ、「記事 N 本」、最初の 3 つの見出し。
- `/digest/[slug]`：パンくず（トップ › まとめ › 記事）、タイトル、日付、対象期間、タグ、目次（h2・h3。900px 以上では横に固定、スマホでは本文の前に折りたためる `<details>`）、本文、前後の記事へのリンク、「このまとめについて」（出典の付け方、確認できなかったことはそう書いている、という 2 文）。`Base` に `article.publishedTime` を渡す。
- `prose.css`：h3 の後の段落に続く箇条書き（注記と出典）を、背景を少し変えた枠に入れて、本文と見分けられるようにする。出典のリンクは長い URL でも折り返す（`overflow-wrap: anywhere`）。

- [ ] **Step 2: RSS 配信を作る**

`@astrojs/rss` で `/rss.xml`。項目は `title`、`pubDate`（`date`）、`link`（`/digest/<slug>`）、`description`（見出しを「、」でつないだもの）。`Base.astro` の head に `<link rel="alternate" type="application/rss+xml">` を足す。

- [ ] **Step 3: ビルドして確かめる**

Run: `npm run build`
Expected: `dist/digest/2026-10-14.html` と `dist/rss.xml` ができる。`Select-String -Path dist -Recurse -Pattern "自分への影響"`（`Get-ChildItem dist -Recurse -File | Select-String "自分への影響"`）が何も返さない。

- [ ] **Step 4: 画面で確かめる**

幅 375px とデスクトップで記事ページのスクリーンショットを撮る。目次のリンクで見出しに飛べることと、長い URL で横スクロールが出ないことを確かめる。

- [ ] **Step 5: コミット**

```powershell
git add src
git commit -m "feat: まとめ記事の一覧・記事ページと RSS 配信を作る"
```

---

### Task 7: トップページと `/about`

**Files:**
- Modify: `src/pages/index.astro`
- Create: `src/pages/about.astro`、`src/components/HowItWorks.astro`

**Interfaces:**
- Consumes: Task 5 の `NewsFeed`（`showControls={false}`、`limit={5}`）と `FeedStatus`、Task 6 の `getDigests` と `DigestCard`（`featured`）。

- [ ] **Step 1: トップページを作る**

上から順に：サイトの説明 1 行（`SITE_DESCRIPTION`）、`FeedStatus`、最新のまとめ（`DigestCard featured`。まとめが 1 本もないときは、この枠ごと出さない）、ゲームの最新 5 件と「ゲームのニュースをすべて見る →」、AI の最新 5 件と「AI のニュースをすべて見る →」。900px 以上では、ゲームと AI を横に並べる。

- [ ] **Step 2: `/about` を作る**

サイトの説明、仕組みの図（`HowItWorks.astro`。インラインの SVG で、Task 3 の CSS 変数を使ってダークでも読めるようにする。中身は設計メモの「構成とデータの流れ」の 2 つの流れ）、使っている技術、情報の扱い（出典、海外記事のタイトルは機械翻訳であること、記事の本文は載せないこと、セールの価格は各ストアで確かめてほしいこと）、ソースの一覧（`loadNews().sources` を `genre` ごとに分けて、`rss:` を取った名前で出す。`SourceStatus` 型に `genre?: "game" | "ai"` を足す）、作った人（GitHub `FSq1v` へのリンクだけ。本名や連絡先は載せない）。

- [ ] **Step 3: 確かめる**

`npm run build` が通ること。幅 375px とデスクトップ、ライトとダークでスクリーンショットを撮る。

- [ ] **Step 4: コミット**

```powershell
git add src
git commit -m "feat: トップページと about ページを作る"
```

---

### Task 8: OGP 画像とメタ情報

**Files:**
- Create: `src/lib/og.ts`、`src/pages/og/[slug].png.ts`、`src/pages/og/site.png.ts`、`src/assets/fonts/NotoSansJP-Bold.ttf`、`src/assets/fonts/OFL.txt`
- Modify: `src/layouts/Base.astro`、`src/pages/digest/[slug].astro`、`package.json`

**Interfaces:**
- Consumes: Task 6 の `getDigests`。
- Produces: `renderOg(opts: { title: string; subtitle: string }): Promise<Buffer>`（1200×630 の PNG）。記事の `ogImage` は `/og/<slug>.png`。

- [ ] **Step 1: フォントを用意する（ダウンロードの前にユーザーの確認を取る）**

Google Fonts の Noto Sans JP（OFL ライセンス）の静的な Bold（`static/NotoSansJP-Bold.ttf`）を `src/assets/fonts/` に置き、ライセンス文も `OFL.txt` として置く。ファイル名、入手先、大きさをユーザーに伝えて、OK をもらってからダウンロードする。

- [ ] **Step 2: 生成の処理を書く**

`npm install satori @resvg/resvg-js`。`og.ts` は satori で、サイト名、タイトル、サブタイトル（記事なら「まとめ・対象期間」）をトークンの色で並べた SVG を作り、resvg で PNG にする。`[slug].png.ts` は `getStaticPaths` で記事ごとの画像を作る。`site.png.ts` はサイト全体の画像（`SITE_NAME` と `SITE_DESCRIPTION`）を作る。

- [ ] **Step 3: head を仕上げる**

`Base.astro` に：`<link rel="canonical">`、`og:type`（記事なら `article`）、`og:title`、`og:description`、`og:image`（絶対 URL）、`og:url`、`og:site_name`、`twitter:card=summary_large_image`、`theme-color`（ライトとダークの 2 つ）、`favicon.svg`、`article:published_time`。

- [ ] **Step 4: 確かめる**

Run: `npm run build`
Expected: `dist/og/site.png` と `dist/og/2026-10-14.png` ができる。Read ツールで 2 枚の画像を開いて、日本語が化けていないことを目で見て確かめる。`dist/digest/2026-10-14.html` に `og:image" content="https://game-news-smoky.vercel.app/og/2026-10-14.png"` がある。

- [ ] **Step 5: コミット**

```powershell
git add -A
git commit -m "feat: OGP 画像を作り、ページごとのメタ情報をそろえる"
```

---

### Task 9: CI とデプロイ

**Files:**
- Modify: `.github/workflows/auto_update.yml`
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: 毎時の処理を直す**

`auto_update.yml` の順番：checkout → setup-python（3.12）→ `pip install` → `pytest -q` → `python -m fetcher` → `data/news.json` をコミット・push（`git add data/news.json`）→ setup-node（`node-version: 22`、`cache: npm`）→ `npm ci` → `npm test` → `vercel pull` → `vercel build --prod`（`vercel.json` の `buildCommand` で `npm run build` が動く）→ `npx linkinator .vercel/output/static --recurse --skip "^https?://"` → `vercel deploy --prebuilt --prod`。どこかで失敗したらデプロイしない。

- [ ] **Step 2: PR のときの確認を足す**

`ci.yml`：`pull_request` と `workflow_dispatch` で、pytest、`npm ci`、`npm test`、`npm run build`、`npm run check:links` を動かす。デプロイはしない。シークレットも使わない。

- [ ] **Step 3: 手元で同じ順番を通す**

```powershell
.venv\Scripts\python -m pytest -q
npm ci
npm test
npm run build
npm run check:links
```

Expected: 全部成功。`check:links` はリンク切れ 0。

- [ ] **Step 4: コミット**

```powershell
git add .github
git commit -m "ci: Astro のビルドとリンクのチェックを毎時の更新と PR に足す"
```

---

### Task 10: README

**Files:**
- Modify: `README.md`
- Create: `docs/images/mobile.png`、`docs/images/desktop.png`

- [ ] **Step 1: スクリーンショットを撮る**

`npm run preview` を動かし、ブラウザのペインで `/` を幅 375px と 1280px で撮って保存する。

- [ ] **Step 2: README を書き直す**

設計メモの「README」の節のとおり：最初にスクリーンショット 2 枚と公開 URL、何のサイトか（3 行）、構成図（Mermaid）、技術を選んだ理由（Astro：毎時変わる一覧と、たまに書く長い記事という中身が静的生成に向いている／Python：今ある収集処理とテストをそのまま使える／Actions から直接デプロイ：収集とビルドとデプロイを 1 つの流れにして、失敗したら公開しない）、品質で気をつけたこと（Task 11 で測った Lighthouse の数字を入れる）、手元での動かし方（Python と Node の両方）、まとめの取り込み方、初回だけ必要な設定、取得元が壊れたときの直し方（今の内容）。文体はユーザーの CLAUDE.md の「AI っぽさを消す」に合わせる。

- [ ] **Step 3: コミット**

```powershell
git add README.md docs/images
git commit -m "docs: README をポートフォリオ向けに書き直す"
```

---

### Task 11: 仕上げの確認と公開の準備

- [ ] **Step 1: Lighthouse を測る**

`npm run build` と `npm run preview` のあと、`npx lighthouse http://localhost:4321/<page> --form-factor=mobile --only-categories=performance,accessibility,best-practices,seo --output=json --quiet --chrome-flags="--headless"` を `/`、`/game`、`/digest/2026-10-14` で動かす。Expected: 4 項目ともすべて 90 以上。足りないものがあれば、原因を直してから測り直す。数字を README に入れてコミットする。

- [ ] **Step 2: 手で確かめる**

幅 375px で全ページ（`/`、`/game`、`/ai`、`/digest`、`/digest/2026-10-14`、`/about`、存在しない URL）を開いて、横スクロールが出ないこと、ダークモードで読めること、キーボードだけで操作できることを確かめる。

- [ ] **Step 3: `origin/main` を取り込む**

`git fetch origin` のあと、`origin/main` の 1 コミットの中身を `git log -p main..origin/main --stat` で確かめてから、`git merge origin/main` を実行する。`public/news.json` で衝突したら、`data/news.json` を正にして `public/news.json` は消したままにする。

- [ ] **Step 4: ユーザーに確認を取る**

ここまでの結果（スクリーンショット、Lighthouse の数字、テストの結果）を見せて、push と PR の作成をしていいか聞く。Vercel のプロジェクト設定（Framework Preset、Output Directory）を変える必要があるかは、`vercel.json` で上書きされるので不要と見込んでいるが、最初のデプロイの結果を見て判断する。設定を変えるときは、またそのときに確認を取る。
