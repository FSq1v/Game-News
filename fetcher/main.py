"""全ソースを集めて、前回データとマージし、data/news.json を書く。"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from . import epic, eshop, psstore, rss, steam
from .common import now_jst, parse_date, to_iso
from .translate import to_japanese

OUTPUT = Path("data/news.json")
NEWS_MAX_PER_GENRE = 150
NEWS_MAX_AGE = timedelta(hours=72)
REUSE_LIMIT = timedelta(hours=24)
TRANSLATE_PER_RUN = 40
_NEEDS_TRANSLATION = re.compile(r"[a-zA-Z]{5,}")

SOURCES: list[tuple[str, Callable[[], list[dict]]]] = [
    *[(f"rss:{f['source']}", lambda f=f: rss.fetch(f)) for f in rss.FEEDS],
    ("steam", steam.fetch),
    ("epic", epic.fetch),
    ("ps", psstore.fetch),
    ("eshop", eshop.fetch),
]
# ソースの id -> ジャンル。RSS は FEEDS の値、セールなどそれ以外は "game"
SOURCE_GENRES = {f"rss:{f['source']}": f.get("genre", "game") for f in rss.FEEDS}


def empty_data() -> dict:
    return {"news": [], "deals": [], "sources": []}


def load_previous(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return {key: data.get(key) or [] for key in ("news", "deals", "sources")}
    except (OSError, ValueError, AttributeError):
        return empty_data()


def _source_of(item: dict) -> str:
    """項目がどのソース由来かを SOURCES の id で返す。"""
    return item["store"] if "store" in item else f"rss:{item['source']}"


def merge(results: dict[str, list[dict] | Exception], previous: dict, now: datetime) -> dict:
    prev_sources = {s["id"]: s for s in previous.get("sources", [])}
    prev_items = previous.get("news", []) + previous.get("deals", [])
    prev_news = {n["id"]: n for n in previous.get("news", [])}

    sources, items = [], []
    for source_id, result in results.items():
        if isinstance(result, Exception):
            last = prev_sources.get(source_id, {}).get("last_success")
            last_dt = parse_date(last)
            # 失敗したソースは、最後に成功してから24時間までは前回のデータを出し続ける
            if last_dt and now - last_dt <= REUSE_LIMIT:
                items += [i for i in prev_items if _source_of(i) == source_id]
            sources.append({"id": source_id, "ok": False, "count": 0,
                            "error": f"{type(result).__name__}: {result}", "last_success": last,
                            "genre": SOURCE_GENRES.get(source_id, "game")})
        else:
            items += result
            sources.append({"id": source_id, "ok": True, "count": len(result),
                            "error": None, "last_success": to_iso(now),
                            "genre": SOURCE_GENRES.get(source_id, "game")})

    news, deals, seen = [], [], set()
    for item in items:
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        (deals if "store" in item else news).append(item)

    merged_news = []
    for n in news:
        n = dict(n)
        n.setdefault("genre", "game")  # ジャンルが付く前の古いデータは game 扱い
        old = prev_news.get(n["id"], {})
        n["first_seen"] = old.get("first_seen") or n.get("first_seen") or to_iso(now)
        for key in ("title", "title_original", "translated"):
            if key in old and "translated" in old:
                n[key] = old[key]
        published = parse_date(n.get("published_at"))
        if published is None or published > now:
            n["published_at"] = n["first_seen"]
        if now - parse_date(n["published_at"]) <= NEWS_MAX_AGE:
            merged_news.append(n)
    merged_news.sort(key=lambda n: n["published_at"], reverse=True)

    # 上限はジャンルごと（新しい順は保つ）
    counts: dict[str, int] = {}
    capped = []
    for n in merged_news:
        counts[n["genre"]] = counts.get(n["genre"], 0) + 1
        if counts[n["genre"]] <= NEWS_MAX_PER_GENRE:
            capped.append(n)

    live_deals = [d for d in deals if not d.get("ends_at") or parse_date(d["ends_at"]) > now]

    return {"updated_at": to_iso(now), "sources": sources,
            "news": capped, "deals": live_deals}


def apply_translations(news: list[dict]) -> None:
    done = 0
    for n in news:
        if n.get("region") != "global" or "translated" in n:
            continue
        if not _NEEDS_TRANSLATION.search(n["title"]):
            n["translated"] = False
            continue
        if done >= TRANSLATE_PER_RUN:
            continue
        done += 1
        translated = to_japanese(n["title"])
        # 失敗したときはキーを付けずにおき、次の実行でもう一度訳す
        if translated:
            n["title_original"], n["title"], n["translated"] = n["title"], translated, True


def _run(fn: Callable[[], list[dict]]) -> list[dict] | Exception:
    try:
        return fn()
    except Exception as e:  # ソース1つの失敗で全体を止めない
        return e


def main(path: Path = OUTPUT) -> int:
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {sid: pool.submit(_run, fn) for sid, fn in SOURCES}
    results = {sid: f.result() for sid, f in futures.items()}
    for sid, r in results.items():
        status = f"ERROR {type(r).__name__}: {r}" if isinstance(r, Exception) else f"{len(r)} items"
        print(f"{sid}: {status}")
    if all(isinstance(r, Exception) for r in results.values()):
        print("All sources failed; news.json was not updated.")
        return 1
    data = merge(results, load_previous(path), now_jst())
    apply_translations(data["news"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {len(data['news'])} news and {len(data['deals'])} deals to {path}")
    return 0
