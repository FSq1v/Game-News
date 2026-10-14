"""海外記事タイトルの日本語訳。

非公式の Google 翻訳エンドポイントを使う。使えなくなっても原文のまま出せばいいので、失敗は None で返す。
"""
import json
import urllib.parse

from .common import http_get

URL = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ja&dt=t&q={q}"


def to_japanese(text: str) -> str | None:
    try:
        data = json.loads(http_get(URL.format(q=urllib.parse.quote(text)), timeout=5))
        translated = "".join(part[0] for part in data[0] if part and part[0])
        return translated or None
    except Exception:
        return None
