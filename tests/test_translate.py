import json
import urllib.error

from fetcher import translate as t


def fake_post(responses, calls):
    """DeepL への POST の代わり。呼ばれた中身を calls に残し、responses を順に返す"""
    def post(url, body, headers):
        calls.append({"url": url, "body": json.loads(body), "headers": headers})
        r = responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return json.dumps(r).encode()
    return post


def deepl_ok(texts):
    return {"translations": [{"detected_source_language": "EN", "text": f"訳:{x}"} for x in texts]}


def http_error(code):
    return urllib.error.HTTPError("https://api-free.deepl.com/v2/translate", code, "err", {}, None)


def test_no_key_translates_nothing(monkeypatch):
    monkeypatch.delenv("DEEPL_API_KEY", raising=False)
    calls = []
    monkeypatch.setattr(t, "_post", fake_post([], calls))
    assert t.translate_many(["Hello world"]) == [None]
    assert calls == []


def test_free_key_uses_free_endpoint_and_sends_ja(monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", "abc:fx")
    calls = []
    monkeypatch.setattr(t, "_post", fake_post([deepl_ok(["Hello", "World"])], calls))
    assert t.translate_many(["Hello", "World"]) == ["訳:Hello", "訳:World"]
    assert calls[0]["url"] == "https://api-free.deepl.com/v2/translate"
    assert calls[0]["body"] == {"text": ["Hello", "World"], "target_lang": "JA"}
    assert calls[0]["headers"]["Authorization"] == "DeepL-Auth-Key abc:fx"


def test_pro_key_uses_pro_endpoint(monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", "abc")
    calls = []
    monkeypatch.setattr(t, "_post", fake_post([deepl_ok(["Hello"])], calls))
    t.translate_many(["Hello"])
    assert calls[0]["url"] == "https://api.deepl.com/v2/translate"


def test_sends_in_batches_of_50(monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", "abc:fx")
    texts = [f"Headline {i}" for i in range(120)]
    calls = []
    monkeypatch.setattr(t, "_post", fake_post(
        [deepl_ok(texts[:50]), deepl_ok(texts[50:100]), deepl_ok(texts[100:])], calls))
    assert t.translate_many(texts) == [f"訳:{x}" for x in texts]
    assert [len(c["body"]["text"]) for c in calls] == [50, 50, 20]


def test_error_stops_and_leaves_rest_untranslated(monkeypatch, capsys):
    # 無料枠切れ（456）などで失敗したら、その回はそれ以上送らない。訳せなかったぶんは None
    monkeypatch.setenv("DEEPL_API_KEY", "abc:fx")
    texts = [f"Headline {i}" for i in range(120)]
    calls = []
    monkeypatch.setattr(t, "_post", fake_post([deepl_ok(texts[:50]), http_error(456)], calls))
    out = t.translate_many(texts)
    assert out[:50] == [f"訳:{x}" for x in texts[:50]]
    assert out[50:] == [None] * 70
    assert len(calls) == 2
    assert "456" in capsys.readouterr().err


def test_broken_response_is_none(monkeypatch):
    monkeypatch.setenv("DEEPL_API_KEY", "abc:fx")
    monkeypatch.setattr(t, "_post", fake_post([{"translations": [{"text": ""}]}], []))
    assert t.translate_many(["Hello"]) == [None]
