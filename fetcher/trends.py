"""「最近伸びているゲーム」の集計。ネットにはつながず、記録（data/trends.json の history）と計算だけをする。

伸びは 2 つの面から見る。
- ニュースの話題量：ゲームのニュースのタイトルに『』で出てきた名前を、記事ごとに 1 回数える。
  直近 3 日の本数を、その前の 7 日の本数（3 日ぶんに直したもの）と比べる。
- Twitch の視聴者数：取得のたびの合計視聴者数を日ごとに平均し、最新の日を前の 7 日の平均と比べる。
どちらも日ごとの記録が要るので、history に 14 日ぶん残す。
"""
import re
import unicodedata
from datetime import date, datetime, timedelta

KEEP_DAYS = 14
RECENT_DAYS = 3
PREV_DAYS = 7
TOP = 10

_NAME = re.compile(r"『([^』]{1,40})』")


def empty_history() -> dict:
    return {"mentions": {}, "twitch": {}, "twitch_games": {}}


# ---------- ゲーム名 ----------

def extract_names(title: str) -> list[str]:
    """タイトルの『』の中身を、出てきた順に重複なしで返す"""
    out: list[str] = []
    for m in _NAME.findall(title or ""):
        name = m.strip()
        if name and name not in out:
            out.append(name)
    return out


def name_key(name: str) -> str:
    """表記ゆれ（全角半角・大文字小文字・空白）をならした比較用の名前"""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", name)).lower()


def _day(iso: str) -> str:
    # first_seen は +09:00 付きなので、先頭 10 文字が日本時間の日付になる
    return (iso or "")[:10]


# ---------- ニュースの話題量 ----------

def record_mentions(hist: dict, news: list[dict]) -> None:
    """ゲームのニュースに出てきた名前を、記事ごとに 1 回だけ記録する"""
    mentions = hist.setdefault("mentions", {})
    for n in news:
        if n.get("genre", "game") != "game":
            continue
        for name in extract_names(n.get("title", "")):
            entry = mentions.setdefault(name_key(name), {"names": {}, "articles": {}})
            if n["id"] in entry["articles"]:
                continue
            entry["articles"][n["id"]] = {"date": _day(n.get("first_seen", "")), "source": n.get("source", "")}
            entry["names"][name] = entry["names"].get(name, 0) + 1


def _days_back(today: date, start: int, count: int) -> set[str]:
    return {(today - timedelta(days=start + i)).isoformat() for i in range(count)}


def buzz_ranking(hist: dict, news: list[dict], now: datetime, limit: int = TOP) -> list[dict]:
    """直近 3 日で、前の 7 日より多く取り上げられているゲーム。2 社以上が書いたものだけ"""
    today = now.date()
    recent_days = _days_back(today, 0, RECENT_DAYS)
    prev_days = _days_back(today, RECENT_DAYS, PREV_DAYS)
    by_id = {n["id"]: n for n in news}

    rows = []
    for entry in hist.get("mentions", {}).values():
        recent = {aid: a for aid, a in entry["articles"].items() if a["date"] in recent_days}
        prev = sum(1 for a in entry["articles"].values() if a["date"] in prev_days)
        sources = sorted({a["source"] for a in recent.values()})
        if len(recent) < 2 or len(sources) < 2:
            continue
        name = max(entry["names"].items(), key=lambda kv: kv[1])[0]
        articles = sorted((by_id[aid] for aid in recent if aid in by_id),
                          key=lambda n: n.get("published_at") or "", reverse=True)[:3]
        rows.append({
            "name": name,
            "recent": len(recent),
            "prev": prev,
            "sources": sources,
            # 前の 7 日の本数を 3 日ぶんに直して引く。ずっと話題のものは 0 前後、急に増えたものが上に来る
            "score": round(len(recent) - prev * RECENT_DAYS / PREV_DAYS, 2),
            "articles": [{"title": n["title"], "link": n["link"], "source": n.get("source", "")} for n in articles],
        })
    rows.sort(key=lambda r: (r["score"], r["recent"]), reverse=True)
    return rows[:limit]


# ---------- Twitch ----------

def record_twitch(hist: dict, viewers: dict[str, int], games: dict[str, dict], now: datetime) -> None:
    """1 回の取得の視聴者数を、その日の合計に足す。runs で割れば日の平均になる"""
    day = hist.setdefault("twitch", {}).setdefault(now.date().isoformat(), {"runs": 0, "sum": {}})
    day["runs"] += 1
    for gid, v in viewers.items():
        day["sum"][gid] = day["sum"].get(gid, 0) + int(v)
    hist.setdefault("twitch_games", {}).update(games)


def daily_average(day: dict, gid: str) -> float:
    return day["sum"].get(gid, 0) / day["runs"] if day.get("runs") else 0.0


def twitch_ranking(hist: dict, limit: int = TOP, min_viewers: int = 1000) -> list[dict]:
    """最新の日の平均視聴者数を、前の 7 日の平均と比べる。前の日がなければ視聴者数の順"""
    days = sorted(hist.get("twitch", {}))
    if not days:
        return []
    latest = days[-1]
    latest_date = date.fromisoformat(latest)
    prev = [d for d in days[:-1] if (latest_date - date.fromisoformat(d)).days <= PREV_DAYS]
    games = hist.get("twitch_games", {})

    rows = []
    for gid in hist["twitch"][latest]["sum"]:
        v = daily_average(hist["twitch"][latest], gid)
        if v < min_viewers or gid not in games:
            continue
        if prev:
            p = sum(daily_average(hist["twitch"][d], gid) for d in prev) / len(prev)
            # 前の日に上位にいなかったゲーム（p が 0 に近い）で伸び率が極端にならないよう、分母に下限を置く
            growth = (v - p) / max(p, 500)
        else:
            p, growth = None, None
        rows.append({
            "name": games[gid]["name"],
            "viewers": round(v),
            "prev_viewers": None if p is None else round(p),
            "growth": growth,
            "box_art": games[gid].get("box_art", ""),
        })
    if prev:
        rows.sort(key=lambda r: (r["growth"], r["viewers"]), reverse=True)
    else:
        rows.sort(key=lambda r: r["viewers"], reverse=True)
    return rows[:limit]


# ---------- 片づけ ----------

def prune(hist: dict, now: datetime, keep_days: int = KEEP_DAYS) -> None:
    """14 日より前の記録を消す"""
    cutoff = (now.date() - timedelta(days=keep_days)).isoformat()
    mentions = hist.get("mentions", {})
    for key in list(mentions):
        arts = mentions[key]["articles"]
        for aid in [a for a, v in arts.items() if v["date"] < cutoff]:
            del arts[aid]
        if not arts:
            del mentions[key]
    for d in [d for d in hist.get("twitch", {}) if d < cutoff]:
        del hist["twitch"][d]
    used = {gid for day in hist.get("twitch", {}).values() for gid in day["sum"]}
    games = hist.get("twitch_games", {})
    for gid in [g for g in games if g not in used]:
        del games[gid]
