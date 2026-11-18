# 生成AI動画チャンネル運用：設計メモ（下書き・未承認）

2026-11-18 時点の相談内容をまとめたもの。続きは帰宅後に再開する。

## 目的
- YouTube と TikTok に生成AIを活用した動画を投稿し、最短で収益化する。
- ブレインロット系は伸びにくい・収益化審査に通りにくいため、トレンド起点の「解説」コンテンツに切り替える。

## 決まったこと
- ジャンル：ゲーム／AI ニュース解説（案A）。このリポジトリの収集パイプライン（`fetcher/` → `data/news.json`）をネタ元に使う。
- 台本：朗読ではなく「フック → 要約 → 解説 → 具体例 → CTA」の構成で、わかりやすく。
- 構成：役割別サブエージェント 4 体＋取りまとめ（案①）
  - `trend-scout`：news.json と Web 検索からネタを 3〜5 本、理由つきで選ぶ
  - `script-writer`：台本・字幕（.srt）・カットリスト（画像生成プロンプト含む）
  - `packaging`：YouTube / TikTok 別のタイトル・サムネ文言・説明文・タグ
  - `policy-check`：量産判定（inauthentic content）、AI 生成の開示、著作物、誤情報をチェック
  - `/make-video` で順に呼ぶ。成果物は `videos/日付-ネタ名/`
- 形式（Claude の提案、修正可）：縦型ショート 45〜60 秒が主力。YouTube / TikTok で台本を共用。
- 素材：ニュース記事の画像・ゲームのスクショは使わない（著作権による収益停止を避ける）。
- 投稿：当面は人が確認してから手動投稿。

## 進め方（提案中・未承認）
- 第 1 段階：サブエージェント 4 体と台本一式
- 第 2 段階：自動動画生成（VOICEVOX 音声 → HTML で図解・テロップ描画 → ffmpeg で 1080×1920 MP4）、`.srt` と編集ソフト用 `.exo` も出力
- 第 3 段階：マネージャー AI（下記）

## 編集ソフト連携
- DaVinci Resolve：Python API と非公式 MCP あり。自宅 PC 上の Claude Code が必要。無料版は外部操作に制限あり。
- AviUtl：`.exo` はテキストなので Claude が直接生成でき、PC 接続不要。旧版と AviUtl2 で形式が違う。

## 環境メモ
- この環境には ffmpeg 6.1、Chromium/Playwright、Node 22、Noto Sans JP あり。
- VOICEVOX のダウンロード（GitHub Releases）はネットワーク設定で 403。許可ホスト追加か GitHub Actions 上で生成する。

## 新規：マネージャー／秘書 AI（要件これから）
- 自分のチャンネルで何が伸びているかを分析し、次に作るべきものを提案する。
- データ取得の前提：
  - YouTube：YouTube Analytics API / Data API。自分の Google アカウントで OAuth 認証が必要（自宅で設定）。
  - TikTok：一般向けの分析 API はほぼ使えないため、TikTok Studio からの CSV 書き出しか手入力を想定。

## 未決事項
1. AviUtl は旧版か AviUtl2 か
2. 段階的に進める順番（第 1 → 2 → 3）でよいか
3. マネージャー AI に何を、どの頻度で報告してほしいか
4. VOICEVOX の取得方法（許可ホスト追加か Actions か）
