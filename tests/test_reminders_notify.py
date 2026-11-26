import asyncio
import json
import sys
import types
from datetime import datetime

import pytest
from helpers import blank

from shokraneh import config, notify, reminders

NOW = datetime(2026, 11, 22, 8, 0)


def letters_data():
    d = blank()
    d["letters"] = [
        {"id": "l_a", "title": "راز", "body": "متن خصوصی", "deliver_at": "2026-12-01T09:00:00", "opened_at": None},
        {"id": "l_b", "title": "گذشته", "body": "x", "deliver_at": "2026-11-20T09:00:00", "opened_at": None},
        {"id": "l_c", "title": "خونده", "body": "x", "deliver_at": "2026-11-01T09:00:00", "opened_at": "2026-11-02T10:00:00"},
        {"id": "l_d", "title": "اعلام‌شده", "body": "x", "deliver_at": "2026-11-21T09:00:00", "opened_at": None, "notified": True},
    ]
    return d


# ------------------------------------------------------------------ letters
def test_letter_states_and_arrivals():
    d = letters_data()
    st = {l["id"]: reminders.letter_state(l, NOW) for l in d["letters"]}
    assert st == {"l_a": "sealed", "l_b": "arrived", "l_c": "opened", "l_d": "arrived"}
    assert [l["id"] for l in reminders.new_arrivals(d, NOW)] == ["l_b"]  # l_d was already announced
    assert reminders.next_sealed(d, NOW)["id"] == "l_a"
    assert reminders.letter_state({"deliver_at": "2026-11-22T08:00:00"}, NOW) == "arrived"  # exactly on time
    assert reminders.letter_state({"deliver_at": "garbage"}, NOW) == "arrived"


def test_letter_nid_is_stable_and_int32():
    a = reminders.letter_nid("l_a")
    assert a == reminders.letter_nid("l_a") and 10_000 <= a < 2**31 and a != reminders.letter_nid("l_b")


# ------------------------------------------------------------------ specs
def test_specs_daily_and_letters():
    d = letters_data()
    specs = reminders.specs(d, "fa", NOW)
    by = {s.kind: s for s in specs}
    assert by["morning"].when == datetime(2026, 11, 23, 7, 30) and by["morning"].repeat == "daily"
    assert by["night"].when == datetime(2026, 11, 22, 21, 30) and by["night"].nid == reminders.NIGHT_ID
    letters = [s for s in specs if s.kind == "letter"]
    assert len(letters) == 1 and letters[0].when == datetime(2026, 12, 1, 9, 0) and letters[0].payload == "letter:l_a"
    assert "راز" not in letters[0].body and "متن خصوصی" not in letters[0].body  # nothing private on a lock screen
    assert len({s.nid for s in specs}) == len(specs)

    d["settings"]["reminders"]["morning"]["enabled"] = False
    d["settings"]["reminders"]["night"]["time"] = "۲۲:۱۵"
    specs2 = reminders.specs(d, "en", NOW)
    assert [s.kind for s in specs2] == ["night", "letter"]
    assert specs2[0].when == datetime(2026, 11, 22, 22, 15) and specs2[0].title == "Good evening 🌙"


def test_due_now_window_and_dedup():
    d = blank()
    at = lambda h, m: datetime(2026, 11, 22, h, m)
    assert reminders.due_now(d, at(7, 29), {}) == []
    assert reminders.due_now(d, at(7, 30), {}) == ["morning"]
    assert reminders.due_now(d, at(7, 49), {}) == ["morning"]
    assert reminders.due_now(d, at(7, 51), {}) == []  # too late: app was opened long after the reminder
    assert reminders.due_now(d, at(7, 35), {"morning": "2026-11-22"}) == []  # already fired today
    assert reminders.due_now(d, at(21, 40), {}) == ["night"]
    d["morning"]["2026-11-22"] = {"answers": {"m6": "x"}}
    assert reminders.due_now(d, at(7, 35), {}) == []  # already written
    d["settings"]["reminders"]["night"]["enabled"] = False
    assert reminders.due_now(d, at(21, 40), {}) == []


# ------------------------------------------------------------------ Notifier with a fake Android plugin
class FakePlugin:
    instances: list = []
    reject_extras = False

    def __init__(self, on_notification_tap=None):
        self.on_tap = on_notification_tap
        self.calls: list = []
        FakePlugin.instances.append(self)

    async def request_permissions(self):
        self.calls.append(("perm",))
        return True

    async def request_exact_alarm_permission(self):
        self.calls.append(("exact",))
        return True

    async def cancel_all(self):
        self.calls.append(("cancel_all",))

    async def schedule_notification(self, notification_id, title, body, scheduled_time, match_date_time_components=None, schedule_mode="inexact_allow_while_idle", **extra):
        if FakePlugin.reject_extras and extra:
            raise TypeError("unexpected keyword")
        self.calls.append(("schedule", notification_id, title, scheduled_time, match_date_time_components, schedule_mode, extra))

    async def show_notification(self, notification_id, title, body, **extra):
        self.calls.append(("show", notification_id, title))


class FakePage:
    def __init__(self):
        self.services = []


@pytest.fixture()
def android(monkeypatch):
    FakePlugin.instances, FakePlugin.reject_extras = [], False
    mod = types.ModuleType("flet_android_notifications")
    mod.FletAndroidNotifications = FakePlugin
    monkeypatch.setitem(sys.modules, "flet_android_notifications", mod)
    monkeypatch.setattr(config, "is_android", lambda: True)
    return FakePage()


def test_native_sync(android):
    n = notify.Notifier(android, lang="en")
    assert n.native and android.services == [FakePlugin.instances[0]] and n.status()["platform"] == "android"
    assert asyncio.run(n.request_permissions()) is True and n.exact is True
    specs = reminders.specs(letters_data(), "en", NOW)
    assert asyncio.run(n.sync(specs)) == 3
    calls = FakePlugin.instances[0].calls
    assert calls[2] == ("cancel_all",)  # perm, exact, then cancel before re-scheduling
    sched = [c for c in calls if c[0] == "schedule"]
    assert [c[1] for c in sched] == [s.nid for s in specs]
    morning = next(c for c in sched if c[1] == reminders.MORNING_ID)
    assert morning[4] == "time" and morning[5] == "exact_allow_while_idle" and morning[6]["channel_id"] == notify.CHANNEL_ID
    letter = next(c for c in sched if c[1] >= 10_000)
    assert letter[4] is None and letter[3] == datetime(2026, 12, 1, 9, 0)
    assert asyncio.run(n.test()) is True and FakePlugin.instances[0].calls[-1][0] == "show"


def test_native_falls_back_when_extras_rejected(android):
    FakePlugin.reject_extras = True
    n = notify.Notifier(android)
    assert asyncio.run(n.sync(reminders.specs(blank(), "fa", NOW))) == 2
    assert all(c[6] == {} for c in FakePlugin.instances[0].calls if c[0] == "schedule")


def test_tap_callback(android):
    got = []
    n = notify.Notifier(android, on_tap=got.append)
    n._tap(types.SimpleNamespace(data=json.dumps({"payload": "letter:l_a", "action_id": ""})))
    n._tap(types.SimpleNamespace(data="not json"))
    assert got == ["letter:l_a", ""]


def test_missing_plugin_never_crashes(monkeypatch):
    monkeypatch.setattr(config, "is_android", lambda: True)
    monkeypatch.setitem(sys.modules, "flet_android_notifications", None)  # import raises ImportError
    n = notify.Notifier(FakePage())
    assert not n.native and "not installed" in n.last_error
    assert asyncio.run(n.sync(reminders.specs(blank(), "fa", NOW))) == 0
    assert asyncio.run(n.request_permissions()) is False and asyncio.run(n.test()) is False
    asyncio.run(n.cancel_all())


def test_plugin_exceptions_are_contained(android):
    class Boom(FakePlugin):
        async def schedule_notification(self, **kw):
            raise RuntimeError("boom")

    sys.modules["flet_android_notifications"].FletAndroidNotifications = Boom
    n = notify.Notifier(android)
    assert asyncio.run(n.sync(reminders.specs(blank(), "fa", NOW))) == 0 and "boom" in n.last_error


# ------------------------------------------------------------------ desktop
def test_desktop_notify_without_helper(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(notify.shutil, "which", lambda _: None)
    assert notify.desktop_notify("t", "b") is False
    monkeypatch.setattr(sys, "platform", "freebsd")
    assert notify.desktop_notify("t", "b") is False


def test_desktop_notify_launches_helper(monkeypatch):
    seen = {}

    class P:
        def __init__(self, cmd, **kw):
            seen["cmd"], seen["kw"] = cmd, kw

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(notify.shutil, "which", lambda _: "/usr/bin/notify-send")
    monkeypatch.setattr(notify.subprocess, "Popen", P)
    assert notify.desktop_notify("عنوان", "متن") is True
    assert seen["cmd"][-2:] == ["عنوان", "متن"]

    monkeypatch.setattr(sys, "platform", "win32")
    assert notify.desktop_notify("عنوان", "متن") is True
    assert seen["kw"]["env"]["SK_TITLE"] == "عنوان" and seen["cmd"][0] == "powershell"
    monkeypatch.setattr(sys, "platform", "darwin")
    assert notify.desktop_notify("a", "b") is True and seen["cmd"][0] == "osascript"


def test_desktop_notifier_has_no_native(monkeypatch):
    monkeypatch.setattr(config, "is_android", lambda: False)
    n = notify.Notifier(FakePage())
    assert not n.native and asyncio.run(n.sync([])) == 0
