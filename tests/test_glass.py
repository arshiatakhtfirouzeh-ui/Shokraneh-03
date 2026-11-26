"""The liquid-glass look: palette, glass surfaces, floating bars, glass dialogs and the look settings."""
import pytest

import fake_flet
import ui_harness as H
from ui_harness import make_app

from shokraneh.ui import kit, theme
from shokraneh.ui.screens import cal, energy, lock, settings


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    H.freeze(monkeypatch)
    H.offline(monkeypatch)
    fake_flet.DROPPED.clear()
    yield


def alpha_of(color: str) -> int:
    assert color.startswith("#") and len(color) == 9, color
    return int(color[1:3], 16)


def named(app, name):
    return [c for c, _ in H.controls(app) if c._name == name]


@pytest.mark.parametrize("dark", [False, True])
def test_palette_modes(dark):
    solid = theme.palette("sage", dark, "off")
    glassy = theme.palette("sage", dark, "full")
    assert solid["surface"].startswith("#") and len(solid["surface"]) == 7 and "aurora" not in solid
    for k in ("surface", "surface2", "border", "accent_soft", "t_sky_soft", "t_rose_soft", "good_soft"):
        assert alpha_of(glassy[k]) < 255, k
    assert len(glassy["aurora"].split(",")) == 3 and glassy["bg_a"] != glassy["bg_b"]
    # soft colours keep their hue: the translucent tone is the tone colour with an alpha
    assert glassy["t_sky_soft"][3:] == glassy["t_sky"][1:]


def test_mix_accepts_translucent_colours():
    assert theme.mix("#112233", "#80FFFFFF", 0.5) == theme.mix("#112233", "#FFFFFF", 0.5)
    assert theme.with_alpha("#112233", 0.5) == "#80112233" and theme.with_alpha("#80112233", 1) == "#FF112233"


def test_glass_card_is_translucent_with_a_highlight(tmp_path):
    app = make_app(tmp_path)
    c = app.ctx()
    card = kit.card(c, kit.text(c, "x"))
    assert card.gradient is not None and all(alpha_of(col) < 255 for col in card.gradient.colors)
    assert getattr(card, "blur", None) is None  # cards are never blurred (cost), only key surfaces
    tinted = kit.card(c, kit.text(c, "x"), tint="sky")
    assert tinted.gradient.colors[0][3:] == c.tone("sky")[0][1:]


@pytest.mark.parametrize("mode,blurred", [("full", True), ("lite", False), ("off", False)])
def test_nav_bar_blur_per_mode(tmp_path, mode, blurred):
    app = make_app(tmp_path)
    app.store.set("glass", mode)
    app.refresh()
    has_blur = [c for c in named(app, "Container") if getattr(c, "blur", None)]
    assert bool(has_blur) is blurred
    assert not H.view_layout_errors(app)


def test_off_mode_is_solid_and_has_no_backdrop(tmp_path):
    app = make_app(tmp_path)
    app.store.set("glass", "off")
    app.refresh()
    assert app.ctx().pal["surface"] == "#FFFFFF" or app.ctx().dark
    assert not any(getattr(c, "gradient", None) is not None and c._name == "Stack" for c in named(app, "Stack"))
    top = app.page.views[-1].controls[0]
    assert top._name == "SafeArea"


def test_full_mode_draws_the_aurora_behind_the_content(tmp_path):
    app = make_app(tmp_path)
    top = app.page.views[-1].controls[0]
    assert top._name == "Stack" and top.controls[0]._name == "Stack" and top.controls[1]._name == "SafeArea"
    glows = [c for c, _ in H.walk(top.controls[0]) if c._name == "Container" and c.gradient.__class__.__name__ == "RadialGradient"]
    assert len(glows) == 3


def test_bottom_bar_floats_over_the_scroll_area(tmp_path):
    app = make_app(tmp_path)
    c = app.ctx()
    stack = [x for x, _ in H.walk(app.page.views[-1].controls[0]) if x._name == "Stack" and len(getattr(x, "controls", [])) >= 3
             and any(getattr(k, "bottom", None) == 0 for k in x.controls)][0]
    nav = [k for k in stack.controls if getattr(k, "bottom", None) == 0]
    assert nav, "the tab bar must be positioned at the bottom of the stack"
    scroller = [x for x in named(app, "Column") if getattr(x, "scroll", None) is not None][0]
    assert scroller.controls[0].padding.bottom >= kit.BOTTOM_ROOM
    assert c.glassy


def test_dialog_is_a_transparent_flet_dialog_around_one_glass_card(tmp_path):
    app = make_app(tmp_path)
    ran = []
    app.confirm("عنوان", "متن", lambda: ran.append(1))
    dlg = app.page.dialogs[-1]
    assert dlg.bgcolor == "#00000000" and getattr(dlg, "title", None) is None and not getattr(dlg, "actions", None)
    assert dlg.content.blur and H.has_text(app, "عنوان") and H.has_text(app, "متن")
    acts = H.dialog_actions(app)
    assert len(acts) == 2
    acts[1].on_click(H.Event(acts[1]))
    assert ran == [1] and not app.page.dialogs
    assert not H.view_layout_errors(app)


def test_dialog_in_plain_mode_is_the_classic_alert_dialog(tmp_path):
    app = make_app(tmp_path)
    app.store.set("glass", "off")
    app.confirm("t", "b", lambda: None)
    dlg = app.page.dialogs[-1]
    assert getattr(dlg, "title", None) is not None and dlg.actions


@pytest.mark.parametrize("mode", ["full", "lite", "off"])
@pytest.mark.parametrize("dark", [False, True])
def test_key_screens_in_every_mode(tmp_path, mode, dark):
    app = make_app(tmp_path, dark=dark)
    app.store.set("glass", mode)
    app.refresh()
    for open_screen in (lambda: app.push(settings.view), lambda: app.push(settings.section, key="creator"), lambda: app.push(cal.view),
                        lambda: app.push(lock.setup, mode="set"), lambda: energy.sheet(app, H.TODAY), lambda: app.go("progress")):
        app.page.dialogs.clear()
        open_screen()
        assert not H.view_layout_errors(app)
    assert not fake_flet.DROPPED and not fake_flet.MISSING_ICONS


def test_look_settings_switch_the_style_and_the_island(tmp_path):
    app = make_app(tmp_path)
    app.push(settings.section, key="look")
    c = app.ctx()
    H.click(app, c.t("set_glass_lite"), exact=True)
    assert app.store.get("glass") == "lite" and app.ctx().glass == "lite"
    assert not [x for x in named(app, "Container") if getattr(x, "blur", None)]
    H.click(app, c.t("set_glass_off"), exact=True)
    assert app.ctx().glass == "off" and app.ctx().pal["surface"] in ("#FFFFFF", "#1A2023")
    sw = H.switches(app)
    island_sw = [s for s in sw if s.value is True][0]
    H.fire(island_sw)
    assert app.store.get("island") is False and app.ctx().island is None


def test_toast_uses_a_snackbar_when_the_island_is_off(tmp_path):
    app = make_app(tmp_path)
    app.store.set("island", False)
    app.refresh()
    app.toast("hello")
    assert [d._name for d in app.page.dialogs] == ["SnackBar"]


def test_pin_pad_keys_are_glass(tmp_path):
    app = make_app(tmp_path)
    app.push(lock.setup, mode="set")
    keys = [c for c in named(app, "Container") if getattr(c, "width", None) == lock.KEY_W and getattr(c, "on_click", None)]
    assert len(keys) >= 10 and all(k.gradient is not None for k in keys)
