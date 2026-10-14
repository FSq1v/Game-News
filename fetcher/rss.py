"""ゲームメディアの RSS / Atom からニュースを取る。"""
import re

from defusedxml import ElementTree as ET

from .common import clean_text, http_get, parse_date, stable_id, to_iso

FEEDS = [
    # --- 国内ニュース ---
    {"url": "https://www.4gamer.net/rss/index.xml", "source": "4Gamer", "region": "jp"},
    {"url": "https://jp.ign.com/feed.xml", "source": "IGN Japan", "region": "jp"},
    {"url": "https://news.denfaminicogamer.jp/feed", "source": "電ファミニコゲーマー", "region": "jp"},
    {"url": "https://automaton-media.com/feed/", "source": "AUTOMATON", "region": "jp"},
    {"url": "https://gamebiz.jp/feed.rss", "source": "gamebiz", "region": "jp"},
    {"url": "https://www.gamespark.jp/rss20/index.rdf", "source": "Game*Spark", "region": "jp"},
    # --- ハード公式 ---
    {"url": "https://www.nintendo.com/jp/topics/c/feed/rss/", "source": "任天堂公式", "region": "official", "platform": "Switch"},
    {"url": "https://blog.ja.playstation.com/feed/", "source": "PlayStation Blog", "region": "official", "platform": "PS5"},
    {"url": "https://news.xbox.com/ja-jp/feed/", "source": "Xbox Wire Japan", "region": "official", "platform": "Xbox"},
    # --- 海外ニュース（タイトルを翻訳する） ---
    {"url": "https://www.gematsu.com/feed", "source": "Gematsu", "region": "global"},
    {"url": "https://www.pcgamer.com/rss/", "source": "PC Gamer", "region": "global"},
    {"url": "https://kotaku.com/rss", "source": "Kotaku", "region": "global"},
    {"url": "https://www.eurogamer.net/feed", "source": "Eurogamer", "region": "global"},
]

PLATFORM_PATTERNS = {
    "Switch": re.compile(r"switch|スイッチ|任天堂|nintendo", re.I),
    "PS5": re.compile(r"ps5|playstation 5|プレイステーション5", re.I),
    "PS4": re.compile(r"ps4|playstation 4|プレイステーション4", re.I),
    "PC": re.compile(r"\bpc\b|steam|epic games|windows", re.I),
    "Xbox": re.compile(r"xbox|game pass|ゲームパス", re.I),
}

ATOM = "{http://www.w3.org/2005/Atom}"
MEDIA = "{http://search.yahoo.com/mrss/}"
RSS1 = "{http://purl.org/rss/1.0/}"
DC = "{http://purl.org/dc/elements/1.1/}"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}"
_IMG_SRC = re.compile(r"<img[^>]+src=[\"']([^\"']+)", re.I)


def detect_platforms(text: str, default: str | None) -> list[str]:
    found = [default] if default else []
    for name, pattern in PLATFORM_PATTERNS.items():
        if name not in found and pattern.search(text):
            found.append(name)
    return found


def _find(item, *tags):
    # Element は子要素がないと False 扱いになるので、`or` でつながず None と比べる
    for tag in tags:
        el = item.find(tag)
        if el is not None:
            return el
    return None


def _text(item, *tags) -> str:
    el = _find(item, *tags)
    return (el.text or "").strip() if el is not None else ""


def _link(item) -> str:
    el = _find(item, "link", f"{RSS1}link")
    if el is not None and (el.text or "").strip():
        return el.text.strip()
    for el in item.findall(f"{ATOM}link"):
        if el.get("rel", "alternate") == "alternate" and el.get("href"):
            return el.get("href")
    return ""


def _image(item, description: str) -> str | None:
    for tag in (f"{MEDIA}content", f"{MEDIA}thumbnail"):
        for el in item.iter(tag):
            if el.get("url"):
                return el.get("url")
    enc = item.find("enclosure")
    if enc is not None and enc.get("type", "").startswith("image/") and enc.get("url"):
        return enc.get("url")
    m = _IMG_SRC.search(description or "")
    return m.group(1) if m else None


def parse_feed(xml: bytes, feed: dict, limit: int = 15) -> list[dict]:
    root = ET.fromstring(xml)
    items = (root.findall(".//item") or root.findall(f".//{RSS1}item")
             or root.findall(f".//{ATOM}entry"))
    news = []
    for item in items[:limit]:
        title = clean_text(_text(item, "title", f"{RSS1}title", f"{ATOM}title"))
        link = _link(item)
        if not title or not link:
            continue
        description = _text(item, "description", f"{RSS1}description",
                            f"{ATOM}summary", f"{ATOM}content")
        summary = clean_text(description, 120)
        published = parse_date(_text(item, "pubDate", f"{DC}date",
                                     f"{ATOM}published", f"{ATOM}updated"))
        body = _text(item, f"{CONTENT}encoded")
        news.append({
            "id": stable_id("n", link),
            "title": title,
            "link": link,
            "summary": summary,
            "source": feed["source"],
            "region": feed["region"],
            "platforms": detect_platforms(f"{title} {summary}", feed.get("platform")),
            "image": _image(item, f"{description} {body}"),
            "published_at": to_iso(published) if published else None,
        })
    return news


def fetch(feed: dict) -> list[dict]:
    return parse_feed(http_get(feed["url"]), feed)
