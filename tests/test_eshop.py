import json
from datetime import datetime
from pathlib import Path

from fetcher.common import JST
from fetcher.eshop import parse

FIX = Path(__file__).parent / "fixtures"
NOW = datetime(2026, 10, 14, 12, 0, tzinfo=JST)


def item(**kw):
    base = {"nsuid": "70010000000001", "title": "Game", "price": 2860.0, "sprice": 2574.0,
            "sale_flg": "1", "ssdate": "2026-10-01 00:00:00", "sedate": "2026-11-05 23:59:59",
            "iurl": "abc"}
    base.update(kw)
    return {"result": {"items": [base]}}


def test_parse_only_sale_items():
    deals = parse(json.loads((FIX / "eshop_search.json").read_text(encoding="utf-8")), NOW)
    assert len(deals) >= 1
    for d in deals:
        assert d["price_sale"] < d["price_original"]
        assert d["ends_at"] > "2026-10-14T12:00:00+09:00"
        assert d["store"] == "eshop"


def test_discount_rounding():
    (d,) = parse(item(), NOW)
    assert d["discount"] == 10
    assert d["ends_at"] == "2026-11-05T23:59:59+09:00"
    assert d["starts_at"] == "2026-10-01T00:00:00+09:00"
    assert d["link"] == "https://store-jp.nintendo.com/item/software/D70010000000001"
    assert d["image"] == "https://img-eshop.cdn.nintendo.net/i/abc.jpg"
    assert d["id"] == "d_eshop_70010000000001"


def test_expired_sale_dropped():
    assert parse(item(sedate="2026-10-01 00:00:00"), NOW) == []


def test_not_on_sale_dropped():
    assert parse(item(sale_flg="0"), NOW) == []
    assert parse(item(sprice=None), NOW) == []


def test_duplicate_nsuid_dropped():
    data = item()
    data["result"]["items"].append(dict(data["result"]["items"][0]))
    assert len(parse(data, NOW)) == 1
