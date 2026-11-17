from datetime import datetime

from fetcher import trends as tr
from fetcher.common import JST

NOW = datetime(2026, 11, 17, 12, 0, tzinfo=JST)


def art(i, title, source="4Gamer", day="2026-11-17", genre="game"):
    return {"id": f"n_{i}", "title": title, "link": f"https://x/{i}", "source": source,
            "genre": genre, "first_seen": f"{day}T09:00:00+09:00",
            "published_at": f"{day}T09:00:00+09:00"}


# ---------- ゲーム名の取り出し ----------

def test_extract_names_from_brackets():
    assert tr.extract_names("『モンスターハンターワイルズ』の新情報、『FF7』も") == ["モンスターハンターワイルズ", "FF7"]


def test_extract_names_skips_too_long_or_empty():
    assert tr.extract_names("『』と『" + "あ" * 41 + "』") == []


def test_name_key_ignores_width_case_and_spaces():
    assert tr.name_key("ＦＦ７ リバース") == tr.name_key("ff7リバース")


# ---------- ニュースの話題量 ----------

def test_record_mentions_counts_each_article_once_and_only_game():
    hist = tr.empty_history()
    news = [art(1, "『Apex』新シーズン『Apex』"), art(2, "『GPT-6』", genre="ai")]
    tr.record_mentions(hist, news)
    tr.record_mentions(hist, news)  # 同じ記事をもう一度見ても増えない
    key = tr.name_key("Apex")
    assert list(hist["mentions"][key]["articles"]) == ["n_1"]
    assert tr.name_key("GPT-6") not in hist["mentions"]


def test_buzz_ranks_growth_and_needs_two_sources():
    hist = tr.empty_history()
    news = [
        # 伸びている：直近 3 日に 3 社
        art(1, "『Rising』", "4Gamer"), art(2, "『Rising』", "AUTOMATON"), art(3, "『Rising』", "Gematsu", "2026-11-16"),
        # ずっと多い：直近 3 本、前の 7 日も 7 本 → 伸びていない
        *[art(10 + i, "『Steady』", s) for i, s in enumerate(["4Gamer", "AUTOMATON", "Kotaku"])],
        *[art(20 + i, "『Steady』", "4Gamer", f"2026-11-{13 - i:02d}") for i in range(7)],
        # 1 社だけ
        art(30, "『Solo』", "4Gamer"), art(31, "『Solo』", "4Gamer"),
    ]
    tr.record_mentions(hist, news)
    ranking = tr.buzz_ranking(hist, news, NOW)
    names = [r["name"] for r in ranking]
    assert names[0] == "Rising"
    assert "Solo" not in names
    rising = ranking[0]
    assert (rising["recent"], rising["prev"]) == (3, 0)
    assert sorted(rising["sources"]) == ["4Gamer", "AUTOMATON", "Gematsu"]
    assert rising["articles"][0]["link"].startswith("https://x/")
    steady = next(r for r in ranking if r["name"] == "Steady")
    assert steady["score"] < rising["score"]


def test_prune_drops_old_mentions():
    hist = tr.empty_history()
    tr.record_mentions(hist, [art(1, "『Old』", day="2026-10-01"), art(2, "『New』")])
    tr.prune(hist, NOW)
    assert tr.name_key("Old") not in hist["mentions"]
    assert tr.name_key("New") in hist["mentions"]


# ---------- Twitch ----------

def test_record_twitch_averages_per_day():
    hist = tr.empty_history()
    games = {"1": {"name": "A", "box_art": "u"}, "2": {"name": "B", "box_art": "v"}}
    tr.record_twitch(hist, {"1": 1000, "2": 500}, games, NOW)
    tr.record_twitch(hist, {"1": 3000}, games, NOW)  # 2 回目は B がいない → 0 とみなす
    day = hist["twitch"]["2026-11-17"]
    assert day["runs"] == 2
    assert tr.daily_average(day, "1") == 2000
    assert tr.daily_average(day, "2") == 250


def test_twitch_ranking_growth_vs_previous_days():
    hist = tr.empty_history()
    games = {"1": {"name": "Up", "box_art": "u"}, "2": {"name": "Flat", "box_art": "v"}}
    for d in ("2026-11-14", "2026-11-15", "2026-11-16"):
        tr.record_twitch(hist, {"1": 1000, "2": 5000}, games, datetime.fromisoformat(f"{d}T12:00:00+09:00"))
    tr.record_twitch(hist, {"1": 3000, "2": 5000}, games, NOW)
    ranking = tr.twitch_ranking(hist)
    assert [r["name"] for r in ranking][:2] == ["Up", "Flat"]
    assert ranking[0]["viewers"] == 3000 and ranking[0]["prev_viewers"] == 1000
    assert round(ranking[0]["growth"], 2) == 2.0
    assert ranking[1]["growth"] == 0


def test_twitch_ranking_without_history_orders_by_viewers():
    hist = tr.empty_history()
    games = {"1": {"name": "Small", "box_art": "u"}, "2": {"name": "Big", "box_art": "v"}}
    tr.record_twitch(hist, {"1": 1500, "2": 9000}, games, NOW)
    ranking = tr.twitch_ranking(hist)
    assert [r["name"] for r in ranking] == ["Big", "Small"]
    assert ranking[0]["growth"] is None


# ---------- 書き出し（fetcher/main.py） ----------

def test_update_trends_writes_file_without_twitch(tmp_path, monkeypatch):
    import json
    from fetcher import main as m
    monkeypatch.delenv("TWITCH_CLIENT_ID", raising=False)
    path = tmp_path / "trends.json"
    news = [art(1, "『Rising』", "4Gamer"), art(2, "『Rising』", "AUTOMATON")]
    m.update_trends(news, NOW, path)
    out = json.loads(path.read_text(encoding="utf-8"))
    assert out["buzz"][0]["name"] == "Rising"
    assert out["twitch"] == [] and out["twitch_enabled"] is False
    # 2 回目は前回の記録を読んで足す
    m.update_trends([art(3, "『Rising』", "Gematsu")], NOW, path)
    out = json.loads(path.read_text(encoding="utf-8"))
    assert out["buzz"][0]["recent"] == 3


def test_update_trends_twitch_failure_keeps_going(tmp_path, monkeypatch):
    import json
    from fetcher import main as m
    monkeypatch.setenv("TWITCH_CLIENT_ID", "id")
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "s")
    monkeypatch.setattr(m.twitch, "fetch", lambda: 1 / 0)
    path = tmp_path / "trends.json"
    m.update_trends([art(1, "『A』"), art(2, "『A』", "Kotaku")], NOW, path)
    out = json.loads(path.read_text(encoding="utf-8"))
    assert out["twitch_enabled"] is True and out["twitch"] == []
    assert out["buzz"][0]["name"] == "A"


def test_update_trends_records_twitch(tmp_path, monkeypatch):
    import json
    from fetcher import main as m
    monkeypatch.setenv("TWITCH_CLIENT_ID", "id")
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "s")
    monkeypatch.setattr(m.twitch, "fetch", lambda: ({"1": 4000}, {"1": {"name": "Apex", "box_art": "u"}}))
    path = tmp_path / "trends.json"
    m.update_trends([], NOW, path)
    out = json.loads(path.read_text(encoding="utf-8"))
    assert out["twitch"][0]["name"] == "Apex" and out["twitch"][0]["viewers"] == 4000
