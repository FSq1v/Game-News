from pathlib import Path

from fetcher.common import stable_id
from fetcher.rss import detect_platforms, parse_feed

FIX = Path(__file__).parent / "fixtures"
FEED = {"url": "https://example.com/rss", "source": "Sample", "region": "jp"}


def rss_items():
    return parse_feed((FIX / "rss_sample.xml").read_bytes(), FEED)


def atom_items():
    return parse_feed((FIX / "atom_sample.xml").read_bytes(), FEED)


def test_parse_rss_gets_all_items():
    items = rss_items()
    assert len(items) == 3
    assert items[0]["title"] == "『テスト』発売決定 & 新情報"
    assert items[0]["image"] == "https://example.com/a1.jpg"
    assert items[0]["summary"] == "本文 その1"
    assert items[0]["published_at"] == "2026-10-14T10:00:00+09:00"
    assert items[0]["source"] == "Sample" and items[0]["region"] == "jp"


def test_parse_rss_image_fallbacks():
    items = rss_items()
    assert items[1]["image"] == "https://example.com/a2.png"
    assert items[2]["image"] == "https://example.com/a3.jpg"


def test_parse_rss_missing_pubdate():
    assert rss_items()[2]["published_at"] is None


def test_parse_atom_link_href():
    items = atom_items()
    assert [i["link"] for i in items] == ["https://example.org/e1", "https://example.org/e2"]
    assert items[0]["published_at"] == "2026-10-14T10:00:00+09:00"
    assert items[1]["published_at"] == "2026-10-13T21:00:00+09:00"


def test_id_from_link():
    item = rss_items()[0]
    assert item["id"] == stable_id("n", item["link"])


def test_limit():
    assert len(parse_feed((FIX / "rss_sample.xml").read_bytes(), FEED, limit=2)) == 2


def test_default_platform_added():
    items = parse_feed((FIX / "rss_sample.xml").read_bytes(), dict(FEED, platform="PS5"))
    assert "PS5" in items[0]["platforms"]


def test_detect_platforms_pc_word():
    assert detect_platforms("New PC port", None) == ["PC"]
    assert "PC" not in detect_platforms("topcoat", None)


def test_parse_rdf_rss10():
    items = parse_feed((FIX / "rdf_sample.xml").read_bytes(), FEED)
    assert len(items) == 1
    item = items[0]
    assert item["title"] == "RDF記事"
    assert item["link"] == "https://example.net/r1"
    assert item["published_at"] == "2026-10-14T09:30:00+09:00"
    assert item["image"] == "https://example.net/r1.jpg"
