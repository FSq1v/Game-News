"""各ソースで使う共通処理（HTTP取得・日時・ID・テキスト整形）。"""
import hashlib
import html
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

JST = timezone(timedelta(hours=9))

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/140.0 Safari/537.36"
)


def now_jst() -> datetime:
    return datetime.now(JST)


def to_iso(dt: datetime) -> str:
    return dt.astimezone(JST).isoformat(timespec="seconds")


def parse_date(value: str | None) -> datetime | None:
    """RFC 822（RSS）と ISO 8601（Atom・API）の日時を読む。読めなければ None。"""
    if not value:
        return None
    value = value.strip()
    dt = None
    try:
        dt = parsedate_to_datetime(value)
    except (TypeError, ValueError, IndexError):
        pass
    if dt is None:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def stable_id(prefix: str, key: str) -> str:
    # hash() は実行ごとに値が変わるので使わない
    return f"{prefix}_{hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]}"


def http_get(url: str, headers: dict | None = None, timeout: int = 10) -> bytes:
    """GET してバイト列を返す。失敗したら1回だけ再試行する。"""
    merged = {"User-Agent": USER_AGENT, "Accept-Language": "ja-JP,ja;q=0.9"}
    if headers:
        merged.update(headers)
    req = urllib.request.Request(url, headers=merged)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.read()
    except Exception:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.read()


_TAG = re.compile(r"<[^>]*>")
_SPACE = re.compile(r"\s+")


def clean_text(text: str | None, limit: int | None = None) -> str:
    if not text:
        return ""
    cleaned = _SPACE.sub(" ", html.unescape(_TAG.sub(" ", text))).strip()
    return cleaned[:limit] if limit else cleaned
