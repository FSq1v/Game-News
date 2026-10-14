"""PlayStation Store の「すべてのセール」を取る。

公式 API がないので、ストアのページが内部で使っている GraphQL（persisted query）を呼ぶ。
PS 側の更新で QUERY_HASH が変わると取れなくなるので、そのときはこの値を更新する。
"""
import json
import re
import urllib.parse

from .common import http_get

CATEGORY_ID = "3f772501-f6f8-49b7-abac-874a88ca4897"  # すべてのセール（cat.gma.AllDeals）
QUERY_HASH = "88c0b9a1273c6d320c51cd73e390924e21ae28bf09f01cde8b84b1034b16cd03"  # categoryGridRetrieve
API = "https://web.np.playstation.com/api/graphql/v1/op"
HEADERS = {"x-psn-store-locale-override": "ja-JP", "content-type": "application/json"}
IMAGE_ROLES = ("MASTER", "GAMEHUB_COVER_ART")

_DIGITS = re.compile(r"\d+")


def build_url(offset: int, size: int) -> str:
    variables = {"id": CATEGORY_ID, "pageArgs": {"size": size, "offset": offset},
                 "sortBy": None, "filterBy": [], "facetOptions": []}
    extensions = {"persistedQuery": {"version": 1, "sha256Hash": QUERY_HASH}}
    query = urllib.parse.urlencode({
        "operationName": "categoryGridRetrieve",
        "variables": json.dumps(variables, separators=(",", ":")),
        "extensions": json.dumps(extensions, separators=(",", ":")),
    })
    return f"{API}?{query}"


def parse_price(text: str | None) -> int | None:
    digits = "".join(_DIGITS.findall(text or ""))
    return int(digits) if digits else None


def _image(media: list) -> str | None:
    images = [m for m in media or [] if m.get("type") == "IMAGE" and m.get("url")]
    for role in IMAGE_ROLES:
        for m in images:
            if m.get("role") == role:
                return m["url"]
    return images[0]["url"] if images else None


def parse(data: dict) -> list[dict]:
    products = (data.get("data") or {}).get("categoryGridRetrieve", {}).get("products") or []
    deals = []
    for p in products:
        price = p.get("price") or {}
        # PS Plus 加入者限定の価格は誰でも買える値段ではないので除く
        if price.get("isTiedToSubscription") or not price.get("discountText"):
            continue
        original = parse_price(price.get("basePrice"))
        sale = parse_price(price.get("discountedPrice"))
        discount = parse_price(price.get("discountText"))
        if not original or not sale or sale >= original or not discount:
            continue
        deals.append({
            "id": f"d_ps_{p['id']}",
            "store": "ps",
            "title": p.get("name", ""),
            "link": f"https://store.playstation.com/ja-jp/product/{p['id']}",
            "image": _image(p.get("media")),
            "price_original": original,
            "price_sale": sale,
            "discount": discount,
            "is_free": False,
            "upcoming": False,
            "starts_at": None,
            "ends_at": None,
        })
    return deals


def fetch(limit: int = 60) -> list[dict]:
    deals, size = [], 30
    for offset in range(0, limit, size):
        deals.extend(parse(json.loads(http_get(build_url(offset, size), HEADERS))))
    return deals[:limit]
