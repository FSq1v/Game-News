"""Epic Games Store の無料配布（今週・来週）を取る。"""
import json
from datetime import datetime

from .common import http_get, now_jst, parse_date, to_iso

URL = (
    "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions"
    "?locale=ja&country=JP&allowCountries=JP"
)
IMAGE_TYPES = ("OfferImageWide", "DieselStoreFrontWide", "Thumbnail")


def _free_offer(groups: list, now: datetime, upcoming: bool) -> tuple | None:
    """無料（discountPercentage == 0）のオファーの (開始, 終了) を返す。"""
    for group in groups or []:
        for offer in group.get("promotionalOffers", []):
            if offer.get("discountSetting", {}).get("discountPercentage") != 0:
                continue
            start, end = parse_date(offer.get("startDate")), parse_date(offer.get("endDate"))
            if not start or not end or end <= now:
                continue
            if upcoming or start <= now:
                return start, end
    return None


def _link(el: dict) -> str:
    mappings = ((el.get("catalogNs") or {}).get("mappings") or []) + (el.get("offerMappings") or [])
    for m in mappings:
        if m.get("pageSlug"):
            return f"https://store.epicgames.com/ja/p/{m['pageSlug']}"
    if el.get("productSlug"):
        return f"https://store.epicgames.com/ja/p/{el['productSlug'].split('/')[0]}"
    return "https://store.epicgames.com/ja/free-games"


def _image(el: dict) -> str | None:
    images = {img.get("type"): img.get("url") for img in el.get("keyImages", [])}
    return next((images[t] for t in IMAGE_TYPES if images.get(t)), None)


def parse(data: dict, now: datetime) -> list[dict]:
    elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
    deals = []
    for el in elements:
        promotions = el.get("promotions") or {}
        current = _free_offer(promotions.get("promotionalOffers"), now, upcoming=False)
        upcoming = None if current else _free_offer(
            promotions.get("upcomingPromotionalOffers"), now, upcoming=True)
        offer = current or upcoming
        if not offer or not el.get("title"):
            continue
        total = el.get("price", {}).get("totalPrice", {})
        decimals = total.get("currencyInfo", {}).get("decimals", 0)
        deals.append({
            "id": f"d_epic_{el['id']}",
            "store": "epic",
            "title": el["title"],
            "link": _link(el),
            "image": _image(el),
            "price_original": total.get("originalPrice", 0) // (10 ** decimals),
            "price_sale": 0,
            "discount": 100,
            "is_free": True,
            "upcoming": current is None,
            "starts_at": to_iso(offer[0]),
            "ends_at": to_iso(offer[1]),
        })
    return deals


def fetch() -> list[dict]:
    return parse(json.loads(http_get(URL)), now_jst())
