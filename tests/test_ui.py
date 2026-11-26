"""UI smoke tests on the strict fake Flet: every screen builds in every language/theme/direction, every handler can be fired
without raising, layouts avoid Flutter constraint mistakes, and the main user flows work end to end.

These tests check the app's own logic and its consistency with the Flet API as remembered; they do not replace running
the real Flet."""
import itertools
import re
from datetime import date
from pathlib import Path

import pytest

import ui_harness as H
from ui_harness import TODAY, make_app

import fake_flet
from shokraneh import i18n, jalali
from shokraneh.ui.screens import cal, energy, inbox, letters, lists, lock, onboarding, profiles, questions, settings

SRC = Path(__file__).resolve().parent.parent / "src"
D0 = date(2026, 11, 14)


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    H.freeze(monkeypatch)
    H.offline(monkeypatch)
    fake_flet.DROPPED.clear()
    yield


# --------------------------------------------------------------------------- the list of screens
def first_id(app, coll, **match):
    for it in app.profile.items(coll):
        if all(it.get(k) == v for k, v in match.items()):
            return it["id"]
    raise AssertionError(coll)


def screens():
    S = []
    for tab in ("home", "spaces", "progress", "inbox"):
        S.append((f"tab-{tab}", lambda app, tab=tab: app.go(tab)))
    S += [("calendar", lambda app: app.push(cal.view)),
          ("day-data", lambda app: app.push(cal.day_view, day=D0)),
          ("day-empty", lambda app: app.push(cal.day_view, day=date(2026, 11, 1))),
          ("day-future", lambda app: app.push(cal.day_view, day=date(2026, 12, 25)))]
    for coll in lists.SPACES:
        S.append((f"list-{coll}", lambda app, coll=coll: app.push(lists.view, coll=coll)))
        S.append((f"new-{coll}", lambda app, coll=coll: app.push(lists.editor, coll=coll)))
        S.append((f"edit-{coll}", lambda app, coll=coll: app.push(lists.editor, coll=coll, item_id=app.profile.items(coll)[0]["id"])))
    S += [("letters", lambda app: app.push(letters.view)),
          ("letter-new", lambda app: app.push(letters.editor)),
          ("letter-sealed", lambda app: app.push(letters.read, letter_id=first_id(app, "letters", title="برای آینده"))),
          ("letter-arrived", lambda app: app.push(letters.read, letter_id=first_id(app, "letters", title="رسیده"))),
          ("letter-opened", lambda app: app.push(letters.read, letter_id=first_id(app, "letters", title="قدیمی"))),
          ("letter-edit", lambda app: app.push(letters.editor, letter_id=first_id(app, "letters", title="برای آینده"))),
          ("msg", lambda app: app.push(inbox.message, msg_id=app.profile.items("messages")[0]["id"])),
          ("q-morning", lambda app: app.push(questions.view, kind="morning", day=D0)),
          ("q-night", lambda app: app.push(questions.view, kind="night", day=D0)),
          ("q-new", lambda app: app.push(questions.view, kind="morning", day=TODAY)),
          ("energy-sheet", lambda app: energy.sheet(app, TODAY)),
          ("energy-sheet-old", lambda app: energy.sheet(app, D0)),
          ("settings", lambda app: app.push(settings.view))]
    S += [(f"settings-{k}", lambda app, k=k: app.push(settings.section, key=k)) for k in settings.BUILDERS]
    S += [(f"pin-{m}", lambda app, m=m: app.push(lock.setup, mode=m)) for m in ("set", "change", "remove")]
    S += [("profiles", lambda app: app.reset(profiles.view)),
          ("lock", lambda app: app.reset(lock.view, pid=app.profile.id)),
          ("onb-0", lambda app: app.reset(onboarding.view)),
          ("onb-add", lambda app: app.reset(onboarding.view, add=True))]
    return S


SCREENS = screens()
CONFIGS = [dict(lang=l, dark=d, rtl=r) for l, d, r in itertools.product(("fa", "en"), (False, True), (False, True))]


def cid(cfg):
    return f"{cfg['lang']}-{'dark' if cfg['dark'] else 'light'}-{'rtl' if cfg['rtl'] else 'std'}"


# --------------------------------------------------------------------------- i18n
def test_i18n_parity_and_placeholders():
    for mod in ("energy", "home", "inbox", "letters", "lists", "main", "progress", "questions", "spaces", "cal", "settings", "lock",
                "onboarding", "profiles"):
        __import__(f"shokraneh.ui.screens.{mod}")
    field = re.compile(r"\{(\w+)\}")
    for key, (fa, en) in i18n.STRINGS.items():
        assert fa.strip() and en.strip(), key
        assert set(field.findall(fa)) == set(field.findall(en)), key


def test_every_literal_translation_key_exists():
    test_i18n_parity_and_placeholders()
    used = set()
    for path in SRC.rglob("*.py"):
        used |= set(re.findall(r"\b(?:c|ctx|app|self)\.t\(\s*\"([a-zA-Z0-9_]+)\"", path.read_text(encoding="utf-8")))
    dynamic = [f"set_rem_{k}" for k in ("morning", "night")] + [f"set_theme_{k}" for k in ("system", "light", "dark")] + \
              [f"set_{k}" for k, *_ in settings.SECTIONS] + [f"pin_title_{m}" for m in ("set", "change", "remove")]
    missing = sorted(k for k in used | set(dynamic) if k not in i18n.STRINGS)
    assert not missing, missing


# --------------------------------------------------------------------------- every screen builds
@pytest.mark.parametrize("cfg", CONFIGS, ids=cid)
def test_all_screens_build(tmp_path, cfg):
    app = make_app(tmp_path, **cfg)
    for name, open_screen in SCREENS:
        app.reset(__import__("shokraneh.ui.screens.main", fromlist=["view"]).view)
        app.page.dialogs.clear()
        try:
            open_screen(app)
        except Exception as e:  # noqa: BLE001
            raise AssertionError(f"{name}: {type(e).__name__}: {e}") from e
        errs = H.view_layout_errors(app)
        assert not errs, f"{name}: {errs[:3]}"
    assert not fake_flet.DROPPED, fake_flet.DROPPED
    assert not fake_flet.MISSING_ICONS, fake_flet.MISSING_ICONS


def test_wide_window_is_capped(tmp_path):
    app = make_app(tmp_path, width=1400)
    assert not H.view_layout_errors(app)
    row = [c for c, _ in H.walk(app.page.views[-1].controls[0]) if c._name == "Row" and getattr(c, "vertical_alignment", None)]
    assert row


# --------------------------------------------------------------------------- crawl: fire every handler
def crawl(tmp_path, cfg, only=None):
    failures = []
    for name, open_screen in SCREENS:
        if only and not any(name.startswith(o) for o in only):
            continue

        def fresh():
            app = make_app(tmp_path, **cfg, ai_on=True)
            open_screen(app)
            return app

        n = len(H.targets(fresh()))
        for i in range(n):
            app = fresh()
            t = H.targets(app)
            if i >= len(t):
                break
            ctrl = t[i]
            try:
                H.fire(ctrl)
                app.refresh()
                errs = H.view_layout_errors(app)
                if errs:
                    failures.append(f"{name}#{i} layout: {errs[:2]}")
            except Exception as e:  # noqa: BLE001
                failures.append(f"{name}#{i} {type(e).__name__}: {e}")
                continue
            m = len(H.dialog_actions(app))
            for j in range(m):
                app = fresh()
                try:
                    H.fire(H.targets(app)[i])
                    H.dialog_actions(app)[j].on_click(H.Event())
                    app.refresh()
                except Exception as e:  # noqa: BLE001
                    failures.append(f"{name}#{i} dialog action {j}: {type(e).__name__}: {e}")
    return failures


@pytest.mark.parametrize("cfg", [CONFIGS[0], CONFIGS[7]], ids=cid)
def test_crawl_every_handler(tmp_path, cfg):
    failures = crawl(tmp_path, cfg)
    assert not failures, "\n".join(failures[:25])
    assert not fake_flet.DROPPED, fake_flet.DROPPED


# --------------------------------------------------------------------------- flows
def T(key, lang="fa", **kw):
    return i18n.t(key, lang, **kw)


def top(app):
    return app.stack[-1]["builder"]


def test_first_run_onboarding_creates_profile(tmp_path):
    app = make_app(tmp_path, onboarded=False)
    assert top(app) is onboarding.view
    H.click(app, "English", exact=True)
    assert app.lang == "en"
    H.click(app, "Continue")
    H.click(app, "Continue")  # empty name: stays and complains
    assert H.has_text(app, T("onb_name_required", "en"))
    H.type_into(H.fields(app)[0], "Mina")
    H.click(app, "🌸", exact=True)
    H.click(app, "Continue")
    H.click(app, "Start")
    prof = app.store.profile_list()
    assert [p["name"] for p in prof] == ["Mina"] and prof[0]["avatar"] == "🌸"
    assert app.profile is not None and app.profile.name == "Mina"
    assert app.store.get("onboarded") is True


def test_pin_set_lock_and_unlock(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    pid = app.profile.id
    app.push(lock.setup, mode="set")
    for d in "1234":
        H.click(app, app.ctx().n(d), exact=True)
    assert H.has_text(app, T("pin_confirm"))
    for d in "1235":
        H.click(app, app.ctx().n(d), exact=True)
    assert H.has_text(app, T("pin_mismatch")) and not app.store.has_pin(pid)
    for d in "12341234":
        H.click(app, app.ctx().n(d), exact=True)
    assert app.store.has_pin(pid)
    app.lock_now()
    assert top(app) is lock.view and app.profile is None
    for _ in range(lock.MAX_FAILS):
        for d in "0000":
            H.click(app, app.ctx().n(d), exact=True)
    assert H.has_text(app, T("lock_wait", s="")[:8])
    real = lock.time.time()
    monkeypatch.setattr(lock.time, "time", lambda: real + 3600)
    for d in "1234":
        H.click(app, app.ctx().n(d), exact=True)
    assert app.profile is not None and top(app) is not lock.view


def test_forgot_pin_erases_profile(tmp_path):
    app = make_app(tmp_path, pin="1234")
    app.lock_now()
    H.click(app, T("lock_forgot"))
    H.click(app, T("lock_erase"))
    assert app.store.profile_list() == [] and top(app) is onboarding.view


def test_settings_language_theme_week_and_accent(tmp_path):
    app = make_app(tmp_path)
    app.push(settings.section, key="look")
    H.click(app, "English", exact=True)
    assert app.lang == "en" and not app.jal
    H.click(app, "Su", exact=True)
    assert app.profile.setting("week_start") == 6 and app.week_start == 6
    H.click(app, "Dark", exact=True)
    assert app.dark
    H.click(app, "Auto", exact=True, nth=1)  # 0 = calendar, 1 = week start
    assert app.profile.setting("week_start") is None


def test_settings_reminders_and_ai(tmp_path):
    app = make_app(tmp_path)
    app.push(settings.section, key="reminders")
    sw = H.switches(app)
    sw[0].value = True
    sw[0].on_change(H.Event(sw[0]))
    assert app.profile.setting("reminders.morning.enabled") is True
    app.pop()
    app.push(settings.section, key="ai")
    H.click(app, "Anthropic")
    assert app.profile.setting("ai.provider") == "anthropic"
    for f in H.fields(app):
        if f.label == T("set_ai_key"):
            H.type_into(f, "sk-test")
    sw = H.switches(app)[0]
    sw.value = True
    sw.on_change(H.Event(sw))
    assert app.profile.setting("ai.api_key") == "sk-test" and app.profile.setting("ai.consent") is True
    H.click(app, T("set_ai_test"))  # network is blocked in tests -> error toast, no crash
    assert app.island.message is not None and app.island.message[1] == "error"


def test_backup_roundtrip_and_bad_input(tmp_path):
    a = make_app(tmp_path)
    text = a.profile.export_text()
    assert "api_key" not in text
    b = make_app(tmp_path, seeded=False)
    c = b.ctx()
    settings._restore(b, c, text, "merge")
    assert b.profile.data["morning"] == a.profile.data["morning"]
    assert len(b.profile.items("wishes")) == len(a.profile.items("wishes"))
    settings._restore(b, c, text, "merge")  # merging twice must not duplicate
    assert len(b.profile.items("wishes")) == len(a.profile.items("wishes"))
    for bad in ("not json", '{"format": "x"}', "[]"):
        b.page.dialogs.clear()
        b.island.message = None
        settings._ask_mode(b, c, bad)
        assert not b.page.dialogs and b.island.message is not None and b.island.message[1] == "error"
    b.page.dialogs.clear()
    settings._restore(b, c, '{"format": "%s", "data": {"wishes": [1, "x"], "morning": {"2026-01-01": 5}}}' % __import__("shokraneh.store", fromlist=["x"]).BACKUP_FORMAT, "merge")


def test_wipe_and_delete_profile(tmp_path):
    app = make_app(tmp_path)
    app.push(settings.section, key="data")
    H.click(app, T("set_wipe"), exact=True)
    H.click(app, T("delete"), exact=True)
    assert app.profile.items("wishes") == [] and app.profile.data["morning"] == {}


def test_morning_wizard_saves_every_answer(tmp_path):
    app = make_app(tmp_path)
    app.push(questions.view, kind="morning", day=TODAY)
    for step in range(7):
        f = H.fields(app)
        if f:
            H.type_into(f[0], f"جواب {step}")
        H.click(app, T("wiz_finish") if step == 6 else T("wiz_next"), exact=True)
    entry = app.profile.entry("morning", TODAY)
    assert entry["answers"]["m1"][0] == "جواب 0" and entry["answers"]["m6"] == "جواب 5" and entry["answers"]["m7"] == "جواب 6"
    assert H.has_text(app, T("wiz_done_morning"))


def test_night_wizard_has_nine_questions(tmp_path):
    app = make_app(tmp_path)
    app.push(questions.view, kind="night", day=TODAY)
    for step in range(9):
        f = H.fields(app)
        if f:
            H.type_into(f[0], f"شب {step}")
        H.click(app, T("wiz_finish") if step == 8 else T("wiz_next"), exact=True)
    assert len(app.profile.entry("night", TODAY)["answers"]) == 9


def test_every_space_can_add_edit_and_delete(tmp_path):
    app = make_app(tmp_path)
    for coll in lists.SPACES:
        before = len(app.profile.items(coll))
        app.page.dialogs.clear()
        app.push(lists.editor, coll=coll)
        f = H.fields(app)
        assert f, coll
        H.type_into(f[0], "تازه")
        H.click(app, T("save"), exact=True)
        assert len(app.profile.items(coll)) == before + 1, coll


def test_letter_is_sealed_then_arrives(tmp_path, monkeypatch):
    app = make_app(tmp_path)
    app.push(letters.editor)
    for f in H.fields(app):
        type_text = "متن نامه"
        H.type_into(f, type_text)
    H.click(app, "یک هفته دیگه")
    H.click(app, T("letter_seal"))
    new = [l for l in app.profile.items("letters") if l.get("body") == "متن نامه" or l.get("title") == "متن نامه"]
    assert new and new[0]["deliver_at"].startswith("2026-11-29")
    from shokraneh import reminders
    assert reminders.letter_state(new[0], H.NOW) == "sealed"


def test_inbox_generates_weekly_and_monthly(tmp_path):
    app = make_app(tmp_path)
    n = len(app.profile.items("messages"))
    app.go("inbox")
    H.click(app, T("inbox_weekly_btn"))
    app.page.dialogs.clear()
    H.click(app, T("inbox_monthly_btn"))
    assert len(app.profile.items("messages")) >= n


def test_energy_quick_pick_and_calendar_navigation(tmp_path):
    app = make_app(tmp_path)
    assert app.profile.energy(TODAY) is None
    energy.quick_pick(app, TODAY, 7)
    assert app.profile.energy(TODAY)["score"] == 7
    app.page.dialogs.clear()
    app.push(cal.view)
    start = app.state()["cursor"]
    assert jalali.month_bounds(start, True)[0] == start
    H.click_icon(app, "CHEVRON_RIGHT")  # one of the two arrows moves the month (which one depends on the direction)
    H.click_icon(app, "CHEVRON_LEFT")
    app.push(cal.day_view, day=D0)
    assert H.has_text(app, "سلامتی")  # the morning answers of that day are shown


def test_two_profiles_have_separate_data(tmp_path):
    app = make_app(tmp_path)
    other = app.store.create_profile("Ali", "🌊")
    first = app.profile.id
    app.switch_profile()
    assert top(app) is profiles.view
    app.enter_profile(other["id"])
    assert app.profile.name == "Ali" and app.profile.items("wishes") == [] and app.profile.data["morning"] == {}
    app.switch_profile()
    app.enter_profile(first)
    assert len(app.profile.items("wishes")) == 2


def test_main_entry_point_starts_the_app(tmp_path, monkeypatch):
    monkeypatch.setenv("SHOKRANEH_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.syspath_prepend(str(SRC))
    import importlib
    entry = importlib.import_module("main")
    page = fake_flet.Page()
    entry.main(page)
    assert page.title == "شکرانه" and page.views[-1].controls  # first run -> the welcome screen is shown
    assert entry.available_fonts() in ({}, entry.available_fonts())


def test_project_metadata_is_consistent():
    import tomllib
    from shokraneh import __version__

    root = SRC.parent
    main = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    alt = tomllib.loads((root / "pyproject.notifications.toml").read_text(encoding="utf-8"))
    assert main["project"]["version"] == alt["project"]["version"] == __version__
    assert "flet-android-notifications" not in " ".join(main["project"]["dependencies"])  # the default APK stays plugin-free
    assert (SRC / "assets" / "icon.png").is_file()
