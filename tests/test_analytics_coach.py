import re
from datetime import date, timedelta

import pytest
from helpers import D0, END, blank, month_data, put, put_energy, rich_week

from shokraneh import analytics, coach

# --------------------------------------------------------------- analytics
def test_streaks():
    data = blank()
    for i in (0, 1, 2, 5, 6, 7, 8):
        put_energy(data, D0 + timedelta(days=i), 5)
    cur, best = analytics.streaks(data, D0 + timedelta(days=8))
    assert (cur, best) == (4, 4)
    # a missing "today" does not break the streak yet
    assert analytics.streaks(data, D0 + timedelta(days=9))[0] == 4
    assert analytics.streaks(data, D0 + timedelta(days=11))[0] == 0
    assert analytics.streaks(blank(), D0) == (0, 0)


def test_energy_summary():
    data = blank()
    for i, s in enumerate([2, 3, 6, 8]):
        put_energy(data, D0 + timedelta(days=i), s)
    sm = analytics.energy_summary(analytics.energy_series(data, D0, D0 + timedelta(days=5)))
    assert sm["logged"] == 4 and sm["avg"] == 4.8 and sm["best"][1] == 8 and sm["worst"][1] == 2
    assert sm["low"] == 2 and sm["high"] == 1 and sm["delta"] == 4.5
    empty = analytics.energy_summary(analytics.energy_series(blank(), D0, END))
    assert empty["avg"] is None and empty["logged"] == 0


def test_text_helpers():
    texts = [
        {"day": D0, "kind": "morning", "qid": "m1", "items": ["سلامتی", "خانواده"]},
        {"day": D0, "kind": "night", "qid": "n1", "items": ["سلامتی", "قهوه با مریم"]},
    ]
    ratio, n = analytics.generic_ratio(texts)
    assert n == 4 and ratio == 0.75
    assert analytics.repeated_items(texts)[0][1] == 2
    assert analytics.crisis_flag(["می‌خوام خودکشی کنم"]) and analytics.crisis_flag(["I want to die"])
    assert not analytics.crisis_flag(["امروز روز خوبی بود"])
    assert analytics.negative_hits(["خیلی ناراحت و خسته بودم"]) == 2


def test_people_neglected():
    data = rich_week()
    out = analytics.people_neglected(data, END)
    assert out and out[0][0] == "مامان" and out[0][1] >= 40


def test_week_digest_numbers():
    data = rich_week()
    dg = analytics.week_digest(data, D0, END, END)
    assert dg["days"] == 7 and dg["morning_days"] == 7 and dg["night_days"] == 5 and dg["energy_days"] == 7
    assert dg["avg"] == 6.1 and dg["best"][1] == 8 and dg["worst"][1] == 3
    assert dg["wins_added"] == 1 and dg["hard_days"] and dg["lessons"] == 1 and dg["god_talks"] == 2
    assert dg["deed_days"] == 4
    assert dg["generic_ratio"] > 0.5
    assert dg["low_tags"] and dg["low_tags"][0][0] == "stress"
    assert dg["neglected"] and not dg["safety"]


# --------------------------------------------------------------- coach (weekly)
BRACES = re.compile(r"[{}]|None|nan")


def flatten(report):
    parts = [report["title"]]
    for s in report["sections"]:
        parts.append(s.get("h", ""))
        parts.append(s.get("text", ""))
        parts += s.get("items", [])
    return parts


@pytest.mark.parametrize("lang", ["fa", "en"])
@pytest.mark.parametrize("jal", [True, False])
def test_weekly_report_shape(lang, jal):
    dg = analytics.week_digest(rich_week(), D0, END, END)
    rep = coach.weekly_report(dg, lang, "Sara" if lang == "en" else "سارا", jal)
    assert rep["source"] == "offline" and rep["title"]
    heads = [s.get("h") for s in rep["sections"] if s.get("h")]
    assert heads[:3] == [coach.heading(k, lang) for k in ("glance", "well", "feedback")] or len(heads) >= 3
    for part in flatten(rep):
        assert not BRACES.search(part), part
    assert len(rep["sections"][-1]["text"]) > 10
    glance = rep["sections"][0]["text"]
    assert ("۶٫۱" in glance) if lang == "fa" else ("6.1" in glance)
    fb = next(s for s in rep["sections"] if s.get("h") == coach.heading("feedback", lang))
    assert 1 <= len(fb["items"]) <= 4
    nx = next(s for s in rep["sections"] if s.get("h") == coach.heading("next", lang))
    assert len(nx["items"]) == 3


def test_weekly_report_empty_and_safety():
    dg = analytics.week_digest(blank(), D0, END, END)
    rep = coach.weekly_report(dg, "fa")
    assert len(rep["sections"]) == 3  # glance + next + closing
    assert "هنوز چیزی ننوشتی" in rep["sections"][0]["text"]
    assert not any(BRACES.search(p) for p in flatten(rep))

    data = rich_week()
    data["energy"][D0.isoformat()]["note"] = "دلم میخواد بمیرم"
    dg2 = analytics.week_digest(data, D0, END, END)
    assert dg2["safety"]
    rep2 = coach.weekly_report(dg2, "fa")
    assert any(s.get("h") == coach.heading("note", "fa") for s in rep2["sections"])
    rep3 = coach.weekly_report(dg2, "en")
    assert any("trust" in (s.get("text") or "") for s in rep3["sections"])


def test_weekly_report_deterministic():
    dg = analytics.week_digest(rich_week(), D0, END, END)
    assert coach.weekly_report(dg, "en") == coach.weekly_report(dg, "en")


# --------------------------------------------------------------- monthly
def test_month_stats_and_review():
    data, s, e = month_data()
    ms = analytics.month_stats(data, s, e, prev=None, today=e)
    assert ms["summary"]["logged"] == 30 and ms["weekday"] and ms["tags"]
    assert ms["tags"][0]["tag"] in ("movement", "stress")
    for lang in ("fa", "en"):
        rev = coach.monthly_review(ms, lang)
        for part in flatten(rev):
            assert not BRACES.search(part), part
        tips = next(x for x in rev["sections"] if x.get("h") == coach.heading("tips", lang))
        assert 1 <= len(tips["items"]) <= 6 and len(set(tips["items"])) == len(tips["items"])
        pats = next(x for x in rev["sections"] if x.get("h") == coach.heading("patterns", lang))
        assert len(pats["items"]) >= 2


def test_month_review_empty_and_low():
    ms = analytics.month_stats(blank(), date(2026, 10, 23), date(2026, 11, 21), today=date(2026, 11, 21))
    rev = coach.monthly_review(ms, "en")
    assert "haven't logged" in rev["sections"][0]["text"]
    assert coach.monthly_tips(ms, "en")  # still gives at least one useful tip

    data, s, e = month_data(low=True)
    ms2 = analytics.month_stats(data, s, e, today=e)
    assert ms2["low_streak"]
    rev2 = coach.monthly_review(ms2, "fa")
    assert any(sec.get("h") == coach.heading("note", "fa") for sec in rev2["sections"])
    tips = coach.monthly_tips(ms2, "fa")
    assert any("مشاور" in t for t in tips)


def test_month_compare_text():
    data, s, e = month_data()
    ms = analytics.month_stats(data, s, e, prev=(s - timedelta(days=30), s - timedelta(days=1)), today=e)
    assert ms["prev_avg"] is None  # nothing logged before
    ms["prev_avg"] = 5.0
    rev = coach.monthly_review(ms, "en")
    assert "points" in rev["sections"][0]["text"]
