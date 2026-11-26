import json
from datetime import date, datetime, timedelta

import pytest

from shokraneh import content, jalali, security, util
from shokraneh.store import Store, deep_merge, PROFILE_DEFAULTS


# ------------------------------------------------------------------ util
def test_digits_and_norm():
    assert util.to_fa_digits("2026") == "۲۰۲۶"
    assert util.to_en_digits("۱۴۰۵/۰۸") == "1405/08"
    assert util.norm_text("مي‌خوام،  خوشحال!") == util.norm_text("میخوام خوشحال")
    assert util.norm_text("Hello,  WORLD!") == "hello world"


def test_logical_today_rollover():
    assert util.logical_today(datetime(2026, 11, 22, 1, 30)) == date(2026, 11, 21)
    assert util.logical_today(datetime(2026, 11, 22, 3, 0)) == date(2026, 11, 22)


def test_hhmm():
    assert util.parse_hhmm("07:30") == (7, 30)
    assert util.parse_hhmm("۲۱:۰۵") == (21, 5)
    assert util.parse_hhmm("99:99", (1, 2)) == (1, 2)
    assert util.stable_int("abc") == util.stable_int("abc") < 2_000_000_000


# ------------------------------------------------------------------ jalali
ANCHORS = [
    (date(2021, 3, 21), (1400, 1, 1)),
    (date(2024, 3, 20), (1403, 1, 1)),
    (date(2025, 3, 20), (1403, 12, 30)),
    (date(2025, 3, 21), (1404, 1, 1)),
    (date(2026, 3, 21), (1405, 1, 1)),
    (date(2026, 9, 23), (1405, 7, 1)),
    (date(2026, 10, 23), (1405, 8, 1)),
    (date(2026, 11, 21), (1405, 8, 30)),
    (date(2026, 12, 22), (1405, 10, 1)),
]


@pytest.mark.parametrize("g,j", ANCHORS)
def test_jalali_anchors(g, j):
    assert jalali.to_jalali(g) == j
    assert jalali.from_jalali(*j) == g


def test_jalali_roundtrip_and_continuity():
    d = date(1990, 1, 1)
    prev = jalali.to_jalali(d)
    while d < date(2100, 12, 31):
        d += timedelta(days=1)
        cur = jalali.to_jalali(d)
        assert jalali.from_jalali(*cur) == d
        py, pm, pd = prev
        if cur[2] == pd + 1 and cur[:2] == (py, pm):
            assert cur[2] <= jalali.month_len(py, pm)
        else:
            assert cur[2] == 1 and pd == jalali.month_len(py, pm)
            assert cur[:2] == ((py, pm + 1) if pm < 12 else (py + 1, 1))
        prev = cur


def test_leap_years():
    assert jalali.is_leap(1399) and jalali.is_leap(1403) and jalali.is_leap(1408)
    assert not jalali.is_leap(1404) and not jalali.is_leap(1405)
    assert jalali.month_len(1403, 12) == 30 and jalali.month_len(1404, 12) == 29


def test_formatting():
    d = date(2026, 11, 21)
    assert jalali.format_day(d, "fa", True, "long") == "شنبه ۳۰ آبان ۱۴۰۵"
    assert jalali.format_day(d, "fa", True, "short") == "۱۴۰۵/۰۸/۳۰"
    assert jalali.format_day(d, "en", False, "long") == "Saturday, 21 November 2026"
    assert jalali.format_day(d, "en", False, "short") == "2026-11-21"
    assert jalali.month_label(d, "fa", True) == "آبان ۱۴۰۵"
    assert jalali.month_label(d, "en", False) == "November 2026"


def test_month_helpers():
    d = date(2026, 11, 21)
    assert jalali.month_bounds(d, True) == (date(2026, 10, 23), date(2026, 11, 21))
    assert jalali.month_bounds(d, False) == (date(2026, 11, 1), date(2026, 11, 30))
    assert jalali.shift_month(d, 1, True) == date(2026, 11, 22)
    assert jalali.shift_month(d, -1, True) == date(2026, 9, 23)
    assert jalali.shift_month(d, 3, False) == date(2027, 2, 1)
    grid = jalali.month_matrix(d, True, 5)
    flat = [x for row in grid for x in row if x]
    assert len(flat) == 30 and all(len(r) == 7 for r in grid)
    assert grid[0][0] is None or grid[0][0].weekday() == 5
    assert jalali.week_start_of(date(2026, 11, 21), 5) == date(2026, 11, 21)
    assert jalali.week_start_of(date(2026, 11, 25), 5) == date(2026, 11, 21)
    assert jalali.weekday_headers("fa", 5)[0] == "ش"


# ------------------------------------------------------------------ content
def test_content_integrity():
    ids = [q.id for q in content.MORNING + content.NIGHT]
    assert len(ids) == len(set(ids)) == 16
    assert [q.count for q in content.MORNING if q.kind == "list"] == [5, 3, 3, 3]
    assert [q.count for q in content.NIGHT if q.kind == "list"] == [5]
    for q in content.MORNING + content.NIGHT:
        assert q.fa and q.en and q.hint_fa and q.hint_en
    assert len(content.AFFIRMATIONS["fa"]) == len(content.AFFIRMATIONS["en"])
    assert content.day_affirmation(date(2026, 11, 21), "fa") in content.AFFIRMATIONS["fa"]


# ------------------------------------------------------------------ security
def test_pin():
    rec = security.hash_pin("1234")
    assert security.verify_pin("1234", rec) and not security.verify_pin("1235", rec)
    assert not security.verify_pin("1234", None)


# ------------------------------------------------------------------ store
def make_store(tmp_path):
    s = Store(tmp_path)
    rec = s.create_profile("سارا", "🌸")
    return s, s.open_profile(rec["id"]), rec


def test_store_entries_and_energy(tmp_path):
    s, p, rec = make_store(tmp_path)
    d = date(2026, 11, 21)
    assert p.save_entry("morning", d, {"m1": ["a", "", "c", "", ""], "m4": "calm", "m6": "  "})["answers"] == {
        "m1": ["a", "", "c", "", ""],
        "m4": "calm",
    }
    assert p.entry("morning", d)["answers"]["m4"] == "calm"
    assert p.save_entry("morning", d, {"m1": ["", ""], "m4": ""}) is None and p.entry("morning", d) is None
    p.set_energy(d, 99, ["sleep"], " ok ")
    assert p.energy(d)["score"] == 10 and p.energy(d)["note"] == "ok"
    p.set_energy(d, 0)
    assert p.energy(d)["score"] == 1
    # persisted to disk and reloadable
    s2 = Store(tmp_path)
    p2 = s2.open_profile(rec["id"])
    assert p2.energy(d)["score"] == 1 and p2.name == "سارا"


def test_store_items(tmp_path):
    s, p, _ = make_store(tmp_path)
    a = p.add_item("wishes", text="سفر", done=False)
    p.update_item("wishes", a["id"], done=True)
    assert p.get_item("wishes", a["id"])["done"] is True
    assert p.delete_item("wishes", a["id"]) and not p.items("wishes")
    m = p.add_message("weekly", "t", [{"h": "x", "text": "y"}], period="2026-W47")
    assert p.unread_count() == 1 and p.message_for_period("weekly", "2026-W47")["id"] == m["id"]
    p.mark_read(m["id"])
    assert p.unread_count() == 0


def test_batch_single_write(tmp_path):
    s, p, _ = make_store(tmp_path)
    writes = []
    orig = p._flush
    p._flush = lambda: (writes.append(1), orig())[1]
    with p.batch():
        p.add_item("wins", text="a")
        p.add_item("wins", text="b")
        p.set_setting("reminders.morning.time", "06:00")
    assert len(writes) == 1 and p.setting("reminders.morning.time") == "06:00"


def test_corruption_recovery(tmp_path):
    s, p, rec = make_store(tmp_path)
    p.add_item("wins", text="one")
    p.add_item("wins", text="two")  # second save creates a .bak of the first
    p.path.write_text("{not json", encoding="utf-8")
    s2 = Store(tmp_path)
    p2 = s2.open_profile(rec["id"])
    assert [w["text"] for w in p2.items("wins")] == ["one"]  # recovered from .bak
    assert list(tmp_path.glob("profiles/*.corrupt-*"))  # corrupt file preserved


def test_export_import(tmp_path):
    s, p, _ = make_store(tmp_path)
    d = date(2026, 11, 21)
    p.save_entry("night", d, {"n2": "مامان"})
    p.add_item("people", name="مامان", relation="family")
    p.set_setting("ai.api_key", "SECRET")
    text = p.export_text()
    assert "SECRET" not in text and json.loads(text)["format"] == "shokraneh-backup"
    other = s.open_profile(s.create_profile("Ali")["id"])
    counts = other.import_text(text)
    assert counts["night"] == 1 and counts["people"] == 1
    assert other.import_text(text)["people"] == 0  # idempotent merge
    with pytest.raises(ValueError):
        other.import_text("[]")
    with pytest.raises(ValueError):
        other.import_text("nope")
    other.wipe()
    assert not other.items("people") and other.entry("night", d) is None


def test_pin_and_profiles(tmp_path):
    s, p, rec = make_store(tmp_path)
    assert not s.has_pin(rec["id"]) and s.check_pin(rec["id"], "")
    s.set_pin(rec["id"], "4321")
    assert s.has_pin(rec["id"]) and s.check_pin(rec["id"], "4321") and not s.check_pin(rec["id"], "1111")
    assert Store(tmp_path).has_pin(rec["id"])
    s.set_pin(rec["id"], None)
    assert not s.has_pin(rec["id"])
    s.delete_profile(rec["id"])
    assert s.profile_list() == [] and not p.path.exists()


def test_deep_merge_defaults():
    out = deep_merge(PROFILE_DEFAULTS, {"settings": {"ai": {"provider": "anthropic"}}, "wishes": "bad", "extra": 1})
    assert out["settings"]["ai"]["provider"] == "anthropic"
    assert out["settings"]["reminders"]["morning"]["time"] == "07:30"
    assert out["wishes"] == [] and out["extra"] == 1
