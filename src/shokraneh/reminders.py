"""Reminder and letter logic (pure functions, no Flet / OS calls).

* notify.Notifier turns `Spec`s into real OS notifications.
* ui/app.py runs a ~30 s ticker that uses `due_now()` and `new_arrivals()` while the app is open.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from . import i18n, util

MORNING_ID, NIGHT_ID = 1001, 1002
FIRE_WINDOW = timedelta(minutes=20)  # an open app only fires a reminder if it is at most this late


@dataclass(frozen=True)
class Spec:
    nid: int
    kind: str  # morning | night | letter
    title: str
    body: str
    when: datetime
    repeat: str | None  # "daily" | None
    payload: str  # what tapping the notification opens: "morning" | "night" | "letter:<id>"


# --------------------------------------------------------------------------- letters
def letter_nid(letter_id: str) -> int:
    """Stable positive int32 id for a letter's notification (10_000 … < 2^31)."""
    return 10_000 + util.stable_int(letter_id, 1_900_000_000)


def deliver_at(letter: dict) -> datetime | None:
    return util.parse_dt(letter.get("deliver_at"))


def letter_state(letter: dict, now: datetime) -> str:
    """'sealed' (not yet time) | 'arrived' (time has come, unread) | 'opened'."""
    if letter.get("opened_at"):
        return "opened"
    due = deliver_at(letter)
    if due is None or due <= now:
        return "arrived"
    return "sealed"


def letters_in_state(data: dict, now: datetime, state: str) -> list[dict]:
    out = [l for l in data.get("letters", []) if letter_state(l, now) == state]
    return sorted(out, key=lambda l: deliver_at(l) or datetime.min, reverse=(state == "opened"))


def new_arrivals(data: dict, now: datetime) -> list[dict]:
    """Arrived letters the person has not been told about inside the app yet."""
    return [l for l in letters_in_state(data, now, "arrived") if not l.get("notified")]


def next_sealed(data: dict, now: datetime) -> dict | None:
    sealed = letters_in_state(data, now, "sealed")
    return sealed[0] if sealed else None


# --------------------------------------------------------------------------- daily reminders
def reminder_conf(data: dict, kind: str) -> tuple[bool, tuple[int, int]]:
    r = ((data.get("settings") or {}).get("reminders") or {}).get(kind) or {}
    default = (7, 30) if kind == "morning" else (21, 30)
    return bool(r.get("enabled")), util.parse_hhmm(r.get("time"), default)


def next_occurrence(hm: tuple[int, int], now: datetime) -> datetime:
    at = now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
    return at if at > now else at + timedelta(days=1)


def specs(data: dict, lang: str, now: datetime) -> list[Spec]:
    """Everything the OS should be told about (idempotent: ids are stable)."""
    out: list[Spec] = []
    for kind, nid in (("morning", MORNING_ID), ("night", NIGHT_ID)):
        enabled, hm = reminder_conf(data, kind)
        if enabled:
            out.append(
                Spec(
                    nid,
                    kind,
                    i18n.t(f"notif_{kind}_title", lang),
                    i18n.t(f"notif_{kind}_body", lang),
                    next_occurrence(hm, now),
                    "daily",
                    kind,
                )
            )
    for l in letters_in_state(data, now, "sealed"):
        due = deliver_at(l)
        if due:  # the body is deliberately generic: a lock screen must not reveal a private letter
            out.append(
                Spec(
                    letter_nid(l["id"]),
                    "letter",
                    i18n.t("notif_letter_title", lang),
                    i18n.t("notif_letter_body", lang),
                    due,
                    None,
                    f"letter:{l['id']}",
                )
            )
    return out


def due_now(data: dict, now: datetime, fired: dict) -> list[str]:
    """Reminder kinds ('morning' / 'night') an OPEN app should announce right now.

    A reminder fires once per day, only inside FIRE_WINDOW after its time, and not if that
    day's entry was already written.
    """
    out: list[str] = []
    today = util.logical_today(now)
    for kind in ("morning", "night"):
        enabled, hm = reminder_conf(data, kind)
        if not enabled or fired.get(kind) == now.date().isoformat():
            continue
        at = now.replace(hour=hm[0], minute=hm[1], second=0, microsecond=0)
        if not (at <= now < at + FIRE_WINDOW):
            continue
        if (data.get(kind) or {}).get(today.isoformat()):
            continue
        out.append(kind)
    return out
