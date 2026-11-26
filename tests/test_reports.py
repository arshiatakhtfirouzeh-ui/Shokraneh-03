from datetime import date, timedelta

import pytest
from helpers import D0, END, blank, month_data, put, put_energy, rich_week

from shokraneh import ai, coach, reports
from shokraneh.store import Store

TODAY = END + timedelta(days=3)  # a Tuesday after the week D0..END (Sat..Fri)


def profile_with(tmp_path, data):
    s = Store(tmp_path)
    p = s.open_profile(s.create_profile("سارا")["id"])
    p.data.update({k: v for k, v in data.items() if k not in ("settings", "meta")})
    p.save()
    return p


# ------------------------------------------------------------------ periods
def test_period_helpers():
    # Jalali (Saturday-start) weeks
    assert reports.week_bounds(date(2026, 11, 25), 5) == (date(2026, 11, 21), date(2026, 11, 27))
    assert reports.last_complete_week(date(2026, 11, 25), 5) == (date(2026, 11, 14), date(2026, 11, 20))
    assert reports.week_key(date(2026, 11, 14)) == "W2026-11-14"
    # Jalali month containing 2026-11-22 is Azar 1405; the last complete month is Aban
    assert reports.last_complete_month(date(2026, 11, 22), True) == (date(2026, 10, 23), date(2026, 11, 21))
    assert reports.month_key(date(2026, 10, 23), True) == "J1405-08"
    assert reports.last_complete_month(date(2026, 11, 22), False) == (date(2026, 10, 1), date(2026, 10, 31))
    assert reports.month_key(date(2026, 10, 1), False) == "G2026-10"
    assert reports.previous_month(date(2026, 11, 22), True) == (date(2026, 10, 23), date(2026, 11, 21))


def test_pending_rules():
    data = rich_week()
    # TODAY (2026-11-23) is in Azar; the finished week (Nov 14-20) and the finished month (Aban) both have data
    got = reports.pending(data, TODAY, True, 5)
    assert [p["kind"] for p in got] == ["weekly", "monthly"]
    assert got[0]["period"] == "W2026-11-14" and got[1]["period"] == "J1405-08"
    # with Gregorian months the finished month is October, which has no data
    assert [p["kind"] for p in reports.pending(data, TODAY, False, 0)] == ["weekly"]
    assert reports.pending(blank(), TODAY, True, 5) == []
    # the current (unfinished) week is never "pending"
    assert reports.pending(data, D0 + timedelta(days=3), True, 5) == []
    data["messages"] += [
        {"id": "m1", "kind": "weekly", "period": "W2026-11-14", "partial": False},
        {"id": "m2", "kind": "monthly", "period": "J1405-08", "partial": False},
    ]
    assert reports.pending(data, TODAY, True, 5) == []
    data["messages"][0]["partial"] = True  # a partial report is rebuilt once the week is over
    assert [p["kind"] for p in reports.pending(data, TODAY, True, 5)] == ["weekly"]


# ------------------------------------------------------------------ build / save
def test_run_pending_offline_and_idempotent(tmp_path):
    p = profile_with(tmp_path, rich_week())
    made = reports.run_pending(p, TODAY, "fa", True, 5, "سارا")
    assert [m["kind"] for m in made] == ["weekly", "monthly"]
    w = made[0]
    assert w["source"] == "offline" and not w["read"] and w["start"] == "2026-11-14" and w["partial"] is False
    assert p.unread_count() == 2
    assert reports.run_pending(p, TODAY, "fa", True, 5, "سارا") == []  # nothing new on the next call
    assert len(p.items("messages")) == 2


def test_monthly_pending_and_message(tmp_path):
    data, s, e = month_data()  # 1405-08 (Aban), fully logged
    p = profile_with(tmp_path, data)
    day = e + timedelta(days=2)
    made = reports.run_pending(p, day, "en", True, 5)
    kinds = {m["kind"]: m for m in made}
    assert "monthly" in kinds and kinds["monthly"]["period"] == "J1405-08"
    assert kinds["monthly"]["title"].startswith("Monthly review")


def test_ai_success_adds_safety_note_and_failure_falls_back(tmp_path, monkeypatch):
    data = rich_week()
    data["energy"][D0.isoformat()]["note"] = "I want to die"
    p = profile_with(tmp_path, data)
    p.set_setting("ai.provider", "anthropic")
    p.set_setting("ai.api_key", "k")
    p.set_setting("ai.consent", True)

    fake = {"title": "AI title", "sections": [{"h": "x", "text": "y"}], "source": "ai"}
    monkeypatch.setattr(ai, "generate_weekly", lambda *a, **k: fake)
    msg = reports.generate_now(p, "weekly", D0 + timedelta(days=2), "en", False, 5, "Sara")
    assert msg["source"] == "ai" and msg["partial"] is True and msg["ai_error"] == ""
    assert msg["sections"][-1]["h"] == coach.heading("note", "en") and "trust" in msg["sections"][-1]["text"]
    assert len(fake["sections"]) == 1  # the original report object was not mutated

    def boom(*a, **k):
        raise ai.AIError("rate")

    monkeypatch.setattr(ai, "generate_weekly", boom)
    again = reports.regenerate(p, msg["id"], TODAY, "fa", True, "سارا")
    assert again["id"] == msg["id"] and again["source"] == "offline" and again["ai_error"] == "rate"
    assert again["partial"] is False and len(p.items("messages")) == 1  # updated in place, now final

    monkeypatch.setattr(ai, "generate_weekly", lambda *a, **k: (_ for _ in ()).throw(ValueError("odd")))
    assert reports.regenerate(p, msg["id"], TODAY, "fa", True)["ai_error"] == "http"  # unexpected errors are contained


def test_ai_not_used_without_consent(tmp_path, monkeypatch):
    p = profile_with(tmp_path, rich_week())
    p.set_setting("ai.provider", "anthropic")
    p.set_setting("ai.api_key", "k")  # no consent
    monkeypatch.setattr(ai, "generate_weekly", lambda *a, **k: pytest.fail("must not be called without consent"))
    msg = reports.generate_now(p, "weekly", TODAY, "fa", True, 5)
    assert msg["source"] == "offline" and msg["ai_error"] == ""


def test_generate_now_monthly_and_regenerate_unknown(tmp_path):
    data, s, e = month_data()
    p = profile_with(tmp_path, data)
    msg = reports.generate_now(p, "monthly", s + timedelta(days=10), "fa", True, 5)
    assert msg["period"] == "J1405-08" and msg["partial"] is True
    assert reports.regenerate(p, "nope", TODAY, "fa", True) is None
    ov = reports.month_overview(p.snapshot(), s + timedelta(days=10), True)
    assert ov["summary"]["logged"] == 30 and ov["start"] == s


def test_snapshot_is_a_copy(tmp_path):
    p = profile_with(tmp_path, rich_week())
    snap = p.snapshot()
    snap["energy"].clear()
    assert p.data["energy"]
