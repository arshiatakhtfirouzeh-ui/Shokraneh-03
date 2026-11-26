"""Shared synthetic data for the analytics / coach / ai / reports tests."""
import copy
from datetime import date, timedelta

from shokraneh.store import PROFILE_DEFAULTS

D0 = date(2026, 11, 14)  # a Saturday
END = D0 + timedelta(days=6)


def blank():
    return copy.deepcopy(PROFILE_DEFAULTS)


def put(data, kind, d, answers):
    data[kind][d.isoformat()] = {"answers": answers}


def put_energy(data, d, score, tags=(), note=""):
    data["energy"][d.isoformat()] = {"score": score, "tags": list(tags), "note": note}


def rich_week():
    data = blank()
    for i in range(7):
        d = D0 + timedelta(days=i)
        put(data, "morning", d, {"m1": ["سلامتی", "خانواده", "خونه", "", ""], "m5": ["ورزش", "", ""], "m6": "کمک به همسایه" if i % 2 == 0 else ""})
        if i < 5:
            put(data, "night", d, {"n1": ["چای", "", "", "", ""], "n7": "استرس کار", "n5": ""})
        put_energy(data, d, [6, 7, 4, 8, 3, 7, 8][i], ["sleep"] if i in (0, 3) else ["stress"] if i == 4 else [])
    data["people"].append({"id": "p1", "name": "مامان", "created": "2026-09-01T10:00:00", "last_reached": "2026-10-01"})
    data["wins"].append({"id": "w1", "text": "x", "created": "2026-11-15T10:00:00"})
    data["hard_days"].append({"id": "h1", "date": "2026-11-16", "lesson": "صبر", "created": "2026-11-16T10:00:00"})
    data["god_talks"] += [{"id": f"g{i}", "text": "t", "created": f"2026-11-1{5 + i}T10:00:00"} for i in range(2)]
    return data


def month_data(low=False):
    data = blank()
    start = date(2026, 10, 23)
    for i in range(30):
        d = start + timedelta(days=i)
        base = 2 if low else (4 if d.weekday() == 0 else 7)
        walk = (i % 2 == 0)
        put_energy(data, d, base + (1 if walk else 0), ["movement"] if walk else ["stress"])
        if i % 3 != 0:
            put(data, "morning", d, {"m1": ["a b", "c d", "e f", "", ""]})
        if i % 2 == 0:
            put(data, "night", d, {"n6": "کمک"})
    return data, start, start + timedelta(days=29)
