"""海外記事タイトルの日本語訳。

非公式の Google 翻訳エンドポイントを使う。使えなくなっても原文のまま出せばいいので、失敗は None で返す。
"""
import json
import sys
import urllib.parse

from .common import http_get

URL = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ja&dt=t&q={q}"


# 失敗の理由をログに出すのは最初の数件だけ（全件出すとログが埋まる）
_LOGGED_FAILURES = 0
_MAX_LOGGED_FAILURES = 3


def to_japanese(text: str) -> str | None:
    global _LOGGED_FAILURES
    try:
        data = json.loads(http_get(URL.format(q=urllib.parse.quote(text)), timeout=5))
        translated = "".join(part[0] for part in data[0] if part and part[0])
        return translated or None
    except Exception as e:
        if _LOGGED_FAILURES < _MAX_LOGGED_FAILURES:
            _LOGGED_FAILURES += 1
            print(f"translate failed: {type(e).__name__}: {str(e)[:200]}", file=sys.stderr)
        return None
