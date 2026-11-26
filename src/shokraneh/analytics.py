"""Statistics over a profile's data (pure functions; no Flet imports)."""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta
from statistics import mean, pstdev
from typing import Any

from . import content, util

LIST_QIDS = ("m1", "m2", "m3", "m5", "n1")  # questions answered as several short lines
GRATITUDE_QIDS = ("m1", "m2", "n1")

_STOP_RAW = """
و در به از که این را با برای من هم یه یک اون اینکه هر تو رو بود شد می میشه خیلی امروز فردا بابت چیزی چه چی کرد
کردم دارم هستم هست نیست بعد قبل همه هیچ ولی اما یا تا اگه اگر باز هنوز دیگه فقط مثل بدون درباره روی زیر وقتی چون
پس باید میخوام میتونم بشه بکنم انجام دادم داد دارن داره شده شدم کنم کنه میکنم همین همون اینجا کمی بیشتر کم زیاد
یکی دو سه چهار پنج اول دوم ام ایم اش شون تون مون بودم بودن باشه باشم میشم شو نه آره
the a an and or of to in on for with my i me we is was were be been am are it that this so but at by from as had have has
do did not no today tomorrow very more much just also again about into over then them they he she his her our your you
"""
STOP = {util.norm_text(w) for w in _STOP_RAW.split()}

_NEG_STEMS = tuple(
    util.norm_text(s)
    for s in (
        "ناراحت غمگین عصبی عصبانی استرس نگران ترس تنها خسته اذیت بد افسرده ناامید دعوا گریه مشکل فشار پشیمون شکست درد "
        "بیحوصله کلافه دلتنگ sad angry upset stress anxious worried afraid fear lonely tired hurt depress hopeless "
        "fight cry problem pressure regret fail pain frustrat overwhelm"
    ).split()
)

_CRISIS = tuple(
    util.norm_text(s)
    for s in (
        "خودکشی|بمیرم|نمیخوام زنده باشم|نخوام زنده|خودم رو بکشم|خودمو بکشم|به زندگیم پایان|دلم میخواد بمیرم|"
        "suicide|kill myself|want to die|end my life|hurt myself|self harm|selfharm|dont want to live|don t want to live"
    ).split("|")
)


# --------------------------------------------------------------------------- basic
def _to_day(s: str) -> date | None:
    try:
        return date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        return None


def entries_between(data: dict, kind: str, start: date, end: date) -> dict[date, dict]:
    out: dict[date, dict] = {}
    for k, v in data.get(kind, {}).items():
        d = _to_day(k)
        if d and start <= d <= end:
            out[d] = v
    return dict(sorted(out.items()))


def active_days(data: dict) -> set[date]:
    days: set[date] = set()
    for kind in ("morning", "night", "energy"):
        for k in data.get(kind, {}):
            d = _to_day(k)
            if d:
                days.add(d)
    return days


def streaks(data: dict, today: date) -> tuple[int, int]:
    """(current streak, best streak) in consecutive active days."""
    days = active_days(data)
    if not days:
        return 0, 0
    best = run = 0
    prev: date | None = None
    for d in sorted(days):
        run = run + 1 if prev and (d - prev).days == 1 else 1
        best = max(best, run)
        prev = d
    cur = 0
    d = today if today in days else today - timedelta(days=1)
    while d in days:
        cur += 1
        d -= timedelta(days=1)
    return cur, best


# --------------------------------------------------------------------------- energy
def energy_series(data: dict, start: date, end: date) -> list[tuple[date, int | None]]:
    out: list[tuple[date, int | None]] = []
    store = data.get("energy", {})
    for d in util.daterange(start, end):
        e = store.get(d.isoformat())
        out.append((d, int(e["score"]) if isinstance(e, dict) and "score" in e else None))
    return out


def energy_summary(series: list[tuple[date, int | None]]) -> dict[str, Any]:
    vals = [(d, s) for d, s in series if s is not None]
    if not vals:
        return {"logged": 0, "avg": None, "best": None, "worst": None, "low": 0, "high": 0, "delta": None}
    scores = [s for _, s in vals]
    best = max(vals, key=lambda x: (x[1], -x[0].toordinal()))
    worst = min(vals, key=lambda x: (x[1], x[0].toordinal()))
    half = len(scores) // 2
    delta = (mean(scores[half:]) - mean(scores[:half])) if len(scores) >= 4 else None
    return {
        "logged": len(scores),
        "avg": round(mean(scores), 1),
        "best": best,
        "worst": worst,
        "low": sum(1 for s in scores if s <= 3),
        "high": sum(1 for s in scores if s >= 8),
        "delta": None if delta is None else round(delta, 1),
        "stdev": round(pstdev(scores), 1) if len(scores) > 1 else 0.0,
    }


def weekday_profile(series: list[tuple[date, int | None]], min_n: int = 2) -> dict[int, float]:
    buckets: dict[int, list[int]] = {i: [] for i in range(7)}
    for d, s in series:
        if s is not None:
            buckets[d.weekday()].append(s)
    return {wd: round(mean(v), 1) for wd, v in buckets.items() if len(v) >= min_n}


def tag_impact(data: dict, start: date, end: date, min_each: int = 3, min_delta: float = 0.8) -> list[dict]:
    rows = [e for e in entries_between(data, "energy", start, end).values() if isinstance(e, dict) and "score" in e]
    out = []
    for tag in content.TAGS:
        w = [e["score"] for e in rows if tag in e.get("tags", [])]
        wo = [e["score"] for e in rows if tag not in e.get("tags", [])]
        if len(w) >= min_each and len(wo) >= min_each:
            delta = mean(w) - mean(wo)
            if abs(delta) >= min_delta:
                out.append({"tag": tag, "delta": round(delta, 1), "n": len(w)})
    out.sort(key=lambda r: -abs(r["delta"]))
    return out


def activity_effects(data: dict, start: date, end: date, min_each: int = 3, min_delta: float = 0.8) -> list[dict]:
    """Does energy differ on days with a morning entry / after a night entry / with a good deed?"""
    series = [(d, s) for d, s in energy_series(data, start, end) if s is not None]

    def has_morning(d: date) -> bool:
        return bool(data["morning"].get(d.isoformat()))

    def has_prev_night(d: date) -> bool:
        return bool(data["night"].get((d - timedelta(days=1)).isoformat()))

    def has_deed(d: date) -> bool:
        m = (data["morning"].get(d.isoformat()) or {}).get("answers", {})
        n = (data["night"].get(d.isoformat()) or {}).get("answers", {})
        return bool(m.get("m6") or n.get("n6"))

    out = []
    for key, fn in (("morning", has_morning), ("prev_night", has_prev_night), ("deed", has_deed)):
        w = [s for d, s in series if fn(d)]
        wo = [s for d, s in series if not fn(d)]
        if len(w) >= min_each and len(wo) >= min_each:
            delta = mean(w) - mean(wo)
            if abs(delta) >= min_delta:
                out.append({"key": key, "delta": round(delta, 1), "n": len(w)})
    out.sort(key=lambda r: -abs(r["delta"]))
    return out


# --------------------------------------------------------------------------- text
def _flatten(ans: Any) -> list[str]:
    if isinstance(ans, list):
        return [str(x).strip() for x in ans if str(x).strip()]
    s = str(ans or "").strip()
    return [s] if s else []


def collect_texts(data: dict, start: date, end: date) -> list[dict]:
    out: list[dict] = []
    for kind in ("morning", "night"):
        for d, entry in entries_between(data, kind, start, end).items():
            for qid, ans in (entry.get("answers") or {}).items():
                items = _flatten(ans)
                if items:
                    out.append({"day": d, "kind": kind, "qid": qid, "items": items})
    return out


def avg_words(items: list[str]) -> float:
    return round(mean(len(util.tokens(i)) for i in items), 1) if items else 0.0


def generic_ratio(texts: list[dict]) -> tuple[float, int]:
    """Share of list-type items that are a single word (e.g. 'health'), and the item count."""
    items = [i for t in texts if t["qid"] in LIST_QIDS for i in t["items"]]
    if not items:
        return 0.0, 0
    return sum(1 for i in items if len(util.tokens(i)) <= 1) / len(items), len(items)


def repeated_items(texts: list[dict], min_count: int = 2, qids=GRATITUDE_QIDS) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    first: dict[str, str] = {}
    for t in texts:
        if t["qid"] in qids:
            for i in t["items"]:
                k = util.norm_text(i)
                if k:
                    counter[k] += 1
                    first.setdefault(k, i)
    return [(first[k], c) for k, c in counter.most_common() if c >= min_count][:5]


def top_words(items: list[str], n: int = 5, min_len: int = 3, min_count: int = 2) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()
    for it in items:
        for tok in set(util.tokens(it)):
            if len(tok) >= min_len and tok not in STOP and not tok.isdigit():
                counter[tok] += 1
    return [(w, c) for w, c in counter.most_common(n) if c >= min_count]


def negative_hits(items: list[str]) -> int:
    hits = 0
    for it in items:
        for tok in util.tokens(it):
            if any(tok.startswith(s) for s in _NEG_STEMS):
                hits += 1
    return hits


def crisis_flag(items: list[str]) -> bool:
    return any(c and c in util.norm_text(it) for it in items for c in _CRISIS)


# --------------------------------------------------------------------------- people / lists
def people_neglected(data: dict, today: date, days: int = 21) -> list[tuple[str, int]]:
    out = []
    for p in data.get("people", []):
        last = _to_day(p.get("last_reached") or p.get("created") or "")
        if last:
            gap = (today - last).days
            if gap >= days:
                out.append((p.get("name", ""), gap))
    return sorted(out, key=lambda x: -x[1])


def _count_in(items: list[dict], field: str, start: date, end: date) -> list[dict]:
    out = []
    for it in items:
        d = _to_day(it.get(field) or it.get("created") or "")
        if d and start <= d <= end:
            out.append(it)
    return out


# --------------------------------------------------------------------------- digests
def week_digest(data: dict, start: date, end: date, today: date | None = None) -> dict[str, Any]:
    today = today or end
    days = (end - start).days + 1
    morning = entries_between(data, "morning", start, end)
    night = entries_between(data, "night", start, end)
    series = energy_series(data, start, end)
    summ = energy_summary(series)
    texts = collect_texts(data, start, end)
    all_items = [i for t in texts for i in t["items"]]
    upset = [i for t in texts if t["qid"] == "n7" for i in t["items"]]
    goals = [i for t in texts if t["qid"] == "m5" for i in t["items"]]
    answered = Counter(t["qid"] for t in texts)
    low_tags: Counter[str] = Counter()
    for d, s in series:
        e = data["energy"].get(d.isoformat())
        if s is not None and s <= 4 and e:
            low_tags.update(e.get("tags", []))
    deed_days = sum(
        1
        for d in util.daterange(start, end)
        if ((morning.get(d) or {}).get("answers", {}).get("m6") or (night.get(d) or {}).get("answers", {}).get("n6"))
    )
    gen, n_items = generic_ratio(texts)
    cur, best = streaks(data, today)
    hard = _count_in(data.get("hard_days", []), "date", start, end)
    recent = [i for i in all_items] + [e.get("note", "") for e in entries_between(data, "energy", start, end).values()]
    return {
        "start": start,
        "end": end,
        "days": days,
        "morning_days": len(morning),
        "night_days": len(night),
        "energy_days": summ["logged"],
        "avg": summ["avg"],
        "best": summ["best"],
        "worst": summ["worst"],
        "delta": summ["delta"],
        "series": series,
        "low_tags": low_tags.most_common(3),
        "streak": cur,
        "wins_added": len(_count_in(data.get("wins", []), "date", start, end)),
        "wishes_done": len(_count_in([w for w in data.get("wishes", []) if w.get("done")], "done_at", start, end)),
        "hard_days": hard,
        "lessons": sum(1 for h in hard if (h.get("lesson") or "").strip()),
        "god_talks": len(_count_in(data.get("god_talks", []), "created", start, end)),
        "deed_days": deed_days,
        "answered": dict(answered),
        "avg_words": avg_words([i for t in texts if t["qid"] not in ("m4",) for i in t["items"]]),
        "generic_ratio": gen,
        "list_items": n_items,
        "repeats": repeated_items(texts),
        "themes": top_words([i for t in texts if t["qid"] in GRATITUDE_QIDS for i in t["items"]]),
        "upset_themes": top_words(upset, n=3),
        "goal_words": avg_words(goals) if goals else None,
        "neglected": people_neglected(data, today),
        "negative_hits": negative_hits([i for t in texts if t["qid"] in ("n5", "n7") for i in t["items"]]),
        "safety": crisis_flag(recent),
        "texts": texts,
    }


def recent_low_streak(data: dict, today: date, window: int = 7, min_low: int = 5) -> bool:
    """True when at least `min_low` of the last `window` logged days scored <= 3."""
    series = [s for _, s in energy_series(data, today - timedelta(days=window - 1), today) if s is not None]
    return len(series) >= min_low and sum(1 for s in series if s <= 3) >= min_low


def month_stats(data: dict, start: date, end: date, prev: tuple[date, date] | None = None, today: date | None = None) -> dict:
    today = today or end
    series = energy_series(data, start, end)
    summ = energy_summary(series)
    prev_avg = None
    if prev:
        prev_avg = energy_summary(energy_series(data, prev[0], prev[1]))["avg"]
    morning = entries_between(data, "morning", start, end)
    night = entries_between(data, "night", start, end)
    hard = _count_in(data.get("hard_days", []), "date", start, end)
    return {
        "start": start,
        "end": end,
        "days": (end - start).days + 1,
        "series": series,
        "summary": summ,
        "weekday": weekday_profile(series),
        "tags": tag_impact(data, start, end),
        "effects": activity_effects(data, start, end),
        "morning_days": len(morning),
        "night_days": len(night),
        "streak": streaks(data, min(today, end)),
        "prev_avg": prev_avg,
        "hard_days": len(hard),
        "lessons": sum(1 for h in hard if (h.get("lesson") or "").strip()),
        "low_streak": recent_low_streak(data, min(today, end)),
        "safety": crisis_flag(
            [e.get("note", "") for e in entries_between(data, "energy", start, end).values()]
            + [i for t in collect_texts(data, start, end) for i in t["items"]]
        ),
    }
