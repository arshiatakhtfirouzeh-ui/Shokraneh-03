"""The "dynamic island": a small dark pill floating at the top of the screen.

* idle   - a live summary of today (morning / night / mood check-ins and the streak); only on the four main tabs
* open   - tap the pill and it grows into three quick actions
* toast  - messages ("saved", reminders, errors) morph the pill into a banner and shrink back afterwards

One `Island` lives in the `App`. Every screen builds a fresh pill with `build()` (a control cannot be in two views at
once); state changes then mutate the newest pill in place, so Flutter animates the size / radius change by itself.
"""
from __future__ import annotations

from typing import Any, Callable

import flet as ft

from .. import today as today_mod
from ..i18n import register
from . import compat as C
from . import kit
from .compat import A, mk

register({
    "island_today": ("امروز · {d} از {t}", "Today · {d} of {t}"),
    "island_morning": ("صبح", "Morning"),
    "island_night": ("شب", "Evening"),
    "island_energy": ("حال", "Mood"),
})

# The pill is dark in both themes, so it always uses the light-on-dark tones.
TONE = {"morning": "#D8AE7A", "night": "#A898D4", "energy": "#86B79F", "streak": "#E2BC76"}
KINDS = {"ok": ("CHECK_CIRCLE", "#86B79F"), "error": ("ERROR_OUTLINE", "#E08A82"),
         "bell": ("NOTIFICATIONS_ACTIVE", "#E2BC76"), "info": ("INFO_OUTLINE", "#9CC3E0")}
TOAST_SECONDS = 3.4
ERROR_SECONDS = 4.8


class Island:
    def __init__(self, app: Any):
        self.app = app
        self.mode = "idle"  # idle | open | toast
        self.message: tuple[str, str] | None = None
        self.last_toast: str = ""
        self.host: Any = None
        self.c: kit.Ctx | None = None
        self.on_main = False
        self.size: tuple[float, float] = (0.0, 0.0)

    # ------------------------------------------------------------------ scheduling (replaced in tests)
    def schedule(self, key: str, delay: float, fn: Callable[[], None]) -> None:
        self.app.debounce(key, delay, fn)

    # ------------------------------------------------------------------ geometry
    def shown(self) -> str:
        """What the pill looks like right now: hidden | idle | open | toast."""
        if self.mode == "toast" and self.message:
            return "toast"
        if not self.on_main:
            return "hidden"
        return "open" if self.mode == "open" else "idle"

    @staticmethod
    def _size(c: kit.Ctx, shown: str) -> tuple[float, float]:
        width = min(c.width, 440.0)
        if shown == "hidden":
            return 48.0, 8.0
        if shown == "idle":
            return 164.0, 38.0
        if shown == "toast":
            return max(180.0, width - 40.0), 56.0
        return max(220.0, width - 32.0), 142.0

    @staticmethod
    def _radius(shown: str, h: float) -> float:
        return 30.0 if shown == "open" else h / 2

    # ------------------------------------------------------------------ building
    def build(self, c: kit.Ctx, on_main: bool) -> Any:
        """A fresh pill for a screen that is being built. Returns the positioned control for the screen's Stack."""
        self.c, self.on_main = c, on_main
        if self.mode == "open" and not on_main:
            self.mode = "idle"
        shown = self.shown()
        w, h = self._size(c, shown)
        self.size = (w, h)
        self.host = kit.box(
            c, self._content(c, shown), width=w, height=h, bg="island", radius=self._radius(shown, h),
            gradient=C.gradient(["#F2343F43", "#F20A0E10"], (-1, -1), (1, 1)) if c.glassy else None,  # smoked glass
            border=c.glassy, border_color="#2EFFFFFF",
            padding=C.pad(14, 0, 14, 0) if shown != "open" else C.pad(16, 14, 16, 14), clip=True, shadow=shown != "hidden",
            opacity=0.0 if shown == "hidden" else 1.0, on_click=self._tap if shown != "hidden" else None,
            animate=C.animation(340), animate_opacity=C.animation(220), align=C.center() if shown != "open" else None,
        )
        return mk(ft.Row, controls=[self.host], alignment=A.MAIN_CENTER, left=0, right=0, top=6)

    def _content(self, c: kit.Ctx, shown: str) -> Any:
        if shown == "toast" and self.message:
            return self._toast_view(c, *self.message)
        if shown == "idle":
            return self._idle_view(c)
        if shown == "open":
            return self._open_view(c)
        return None

    def _status(self) -> dict | None:
        p = self.app.profile
        return today_mod.status(p, self.app.today()) if p is not None else None

    def _idle_view(self, c: kit.Ctx) -> Any:
        st = self._status()
        if st is None:
            return None

        def dot(icon_name: str, key: str, done: bool) -> Any:
            return kit.icon(c, icon_name, 18, TONE[key] if done else "island_dim")

        streak = st["streak"]
        flame = kit.row(c, [kit.icon(c, "LOCAL_FIRE_DEPARTMENT", 16, TONE["streak"] if streak else "island_dim"),
                            kit.text(c, c.n(streak), 13, "bold", "island_text" if streak else "island_dim")], spacing=3)
        return kit.row(c, [dot("WB_SUNNY", "morning", st["morning_done"]), dot("NIGHTLIGHT_ROUND", "night", st["night_done"]),
                           dot("SENTIMENT_SATISFIED_ALT", "energy", st["energy"]),
                           kit.box(c, None, width=1, height=16, bg="island_line", radius=0), flame], spacing=10, align="center")

    def _toast_view(self, c: kit.Ctx, message: str, kind: str) -> Any:
        icon_name, tone = KINDS.get(kind, KINDS["ok"])
        badge = kit.box(c, kit.icon(c, icon_name, 20, tone), width=32, height=32, radius=16, bg="island_line", align=C.center())
        return kit.row(c, [badge, kit.text(c, message, 13.5, "medium", "island_text", max_lines=2, expand=True)], spacing=10)

    def _open_view(self, c: kit.Ctx) -> Any:
        st = self._status()
        if st is None:
            return None
        streak = st["streak"]
        head = kit.row(c, [
            kit.text(c, c.t("island_today", d=c.n(st["done"]), t=c.n(st["total"])), 14.5, "bold", "island_text", expand=True),
            kit.icon(c, "LOCAL_FIRE_DEPARTMENT", 16, TONE["streak"] if streak else "island_dim"),
            kit.text(c, c.n(streak), 13, "bold", "island_text" if streak else "island_dim")], spacing=4)

        def action(icon_name: str, key: str, label: str, done: bool, handler: Callable) -> Any:
            top = kit.row(c, [kit.icon(c, icon_name, 20, TONE[key]), kit.icon(c, "CHECK", 14, "island_text") if done else None], spacing=4, align="center")
            inner = kit.col(c, [top, kit.text(c, label, 12.5, "medium", "island_text", align="center")], spacing=5, h="center")
            return kit.box(c, inner, padding=C.pad(6, 10, 6, 10), bg="island_line", radius=18, expand=True, align=C.center(), on_click=handler)

        row = kit.row(c, [
            action("WB_SUNNY", "morning", c.t("island_morning"), st["morning_done"], lambda e: self._practice("morning")),
            action("NIGHTLIGHT_ROUND", "night", c.t("island_night"), st["night_done"], lambda e: self._practice("night")),
            action("SENTIMENT_SATISFIED_ALT", "energy", c.t("island_energy"), st["energy"], lambda e: self._energy()),
        ], spacing=8)
        return kit.col(c, [head, row], spacing=12)

    # ------------------------------------------------------------------ interaction
    def _tap(self, e: Any = None) -> None:
        shown = self.shown()
        if shown == "idle":
            self._morph("open")
        elif shown == "open":
            self._morph("idle")
        elif shown == "toast":
            self.end_toast()

    def _practice(self, kind: str) -> None:
        from .screens import questions

        self.mode = "idle"
        self.app.push(questions.view, kind=kind, day=self.app.today())

    def _energy(self) -> None:
        from .screens import energy

        self._morph("idle")
        energy.sheet(self.app, self.app.today())

    def collapse(self) -> None:
        if self.mode == "open":
            self._morph("idle")

    def reset_nav(self) -> None:
        """Called when the screen changes: an open pill folds away (the new screen builds it closed)."""
        if self.mode == "open":
            self.mode = "idle"

    # ------------------------------------------------------------------ toast
    def show(self, message: str, kind: str = "ok") -> bool:
        """Morph into a banner. False when no pill is on screen (the caller then falls back to a SnackBar)."""
        self.last_toast = message
        if self.host is None or self.c is None:
            return False
        self.message = (message, kind)
        self.mode = "toast"
        self._morph("toast")
        self.schedule("island-toast", ERROR_SECONDS if kind == "error" else TOAST_SECONDS, self.end_toast)
        return True

    def end_toast(self) -> None:
        self.message = None
        self._morph("idle")

    # ------------------------------------------------------------------ morphing
    def _morph(self, mode: str) -> None:
        host, c = self.host, self.c
        self.mode = mode
        if host is None or c is None:
            return
        shown = self.shown()
        w, h = self._size(c, shown)
        grow = w > self.size[0] or h > self.size[1]
        self.size = (w, h)
        host.width, host.height = w, h
        host.border_radius = self._radius(shown, h)
        host.padding = C.pad(14, 0, 14, 0) if shown != "open" else C.pad(16, 14, 16, 14)
        host.alignment = C.center() if shown != "open" else None
        host.opacity = 0.0 if shown == "hidden" else 1.0
        host.on_click = self._tap if shown != "hidden" else None
        if grow:  # let the pill widen first, then fill it (so the content never overflows a half-grown pill)
            host.content = None
            self._update()
            self.schedule("island-fill", 0.3, self._fill)
        else:
            host.content = self._content(c, shown)
            self._update()

    def _fill(self) -> None:
        if self.host is None or self.c is None:
            return
        self.host.content = self._content(self.c, self.shown())
        self._update()

    def _update(self) -> None:
        try:
            self.app.page.update()
        except Exception:
            pass
