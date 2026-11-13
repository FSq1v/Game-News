"""海外記事タイトルの日本語訳（DeepL API）。

キーは環境変数 DEEPL_API_KEY（GitHub Actions では Secrets から渡す）。無料プランのキーは末尾が ":fx" で、
送り先が api-free.deepl.com になる。訳せなかったときは None を返し、呼ぶ側は原文のまま出して次の実行で訳し直す。

以前は非公式の Google 翻訳エンドポイントを使っていたが、2026-11-13 から GitHub Actions の実行環境からだと
429（Too Many Requests）しか返らなくなったので、公式の API に切り替えた。
"""
import json
import os
import sys
import urllib.request

from .common import USER_AGENT

BATCH = 50  # DeepL が 1 回に受け付けるテキストの数の上限
FREE_URL = "https://api-free.deepl.com/v2/translate"
PRO_URL = "https://api.deepl.com/v2/translate"


def _post(url: str, body: bytes, headers: dict) -> bytes:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=20) as res:
        return res.read()


def translate_many(texts: list[str]) -> list[str | None]:
    """texts を日本語に訳す。順番は texts と同じ。訳せなかったものは None"""
    out: list[str | None] = [None] * len(texts)
    key = os.environ.get("DEEPL_API_KEY", "").strip()
    if not texts:
        return out
    if not key:
        print("DEEPL_API_KEY is not set; titles stay untranslated", file=sys.stderr)
        return out

    url = FREE_URL if key.endswith(":fx") else PRO_URL
    headers = {
        "Authorization": f"DeepL-Auth-Key {key}",
        "Content-Type": "application/json",
        "User-Agent": USER_AGENT,
    }
    for start in range(0, len(texts), BATCH):
        chunk = texts[start:start + BATCH]
        try:
            body = json.dumps({"text": chunk, "target_lang": "JA"}).encode()
            data = json.loads(_post(url, body, headers))
            results = [t.get("text") or None for t in data["translations"]]
        except Exception as e:
            # 403 はキーの間違い、456 は無料枠の使い切り、429 は送りすぎ。どれもその回はそれ以上送らない
            print(f"translate failed: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)
            break
        if len(results) != len(chunk):
            print(f"translate failed: got {len(results)} results for {len(chunk)} texts", file=sys.stderr)
            break
        out[start:start + len(chunk)] = results
    return out
