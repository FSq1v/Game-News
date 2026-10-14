import json
from datetime import datetime
from pathlib import Path

from fetcher.common import JST
from fetcher.epic import parse

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 14, 12, 0, tzinfo=JST)


def fixture():
    return json.loads((FIX / "epic_free.json").read_text(encoding="utf-8"))


def element(offers_key, discount, price=1980, decimals=0):
    return {"data": {"Catalog": {"searchStore": {"elements": [{
        "id": "abc", "title": "Game", "keyImages": [], "productSlug": None,
        "catalogNs": {"mappings": [{"pageSlug": "game-1", "pageType": "productHome"}]},
        "price": {"totalPrice": {"originalPrice": price, "currencyInfo": {"decimals": decimals}}},
        "promotions": {offers_key: [{"promotionalOffers": [{
            "startDate": "2026-10-15T15:00:00.000Z", "endDate": "2026-10-22T15:00:00.000Z",
            "discountSetting": {"discountPercentage": discount}}]}]},
    }]}}}}


def test_current_free():
    deals = [d for d in parse(fixture(), NOW) if not d["upcoming"]]
    assert sorted(d["title"] for d in deals) == ["Out of Sight", "TerraScape"]
    d = deals[0]
    assert d["is_free"] and d["store"] == "epic"
    assert d["price_sale"] == 0 and d["discount"] == 100
    assert d["ends_at"] == "2026-10-16T00:00:00+09:00"
    assert d["link"].startswith("https://store.epicgames.com/ja/p/")


def test_upcoming_free_from_fixture():
    up = [d for d in parse(fixture(), NOW) if d["upcoming"]]
    assert sorted(d["title"] for d in up) == ["Agent A - 偽装のパズル", "Bad Cheese"]
    assert up[0]["starts_at"] == "2026-10-16T00:00:00+09:00"


def test_ignores_paid_discount():
    assert parse(element("upcomingPromotionalOffers", 20), NOW) == []


def test_price_uses_decimals():
    d = parse(element("upcomingPromotionalOffers", 0, price=198000, decimals=2), NOW)[0]
    assert d["price_original"] == 1980
    assert d["link"] == "https://store.epicgames.com/ja/p/game-1"
    assert d["id"] == "d_epic_abc"
