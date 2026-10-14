"""Nintendo eShop（日本）のセールを取る。

公式 API がないので、任天堂の検索サイト（search.nintendo.jp）が使っている検索 API を呼ぶ。
"""
import json
from datetime import datetime

from .common import JST, http_get, now_jst, to_iso

SEARCH_URL = "https://search.nintendo.jp/nintendo_soft/search.json?opt_sshow=1&opt_osale=1&limit=100&page={page}"


def _jst(value: str | None) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=JST)
    except (TypeError, ValueError):
        return None


def parse(data: dict, now: datetime) -> list[dict]:
    deals, seen = [], set()
    for it in data.get("result", {}).get("items", []):
        nsuid, price, sprice = it.get("nsuid"), it.get("price"), it.get("sprice")
        end = _jst(it.get("sedate"))
        if (it.get("sale_flg") != "1" or not nsuid or nsuid in seen
                or not price or sprice is None or sprice >= price or not end or end <= now):
            continue
        seen.add(nsuid)
        start = _jst(it.get("ssdate"))
        deals.append({
            "id": f"d_eshop_{nsuid}",
            "store": "eshop",
            "title": it.get("title", ""),
            "link": f"https://store-jp.nintendo.com/item/software/D{nsuid}",
            "image": f"https://img-eshop.cdn.nintendo.net/i/{it['iurl']}.jpg" if it.get("iurl") else None,
            "price_original": int(price),
            "price_sale": int(sprice),
            "discount": round((1 - sprice / price) * 100),
            "is_free": False,
            "upcoming": False,
            "starts_at": to_iso(start) if start else None,
            "ends_at": to_iso(end),
        })
    return deals


def fetch(pages: int = 3, limit: int = 60) -> list[dict]:
    now, deals, seen = now_jst(), [], set()
    for page in range(1, pages + 1):
        for d in parse(json.loads(http_get(SEARCH_URL.format(page=page))), now):
            if d["id"] not in seen:
                seen.add(d["id"])
                deals.append(d)
    # 割引率順にすると投げ売りの無名タイトルばかりになるので、検索 API の並び順のまま使う
    return deals[:limit]
