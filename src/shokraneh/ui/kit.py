"""Reusable, direction-aware UI pieces.

Screens are built only from these helpers (never raw ft.Row / ft.Text), so styling and right-to-left handling live in
one place. `Ctx` carries language, palette and the manual-RTL switch.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Iterable

import flet as ft

from .. import config, i18n, jalali, util
from . import compat as C
from . import theme
from .compat import A, mk

# Are Flet's icons mirrored automatically in right-to-left layouts? (string icon names -> Flutter constants -> yes)
BOTTOM_ROOM = 96  # scroll padding that keeps the last item clear of a floating bottom bar
ICONS_MIRROR = isinstance(getattr(getattr(ft, "Icons", None), "ARROW_BACK", None), str)

# semantic keys used by content.py -> Material icon names
SEMANTIC = {
    "heart": "FAVORITE", "star": "STAR", "sparkle": "AUTO_AWESOME", "mood": "SENTIMENT_SATISFIED_ALT",
    "flag": "FLAG", "hands": "VOLUNTEER_ACTIVISM", "quote": "FORMAT_QUOTE", "party": "CELEBRATION",
    "person": "PERSON", "trophy": "EMOJI_EVENTS", "bulb": "LIGHTBULB", "growth": "TRENDING_UP",
    "gift": "CARD_GIFTCARD", "cloud": "CLOUD", "sunrise": "WB_TWILIGHT", "pray": "SELF_IMPROVEMENT",
}

_MAIN = {"start": A.MAIN_START, "center": A.MAIN_CENTER, "end": A.MAIN_END, "between": A.MAIN_BETWEEN, "around": A.MAIN_AROUND}
_CROSS = {"start": A.CROSS_START, "center": A.CROSS_CENTER, "end": A.CROSS_END, "stretch": A.CROSS_STRETCH}


@dataclass
class Ctx:
    lang: str = "fa"
    dark: bool = False
    accent: str = "sage"
    jal: bool = True
    week_start: int = 5
    manual_rtl: bool = False  # we mirror layouts ourselves (the platform stays left-to-right)
    fonts: bool = False  # Vazirmatn available
    width: float = 420.0
    island: Any = None  # ui.island.Island - the floating pill drawn on top of every screen
    glass: str = "full"  # liquid-glass look: "full" (blurred key surfaces) | "lite" (translucent, no blur) | "off" (solid)
    pal: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.glass not in ("full", "lite", "off"):
            self.glass = "full"
        if not self.pal:
            self.pal = theme.palette(self.accent, self.dark, self.glass)

    @property
    def glassy(self) -> bool:
        return self.glass != "off"

    def alpha(self, color: str, a: float) -> str:
        return theme.with_alpha(self.pal.get(color, color), a)

    # ---- language helpers
    @property
    def rtl(self) -> bool:
        return i18n.is_rtl(self.lang)

    def t(self, key: str, **kw: Any) -> str:
        return i18n.t(key, self.lang, **kw)

    def n(self, v: Any) -> str:
        return util.digits(v, self.lang)

    def fnum(self, x: float) -> str:
        """One-decimal number with a Persian decimal separator when needed."""
        s = util.digits(f"{x:.1f}".rstrip("0").rstrip("."), self.lang)
        return s.replace(".", "٫") if self.lang == "fa" else s

    def date(self, d: date, style: str = "long") -> str:
        return jalali.format_day(d, self.lang, self.jal, style)

    def day_num(self, d: date) -> int:
        return jalali.ymd(d, self.jal)[2]

    # ---- style helpers
    def c(self, name: str | None) -> str | None:
        return self.pal.get(name, name) if name else None

    def font(self, weight: str) -> tuple[str | None, Any]:
        if self.fonts:
            return {"regular": "Vazir", "medium": "VazirM", "bold": "VazirB"}.get(weight, "Vazir"), None
        return None, {"regular": None, "medium": A.W500, "bold": A.BOLD}.get(weight)

    def energy(self, score: int | None) -> str:
        return theme.energy_color(score, self.dark)

    def tone(self, name: str) -> tuple[str, str]:
        return theme.tone(self.pal, name)

    def dir_icon(self, kind: str) -> str:
        """Arrow / chevron pointing the right way for the reading direction."""
        ltr, rtl = {
            "back": ("ARROW_BACK", "ARROW_FORWARD"),
            "forward": ("ARROW_FORWARD", "ARROW_BACK"),
            "prev": ("CHEVRON_LEFT", "CHEVRON_RIGHT"),
            "next": ("CHEVRON_RIGHT", "CHEVRON_LEFT"),
        }[kind]
        flipped = self.rtl and not (ICONS_MIRROR and not self.manual_rtl)
        return rtl if flipped else ltr


# --------------------------------------------------------------------------- primitives
def _flip(ctx: Ctx, a: str) -> str:
    return {"start": "end", "end": "start"}.get(a, a) if ctx.manual_rtl else a


def text(ctx: Ctx, value: Any, size: float = 15, weight: str = "regular", color: str = "text", align: str | None = None,
         max_lines: int | None = None, selectable: bool = False, italic: bool = False, expand: bool = False) -> Any:
    fam, w = ctx.font(weight)
    if align is None and ctx.manual_rtl:
        align = "start"
    ta = None
    if align:
        if ctx.manual_rtl:
            ta = {"start": A.TEXT_RIGHT, "end": A.TEXT_LEFT, "center": A.TEXT_CENTER}[align]
        else:
            ta = {"start": A.TEXT_START, "end": A.TEXT_END, "center": A.TEXT_CENTER}[align]
    return mk(ft.Text, value=str(value), size=size, color=ctx.c(color), font_family=fam, weight=w, text_align=ta,
              max_lines=max_lines, overflow=A.ELLIPSIS if max_lines else None, selectable=selectable or None,
              italic=italic or None, expand=expand or None)


def row(ctx: Ctx, controls: Iterable[Any], spacing: float = 8, align: str = "start", v: str = "center", wrap: bool = False,
        run_spacing: float = 8, expand: bool = False, width: float | None = None) -> Any:
    items = [c for c in controls if c is not None]
    if ctx.manual_rtl:
        items.reverse()
    return mk(ft.Row, controls=items, spacing=spacing, alignment=_MAIN[_flip(ctx, align)], vertical_alignment=_CROSS[v],
              wrap=wrap or None, run_spacing=run_spacing if wrap else None, expand=expand or None, width=width)


def ltr_row(ctx: Ctx, controls: Iterable[Any], spacing: float = 8, align: str = "center", v: str = "center") -> Any:
    """A row whose children always read left-to-right on screen (clock digits, PIN pad)."""
    items = [c for c in controls if c is not None]
    if ctx.rtl and not ctx.manual_rtl:
        items.reverse()  # the platform mirrors rows in RTL; undo it
    return mk(ft.Row, controls=items, spacing=spacing, alignment=_MAIN[align], vertical_alignment=_CROSS[v])


def col(ctx: Ctx, controls: Iterable[Any], spacing: float = 8, align: str = "start", h: str = "stretch", scroll: bool = False,
        expand: bool = False, width: float | None = None, height: float | None = None) -> Any:
    items = [c for c in controls if c is not None]
    for c in items:  # a child of a column is already full-width (stretch); `expand` there would mean vertical flex = unbounded-height error
        if getattr(c, "expand", None):
            c.expand = None
    return mk(ft.Column, controls=items, spacing=spacing, alignment=_MAIN[align],
              horizontal_alignment=_CROSS[_flip(ctx, h)], scroll=A.SCROLL if scroll else None, expand=expand or None,
              width=width, height=height)


def box(ctx: Ctx, content: Any = None, padding: Any = None, bg: str | None = None, radius: float = 16, border: bool = False,
        border_color: str | None = None, on_click: Callable | None = None, width: float | None = None,
        height: float | None = None, expand: bool | None = None, margin: Any = None, align: Any = None,
        gradient: Any = None, shadow: Any = False, opacity: float | None = None, clip: bool = False, **extra: Any) -> Any:
    kw: dict[str, Any] = dict(
        content=content, padding=padding, bgcolor=ctx.c(bg), border_radius=radius, width=width, height=height,
        expand=expand or None, margin=margin, alignment=align, gradient=gradient, opacity=opacity,
    )
    if border:
        kw["border"] = C.border(ctx.c(border_color or "border"))
    if shadow is True:
        kw["shadow"] = C.shadow(ctx.pal["shadow"])
    elif shadow:  # a ready-made BoxShadow
        kw["shadow"] = shadow
    if on_click:
        kw["on_click"] = on_click
        kw["ink"] = True
    if clip:
        kw["clip_behavior"] = A.CLIP
    kw.update(extra)
    return mk(ft.Container, **kw)


def space(ctx: Ctx, h: float = 0, w: float = 0) -> Any:
    return mk(ft.Container, height=h or None, width=w or None)


def divider(ctx: Ctx) -> Any:
    return box(ctx, height=1, bg="border", radius=0)


def icon(ctx: Ctx, name: str, size: float = 22, color: str = "muted") -> Any:
    return mk(ft.Icon, C.ic(SEMANTIC.get(name, name)), size=size, color=ctx.c(color))


def badge(ctx: Ctx, name: str, tone: str = "accent", size: float = 44, icon_size: float | None = None) -> Any:
    fg, soft = ctx.tone(tone)
    return box(ctx, icon(ctx, name, icon_size or size * 0.5, fg), width=size, height=size, bg=soft, radius=size * 0.34,
               align=C.center())


def avatar(ctx: Ctx, emoji: str, size: float = 48) -> Any:
    return box(ctx, text(ctx, emoji, size * 0.5, align="center"), width=size, height=size, bg="accent_soft",
               radius=size / 2, align=C.center())


def glass(ctx: Ctx, content: Any = None, padding: Any = 16, radius: float = 22, tint: str | None = None, strength: str = "normal",
          blur: float = 0, on_click: Callable | None = None, border: bool = True, shadow: bool = True, **extra: Any) -> Any:
    """A frosted-glass panel: translucent fill with a diagonal specular highlight, a light rim and a soft shadow.
    `blur` (sigma) blurs what is behind it - only in the "full" style, so use it on a few key surfaces (bars, dialogs).
    `tint` is a tone name (sky, rose, good ...) that colours the glass. In the "off" style this is a plain solid card."""
    if not ctx.glassy:
        return box(ctx, content, padding=padding, bg=f"t_{tint}_soft" if tint else "surface", radius=radius, border=border,
                   shadow=shadow and not ctx.dark, on_click=on_click, **extra)
    level = {"soft": 0, "normal": 1, "strong": 2}[strength]
    white = "#FFFFFF"
    if ctx.dark:
        a1, a2 = (0.10, 0.04, 0.18)[level], (0.04, 0.02, 0.10)[level]
    else:
        a1, a2 = (0.45, 0.62, 0.84)[level], (0.22, 0.38, 0.66)[level]
    if tint:
        fg = ctx.tone(tint)[0]
        first, second = theme.with_alpha(fg, 0.30 if ctx.dark else 0.34), theme.with_alpha(white, a2 * (0.5 if ctx.dark else 0.9))
    else:
        first, second = theme.with_alpha(white, a1), theme.with_alpha(white, a2)
    kw: dict[str, Any] = dict(gradient=C.gradient([first, second], (-1, -1), (1, 1)),
                              shadow=C.shadow(ctx.pal["shadow"], blur=28, dy=10) if shadow else False)
    if blur and ctx.glass == "full":
        kw["blur"] = C.blur(blur)
    kw.update(extra)
    return box(ctx, content, padding=padding, radius=radius, border=border, on_click=on_click, clip=bool(kw.get("blur")), **kw)


def card(ctx: Ctx, content: Any, padding: Any = 16, on_click: Callable | None = None, bg: str = "surface",
         border: bool = True, gradient: Any = None, radius: float = 22, shadow: bool | None = None, tint: str | None = None,
         **extra: Any) -> Any:
    if ctx.glassy and bg == "surface" and gradient is None:
        return glass(ctx, content, padding=padding, radius=radius, tint=tint, on_click=on_click, border=border,
                     shadow=True if shadow is None else shadow, **extra)
    lift = (not ctx.dark and border) if shadow is None else shadow  # a soft lift in the light theme only
    return box(ctx, content, padding=padding, bg=bg, radius=radius, border=border, on_click=on_click, gradient=gradient,
               shadow=lift, **extra)


def hero(ctx: Ctx, content: Any, padding: Any = 20, radius: float = 30) -> Any:
    """A big gradient panel (accent drifting to blue). Text on it should use the `on_accent` colour."""
    if not ctx.glassy:
        grad = C.gradient([ctx.pal["hero_a"], ctx.pal["hero_b"]], (-1, -1), (1, 1))
        return box(ctx, content, padding=padding, bg="accent", radius=radius, gradient=grad, shadow=not ctx.dark)
    grad = C.gradient([theme.with_alpha(ctx.pal["hero_a"], 0.96), theme.with_alpha(ctx.pal["hero_b"], 0.86)], (-1, -1), (1, 1))
    sheen = box(ctx, None, width=260, height=260, radius=130, gradient=C.radial([theme.with_alpha("#FFFFFF", 0.34), theme.with_alpha("#FFFFFF", 0.0)]),
                left=-70, top=-110)
    glow = box(ctx, None, width=200, height=200, radius=100, gradient=C.radial([theme.with_alpha("#FFFFFF", 0.16), theme.with_alpha("#FFFFFF", 0.0)]),
               right=-60, bottom=-90)
    body = mk(ft.Stack, controls=[sheen, glow, box(ctx, content, padding=padding, radius=0)])
    return box(ctx, body, gradient=grad, radius=radius, clip=True, border=True, border_color=theme.with_alpha("#FFFFFF", 0.38),
               shadow=C.shadow(theme.with_alpha(ctx.pal["hero_a"], 0.35 if not ctx.dark else 0.25), blur=30, dy=12))


def pill(ctx: Ctx, label: str, tone: str = "accent") -> Any:
    fg, soft = ctx.tone(tone)
    return box(ctx, text(ctx, label, 12, "medium", fg), padding=C.pad(10, 3, 10, 3), bg=soft, radius=999)


def link(ctx: Ctx, label: str, on_click: Callable, color: str = "accent_strong") -> Any:
    return box(ctx, text(ctx, label, 14, "medium", color), padding=C.pad(6, 4, 6, 4), radius=8, on_click=on_click)


# --------------------------------------------------------------------------- controls
def button(ctx: Ctx, label: str, on_click: Callable | None = None, kind: str = "primary", icon_name: str | None = None,
           expand: bool = False, size: str = "md", disabled: bool = False) -> Any:
    styles = {
        "primary": ("accent", "on_accent", False),
        "soft": ("accent_soft", "accent_strong", False),
        "ghost": (None, "muted", True),
        "danger": ("bad_soft", "bad", False),
        "outline": (None, "accent_strong", True),
    }
    bg, fg, bordered = styles[kind]
    inner = row(ctx, [icon(ctx, icon_name, 18, fg) if icon_name else None, text(ctx, label, 15 if size == "md" else 13.5, "medium", fg)],
                spacing=8, align="center")
    pd = C.pad(22, 14, 22, 14) if size == "md" else C.pad(14, 8, 14, 8)
    grad = C.gradient([ctx.pal["accent"], ctx.pal["hero_b"]], (-1, 0), (1, 0)) if kind == "primary" else None
    extra: dict[str, Any] = {}
    if kind == "primary" and ctx.glassy and not disabled:  # a glossy "jelly" button: light rim + coloured glow
        extra = dict(shadow=C.shadow(theme.with_alpha(ctx.pal["accent"], 0.38), blur=18, dy=7))
        bordered = True
    return box(ctx, inner, padding=pd, bg=bg, radius=16 if size == "md" else 13, border=bordered,
               border_color="accent" if kind == "outline" else ("#66FFFFFF" if kind == "primary" else "border"), gradient=grad, **extra,
               on_click=None if disabled else on_click, expand=expand or None, align=C.center(), opacity=0.45 if disabled else None)


def icon_button(ctx: Ctx, name: str, on_click: Callable | None, color: str = "muted", size: float = 22, tooltip: str | None = None) -> Any:
    return mk(ft.IconButton, icon=C.ic(SEMANTIC.get(name, name)), icon_color=ctx.c(color), icon_size=size, on_click=on_click, tooltip=tooltip)


def field(ctx: Ctx, label: str | None = None, value: str = "", on_change: Callable[[str], None] | None = None,
          multiline: bool = False, lines: int = 1, hint: str | None = None, keyboard: Any = None, password: bool = False,
          autofocus: bool = False, max_length: int | None = None, on_blur: Callable | None = None,
          on_submit: Callable | None = None, width: float | None = None, expand: bool | None = None, size: float = 15,
          text_align: str | None = None, reveal: bool = False) -> Any:
    def _changed(e: Any) -> None:
        if on_change:
            on_change(e.control.value or "")

    ta = None
    if text_align == "center":
        ta = A.TEXT_CENTER
    elif ctx.manual_rtl:
        ta = A.TEXT_RIGHT
    fam, _ = ctx.font("regular")
    return mk(
        ft.TextField, value=value or "", label=label, hint_text=hint, multiline=multiline or None,
        min_lines=lines if multiline else None, max_lines=(lines + 5) if multiline else None, on_change=_changed,
        on_blur=on_blur, on_submit=on_submit, border_radius=14, filled=True, fill_color=ctx.c("surface"),
        border_color=ctx.c("border"), focused_border_color=ctx.c("accent"), border_width=1,
        content_padding=C.pad(16, 14, 16, 14), text_size=size, text_align=ta, keyboard_type=keyboard,
        password=password or None, can_reveal_password=True if (password and reveal) else None,
        autofocus=autofocus or None, max_length=max_length, width=width, expand=expand,
        cursor_color=ctx.c("accent"), text_style=mk(ft.TextStyle, font_family=fam, color=ctx.c("text")) if fam else None,
    )


def chip(ctx: Ctx, label: str, selected: bool = False, on_click: Callable | None = None, icon_name: str | None = None) -> Any:
    fg = "accent_strong" if selected else "muted"
    inner = row(ctx, [icon(ctx, icon_name, 16, fg) if icon_name else None, text(ctx, label, 13.5, "medium" if selected else "regular", fg)], spacing=6)
    return box(ctx, inner, padding=C.pad(14, 8, 14, 8), bg="accent_soft" if selected else "surface2", radius=999, border=True,
               border_color="accent" if selected else "border", on_click=on_click)


def chips(ctx: Ctx, options: list[tuple[str, str]], selected: Any, on_select: Callable[[str], None], multi: bool = False) -> Any:
    items = []
    for key, label in options:
        sel = key in selected if multi else key == selected
        items.append(chip(ctx, label, sel, (lambda e, k=key: on_select(k))))
    return row(ctx, items, spacing=8, wrap=True, run_spacing=8)


def segmented(ctx: Ctx, options: list[tuple[str, str]], value: str, on_change: Callable[[str], None]) -> Any:
    segs = []
    for key, label in options:
        sel = key == value
        if ctx.glassy:  # the selected option is a bright glass "lens" sitting in a dark-ish groove
            thumb = dict(bg="#E6FFFFFF" if not ctx.dark else "#33FFFFFF", shadow=True, border=True, border_color="#99FFFFFF" if not ctx.dark else "#40FFFFFF") if sel else {}
            fg = "accent_strong" if sel else "muted"
        else:
            thumb, fg = (dict(bg="accent"), "on_accent") if sel else ({}, "muted")
        segs.append(box(ctx, text(ctx, label, 14, "medium", fg, align="center"), padding=C.pad(10, 10, 10, 10), radius=12, expand=True,
                        align=C.center(), on_click=(lambda e, k=key: on_change(k)), **thumb))
    return box(ctx, row(ctx, segs, spacing=4), padding=4, bg="surface2", radius=16)


def switch_row(ctx: Ctx, title: str, value: bool, on_change: Callable[[bool], None], subtitle: str | None = None,
               icon_name: str | None = None) -> Any:
    sw = mk(ft.Switch, value=bool(value), on_change=lambda e: on_change(bool(e.control.value)), active_color=ctx.c("accent"))
    label = col(ctx, [text(ctx, title, 15, "medium"), text(ctx, subtitle, 12.5, color="muted") if subtitle else None], spacing=2, expand=True)
    return row(ctx, [icon(ctx, icon_name, 22, "muted") if icon_name else None, label, sw], spacing=12)


def stat(ctx: Ctx, value: str, label: str, tone: str = "accent", icon_name: str | None = None) -> Any:
    fg, soft = ctx.tone(tone)
    return box(ctx, col(ctx, [icon(ctx, icon_name, 20, fg) if icon_name else None, text(ctx, value, 22, "bold", fg, align="center"),
                              text(ctx, label, 11.5, color="muted", align="center", max_lines=2)],
                        spacing=2, h="center"), padding=C.pad(8, 12, 8, 12), bg=soft, radius=20, expand=True)


def ring(ctx: Ctx, value: float, size: float = 84, stroke: float = 8, center: Any = None, color: str = "on_accent",
         track: str = "glass") -> Any:
    """A circular progress indicator with `center` drawn inside it."""
    v = max(0.0, min(1.0, float(value)))
    r = mk(ft.ProgressRing, value=v, stroke_width=stroke, width=size, height=size, color=ctx.c(color), bgcolor=ctx.c(track))
    mid = box(ctx, center, width=size, height=size, radius=0, align=C.center())
    return mk(ft.Stack, controls=[r, mid], width=size, height=size)


def progress_bar(ctx: Ctx, value: float, height: float = 8, color: str = "accent") -> Any:
    v = max(0.0, min(1.0, value))
    parts = []
    if v > 0:
        parts.append(box(ctx, height=height, bg=color, radius=height / 2, expand=max(1, round(v * 1000))))
    if v < 1:
        parts.append(box(ctx, height=height, bg=None, radius=0, expand=max(1, round((1 - v) * 1000))))
    return box(ctx, mk(ft.Row, controls=parts, spacing=0), bg="surface2", radius=height / 2, height=height)


def steps_bar(ctx: Ctx, total: int, current: int) -> Any:
    segs = [box(ctx, height=5, bg="accent" if i <= current else "surface2", radius=3, expand=True) for i in range(total)]
    return row(ctx, segs, spacing=4)


# --------------------------------------------------------------------------- composite
def header(ctx: Ctx, title: str, subtitle: str | None = None, on_back: Callable | None = None, actions: Iterable[Any] = ()) -> Any:
    lead = icon_button(ctx, ctx.dir_icon("back"), lambda e: on_back(), "text", 24) if on_back else None
    if lead is not None and ctx.glassy:
        lead = glass(ctx, lead, padding=0, radius=22, strength="soft", width=46, height=46, align=C.center(), shadow=False)
    titles = col(ctx, [text(ctx, title, 22, "bold", max_lines=1), text(ctx, subtitle, 13, color="muted", max_lines=1) if subtitle else None],
                 spacing=1, expand=True)
    return box(ctx, row(ctx, [lead, titles, *actions], spacing=4), padding=C.pad(14 if not on_back else 6, 12, 10, 6))


def backdrop(ctx: Ctx) -> Any:
    """The "aurora" the glass floats over: a soft two-tone wash plus three blurred glows. Static, so it is cheap."""
    glows = ctx.pal["aurora"].split(",")
    a = 0.34 if ctx.dark else 0.52

    def blob(color: str, size: float, **pos: Any) -> Any:
        grad = C.radial([theme.with_alpha(color, a), theme.with_alpha(color, 0.0)])
        return box(ctx, None, width=size, height=size, radius=size / 2, gradient=grad, **pos)

    wash = box(ctx, None, gradient=C.gradient([ctx.pal["bg_a"], ctx.pal["bg_b"]], (-1, -1), (1, 1)), radius=0, left=0, top=0, right=0, bottom=0)
    return mk(ft.Stack, controls=[wash, blob(glows[0], 460, left=-150, top=-110), blob(glows[1], 420, right=-170, top=210),
                                  blob(glows[2], 480, left=-120, bottom=-170)], left=0, top=0, right=0, bottom=0)


def screen(ctx: Ctx, body: Iterable[Any], title: str | None = None, subtitle: str | None = None,
           on_back: Callable | None = None, actions: Iterable[Any] = (), bottom: Any = None, pad_body: bool = True,
           main: bool = False) -> list[Any]:
    """`main=True` marks one of the four tabs: it reserves room at the top for the idle dynamic island.
    `bottom` (the tab bar / a wizard's buttons) floats over the content, which scrolls underneath it."""
    parts: list[Any] = []
    if main and ctx.island is not None:
        parts.append(space(ctx, 50))
    if title is not None or on_back:
        parts.append(header(ctx, title or "", subtitle, on_back, actions))
    inner = col(ctx, body, spacing=14)
    pad = C.pad(20, 6, 20, 28 + (BOTTOM_ROOM if bottom is not None else 0)) if pad_body else 0
    parts.append(mk(ft.Column, controls=[box(ctx, inner, padding=pad)], scroll=A.SCROLL, expand=True, spacing=0,
                    horizontal_alignment=A.CROSS_STRETCH))
    # inside a Stack the page must not be `expand`ed (Expanded needs a Flex parent): the Column simply fills the loose max height
    page = mk(ft.Column, controls=parts, spacing=0, horizontal_alignment=A.CROSS_STRETCH)
    wide = ctx.width > config.MAX_CONTENT_WIDTH + 1  # wide desktop window: keep the content in a calm centred column
    if wide:
        page = mk(ft.Row, controls=[box(ctx, page, width=config.MAX_CONTENT_WIDTH, radius=0)], alignment=A.MAIN_CENTER,
                  vertical_alignment=A.CROSS_STRETCH, spacing=0)
    layers = [page]
    if bottom is not None:
        shelf = box(ctx, bottom, width=config.MAX_CONTENT_WIDTH, radius=0) if wide else bottom
        layers.append(mk(ft.Row, controls=[shelf], alignment=A.MAIN_CENTER, left=0, right=0, bottom=0) if wide else
                      box(ctx, bottom, radius=0, left=0, right=0, bottom=0))
    if ctx.island is not None:
        layers.append(ctx.island.build(ctx, main))
    # No `expand` on anything that sits in a Stack / SafeArea: the page Column already fills the available height.
    stack = mk(ft.Stack, controls=layers)
    if not ctx.glassy:
        return [mk(C.cls_or("SafeArea"), content=stack, expand=True)]  # a direct child of the View may expand
    return [mk(ft.Stack, controls=[backdrop(ctx), mk(C.cls_or("SafeArea"), content=stack)], expand=True)]


def section_title(ctx: Ctx, title: str, action_label: str | None = None, on_action: Callable | None = None) -> Any:
    return row(ctx, [text(ctx, title, 16, "bold", expand=True), link(ctx, action_label, on_action) if action_label else None], spacing=4)


def tile(ctx: Ctx, title: str, subtitle: str | None = None, icon_name: str = "circle", tone: str = "accent", trailing: Any = None,
         on_click: Callable | None = None, chevron: bool = True) -> Any:
    right = trailing if trailing is not None else (icon(ctx, ctx.dir_icon("next"), 20, "faint") if chevron and on_click else None)
    body = col(ctx, [text(ctx, title, 15.5, "medium", max_lines=2), text(ctx, subtitle, 12.5, color="muted", max_lines=2) if subtitle else None],
               spacing=2, expand=True)
    return card(ctx, row(ctx, [badge(ctx, icon_name, tone, 42), body, right], spacing=14), padding=C.pad(14, 12, 14, 12), on_click=on_click)


def empty(ctx: Ctx, icon_name: str, title: str, body: str, action_label: str | None = None, on_action: Callable | None = None) -> Any:
    return col(ctx, [
        space(ctx, 24), box(ctx, badge(ctx, icon_name, "accent", 72, 34), align=C.center()),
        text(ctx, title, 18, "bold", align="center"), text(ctx, body, 14, color="muted", align="center"),
        space(ctx, 4), box(ctx, button(ctx, action_label, on_action, "soft", "ADD"), align=C.center()) if action_label else None,
    ], spacing=10, h="center")


def quote_card(ctx: Ctx, body: str, caption: str | None = None, tone: str = "accent") -> Any:
    fg, soft = ctx.tone(tone)
    inner = col(ctx, [icon(ctx, "quote", 22, fg), text(ctx, body, 17, "medium", expand=False),
                      text(ctx, caption, 12.5, color="muted") if caption else None], spacing=8)
    if ctx.glassy:
        return glass(ctx, inner, padding=20, radius=26, tint=tone, strength="normal")
    grad = C.gradient([soft, ctx.c("surface")], (-1, -1), (1, 1))
    return card(ctx, inner, padding=20, gradient=grad, bg=soft, radius=24)


def energy_picker(ctx: Ctx, value: int | None, on_pick: Callable[[int], None]) -> Any:
    def cell(i: int) -> Any:
        sel = value == i
        base = ctx.energy(i)
        fg = "#10181A" if ctx.dark else ("#FFFFFF" if i <= 3 or i >= 8 else "#2A2418")
        return box(ctx, text(ctx, ctx.n(i), 17, "bold" if sel else "medium", fg if sel else "text", align="center"),
                   height=48, expand=True, radius=14, bg=base if sel else theme.mix(base, ctx.pal["surface"], 0.2),
                   align=C.center(), on_click=(lambda e, i=i: on_pick(i)))
    rows = [ltr_row(ctx, [cell(i) for i in range(start, start + 5)], spacing=8, align="center") for start in (1, 6)]
    return col(ctx, rows, spacing=8)


def energy_chart(ctx: Ctx, series: list[tuple[date, int | None]], height: float = 150, on_tap: Callable[[date], None] | None = None,
                 today: date | None = None) -> Any:
    n = max(len(series), 1)
    bar_w = max(4, min(16, int((ctx.width - 72) / n) - 4))
    cells, labels = [], []
    for i, (d, s) in enumerate(series):
        fill = box(ctx, None, width=bar_w, height=max(10, round(height * s / 10)), bg=ctx.energy(s), radius=bar_w / 2) if s is not None else None
        track = box(ctx, fill, width=bar_w, height=height, bg="surface2", radius=bar_w / 2, align=C.align(0, 1),
                    border=(d == today), border_color="accent")
        cells.append(box(ctx, track, expand=True, height=height, align=C.center(), on_click=(lambda e, d=d: on_tap(d)) if on_tap else None))
        show = i == 0 or i == n - 1 or (i + 1) % 5 == 0
        labels.append(box(ctx, text(ctx, ctx.n(ctx.day_num(d)), 10.5, color="faint", align="center") if show else None, expand=True, align=C.center()))
    return col(ctx, [row(ctx, cells, spacing=0, v="end"), row(ctx, labels, spacing=0)], spacing=6)


def time_stepper(ctx: Ctx, hhmm: str, on_change: Callable[[str], None]) -> Any:
    h, m = util.parse_hhmm(hhmm, (8, 0))

    def unit(val: int, up: Callable, down: Callable) -> Any:
        return col(ctx, [icon_button(ctx, "KEYBOARD_ARROW_UP", up, "accent_strong", 22),
                         text(ctx, ctx.n(f"{val:02d}"), 24, "bold", align="center"),
                         icon_button(ctx, "KEYBOARD_ARROW_DOWN", down, "accent_strong", 22)], spacing=0, h="center")

    hour = unit(h, lambda e: on_change(util.fmt_hhmm((h + 1) % 24, m)), lambda e: on_change(util.fmt_hhmm((h - 1) % 24, m)))
    minute = unit(m, lambda e: on_change(util.fmt_hhmm(h, (m + 5) % 60)), lambda e: on_change(util.fmt_hhmm(h, (m - 5) % 60)))
    return ltr_row(ctx, [hour, text(ctx, ":", 24, "bold", "muted"), minute], spacing=6)


def nav_bar(ctx: Ctx, items: list[tuple[str, str, str]], current: str, on_select: Callable[[str], None], badges: dict | None = None) -> Any:
    """A floating glass pill: the selected tab is a glowing lens with icon + label, the others are icons only."""
    cells = []
    for key, icon_name, label in items:
        sel = key == current
        inner = row(ctx, [icon(ctx, icon_name, 22, "on_accent" if sel else "muted"),
                          text(ctx, label, 13, "medium", "on_accent") if sel else None], spacing=6, align="center")
        look: dict[str, Any] = {}
        if sel:
            look = dict(bg="accent", gradient=C.gradient([ctx.pal["accent"], ctx.pal["hero_b"]], (-1, -1), (1, 1)))
            if ctx.glassy:
                look.update(border=True, border_color="#66FFFFFF", shadow=C.shadow(theme.with_alpha(ctx.pal["accent"], 0.40), blur=16, dy=5))
        pillbox = box(ctx, inner, padding=C.pad(18 if sel else 14, 11, 18 if sel else 14, 11), radius=999, animate=C.animation(260),
                      on_click=(lambda e, k=key: on_select(k)), **look)
        top: Any = pillbox
        if badges and badges.get(key):
            dot = box(ctx, None, width=10, height=10, bg="bad", radius=5, border=True, border_color="#FFFFFFFF", right=8, top=6)
            top = mk(ft.Stack, controls=[pillbox, dot])
        cells.append(top)
    return glass(ctx, row(ctx, cells, spacing=2, align="around"), padding=C.pad(8, 8, 8, 8), radius=34, strength="strong", blur=26,
                 margin=C.pad(16, 4, 16, 12))


class DatePicker:
    """A month grid. Place `.host` in a dialog; call `.render()` after external changes."""

    def __init__(self, ctx: Ctx, selected: date, on_pick: Callable[[date], None], min_day: date | None = None,
                 max_day: date | None = None, page: Any = None):
        self.ctx, self.selected, self.on_pick = ctx, selected, on_pick
        self.min_day, self.max_day, self.page = min_day, max_day, page
        self.cursor = jalali.month_bounds(selected, ctx.jal)[0]
        self.host = box(ctx, None)
        self.render()

    def _shift(self, n: int) -> None:
        self.cursor = jalali.shift_month(self.cursor, n, self.ctx.jal)
        self.refresh()

    def _pick(self, d: date) -> None:
        self.selected = d
        self.on_pick(d)
        self.refresh()

    def refresh(self) -> None:
        self.render()
        if self.page is not None:
            self.page.update()

    def render(self) -> None:
        ctx = self.ctx
        head = row(ctx, [icon_button(ctx, ctx.dir_icon("prev"), lambda e: self._shift(-1), "text"),
                         text(ctx, jalali.month_label(self.cursor, ctx.lang, ctx.jal), 16, "bold", align="center", expand=True),
                         icon_button(ctx, ctx.dir_icon("next"), lambda e: self._shift(1), "text")], spacing=0)
        names = row(ctx, [box(ctx, text(ctx, h, 12, color="faint", align="center"), expand=True, align=C.center())
                          for h in jalali.weekday_headers(ctx.lang, ctx.week_start)], spacing=0)
        weeks = []
        for week in jalali.month_matrix(self.cursor, ctx.jal, ctx.week_start):
            cells = []
            for d in week:
                if d is None:
                    cells.append(box(ctx, None, expand=True, height=40))
                    continue
                sel = d == self.selected
                off = bool((self.min_day and d < self.min_day) or (self.max_day and d > self.max_day))
                cells.append(box(ctx, text(ctx, ctx.n(ctx.day_num(d)), 14, "bold" if sel else "regular",
                                           "on_accent" if sel else ("faint" if off else "text"), align="center"),
                                 expand=True, height=40, radius=12, bg="accent" if sel else None, align=C.center(),
                                 on_click=None if off else (lambda e, d=d: self._pick(d))))
            weeks.append(row(ctx, cells, spacing=2))
        self.host.content = col(ctx, [head, names, *weeks], spacing=4)
