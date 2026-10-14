import json
import urllib.parse
from pathlib import Path

from fetcher.psstore import CATEGORY_ID, build_url, parse, parse_price

FIX = Path(__file__).parent / "fixtures"


def product(**price):
    base = {"basePrice": "¥2,000", "discountedPrice": "¥1,000", "discountText": "-50%",
            "isFree": False, "isTiedToSubscription": False}
    base.update(price)
    return {"id": "JP0001-X", "name": "Game", "media": [
        {"role": "SCREENSHOT", "type": "IMAGE", "url": "https://img/s.jpg"},
        {"role": "MASTER", "type": "IMAGE", "url": "https://img/m.png"}], "price": base}


def wrap(*products):
    return {"data": {"categoryGridRetrieve": {"products": list(products)}}}


def test_parse_price():
    assert parse_price("¥8,470") == 8470
    assert parse_price("無料") is None
    assert parse_price(None) is None


def test_parse_products_from_fixture():
    deals = parse(json.loads((FIX / "ps_category.json").read_text(encoding="utf-8")))
    assert len(deals) >= 1
    for d in deals:
        assert 0 < d["discount"] < 100
        assert d["price_sale"] < d["price_original"]
        assert d["store"] == "ps" and d["ends_at"] is None
        assert d["link"].startswith("https://store.playstation.com/ja-jp/product/")


def test_parse_minimal_product():
    (d,) = parse(wrap(product()))
    assert (d["id"], d["discount"], d["price_original"], d["price_sale"], d["image"]) == (
        "d_ps_JP0001-X", 50, 2000, 1000, "https://img/m.png")


def test_skips_subscription_price():
    assert parse(wrap(product(isTiedToSubscription=True))) == []


def test_skips_without_discount():
    assert parse(wrap(product(discountText=None, discountedPrice="¥2,000"))) == []


def test_build_url_contains_category_and_page():
    url = urllib.parse.unquote(build_url(30, 30))
    assert CATEGORY_ID in url
    assert '"offset":30' in url and '"size":30' in url
    assert "operationName=categoryGridRetrieve" in url


def test_skips_zero_price():
    assert parse(wrap(product(discountedPrice="¥0", discountText="-100%"))) == []
