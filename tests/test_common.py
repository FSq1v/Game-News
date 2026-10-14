from fetcher.common import clean_text, parse_date, stable_id, to_iso


def test_stable_id_is_deterministic():
    a = stable_id("n", "https://a/1")
    assert a == stable_id("n", "https://a/1")
    assert len(a) == 14
    assert a != stable_id("n", "https://a/2")


def test_parse_date_rfc822():
    assert to_iso(parse_date("Tue, 14 Oct 2026 01:00:00 GMT")) == "2026-10-14T10:00:00+09:00"


def test_parse_date_iso_z():
    assert to_iso(parse_date("2026-10-14T01:00:00Z")) == "2026-10-14T10:00:00+09:00"


def test_parse_date_bad():
    assert parse_date("not a date") is None
    assert parse_date(None) is None


def test_clean_text():
    assert clean_text("<p>A&amp;B\n  C</p>", 3) == "A&B"
