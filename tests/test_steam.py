import json
from pathlib import Path

from fetcher.steam import parse_expirations, parse_search

FIX = Path(__file__).parent / "fixtures"


def search_items():
    return parse_search((FIX / "steam_search.html").read_text(encoding="utf-8"))


def test_parse_search_reads_prices():
    items = search_items()
    assert len(items) >= 10
    for it in items:
        assert it["discount"] > 0
        assert it["price_sale"] < it["price_original"]
        assert it["title"]
    sf6 = [it for it in items if it["appid"] == 1364780]
    if sf6:
        assert sf6[0]["discount"] == 60
        assert sf6[0]["price_original"] == 4990
        assert sf6[0]["price_sale"] == 1996


def test_parse_search_skips_no_discount():
    html = '''
    <a href="https://store.steampowered.com/app/10/X/" data-ds-appid="10" class="search_result_row">
      <span class="title">No sale</span>
      <div class="discount_block search_discount_block" data-discount="0"><div class="discount_final_price">¥1,000</div></div>
    </a>
    <a href="https://store.steampowered.com/app/20/Y/" data-ds-appid="20" class="search_result_row">
      <span class="title">Sale &amp; more</span>
      <div class="discount_block search_discount_block" data-discount="25"><div class="discount_pct">-25%</div>
      <div class="discount_prices"><div class="discount_original_price">¥2,000</div><div class="discount_final_price">¥1,500</div></div></div>
    </a>'''
    items = parse_search(html)
    assert [(i["appid"], i["title"], i["discount"], i["price_original"], i["price_sale"]) for i in items] == [
        (20, "Sale & more", 25, 2000, 1500)
    ]


def test_parse_expirations():
    data = json.loads((FIX / "steam_featured.json").read_text(encoding="utf-8"))
    exp = parse_expirations(data)
    first = data["specials"]["items"][0]
    assert exp[first["id"]] == first["discount_expiration"]


def test_parse_search_keeps_capsule_image():
    items = search_items()
    assert all(it["image"].startswith("https://") for it in items)
    assert "capsule_231x87" in items[0]["image"]


def test_parse_search_skips_zero_price():
    html = '''
    <a href="https://store.steampowered.com/app/30/Z/" data-ds-appid="30" class="search_result_row">
      <span class="title">Free now</span>
      <div class="discount_block search_discount_block" data-discount="100"><div class="discount_pct">-100%</div>
      <div class="discount_prices"><div class="discount_original_price">¥2,000</div><div class="discount_final_price">¥ 0</div></div></div>
    </a>'''
    assert parse_search(html) == []
