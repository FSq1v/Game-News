"""Steam のセール（売上上位のセール中タイトル）を取る。"""
import json
import re
from datetime import datetime
from html.parser import HTMLParser

from .common import JST, http_get, to_iso

SEARCH_URL = (
    "https://store.steampowered.com/search/results/"
    "?specials=1&cc=jp&l=japanese&count=50&infinite=1&filter=topsellers"
)
FEATURED_URL = "https://store.steampowered.com/api/featuredcategories/?cc=jp&l=japanese"

_DIGITS = re.compile(r"\d+")


def _yen(text: str) -> int | None:
    digits = "".join(_DIGITS.findall(text or ""))
    return int(digits) if digits else None


class _SearchParser(HTMLParser):
    """検索結果の行（a.search_result_row）ごとに必要な値を集める。"""

    def __init__(self):
        super().__init__()
        self.rows: list[dict] = []
        self._row: dict | None = None
        self._field: str | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if tag == "a" and "search_result_row" in classes:
            self._row = {"appid": a.get("data-ds-appid", ""), "title": "",
                         "discount": 0, "original": "", "final": "", "image": ""}
            self.rows.append(self._row)
            return
        if self._row is None:
            return
        if tag == "img" and not self._row["image"]:
            self._row["image"] = a.get("src", "")
        if "title" in classes:
            self._field = "title"
        elif "discount_original_price" in classes:
            self._field = "original"
        elif "discount_final_price" in classes:
            self._field = "final"
        if "discount_block" in classes and a.get("data-discount"):
            self._row["discount"] = int(a["data-discount"])

    def handle_endtag(self, tag):
        if tag in ("span", "div"):
            self._field = None
        elif tag == "a":
            self._row = None

    def handle_data(self, data):
        if self._row is not None and self._field:
            self._row[self._field] += data


def parse_search(results_html: str) -> list[dict]:
    parser = _SearchParser()
    parser.feed(results_html)
    items = []
    for row in parser.rows:
        # バンドルは "1,2,3" のように複数 appid になるので、単体のアプリだけ扱う
        if not row["appid"].isdigit():
            continue
        original, sale = _yen(row["original"]), _yen(row["final"])
        # ¥0 は無料配布で値引きセールではないので除く
        if row["discount"] <= 0 or not original or not sale or sale >= original:
            continue
        items.append({
            "appid": int(row["appid"]),
            "title": row["title"].strip(),
            "discount": row["discount"],
            "price_original": original,
            "price_sale": sale,
            "image": row["image"],
        })
    return items


def parse_expirations(featured: dict) -> dict[int, int]:
    return {
        it["id"]: it["discount_expiration"]
        for it in featured.get("specials", {}).get("items", [])
        if it.get("id") and it.get("discount_expiration")
    }


def parse_headers(featured: dict) -> dict[int, str]:
    return {
        it["id"]: it["header_image"]
        for it in featured.get("specials", {}).get("items", [])
        if it.get("id") and it.get("header_image")
    }


def fetch() -> list[dict]:
    rows = parse_search(json.loads(http_get(SEARCH_URL))["results_html"])
    try:
        featured = json.loads(http_get(FEATURED_URL))
    except Exception:
        featured = {}
    expirations, headers = parse_expirations(featured), parse_headers(featured)
    deals = []
    for r in rows:
        appid = r["appid"]
        exp = expirations.get(appid)
        deals.append({
            "id": f"d_steam_{appid}",
            "store": "steam",
            "title": r["title"],
            "link": f"https://store.steampowered.com/app/{appid}/",
            # 検索結果の画像は小さいので、大きいヘッダー画像がわかるときはそちらを使う
            "image": headers.get(appid) or r["image"] or None,
            "price_original": r["price_original"],
            "price_sale": r["price_sale"],
            "discount": r["discount"],
            "is_free": False,
            "upcoming": False,
            "starts_at": None,
            "ends_at": to_iso(datetime.fromtimestamp(exp, JST)) if exp else None,
        })
    return deals
