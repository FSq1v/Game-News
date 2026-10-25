from datetime import datetime, timedelta

from fetcher import main as m
from fetcher.common import JST, to_iso

NOW = datetime(2026, 10, 14, 12, 0, tzinfo=JST)


def news(i, source="AUTOMATON", hours_ago=1, **kw):
    item = {"id": f"n_{i}", "title": f"t{i}", "link": f"https://x/{i}", "summary": "",
            "source": source, "region": "jp", "genre": "game", "platforms": [], "image": None,
            "published_at": to_iso(NOW - timedelta(hours=hours_ago))}
    item.update(kw)
    return item


def deal(i, store="steam", ends_in_hours=24):
    return {"id": f"d_{store}_{i}", "store": store, "title": f"g{i}", "link": f"https://y/{i}",
            "image": None, "price_original": 1000, "price_sale": 500, "discount": 50,
            "is_free": False, "upcoming": False, "starts_at": None,
            "ends_at": to_iso(NOW + timedelta(hours=ends_in_hours)) if ends_in_hours is not None else None}


def previous(news_items=(), deals=(), last_success_hours_ago=1, source_id="rss:AUTOMATON"):
    return {"news": list(news_items), "deals": list(deals), "sources": [
        {"id": source_id, "ok": True, "count": 1, "error": None,
         "last_success": to_iso(NOW - timedelta(hours=last_success_hours_ago))}]}


def test_failed_source_reuses_previous_within_24h():
    prev = previous([news(1, first_seen=to_iso(NOW))], last_success_hours_ago=5)
    out = m.merge({"rss:AUTOMATON": RuntimeError("boom")}, prev, NOW)
    assert [n["id"] for n in out["news"]] == ["n_1"]
    (src,) = out["sources"]
    assert src["ok"] is False and src["error"] == "RuntimeError: boom"
    assert src["last_success"] == to_iso(NOW - timedelta(hours=5))


def test_failed_source_dropped_after_24h():
    prev = previous([news(1, first_seen=to_iso(NOW))], last_success_hours_ago=25)
    out = m.merge({"rss:AUTOMATON": RuntimeError("boom")}, prev, NOW)
    assert out["news"] == []


def test_failed_deal_source_reuses_previous():
    prev = previous(deals=[deal(1)], source_id="steam")
    out = m.merge({"steam": RuntimeError("x")}, prev, NOW)
    assert [d["id"] for d in out["deals"]] == ["d_steam_1"]


def test_first_seen_kept_for_known_article():
    seen = to_iso(NOW - timedelta(hours=3))
    prev = previous([news(1, first_seen=seen, title="訳", title_original="orig", translated=True)])
    out = m.merge({"rss:AUTOMATON": [news(1, title="orig")]}, prev, NOW)
    (n,) = out["news"]
    assert n["first_seen"] == seen
    assert (n["title"], n["title_original"], n["translated"]) == ("訳", "orig", True)


def test_new_article_first_seen_is_now():
    out = m.merge({"rss:AUTOMATON": [news(1)]}, m.empty_data(), NOW)
    assert out["news"][0]["first_seen"] == to_iso(NOW)


def test_future_published_at_falls_back_to_first_seen():
    out = m.merge({"rss:AUTOMATON": [news(1, hours_ago=-5), news(2, published_at=None)]},
                  m.empty_data(), NOW)
    assert all(n["published_at"] == to_iso(NOW) for n in out["news"])


def test_news_sorted_newest_first():
    out = m.merge({"rss:AUTOMATON": [news(1, hours_ago=5), news(2, hours_ago=1)]},
                  m.empty_data(), NOW)
    assert [n["id"] for n in out["news"]] == ["n_2", "n_1"]


def test_old_news_dropped_after_72h():
    out = m.merge({"rss:AUTOMATON": [news(1, hours_ago=73), news(2, hours_ago=71)]},
                  m.empty_data(), NOW)
    assert [n["id"] for n in out["news"]] == ["n_2"]


def test_news_capped_at_150_per_genre():
    items = [news(i, hours_ago=i / 10) for i in range(250)]
    out = m.merge({"rss:AUTOMATON": items}, m.empty_data(), NOW)
    assert len(out["news"]) == m.NEWS_MAX_PER_GENRE == 150


def test_duplicate_news_id_kept_once():
    out = m.merge({"rss:A": [news(1, source="A")], "rss:B": [news(1, source="B")]},
                  m.empty_data(), NOW)
    assert len(out["news"]) == 1


def test_expired_deal_dropped():
    out = m.merge({"steam": [deal(1, ends_in_hours=-1), deal(2), deal(3, ends_in_hours=None)]},
                  m.empty_data(), NOW)
    assert [d["id"] for d in out["deals"]] == ["d_steam_2", "d_steam_3"]


def test_sources_report_counts():
    out = m.merge({"steam": [deal(1), deal(2)], "epic": []}, m.empty_data(), NOW)
    by_id = {s["id"]: s for s in out["sources"]}
    assert by_id["steam"] == {"id": "steam", "ok": True, "count": 2, "error": None,
                              "last_success": to_iso(NOW), "genre": "game"}
    assert by_id["epic"]["count"] == 0
    assert out["updated_at"] == to_iso(NOW)


def test_load_previous_missing_or_broken(tmp_path):
    assert m.load_previous(tmp_path / "none.json") == m.empty_data()
    broken = tmp_path / "broken.json"
    broken.write_text("{", encoding="utf-8")
    assert m.load_previous(broken) == m.empty_data()


def test_main_all_failed_returns_1(tmp_path, monkeypatch):
    def boom():
        raise RuntimeError("down")
    monkeypatch.setattr(m, "SOURCES", [("steam", boom), ("epic", boom)])
    out = tmp_path / "news.json"
    assert m.main(out) == 1
    assert not out.exists()


def test_main_writes_file(tmp_path, monkeypatch):
    monkeypatch.setattr(m, "SOURCES", [("steam", lambda: [deal(1, ends_in_hours=10_000)])])
    monkeypatch.setattr(m, "apply_translations", lambda items: None)
    out = tmp_path / "news.json"
    assert m.main(out) == 0
    assert '"d_steam_1"' in out.read_text(encoding="utf-8")


def test_apply_translations_only_new_global(monkeypatch):
    calls = []
    monkeypatch.setattr(m, "to_japanese", lambda t: calls.append(t) or f"訳:{t}")
    items = [news(1, region="global", title="Hello world"),
             news(2, region="jp", title="こんにちは"),
             news(3, region="global", title="done", translated=False)]
    m.apply_translations(items)
    assert calls == ["Hello world"]
    assert (items[0]["title"], items[0]["title_original"], items[0]["translated"]) == (
        "訳:Hello world", "Hello world", True)
    assert "translated" not in items[1]


def test_apply_translations_failure_retries_next_time(monkeypatch):
    monkeypatch.setattr(m, "to_japanese", lambda t: None)
    items = [news(1, region="global", title="Hello world")]
    m.apply_translations(items)
    assert items[0]["title"] == "Hello world" and "translated" not in items[0]


def test_apply_translations_skips_non_english(monkeypatch):
    monkeypatch.setattr(m, "to_japanese", lambda t: 1 / 0)
    items = [news(1, region="global", title="PS5 版")]
    m.apply_translations(items)
    assert items[0]["translated"] is False


def test_apply_translations_capped(monkeypatch):
    monkeypatch.setattr(m, "to_japanese", lambda t: "訳")
    items = [news(i, region="global", title="Hello world") for i in range(50)]
    m.apply_translations(items)
    assert sum(1 for n in items if n.get("translated")) == 40


def test_cap_is_per_genre(monkeypatch):
    monkeypatch.setattr(m, "NEWS_MAX_PER_GENRE", 2)
    game = [news(i, hours_ago=1) for i in range(5)]
    ai = [news(f"a{i}", source="AI src", hours_ago=10, genre="ai") for i in range(3)]
    out = m.merge({"rss:AUTOMATON": game, "rss:AI src": ai}, m.empty_data(), NOW)
    genres = [n["genre"] for n in out["news"]]
    assert genres.count("game") == 2 and genres.count("ai") == 2


def test_previous_item_without_genre_becomes_game():
    old = news(1, first_seen=to_iso(NOW))
    del old["genre"]
    out = m.merge({"rss:AUTOMATON": RuntimeError("x")}, previous([old]), NOW)
    assert out["news"][0]["genre"] == "game"


def test_source_status_has_genre(monkeypatch):
    monkeypatch.setattr(m, "SOURCE_GENRES", {"rss:AI src": "ai"})
    out = m.merge({"rss:AI src": [], "steam": RuntimeError("x")}, m.empty_data(), NOW)
    assert {s["id"]: s["genre"] for s in out["sources"]} == {"rss:AI src": "ai", "steam": "game"}
