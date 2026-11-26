"""Helpers for the UI tests: strict fake Flet, a deterministic App (frozen clock, no threads, no network), tree walking,
a crawler that fires every handler, and a layout validator for the Flutter constraint mistakes the fake cannot catch."""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta
from typing import Any, Callable, Iterator

import fake_flet

fake_flet.install()

from helpers import rich_week  # noqa: E402
from shokraneh import ai, notify, util  # noqa: E402
from shokraneh.store import Store  # noqa: E402
from shokraneh.ui.app import App  # noqa: E402

NOW = datetime(2026, 11, 22, 9, 30)  # Sunday 1 Azar 1405
TODAY = date(2026, 11, 22)
Event = fake_flet.Event
_counter = [0]


def freeze(monkeypatch) -> None:
    monkeypatch.setattr(util, "now", lambda: NOW)
    monkeypatch.setattr(util, "logical_today", lambda at=None, start_hour=util.DAY_START_HOUR: ((at or NOW) - timedelta(hours=start_hour)).date())


def offline(monkeypatch) -> list:
    sent: list = []

    def boom(*a, **k):
        raise ai.AIError("network")

    monkeypatch.setattr(ai, "complete", boom)
    monkeypatch.setattr(notify, "desktop_notify", lambda t, b: sent.append((t, b)) or True)
    return sent


def seed(prof) -> None:
    for k, v in rich_week().items():
        if k not in ("settings", "meta", "version"):
            prof.data[k] = copy.deepcopy(v)
    prof.data["people"], prof.data["wins"], prof.data["hard_days"], prof.data["god_talks"] = [], [], [], []
    prof.add_item("wishes", text="سفر به شمال", note="با خانواده")
    prof.add_item("wishes", text="یادگیری گیتار", note="", done=True)
    prof.add_item("wins", text="کارم رو تحویل دادم", category="work", date="2026-11-15")
    prof.add_item("god_talks", text="خدایا ممنون", )
    prof.add_item("prayers", text="سلامتی خانواده", note="", answered=False)
    prof.add_item("prayers", text="قبولی", note="", answered=True)
    prof.add_item("people", name="مامان", relation="family", gratitude="مهربونه", keep="بیشتر زنگ بزنم", last_reached="2026-10-01")
    prof.add_item("hard_days", date="2026-11-16", what="خسته بودم", lesson="صبر", next="استراحت")
    prof.add_item("letters", title="برای آینده", body="امیدوارم خوب باشی", deliver_at="2027-01-01T09:00")
    prof.add_item("letters", title="رسیده", body="سلام", deliver_at="2026-11-20T09:00")
    prof.add_item("letters", title="قدیمی", body="سلام", deliver_at="2026-10-01T09:00", opened_at="2026-10-01T10:00:00", notified=True)
    prof.add_message("weekly", "گزارش نمونه", [{"h": "نگاه کلی", "text": "خوب بود"}, {"h": "نکته‌ها", "items": ["الف", "ب"]}], source="ai", period="w1", ai_error="network")
    prof.save()


def make_app(tmp_path, lang="fa", dark=False, rtl=False, calendar="auto", accent="sage", seeded=True, start=True, pin=None, ai_on=False,
             width=420, onboarded=True) -> App:
    _counter[0] += 1
    store = Store(tmp_path / f"s{_counter[0]}")
    store.app.update(language=lang, theme_mode="dark" if dark else "light", rtl_compat=rtl, calendar=calendar, accent=accent, onboarded=onboarded)
    store.save_app()
    if onboarded:
        rec = store.create_profile("سارا" if lang == "fa" else "Sara", "🌿")
        prof = store.open_profile(rec["id"])
        if seeded:
            seed(prof)
        if ai_on:
            prof.set_setting("ai", {"provider": "anthropic", "api_key": "k", "consent": True})
        if pin:
            store.set_pin(rec["id"], pin)
        store.close_profile(rec["id"])
    page = fake_flet.Page()
    page.width = width
    app = App(page, store=store, fonts_ok=False)

    def bg(fn, *args, done=None):
        res, err = None, None
        try:
            res = fn(*args)
        except Exception as e:  # noqa: BLE001
            err = e
        if done:
            done(res, err)

    app.bg = bg
    app.debounce = lambda key, delay, fn: fn()
    app.start_ticker = lambda: None
    # the pill fills itself at once; the "toast ends" timer is not fired so the banner stays visible for the test
    app.island.schedule = lambda key, delay, fn: fn() if key == "island-fill" else None
    if start:
        app.start()
        page.dialogs.clear()
        if app.island.message:  # e.g. the "new report" banner raised during start-up
            app.island.end_toast()
    return app


# --------------------------------------------------------------------------- tree helpers
def walk(c: Any, parents: tuple = ()) -> Iterator[tuple[Any, tuple]]:
    yield c, parents
    for k in c.kids():
        yield from walk(k, parents + (c,))


def roots(app: App) -> list:
    if app.page.dialogs:
        d = app.page.dialogs[-1]
        return [d]
    return list(app.page.views[-1].controls)


def controls(app: App) -> list[tuple[Any, tuple]]:
    out: list = []
    for r in roots(app):
        out += list(walk(r))
    return out


def texts(app: App) -> list[str]:
    return [str(c.value) for c, _ in controls(app) if c._name == "Text"]


def has_text(app: App, needle: str) -> bool:
    return any(needle in t for t in texts(app))


def _handler(c: Any, names=("on_click",)):
    for n in names:
        h = getattr(c, n, None)
        if h:
            return h
    return None


def click(app: App, label: str, exact: bool = False, nth: int = 0) -> None:
    seen = 0
    for c, parents in controls(app):
        if c._name == "Text" and (str(c.value) == label if exact else label in str(c.value)):
            seen += 1
            if seen <= nth:
                continue
            for node in (c, *reversed(parents)):
                h = getattr(node, "on_click", None)
                if h:
                    h(Event(node))
                    return
    raise AssertionError(f"no clickable text {label!r}; have: {texts(app)[:40]}")


def click_icon(app: App, icon_name: str) -> None:
    for c, parents in controls(app):
        if c._name in ("Icon", "IconButton") and getattr(c, "icon", None) == icon_name:
            for node in (c, *reversed(parents)):
                h = getattr(node, "on_click", None)
                if h:
                    h(Event(node))
                    return
    raise AssertionError(f"no clickable icon {icon_name}")


def fields(app: App) -> list[Any]:
    return [c for c, _ in controls(app) if c._name == "TextField"]


def type_into(ctrl: Any, value: str) -> None:
    ctrl.value = value
    ctrl.on_change(Event(ctrl))


def switches(app: App) -> list[Any]:
    return [c for c, _ in controls(app) if c._name == "Switch"]


def fire(ctrl: Any) -> None:
    n = ctrl._name
    if n == "TextField":
        ctrl.value = "نمونه ۱۲۳ test"
        if getattr(ctrl, "on_change", None):
            ctrl.on_change(Event(ctrl))
        if getattr(ctrl, "on_blur", None):
            ctrl.on_blur(Event(ctrl))
        if getattr(ctrl, "on_submit", None):
            ctrl.on_submit(Event(ctrl))
    elif n == "Switch":
        ctrl.value = not ctrl.value
        ctrl.on_change(Event(ctrl))
    else:
        ctrl.on_click(Event(ctrl))


def targets(app: App) -> list[Any]:
    out = []
    for r in roots(app):
        for c, _ in walk(r):
            if (c._name in ("TextField", "Switch") and getattr(c, "on_change", None)) or getattr(c, "on_click", None):
                out.append(c)
    return out


def dialog_actions(app: App) -> list[Any]:
    if not app.page.dialogs:
        return []
    d = app.page.dialogs[-1]
    acts = getattr(d, "actions", None) or getattr(d, "data", None) or []
    return [a for a in acts if getattr(a, "on_click", None)]


# --------------------------------------------------------------------------- layout validator
def layout_errors(root: Any, dialog: bool = False) -> list[str]:
    """Flutter constraint mistakes: expanded children where the main axis is unbounded, unbounded text fields."""
    errs: list[str] = []

    def go(c: Any, hb: bool, vb: bool, path: str) -> None:
        n = c._name
        if getattr(c, "width", None) is not None:
            hb = True
        if getattr(c, "height", None) is not None:
            vb = True
        kids = c.kids()
        here = f"{path}/{n}"
        if n == "TextField" and not hb:
            errs.append(f"{here}: text field with unbounded width")
        for k in kids:
            ke = bool(getattr(k, "expand", None))
            khb, kvb = hb, vb
            if n == "Row":
                if ke and not hb and not getattr(c, "wrap", False):
                    errs.append(f"{here}: expanded child {k._name} in a Row with unbounded width")
                khb = hb if getattr(c, "wrap", False) else (ke and hb)
            elif n == "Column":
                scroll = getattr(c, "scroll", None) is not None
                if ke and (scroll or not vb):
                    errs.append(f"{here}: expanded child {k._name} in a Column with unbounded height")
                kvb = False if scroll else (ke and vb)
            elif n == "AlertDialog":
                kvb = False
            go(k, khb, kvb, here)

    go(root, True, not dialog, "")
    return errs


def view_layout_errors(app: App) -> list[str]:
    errs: list[str] = []
    for r in app.page.views[-1].controls:
        errs += layout_errors(r)
    for d in app.page.dialogs:
        errs += layout_errors(d, dialog=True)
    return errs
