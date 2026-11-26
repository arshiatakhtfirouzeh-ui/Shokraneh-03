"""PIN lock screen and the PIN set / change / remove flow.

The PIN only gates the user interface; it does not encrypt the files (Settings says so too).
"""
from __future__ import annotations

import time
from typing import Any, Callable

from ...i18n import register
from .. import compat as C
from .. import kit

PIN_LEN = 4
MAX_FAILS = 5  # wrong tries in a row before a short pause
COOLDOWN = 30  # seconds

register({
    "lock_title": ("قفل است", "Locked"),
    "lock_enter": ("رمز {n} رقمی‌ت رو وارد کن", "Enter your {n}-digit PIN"),
    "lock_wrong": ("رمز درست نیست", "That PIN isn't right"),
    "lock_wait": ("چند بار اشتباه شد؛ {s} ثانیه صبر کن", "Too many wrong tries — please wait {s} s"),
    "lock_forgot": ("رمزم رو فراموش کردم", "I forgot my PIN"),
    "lock_forgot_title": ("فراموشیِ رمز", "Forgot your PIN"),
    "lock_forgot_body": ("رمز قابل بازیابی نیست. اگه ادامه بدی همه‌ی نوشته‌های این پروفایل برای همیشه پاک می‌شه و از اول شروع می‌کنی. اگه پشتیبان داشته باشی، بعداً می‌تونی برش گردونی.",
                         "A PIN can't be recovered. If you continue, everything in this profile is erased for good and you start fresh. If you have a backup you can restore it afterwards."),
    "lock_erase": ("پاک کردن و شروع دوباره", "Erase and start over"),
    "switch_profile": ("عوض کردن پروفایل", "Switch profile"),
    "pin_new": ("یه رمز {n} رقمی انتخاب کن", "Choose a {n}-digit PIN"),
    "pin_confirm": ("رمز رو یک بار دیگه وارد کن", "Enter the PIN once more"),
    "pin_current": ("رمز فعلی رو وارد کن", "Enter your current PIN"),
    "pin_mismatch": ("دو رمز یکی نبودن؛ از اول امتحان کن", "The two PINs didn't match — start again"),
    "pin_saved": ("رمز تنظیم شد 🔒", "PIN set 🔒"),
    "pin_removed": ("رمز برداشته شد", "PIN removed"),
    "pin_title_set": ("تنظیم رمز", "Set a PIN"),
    "pin_title_change": ("تغییر رمز", "Change PIN"),
    "pin_title_remove": ("برداشتن رمز", "Remove PIN"),
    "pin_note": ("این رمز فقط جلوی باز شدن برنامه رو می‌گیره؛ فایل‌های برنامه رمزگذاری نمی‌شن.",
                 "This PIN only locks the app screen; the app's files are not encrypted."),
})

KEY_W, KEY_H = 76, 62


def dots(c: kit.Ctx, filled: int, total: int = PIN_LEN) -> Any:
    items = [kit.box(c, None, width=14, height=14, radius=7, bg="accent" if i < filled else None, border=i >= filled, border_color="faint")
             for i in range(total)]
    return kit.ltr_row(c, items, spacing=16)


def pin_pad(c: kit.Ctx, on_digit: Callable[[str], None], on_back: Callable[[], None], corner: Any = None) -> Any:
    """A 3×4 number pad that always reads left-to-right. `corner` fills the empty bottom-left slot."""
    def key(label: str, handler: Callable[[Any], None], icon_name: str | None = None) -> Any:
        inner = kit.icon(c, icon_name, 24, "muted") if icon_name else kit.text(c, label, 26, "medium", align="center")
        return kit.glass(c, inner, padding=0, radius=22, strength="soft", width=KEY_W, height=KEY_H, align=C.center(), on_click=handler, shadow=False)

    def digit(d: int) -> Any:
        return key(c.n(d), lambda e, d=d: on_digit(str(d)))

    blank = kit.box(c, corner, width=KEY_W, height=KEY_H)
    rows = [kit.ltr_row(c, [digit(d) for d in (1, 2, 3)], spacing=14), kit.ltr_row(c, [digit(d) for d in (4, 5, 6)], spacing=14),
            kit.ltr_row(c, [digit(d) for d in (7, 8, 9)], spacing=14),
            kit.ltr_row(c, [blank, digit(0), key("", lambda e: on_back(), "BACKSPACE")], spacing=14)]
    return kit.col(c, rows, spacing=14, h="center")


def _status(c: kit.Ctx, st: dict, prompt: str) -> Any:
    wait = int(st.get("until", 0) - time.time()) + 1 if st.get("until", 0) > time.time() else 0
    if wait > 0:
        return kit.text(c, c.t("lock_wait", s=c.n(wait)), 14, "medium", "bad", align="center")
    if st.get("error") == "wrong":
        return kit.text(c, c.t("lock_wrong"), 14, "medium", "bad", align="center")
    if st.get("error") == "mismatch":
        return kit.text(c, c.t("pin_mismatch"), 14, "medium", "bad", align="center")
    return kit.text(c, prompt, 14.5, color="muted", align="center")


# --------------------------------------------------------------------------- unlock
def view(app, pid: str):
    c = app.ctx()
    st = app.state()
    st.setdefault("pin", "")
    st.setdefault("fails", 0)
    st.setdefault("until", 0.0)
    st.setdefault("error", "")
    rec = next((p for p in app.store.profile_list() if p["id"] == pid), None) or {"name": "", "avatar": "🌿"}

    def press(d: str) -> None:
        if time.time() < st["until"]:
            return app.refresh()
        if len(st["pin"]) >= PIN_LEN:
            return
        st["pin"] += d
        st["error"] = ""
        if len(st["pin"]) < PIN_LEN:
            return app.refresh()
        entered, st["pin"] = st["pin"], ""
        if app.store.check_pin(pid, entered):
            return app.open_profile(pid)
        st["fails"] += 1
        st["error"] = "wrong"
        if st["fails"] >= MAX_FAILS:
            st["fails"] = 0
            st["until"] = time.time() + COOLDOWN
        app.refresh()

    def back() -> None:
        st["pin"] = st["pin"][:-1]
        app.refresh()

    def erase() -> None:
        app.store.delete_profile(pid)
        app.profile = None
        app.start()

    def forgot(e: Any = None) -> None:
        app.confirm(c.t("lock_forgot_title"), c.t("lock_forgot_body"), erase, c.t("lock_erase"), danger=True)

    several = len(app.store.profile_list()) > 1
    body = [kit.space(c, 28), kit.box(c, kit.avatar(c, rec["avatar"], 76), align=C.center()),
            kit.text(c, rec["name"], 20, "bold", align="center"), kit.text(c, c.t("lock_title"), 13, color="faint", align="center"),
            kit.space(c, 6), kit.box(c, dots(c, len(st["pin"])), align=C.center()),
            _status(c, st, c.t("lock_enter", n=c.n(PIN_LEN))), kit.space(c, 4),
            kit.box(c, pin_pad(c, press, back), align=C.center()), kit.space(c, 8),
            kit.box(c, kit.row(c, [kit.link(c, c.t("lock_forgot"), forgot, "muted"),
                                   kit.link(c, c.t("switch_profile"), lambda e: app.switch_profile(), "muted") if several else None],
                               spacing=8, align="center", wrap=True), align=C.center())]
    return kit.screen(c, body)


# --------------------------------------------------------------------------- set / change / remove
STEPS = {"set": ("new", "confirm"), "change": ("current", "new", "confirm"), "remove": ("current",)}


def setup(app, mode: str = "set"):
    c = app.ctx()
    st = app.state()
    steps = STEPS.get(mode, STEPS["set"])
    st.setdefault("i", 0)
    st.setdefault("buf", "")
    st.setdefault("new", "")
    st.setdefault("error", "")
    pid = app.profile.id
    step = steps[min(st["i"], len(steps) - 1)]

    def press(d: str) -> None:
        if len(st["buf"]) >= PIN_LEN:
            return
        st["buf"] += d
        st["error"] = ""
        if len(st["buf"]) < PIN_LEN:
            return app.refresh()
        entered, st["buf"] = st["buf"], ""
        if step == "current":
            if not app.store.check_pin(pid, entered):
                st["error"] = "wrong"
                return app.refresh()
            if mode == "remove":
                app.store.set_pin(pid, None)
                app.toast(c.t("pin_removed"))
                return app.pop()
        elif step == "new":
            st["new"] = entered
        else:  # confirm
            if entered != st["new"]:
                st.update(error="mismatch", new="", i=steps.index("new"))
                return app.refresh()
            app.store.set_pin(pid, entered)
            app.toast(c.t("pin_saved"))
            return app.pop()
        st["i"] += 1
        app.refresh()

    def back() -> None:
        st["buf"] = st["buf"][:-1]
        app.refresh()

    prompt = {"current": c.t("pin_current"), "new": c.t("pin_new", n=c.n(PIN_LEN)), "confirm": c.t("pin_confirm")}[step]
    body = [kit.space(c, 16), kit.box(c, kit.badge(c, "LOCK", "rose", 64), align=C.center()), kit.space(c, 4),
            kit.box(c, dots(c, len(st["buf"])), align=C.center()), _status(c, st, prompt), kit.space(c, 4),
            kit.box(c, pin_pad(c, press, back), align=C.center()), kit.space(c, 4),
            kit.text(c, c.t("pin_note"), 12.5, color="faint", align="center")]
    return kit.screen(c, body, title=c.t(f"pin_title_{mode}"), on_back=app.pop)
