"""Notifications.

* Android: optional native plugin `flet-android-notifications` (see README, "اعلان‌ها"). The default APK does NOT
  contain it, so the app degrades to in-app handling (a banner / dialog when it is opened or open).
* Desktop: best-effort OS notifications through the platform's own tools (no extra packages).

Every call swallows errors and records `last_error`; a missing or misbehaving plugin can never crash the app.
"""
from __future__ import annotations

import inspect
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Callable

from . import config, i18n, reminders

CHANNEL_ID = "shokraneh_reminders"

_WIN_TOAST = r"""
$ErrorActionPreference = 'Stop'
[void][Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime]
[void][Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime]
$t = [System.Security.SecurityElement]::Escape($env:SK_TITLE)
$b = [System.Security.SecurityElement]::Escape($env:SK_BODY)
$xml = New-Object Windows.Data.Xml.Dom.XmlDocument
$xml.LoadXml("<toast><visual><binding template='ToastGeneric'><text>$t</text><text>$b</text></binding></visual></toast>")
$toast = New-Object Windows.UI.Notifications.ToastNotification $xml
$id = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier($id).Show($toast)
"""


def desktop_notify(title: str, body: str) -> bool:
    """Fire-and-forget OS notification on Linux / macOS / Windows. Returns True if a helper was launched."""
    quiet: dict[str, Any] = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "stdin": subprocess.DEVNULL}
    try:
        if sys.platform.startswith("linux"):
            exe = shutil.which("notify-send")
            if not exe:
                return False
            subprocess.Popen([exe, "--app-name=Shokraneh", title, body], **quiet)  # noqa: S603
            return True
        if sys.platform == "darwin":
            script = 'display notification (system attribute "SK_BODY") with title (system attribute "SK_TITLE")'
            subprocess.Popen(["osascript", "-e", script], env={**os.environ, "SK_TITLE": title, "SK_BODY": body}, **quiet)  # noqa: S603,S607
            return True
        if sys.platform.startswith("win"):
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.Popen(  # noqa: S603,S607
                ["powershell", "-NoProfile", "-NonInteractive", "-WindowStyle", "Hidden", "-Command", _WIN_TOAST],
                env={**os.environ, "SK_TITLE": title, "SK_BODY": body},
                creationflags=flags,
                **quiet,
            )
            return True
    except Exception:
        return False
    return False


class Notifier:
    """Facade over the native Android plugin (when present) and desktop notifications."""

    def __init__(self, page: Any = None, on_tap: Callable[[str], None] | None = None, lang: str = "fa"):
        self.page = page
        self.on_tap = on_tap
        self.lang = lang
        self.svc: Any = None
        self.native = False
        self.exact = False  # use exact alarms (needs the SCHEDULE_EXACT_ALARM permission to be granted)
        self.last_error = ""
        self.android = config.is_android()
        if self.android:
            self._init_android()

    # ---- setup
    def _init_android(self) -> None:
        try:
            from flet_android_notifications import FletAndroidNotifications  # type: ignore
        except Exception as e:  # not installed in the default APK
            self.last_error = f"plugin not installed ({type(e).__name__})"
            return
        try:
            try:
                svc = FletAndroidNotifications(on_notification_tap=self._tap)
            except TypeError:
                svc = FletAndroidNotifications()
            services = getattr(self.page, "services", None)
            if services is not None and svc not in services:
                services.append(svc)
            self.svc = svc
            self.native = True
        except Exception as e:
            self.last_error = f"plugin failed to start: {e}"

    def _tap(self, e: Any) -> None:
        try:
            data = json.loads(getattr(e, "data", "") or "{}")
            payload = str(data.get("payload") or "")
        except Exception:
            payload = ""
        if self.on_tap:
            try:
                self.on_tap(payload)
            except Exception:
                pass

    # ---- status for the Settings screen
    def status(self) -> dict:
        return {
            "platform": "android" if self.android else "desktop",
            "native": self.native,
            "desktop_ok": (not self.android) and (sys.platform.startswith(("win", "darwin")) or bool(shutil.which("notify-send"))),
            "error": self.last_error,
        }

    # ---- internals
    async def _invoke(self, name: str, **kw: Any) -> Any:
        res = getattr(self.svc, name)(**kw)
        return await res if inspect.isawaitable(res) else res

    async def _call(self, name: str, **kw: Any) -> Any:
        """Call a plugin method; on TypeError (unknown optional argument) retry with the documented core arguments."""
        try:
            return await self._invoke(name, **kw)
        except TypeError:
            core_keys = ("notification_id", "title", "body", "scheduled_time", "match_date_time_components", "schedule_mode")
            return await self._invoke(name, **{k: kw[k] for k in core_keys if k in kw})

    def _extras(self) -> dict:
        name, desc = (("یادآورها", "یادآوری شکرگزاری و نامه‌ها") if self.lang == "fa" else ("Reminders", "Gratitude reminders and letters"))
        return {"channel_id": CHANNEL_ID, "channel_name": name, "channel_description": desc}

    # ---- public (async: run through page.run_task)
    async def request_permissions(self) -> bool:
        if not self.native:
            return False
        try:
            ok = bool(await self._invoke("request_permissions"))
        except Exception as e:
            self.last_error = f"permission request failed: {e}"
            return False
        try:  # exact alarms are optional; without them the OS may delay a notification by several minutes
            self.exact = bool(await self._invoke("request_exact_alarm_permission"))
        except Exception:
            self.exact = False
        return ok

    async def sync(self, specs: list[reminders.Spec]) -> int:
        """Replace every scheduled notification with `specs`. Returns how many were scheduled."""
        if not self.native:
            return 0
        try:
            await self._invoke("cancel_all")
        except Exception as e:
            self.last_error = f"cancel failed: {e}"
        n = 0
        for s in specs:
            kw: dict[str, Any] = {
                "notification_id": s.nid,
                "title": s.title,
                "body": s.body,
                "scheduled_time": s.when,
                "payload": s.payload,
                **self._extras(),
            }
            if s.repeat == "daily":
                kw["match_date_time_components"] = "time"
            if self.exact:
                kw["schedule_mode"] = "exact_allow_while_idle"
            try:
                await self._call("schedule_notification", **kw)
                n += 1
            except Exception as e:
                self.last_error = f"schedule failed: {e}"
        return n

    async def cancel_all(self) -> None:
        if self.native:
            try:
                await self._invoke("cancel_all")
            except Exception as e:
                self.last_error = f"cancel failed: {e}"

    async def show_now(self, title: str, body: str, nid: int = 9001) -> bool:
        """Immediate notification (also used by 'Test notification')."""
        if self.native:
            try:
                await self._call("show_notification", notification_id=nid, title=title, body=body, **self._extras())
                return True
            except Exception as e:
                self.last_error = f"show failed: {e}"
                return False
        if not self.android:
            return desktop_notify(title, body)
        return False

    async def test(self) -> bool:
        return await self.show_now(i18n.t("notif_test_title", self.lang), i18n.t("notif_test_body", self.lang))
