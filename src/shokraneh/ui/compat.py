"""Thin compatibility layer over Flet.

The app targets Flet 1.1, but a keyword, enum member or icon name can differ slightly between Flet releases.
`mk()` drops keyword arguments the installed Flet does not know and every enum / icon / helper lookup has a fallback,
so a small API difference costs a bit of styling instead of crashing the app.
"""
from __future__ import annotations

import re
from typing import Any

import flet as ft

_UNKNOWN_KW = re.compile(r"unexpected keyword argument ['\"]?(\w+)['\"]?")


def mk(cls: Any, *args: Any, **kw: Any) -> Any:
    """Construct a Flet control; `None` means "not set", unknown keyword arguments are dropped."""
    kw = {k: v for k, v in kw.items() if v is not None}
    for _ in range(32):
        try:
            return cls(*args, **kw)
        except TypeError as e:
            m = _UNKNOWN_KW.search(str(e))
            if not m or m.group(1) not in kw:
                raise
            kw.pop(m.group(1))
    return cls(*args, **kw)


def enum(owner: str, *names: str) -> Any:
    holder = getattr(ft, owner, None)
    if holder is None:
        return None
    for n in names:
        v = getattr(holder, n, None)
        if v is not None:
            return v
    return None


def cls_or(name: str, fallback: Any = None) -> Any:
    return getattr(ft, name, None) or fallback or ft.Container


class A:
    """Enum members resolved once (None when this Flet does not have them)."""

    MAIN_START = enum("MainAxisAlignment", "START")
    MAIN_END = enum("MainAxisAlignment", "END")
    MAIN_CENTER = enum("MainAxisAlignment", "CENTER")
    MAIN_BETWEEN = enum("MainAxisAlignment", "SPACE_BETWEEN")
    MAIN_AROUND = enum("MainAxisAlignment", "SPACE_AROUND")
    CROSS_START = enum("CrossAxisAlignment", "START")
    CROSS_END = enum("CrossAxisAlignment", "END")
    CROSS_CENTER = enum("CrossAxisAlignment", "CENTER")
    CROSS_STRETCH = enum("CrossAxisAlignment", "STRETCH")
    SCROLL = enum("ScrollMode", "AUTO")
    TEXT_START = enum("TextAlign", "START", "LEFT")
    TEXT_END = enum("TextAlign", "END", "RIGHT")
    TEXT_LEFT = enum("TextAlign", "LEFT", "START")
    TEXT_RIGHT = enum("TextAlign", "RIGHT", "END")
    TEXT_CENTER = enum("TextAlign", "CENTER")
    ELLIPSIS = enum("TextOverflow", "ELLIPSIS")
    W500 = enum("FontWeight", "W_500", "BOLD")
    W600 = enum("FontWeight", "W_600", "BOLD")
    BOLD = enum("FontWeight", "W_700", "BOLD")
    THEME_LIGHT = enum("ThemeMode", "LIGHT")
    THEME_DARK = enum("ThemeMode", "DARK")
    KB_NUMBER = enum("KeyboardType", "NUMBER")
    KB_MULTILINE = enum("KeyboardType", "MULTILINE")
    CLIP = enum("ClipBehavior", "ANTI_ALIAS", "HARD_EDGE")


# --------------------------------------------------------------------------- icons
def ic(name: str) -> Any:
    icons = getattr(ft, "Icons", None) or getattr(ft, "icons", None)
    if icons is None:
        return None
    for n in (name, name.lower()):
        v = getattr(icons, n, None)
        if v is not None:
            return v
    return getattr(icons, "CIRCLE", None) or getattr(icons, "circle", None)


# --------------------------------------------------------------------------- geometry helpers
def align(x: float, y: float) -> Any:
    try:
        return ft.Alignment(x, y)
    except Exception:
        return getattr(ft, "alignment", None) and ft.alignment.Alignment(x, y)


CENTER = None  # filled lazily (needs ft.Alignment)


def center() -> Any:
    return align(0, 0)


def pad(l: float = 0, t: float = 0, r: float = 0, b: float = 0) -> Any:
    P = getattr(ft, "Padding", None)
    try:
        return P(left=l, top=t, right=r, bottom=b)
    except Exception:
        return ft.padding.only(left=l, top=t, right=r, bottom=b)


def border(color: str, width: float = 1) -> Any:
    B = getattr(ft, "Border", None)
    if B is not None and hasattr(B, "all"):
        return B.all(width, color)
    return ft.border.all(width, color)


def border_side(color: str, width: float = 1) -> Any:
    S = getattr(ft, "BorderSide", None)
    return S(width, color) if S else None


def border_bottom(color: str, width: float = 1) -> Any:
    B = getattr(ft, "Border", None)
    side = border_side(color, width)
    try:
        return B(bottom=side)
    except Exception:
        return ft.border.only(bottom=side)


def shadow(color: str, blur: float = 18, dy: float = 4, spread: float = 0) -> Any:
    BS = getattr(ft, "BoxShadow", None)
    if BS is None:
        return None
    try:
        return mk(BS, spread_radius=spread, blur_radius=blur, color=color, offset=ft.Offset(0, dy))
    except Exception:
        return None


def animation(ms: int = 300, curve: str = "EASE_OUT_CUBIC") -> Any:
    """Implicit-animation spec for Container(animate=...). Falls back to a plain duration in milliseconds."""
    Anim = getattr(ft, "Animation", None)
    cur = enum("AnimationCurve", curve, "EASE_OUT", "EASE_IN_OUT")
    if Anim is not None and cur is not None:
        try:
            return Anim(duration=ms, curve=cur)
        except Exception:
            pass
    return ms


def gradient(colors: list[str], begin: tuple = (-1, -1), end: tuple = (1, 1)) -> Any:
    G = getattr(ft, "LinearGradient", None)
    if G is None:
        return None
    try:
        return mk(G, begin=align(*begin), end=align(*end), colors=colors)
    except Exception:
        return None


def radial(colors: list[str], radius: float = 0.5, center: tuple = (0, 0)) -> Any:
    """A round glow: colours run from the centre outwards (use a transparent last colour for a soft edge)."""
    G = getattr(ft, "RadialGradient", None)
    if G is None:
        return None
    try:
        return mk(G, center=align(*center), radius=radius, colors=colors)
    except Exception:
        return None


def blur(sigma: float) -> Any:
    """Backdrop blur for Container(blur=...) - Flet takes a plain number."""
    return float(sigma)
