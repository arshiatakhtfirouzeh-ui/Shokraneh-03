"""Application controller.

Navigation uses real Flet views (so the Android back button works), plus theme / locale, profiles & PIN lock,
background work, the reminder ticker and native notifications.
"""
from __future__ import annotations

import threading
import time
from datetime import date
from typing import Any, Callable

import flet as ft

from .. import config, i18n, jalali, notify, reminders, reports, util
from ..store import Store
from . import compat as C
from . import kit
from .compat import A, mk
from .island import Island

TICK_SECONDS = 30


class App:
    def __init__(self, page: Any, store: Store | None = None, fonts_ok: bool = False):
        self.page = page
        self.store = store or Store(config.data_root())
        self.fonts_ok = fonts_ok
        self.profile = None
        self.stack: list[dict] = []
        self.tab = "home"
        self.notifier = notify.Notifier(page, on_tap=self.on_notification_tap, lang=self.lang)
        self.pending_payload = ""
        self.suppress_lock_until = 0.0
        self._timers: dict[str, threading.Timer] = {}
        self._ticker: threading.Thread | None = None
        self._stop = threading.Event()
        self._last_day: date | None = None
        self._reports_busy = False
        self._dialog: Any = None
        self.island = Island(self)

    # ------------------------------------------------------------------ settings-derived values
    @property
    def lang(self) -> str:
        return self.store.get("language", "fa") if self.store.get("language", "fa") in i18n.LANGUAGES else "fa"

    @property
    def jal(self) -> bool:
        return jalali.use_jalali(self.lang, self.store.get("calendar", "auto"))

    @property
    def week_start(self) -> int:
        ws = self.profile.setting("week_start") if self.profile else None
        return ws if isinstance(ws, int) and 0 <= ws <= 6 else jalali.default_week_start(self.jal)

    @property
    def dark(self) -> bool:
        mode = self.store.get("theme_mode", "system")
        if mode in ("dark", "light"):
            return mode == "dark"
        b = getattr(self.page, "platform_brightness", None)
        return "dark" in str(getattr(b, "name", b)).lower()

    @property
    def glass_style(self) -> str:
        v = self.store.get("glass", "full")
        return v if v in ("full", "lite", "off") else "full"

    @property
    def island_on(self) -> bool:
        return bool(self.store.get("island", True))

    def ctx(self) -> kit.Ctx:
        return kit.Ctx(
            lang=self.lang, dark=self.dark, accent=self.store.get("accent", "sage"), jal=self.jal,
            week_start=self.week_start, manual_rtl=bool(self.store.get("rtl_compat")) and i18n.is_rtl(self.lang),
            fonts=self.fonts_ok, width=float(getattr(self.page, "width", None) or 420),
            island=self.island if self.island_on else None, glass=self.glass_style,
        )

    def t(self, key: str, **kw: Any) -> str:
        return i18n.t(key, self.lang, **kw)

    def today(self) -> date:
        return util.logical_today()

    # ------------------------------------------------------------------ theme / locale
    def apply_theme(self) -> None:
        c = self.ctx()
        p = self.page
        p.title = self.t("app_name")
        p.padding = 0
        p.spacing = 0
        p.theme_mode = A.THEME_DARK if c.dark else A.THEME_LIGHT
        fam = "Vazir" if self.fonts_ok else None
        for attr in ("theme", "dark_theme"):
            try:
                setattr(p, attr, mk(ft.Theme, font_family=fam, color_scheme_seed=c.pal["accent"], use_material3=True))
            except Exception:
                pass
        p.bgcolor = c.pal["bg"]
        self.apply_locale(c)

    def apply_locale(self, c: kit.Ctx | None = None) -> None:
        """Persian locale makes Flutter mirror the whole layout; with the manual-RTL fallback we stay left-to-right."""
        c = c or self.ctx()
        LC, L = getattr(ft, "LocaleConfiguration", None), getattr(ft, "Locale", None)
        if not (LC and L):
            return
        try:
            use_fa = self.lang == "fa" and not c.manual_rtl
            cur = L("fa", "IR") if use_fa else L("en", "US")
            self.page.locale_configuration = LC(supported_locales=[L("fa", "IR"), L("en", "US")], current_locale=cur)
        except Exception:
            pass

    # ------------------------------------------------------------------ start-up
    def start(self) -> None:
        p = self.page
        self.apply_theme()
        for name, handler in (
            ("on_view_pop", lambda e: self.pop()),
            ("on_resize", self._on_resize),
            ("on_platform_brightness_change", lambda e: (self.apply_theme(), self.refresh())),
            ("on_app_lifecycle_state_change", self._on_lifecycle),
        ):
            try:
                setattr(p, name, handler)
            except Exception:
                pass
        from .screens import onboarding, profiles

        profs = self.store.profile_list()
        if not self.store.get("onboarded") or not profs:
            self.reset(onboarding.view)
        elif len(profs) > 1 and not self.store.get("last_profile"):
            self.reset(profiles.view)
        else:
            self.enter_profile(self.store.get("last_profile") or profs[0]["id"])

    def enter_profile(self, pid: str) -> None:
        from .screens import lock

        if self.store.has_pin(pid):
            self.reset(lock.view, pid=pid)
        else:
            self.open_profile(pid)

    def open_profile(self, pid: str) -> None:
        from .screens import main

        self.profile = self.store.open_profile(pid)
        self.tab = "home"
        self.apply_theme()
        self.reset(main.view)
        self.after_open()

    def after_open(self) -> None:
        self.notifier.lang = self.lang
        self.resync()
        self.ensure_reports()
        self._last_day = self.today()
        self.start_ticker()
        self.tick()
        if self.pending_payload:
            payload, self.pending_payload = self.pending_payload, ""
            self.open_payload(payload)
        else:
            self.maybe_prompt_energy()

    def lock_now(self) -> None:
        from .screens import lock

        if self.profile is None:
            return
        pid = self.profile.id
        self.profile = None
        self.store.close_profile(pid)
        self.close_dialog()
        self.reset(lock.view, pid=pid)

    def switch_profile(self) -> None:
        from .screens import profiles

        if self.profile is not None:
            self.store.close_profile(self.profile.id)
            self.profile = None
        self.reset(profiles.view)

    def suppress_lock(self, seconds: float = 45) -> None:
        self.suppress_lock_until = time.time() + seconds

    # ------------------------------------------------------------------ navigation (real views)
    def _make_view(self, entry: dict) -> Any:
        entry["hooks"] = []
        controls = entry["builder"](self, **entry["kw"])
        return mk(ft.View, route=f"/{len(self.stack)}", controls=controls, padding=0, spacing=0, bgcolor=self.ctx().pal["bg"])

    def push(self, builder: Callable, **kw: Any) -> None:
        self.island.reset_nav()
        entry = {"builder": builder, "kw": kw, "hooks": []}
        self.stack.append(entry)
        self.page.views.append(self._make_view(entry))
        self.page.update()

    def pop(self) -> None:
        if len(self.stack) <= 1:
            return
        self.island.reset_nav()
        self._run_hooks(self.stack[-1])
        self.stack.pop()
        if len(self.page.views) > 1:
            self.page.views.pop()
        self.refresh()  # the revealed screen may be stale (an editor just changed the data)

    def replace(self, builder: Callable, **kw: Any) -> None:
        """Swap the top screen (used after saving an editor)."""
        self.island.reset_nav()
        if not self.stack:
            return self.reset(builder, **kw)
        self._run_hooks(self.stack[-1])
        entry = {"builder": builder, "kw": kw, "hooks": []}
        self.stack[-1] = entry
        self.page.views[-1] = self._make_view(entry)
        self.page.update()

    def reset(self, builder: Callable, **kw: Any) -> None:
        self.island.reset_nav()
        for e in self.stack:
            self._run_hooks(e)
        entry = {"builder": builder, "kw": kw, "hooks": []}
        self.stack = [entry]
        view = self._make_view(entry)
        try:
            self.page.views.clear()
        except Exception:
            pass
        self.page.views.append(view)
        self.page.update()

    def refresh(self) -> None:
        if not self.stack or not self.page.views:
            return
        entry = self.stack[-1]
        entry["hooks"] = []
        view = self.page.views[-1]
        view.controls = entry["builder"](self, **entry["kw"])
        try:
            view.bgcolor = self.ctx().pal["bg"]
            self.page.bgcolor = self.ctx().pal["bg"]
        except Exception:
            pass
        self.page.update()

    def state(self) -> dict:
        """Per-screen scratch dict that survives refresh() (wizard step, form values, ...)."""
        return self.stack[-1].setdefault("state", {}) if self.stack else {}

    def on_leave(self, fn: Callable[[], None]) -> None:
        """Run `fn` when the current screen is closed (autosave)."""
        if self.stack:
            self.stack[-1]["hooks"].append(fn)

    @staticmethod
    def _run_hooks(entry: dict) -> None:
        for fn in entry.get("hooks", []):
            try:
                fn()
            except Exception:
                pass
        entry["hooks"] = []

    def go(self, tab: str) -> None:
        self.island.reset_nav()
        self.tab = tab
        self.refresh()

    # ------------------------------------------------------------------ dialogs / toast
    def show_dialog(self, dlg: Any) -> None:
        self._dialog = dlg
        try:
            self.page.show_dialog(dlg)
            return
        except AttributeError:
            pass
        try:
            self.page.open(dlg)
        except AttributeError:
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()

    def close_dialog(self) -> None:
        # pop_dialog() closes the most recently opened dialog, and a toast (SnackBar) may have been opened after ours:
        # keep popping until our own dialog is the one that was closed.
        dlg = self._dialog
        try:
            for _ in range(5):
                popped = self.page.pop_dialog()
                if popped is None or dlg is None or popped is dlg:
                    break
            self._dialog = None
            return
        except AttributeError:
            pass
        except Exception:
            return
        try:
            self.page.close(self._dialog)
        except Exception:
            if self._dialog is not None:
                self._dialog.open = False
                self.page.update()

    def dialog(self, title: str | None, body: Any, actions: list[tuple[str, Callable | None, str]] | None = None) -> Any:
        """actions: (label, handler, kind). Every action closes the dialog first, then runs its handler."""
        c = self.ctx()

        def wrap(h: Callable | None) -> Callable:
            def _go(e: Any) -> None:
                self.close_dialog()
                if h:
                    h()
            return _go

        btns = [kit.button(c, label, wrap(h), kind, size="sm") for label, h, kind in (actions or [])]
        if not c.glassy:
            content = kit.box(c, body, width=min(c.width - 64, 420)) if body is not None else None
            dlg = mk(ft.AlertDialog, modal=True, title=kit.text(c, title, 18, "bold") if title else None, content=content,
                     actions=btns or None, actions_alignment=A.MAIN_END, bgcolor=c.pal["surface"], scrollable=True)
        else:  # the whole dialog is one blurred glass card; the Flet dialog itself is transparent
            inner = kit.col(c, [kit.text(c, title, 18, "bold") if title else None, body,
                                kit.row(c, btns, spacing=8, align="end", wrap=True) if btns else None], spacing=16)
            card = kit.glass(c, inner, padding=22, radius=30, strength="strong", blur=30, width=min(c.width - 48, 440))
            clear = "#00000000"
            dlg = mk(ft.AlertDialog, modal=True, content=card, bgcolor=clear, shadow_color=clear, surface_tint_color=clear, elevation=0,
                     content_padding=0, inset_padding=C.pad(16, 24, 16, 24), scrollable=True)
            dlg.data = btns  # the buttons live inside the card; keep a handle on them
        self.show_dialog(dlg)
        return dlg

    def confirm(self, title: str, body: str, on_yes: Callable[[], None], yes_label: str | None = None, danger: bool = False) -> None:
        c = self.ctx()
        self.dialog(title, kit.text(c, body, 14.5, color="muted"), [
            (self.t("cancel"), None, "ghost"), (yes_label or self.t("yes"), on_yes, "danger" if danger else "primary")])

    def toast(self, message: str, error: bool = False, kind: str | None = None) -> None:
        """Short message: the dynamic island morphs into a banner; a SnackBar only if no island is on screen."""
        try:
            if self.island_on and self.island.show(message, kind or ("error" if error else "ok")):
                return
        except Exception:
            pass
        c = self.ctx()
        try:
            snack = mk(ft.SnackBar, content=kit.text(c, message, 14, "medium", "#FFFFFF"), bgcolor="#B4524A" if error else "#2F3B36",
                       duration=3200, behavior=C.enum("SnackBarBehavior", "FLOATING"))
            self.page.show_dialog(snack)
        except Exception:
            try:
                self.page.snack_bar = mk(ft.SnackBar, content=kit.text(c, message, 14, color="#FFFFFF"))
                self.page.snack_bar.open = True
                self.page.update()
            except Exception:
                pass

    # ------------------------------------------------------------------ background work
    def run_async(self, fn: Callable, *args: Any) -> None:
        """Run a coroutine function on the page's event loop (file picker, notifications, ...)."""
        try:
            self.page.run_task(fn, *args)
            return
        except Exception:
            pass

        def worker() -> None:
            import asyncio

            try:
                asyncio.run(fn(*args))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def bg(self, fn: Callable, *args: Any, done: Callable[[Any, Exception | None], None] | None = None) -> None:
        def worker() -> None:
            res: Any = None
            err: Exception | None = None
            try:
                res = fn(*args)
            except Exception as e:  # reported to `done`, never raised into the UI thread
                err = e
            if done:
                try:
                    done(res, err)
                except Exception:
                    pass
            try:
                self.page.update()
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def debounce(self, key: str, delay: float, fn: Callable[[], None]) -> None:
        old = self._timers.pop(key, None)
        if old:
            old.cancel()
        timer = threading.Timer(delay, fn)
        timer.daemon = True
        self._timers[key] = timer
        timer.start()

    def _on_resize(self, e: Any) -> None:
        self.debounce("resize", 0.35, lambda: self.profile is not None and self.refresh())

    def _on_lifecycle(self, e: Any) -> None:
        state = getattr(e, "state", "")
        name = str(getattr(state, "name", state)).lower()
        if self.profile is not None and time.time() > self.suppress_lock_until and any(k in name for k in ("pause", "hidden", "detach")):
            if self.store.has_pin(self.profile.id):
                self.lock_now()

    # ------------------------------------------------------------------ reports
    def ensure_reports(self, force: bool = False) -> None:
        """Weekly / monthly messages that became due (AI when enabled, offline otherwise)."""
        p = self.profile
        if p is None or self._reports_busy:
            return
        self._reports_busy = True
        lang, jal, ws, name, today = self.lang, self.jal, self.week_start, p.name, self.today()

        def work() -> list[dict]:
            return reports.run_pending(p, today, lang, jal, ws, name)

        def done(made: Any, err: Exception | None) -> None:
            self._reports_busy = False
            if made:
                self.toast(self.t("toast_new_report"))
                self.refresh()

        self.bg(work, done=done)

    # ------------------------------------------------------------------ notifications / reminders
    def resync(self) -> None:
        if self.profile is None or not self.notifier.native:
            return
        specs = reminders.specs(self.profile.data, self.lang, util.now())
        try:
            self.page.run_task(self.notifier.sync, specs)
        except Exception as e:
            self.notifier.last_error = f"run_task: {e}"

    def on_notification_tap(self, payload: str) -> None:
        if self.profile is None:
            self.pending_payload = payload
        else:
            self.open_payload(payload)

    def open_payload(self, payload: str) -> None:
        from .screens import letters, questions

        if payload in ("morning", "night"):
            self.push(questions.view, kind=payload, day=self.today())
        elif payload.startswith("letter:"):
            self.push(letters.read, letter_id=payload.split(":", 1)[1])

    def notify_local(self, title: str, body: str) -> None:
        if not self.notifier.android and not self.notifier.native:
            threading.Thread(target=notify.desktop_notify, args=(title, body), daemon=True).start()

    def start_ticker(self) -> None:
        if self._ticker is not None and self._ticker.is_alive():
            return

        def loop() -> None:
            while not self._stop.wait(TICK_SECONDS):
                try:
                    self.tick()
                except Exception:
                    pass

        self._ticker = threading.Thread(target=loop, daemon=True)
        self._ticker.start()

    def tick(self) -> None:
        p = self.profile
        if p is None:
            return
        now = util.now()
        day = util.logical_today(now)
        changed = False
        if self._last_day is not None and day != self._last_day:
            self._last_day = day
            self.ensure_reports()
            changed = True
        arrivals = reminders.new_arrivals(p.data, now)
        if arrivals:
            for letter in arrivals:
                p.update_item("letters", letter["id"], notified=True)
            self.notify_local(self.t("notif_letter_title"), self.t("notif_letter_body"))
            self.show_letter_arrived(arrivals[0])
            changed = True
        if not self.notifier.native:
            fired = p.data["meta"].setdefault("fired", {})
            for kind in reminders.due_now(p.data, now, fired):
                fired[kind] = now.date().isoformat()
                p.save()
                title, body = self.t(f"notif_{kind}_title"), self.t(f"notif_{kind}_body")
                self.notify_local(title, body)
                self.toast(f"{title}  {body}", kind="bell")
                changed = True
        if changed:
            self.refresh()

    def show_letter_arrived(self, letter: dict) -> None:
        from .screens import letters

        c = self.ctx()
        self.dialog(self.t("letter_arrived_title"), kit.text(c, self.t("letter_arrived_body"), 14.5, color="muted"), [
            (self.t("later"), None, "ghost"),
            (self.t("open_letter"), lambda: self.push(letters.read, letter_id=letter["id"]), "primary")])

    def maybe_prompt_energy(self) -> None:
        """Once a day, ask for the energy / mood check-in (dismissible)."""
        p = self.profile
        if p is None:
            return
        day = self.today().isoformat()
        meta = p.data["meta"]
        if p.energy(day) is None and meta.get("energy_asked") != day:
            meta["energy_asked"] = day
            p.save()
            from .screens import energy

            energy.sheet(self, self.today())
