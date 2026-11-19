import json

from fetcher import twitch as tw


def stream(gid, viewers):
    return {"game_id": gid, "game_name": f"g{gid}", "viewer_count": viewers}


def fake_api(pages, games):
    """Twitch API の代わり。streams は pages を順に返し、games は id で引いて返す"""
    calls = []

    def request(url, headers, data=None):
        calls.append(url)
        if url.startswith(tw.TOKEN_URL):
            return json.dumps({"access_token": "tok"}).encode()
        if url.startswith(tw.STREAMS_URL):
            i = sum(1 for c in calls if c.startswith(tw.STREAMS_URL)) - 1
            page = pages[i]
            body = {"data": page, "pagination": {"cursor": f"c{i}"} if i + 1 < len(pages) else {}}
            return json.dumps(body).encode()
        if url.startswith(tw.GAMES_URL):
            ids = [p.split("=", 1)[1] for p in url.split("?", 1)[1].split("&")]
            return json.dumps({"data": [games[i] for i in ids if i in games]}).encode()
        raise AssertionError(url)

    return request, calls


def game(gid, name, igdb="123"):
    return {"id": gid, "name": name, "box_art_url": f"https://img/{gid}-{{width}}x{{height}}.jpg", "igdb_id": igdb}


def test_fetch_sums_viewers_and_drops_non_games(monkeypatch):
    monkeypatch.setenv("TWITCH_CLIENT_ID", "id")
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "secret")
    pages = [[stream("1", 5000), stream("2", 9000), stream("1", 1000)], [stream("3", 700), stream("", 50)]]
    games = {"1": game("1", "Apex"), "2": game("2", "Just Chatting", igdb=""), "3": game("3", "Tetris")}
    request, calls = fake_api(pages, games)
    monkeypatch.setattr(tw, "_request", request)

    viewers, info = tw.fetch()

    assert viewers == {"1": 6000, "3": 700}  # 雑談（igdb_id なし）と game_id なしは除く
    assert info["1"] == {"name": "Apex", "box_art": "https://img/1-104x139.jpg"}
    assert sum(1 for c in calls if c.startswith(tw.STREAMS_URL)) == 2


def test_fetch_stops_at_max_pages(monkeypatch):
    monkeypatch.setenv("TWITCH_CLIENT_ID", "id")
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "secret")
    pages = [[stream("1", 100)] for _ in range(20)]
    request, calls = fake_api(pages, {"1": game("1", "A")})
    monkeypatch.setattr(tw, "_request", request)
    tw.fetch()
    assert sum(1 for c in calls if c.startswith(tw.STREAMS_URL)) == tw.MAX_PAGES


def test_enabled_needs_both_keys(monkeypatch):
    monkeypatch.setenv("TWITCH_CLIENT_ID", "id")
    monkeypatch.delenv("TWITCH_CLIENT_SECRET", raising=False)
    assert tw.enabled() is False
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "s")
    assert tw.enabled() is True
