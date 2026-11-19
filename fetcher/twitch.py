"""Twitch の配信から、ゲームごとの視聴者数を取る（Helix API）。

キーは環境変数 TWITCH_CLIENT_ID / TWITCH_CLIENT_SECRET（GitHub Actions では Secrets から渡す）。
視聴者の多い配信から順に最大 MAX_PAGES × 100 本を見て、ゲームごとに視聴者数を足す。
「Just Chatting」や「Music」のようなゲームでないカテゴリは IGDB の id を持たないので、それで除く。
"""
import json
import os
import urllib.parse
import urllib.request

from .common import USER_AGENT

TOKEN_URL = "https://id.twitch.tv/oauth2/token"
STREAMS_URL = "https://api.twitch.tv/helix/streams"
GAMES_URL = "https://api.twitch.tv/helix/games"
MAX_PAGES = 10
TOP_GAMES = 100  # ゲームの情報を引くのは、視聴者の多い順にこの数まで（/games は 1 回 100 件まで）


def enabled() -> bool:
    return bool(os.environ.get("TWITCH_CLIENT_ID", "").strip() and os.environ.get("TWITCH_CLIENT_SECRET", "").strip())


def _request(url: str, headers: dict, data: bytes | None = None) -> bytes:
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT, **headers},
                                 method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=15) as res:
        return res.read()


def _token(client_id: str, secret: str) -> str:
    body = urllib.parse.urlencode({"client_id": client_id, "client_secret": secret,
                                   "grant_type": "client_credentials"}).encode()
    data = json.loads(_request(TOKEN_URL, {"Content-Type": "application/x-www-form-urlencoded"}, body))
    return data["access_token"]


def fetch() -> tuple[dict[str, int], dict[str, dict]]:
    """(ゲーム id → 視聴者数の合計, ゲーム id → {name, box_art}) を返す。ゲームでないカテゴリは入れない"""
    client_id = os.environ["TWITCH_CLIENT_ID"].strip()
    headers = {"Client-Id": client_id,
               "Authorization": f"Bearer {_token(client_id, os.environ['TWITCH_CLIENT_SECRET'].strip())}"}

    viewers: dict[str, int] = {}
    cursor = ""
    for _ in range(MAX_PAGES):
        url = f"{STREAMS_URL}?first=100" + (f"&after={urllib.parse.quote(cursor)}" if cursor else "")
        data = json.loads(_request(url, headers))
        for s in data.get("data", []):
            gid = s.get("game_id") or ""
            if gid:
                viewers[gid] = viewers.get(gid, 0) + int(s.get("viewer_count") or 0)
        cursor = (data.get("pagination") or {}).get("cursor") or ""
        if not cursor:
            break

    top = sorted(viewers, key=viewers.get, reverse=True)[:TOP_GAMES]
    info: dict[str, dict] = {}
    if top:
        url = f"{GAMES_URL}?" + "&".join(f"id={urllib.parse.quote(g)}" for g in top)
        for g in json.loads(_request(url, headers)).get("data", []):
            if not g.get("igdb_id"):
                continue  # Just Chatting や Music など、ゲームでないカテゴリ
            box = (g.get("box_art_url") or "").replace("{width}", "104").replace("{height}", "139")
            info[g["id"]] = {"name": g["name"], "box_art": box}
    return {gid: v for gid, v in viewers.items() if gid in info}, info
