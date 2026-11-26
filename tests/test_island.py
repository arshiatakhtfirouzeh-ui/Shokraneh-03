"""The dynamic island, the creator / copyright section and the 'today' summary."""
import pytest

import fake_flet
import ui_harness as H
from ui_harness import TODAY, make_app

from shokraneh import config, content as qc, i18n, today as today_mod
from shokraneh.ui.screens import energy, settings


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    H.freeze(monkeypatch)
    H.offline(monkeypatch)
    fake_flet.DROPPED.clear()
    yield


def pill(app):
    isl = app.ctx().pal["island"]
    found = [c for c, _ in H.controls(app) if c._name == "Container" and getattr(c, "bgcolor", None) == isl and getattr(c, "animate", None) is not None]
    assert found, "no island pill in the view"
    return found[0]


def tap(app):
    p = pill(app)
    p.on_click(H.Event(p))


def test_idle_pill_on_main_tab(tmp_path):
    app = make_app(tmp_path)
    isl = app.island
    assert isl.shown() == "idle" and isl.on_main
    p = pill(app)
    assert (p.width, p.height) == (164.0, 38.0) and p.opacity == 1.0
    assert p.content is not None  # sun / moon / mood / streak
    assert not H.view_layout_errors(app)


def test_pill_is_hidden_on_pushed_screens(tmp_path):
    app = make_app(tmp_path)
    app.push(settings.view)
    assert app.island.shown() == "hidden"
    p = pill(app)
    assert p.opacity == 0.0 and getattr(p, "on_click", None) is None and getattr(p, "content", None) is None
    app.pop()
    assert app.island.shown() == "idle"


def test_tap_opens_and_folds_away(tmp_path):
    app = make_app(tmp_path)
    tap(app)
    assert app.island.shown() == "open"
    assert H.has_text(app, app.ctx().t("island_morning"))
    assert H.has_text(app, app.ctx().t("island_today", d=app.ctx().n(app.island._status()["done"]), t=app.ctx().n(3)))
    assert pill(app).height == 142.0 and not H.view_layout_errors(app)
    tap(app)
    assert app.island.shown() == "idle" and pill(app).height == 38.0


def test_open_pill_actions(tmp_path):
    app = make_app(tmp_path)
    tap(app)
    H.click(app, app.ctx().t("island_morning"), exact=True)
    assert len(app.stack) == 2 and app.island.mode == "idle"
    app.pop()
    tap(app)
    H.click(app, app.ctx().t("island_energy"), exact=True)
    assert app.page.dialogs  # the mood sheet
    assert app.island.shown() == "idle"


def test_navigation_folds_an_open_pill(tmp_path):
    app = make_app(tmp_path)
    tap(app)
    app.go("spaces")
    assert app.island.mode == "idle"


def test_toast_morphs_the_pill_and_ends(tmp_path):
    app = make_app(tmp_path)
    app.toast("ذخیره شد ✓")
    assert app.island.shown() == "toast" and app.island.last_toast == "ذخیره شد ✓"
    assert not app.page.dialogs  # no SnackBar any more
    assert H.has_text(app, "ذخیره شد")
    p = pill(app)
    assert p.height == 56.0 and p.width > 164
    app.island.end_toast()
    assert app.island.shown() == "idle" and pill(app).height == 38.0


def test_toast_on_a_pushed_screen_hides_again(tmp_path):
    app = make_app(tmp_path)
    app.push(settings.view)
    app.toast("hi", error=True)
    assert app.island.shown() == "toast" and app.island.message[1] == "error"
    assert H.has_text(app, "hi")
    app.island.end_toast()
    assert app.island.shown() == "hidden"


def test_reminder_toast_kind_and_refresh_keeps_it(tmp_path):
    app = make_app(tmp_path)
    app.toast("یادآور", kind="bell")
    app.refresh()  # a rebuilt screen shows the banner straight away
    assert app.island.shown() == "toast" and H.has_text(app, "یادآور")


def test_toast_falls_back_to_snackbar_without_a_screen(tmp_path):
    app = make_app(tmp_path, start=False)
    app.toast("x")
    assert [d._name for d in app.page.dialogs] == ["SnackBar"]


def test_tapping_a_toast_dismisses_it(tmp_path):
    app = make_app(tmp_path)
    app.toast("hello")
    tap(app)
    assert app.island.shown() == "idle"


@pytest.mark.parametrize("lang", ["fa", "en"])
def test_creator_section_and_copyright(tmp_path, lang):
    app = make_app(tmp_path, lang=lang)
    c = app.ctx()
    app.push(settings.view)
    assert H.has_text(app, config.CREATOR_NAME) and H.has_text(app, "©")  # tile summary + footer
    H.click(app, c.t("set_creator"), exact=True)
    assert H.has_text(app, config.CREATOR_NAME)
    assert H.has_text(app, c.t("copyright_title"))
    assert H.has_text(app, c.t("copyright_2", name=config.CREATOR_NAME)[:40])
    year = "۱۴۰۵" if lang == "fa" else "2026"
    assert H.has_text(app, f"© {year}") and H.has_text(app, config.CREATOR_NAME)
    assert not H.view_layout_errors(app)
    assert not fake_flet.DROPPED and not fake_flet.MISSING_ICONS


def test_creator_credit_on_welcome_and_about(tmp_path):
    from shokraneh.ui.screens import onboarding

    app = make_app(tmp_path, onboarded=False)
    assert H.has_text(app, config.CREATOR_NAME)
    app = make_app(tmp_path)
    app.push(settings.section, key="about")
    assert H.has_text(app, config.CREATOR_NAME)
    assert onboarding  # imported for its i18n keys


def test_copyright_keys_exist_in_both_languages():
    __import__("shokraneh.ui.screens.settings")
    for k in ("set_creator", "creator_role", "creator_by", "copyright_line", "copyright_title", "copyright_1", "copyright_2", "copyright_3",
              "copyright_4", "copyright_5"):
        fa, en = i18n.STRINGS[k]
        assert fa.strip() and en.strip()
    assert "ممنوع" in i18n.STRINGS["copyright_2"][0] and "prohibited" in i18n.STRINGS["copyright_2"][1]


def test_today_status(tmp_path):
    app = make_app(tmp_path, seeded=False)
    st = today_mod.status(app.profile, TODAY)
    assert st["done"] == 0 and st["total"] == 3 and st["energy"] is False and st["streak"] == 0
    energy.quick_pick(app, TODAY, 7)
    st = today_mod.status(app.profile, TODAY)
    assert st["energy"] is True and st["done"] == 1
    app.profile.save_entry("morning", TODAY, {q.id: ["x"] for q in qc.MORNING})
    st = today_mod.status(app.profile, TODAY)
    assert st["morning_done"] is True and st["night_done"] is False and st["done"] == 2 and st["streak"] >= 1


def test_home_hero_shows_greeting_ring_and_progress(tmp_path):
    app = make_app(tmp_path, seeded=False)
    c = app.ctx()
    assert H.has_text(app, "سارا") and H.has_text(app, c.t("hero_0"))
    assert any(x._name == "ProgressRing" for x, _ in H.controls(app))
    energy.quick_pick(app, TODAY, 8)
    assert H.has_text(app, c.t("hero_1"))
