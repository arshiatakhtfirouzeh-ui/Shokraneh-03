"""Letter to my future self: write now, choose when it opens; the notification / in-app arrival happens at that time."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from ... import content as qc
from ... import reminders, util
from ...i18n import register
from .. import compat as C
from .. import kit
from . import lists

register({
    "letter_arrived_title": ("نامه‌ای از خودت رسید ✉️", "A letter from your past self ✉️"),
    "letter_arrived_body": ("نامه‌ای که برای این روز نوشته بودی آماده‌ی خوندنه.", "The letter you wrote for this day is ready to read."),
    "open_letter": ("بازش کن", "Open it"),
    "write_letter": ("نوشتنِ نامه", "Write a letter"),
    "letters_intro": ("به خودت بنویس و زمانی رو انتخاب کن؛ همون موقع بهت خبر می‌دیم و نامه باز می‌شه.",
                      "Write to yourself and choose a time — you'll be notified then, and the letter opens."),
    "letter_untitled": ("نامه بدون عنوان", "Untitled letter"),
    "letter_sealed_until": ("مهر‌شده تا {d}", "Sealed until {d}"),
    "letter_opens_in": ("{n} روز دیگه باز می‌شه", "Opens in {n} days"),
    "letter_opens_today": ("امروز ساعت {t} باز می‌شه", "Opens today at {t}"),
    "letter_arrived_label": ("رسیده · آماده‌ی خوندن", "Arrived · ready to read"),
    "letter_written": ("نوشته‌شده در {d}", "Written on {d}"),
    "letter_opened_on": ("خونده‌شده در {d}", "Read on {d}"),
    "section_sealed": ("مهر‌شده‌ها", "Sealed"),
    "section_arrived": ("رسیده‌ها", "Arrived"),
    "section_opened": ("خونده‌شده‌ها", "Read"),
    "f_letter_title": ("عنوان (اختیاری)", "Title (optional)"),
    "f_letter_body": ("نامه‌ات…", "Your letter…"),
    "f_letter_when": ("چه زمانی باز بشه؟", "When should it open?"),
    "letter_custom": ("تاریخ دلخواه", "Pick a date"),
    "letter_time": ("ساعت", "Time of day"),
    "letter_will_open": ("باز می‌شه: {when}", "Opens: {when}"),
    "letter_prompts": ("برای شروع به این‌ها فکر کن", "Some things to think about"),
    "letter_seal": ("مهر کن و به آینده بفرست", "Seal it and send it to the future"),
    "letter_sealed_note": ("نامه‌ی مهرشده تا وقتش خونده نمی‌شه؛ فقط می‌تونی زمان بازشدنش رو عوض کنی.",
                           "A sealed letter can't be read before its time; you can only change when it opens."),
    "letter_change_time": ("ذخیره‌ی زمان جدید", "Save the new time"),
    "letter_reply": ("به آینده‌ی خودت جواب بنویس", "Write back to your future self"),
    "toast_letter_sealed": ("نامه مهر شد و راهیِ آینده شد ✉️", "Your letter is sealed and on its way ✉️"),
    "letter_from_past": ("نامه‌ای از گذشته‌ی تو", "A letter from your past"),
    "letter_not_yet": ("هنوز وقتش نشده", "It's not time yet"),
    "err_future": ("زمان باید در آینده باشه.", "The time must be in the future."),
})


def _deliver_dt(letter: dict) -> datetime | None:
    return reminders.deliver_at(letter)


def _when_text(c: kit.Ctx, dt: datetime) -> str:
    return f"{c.date(dt.date(), 'long')} · {c.n(f'{dt.hour:02d}:{dt.minute:02d}')}"


def _card(app, c: kit.Ctx, letter: dict, state: str) -> Any:
    now = util.now()
    dt = _deliver_dt(letter)
    title = (letter.get("title") or "").strip() or c.t("letter_untitled")
    if state == "sealed" and dt:
        days = (dt.date() - now.date()).days
        sub = c.t("letter_opens_today", t=c.n(f"{dt.hour:02d}:{dt.minute:02d}")) if days <= 0 else c.t("letter_opens_in", n=c.n(days))
        lines = [kit.text(c, sub, 13, "medium", "t_sand"), kit.text(c, c.t("letter_sealed_until", d=c.date(dt.date(), "medium")), 12, color="faint")]
        icon, tone = "LOCK", "sand"
    elif state == "arrived":
        lines = [kit.text(c, c.t("letter_arrived_label"), 13, "bold", "t_rose")]
        icon, tone = "MARK_EMAIL_UNREAD", "rose"
    else:
        lines = [kit.text(c, c.t("letter_opened_on", d=lists.day_text(c, letter.get("opened_at"))), 12.5, color="faint")]
        icon, tone = "MAIL_OUTLINE", "accent"
    body = kit.col(c, [kit.text(c, title, 16, "bold", max_lines=1), *lines], spacing=3, expand=True)
    return kit.card(c, kit.row(c, [kit.badge(c, icon, tone, 46), body], spacing=14), on_click=lambda e: app.push(read, letter_id=letter["id"]),
                    bg="t_rose_soft" if state == "arrived" else "surface", border=state != "arrived")


def view(app):
    c = app.ctx()
    data = app.profile.data
    now = util.now()
    body: list[Any] = [kit.text(c, c.t("letters_intro"), 13.5, color="muted"),
                       kit.button(c, c.t("write_letter"), lambda e: app.push(editor), "soft", "EDIT_NOTE", expand=True)]
    total = 0
    for state, key in (("arrived", "section_arrived"), ("sealed", "section_sealed"), ("opened", "section_opened")):
        items = reminders.letters_in_state(data, now, state)
        if items:
            total += len(items)
            body.append(kit.section_title(c, f"{c.t(key)} · {c.n(len(items))}"))
            body += [_card(app, c, l, state) for l in items]
    if not total:
        body.append(kit.empty(c, "MAIL", c.t("space_letters"), c.t("letters_intro")))
    return kit.screen(c, body, title=c.t("space_letters"), subtitle=c.t("space_letters_sub"), on_back=app.pop)


# --------------------------------------------------------------------------- reading
def read(app, letter_id: str):
    c = app.ctx()
    p = app.profile
    letter = p.get_item("letters", letter_id)
    if letter is None:
        return kit.screen(c, [kit.empty(c, "MAIL", c.t("space_letters"), c.t("letters_intro"))], title=c.t("space_letters"), on_back=app.pop)
    now = util.now()
    state = reminders.letter_state(letter, now)
    dt = _deliver_dt(letter)
    if state == "sealed":
        body = [kit.box(c, kit.badge(c, "LOCK", "sand", 84, 40), align=C.center()), kit.text(c, c.t("letter_not_yet"), 20, "bold", align="center"),
                kit.text(c, c.t("letter_sealed_until", d=_when_text(c, dt) if dt else ""), 14, color="muted", align="center"),
                kit.button(c, c.t("letter_change_time"), lambda e: app.push(editor, letter_id=letter_id), "soft", "SCHEDULE", expand=True)]
        return kit.screen(c, body, title=c.t("letter_from_past"), on_back=app.pop)
    if not letter.get("opened_at"):
        p.update_item("letters", letter_id, opened_at=now.isoformat(), notified=True)
        letter = p.get_item("letters", letter_id)

    def delete() -> None:
        p.delete_item("letters", letter_id)
        app.toast(c.t("deleted"))
        app.pop()

    title = (letter.get("title") or "").strip()
    paper = kit.col(c, [kit.text(c, title, 19, "bold") if title else None,
                        kit.text(c, c.t("letter_written", d=lists.day_text(c, letter.get("created"), "long")), 12.5, color="faint"),
                        kit.divider(c), kit.text(c, letter.get("body", ""), 16.5, selectable=True)], spacing=12)
    body = [kit.card(c, paper, padding=22, bg="t_sand_soft", border=False, radius=24),
            kit.button(c, c.t("letter_reply"), lambda e: app.replace(editor), "soft", "EDIT_NOTE", expand=True),
            kit.button(c, c.t("delete"), lambda e: app.confirm(c.t("confirm_delete_title"), c.t("confirm_delete_body"), delete, c.t("delete"), danger=True),
                       "danger", "DELETE_OUTLINE", expand=True)]
    return kit.screen(c, body, title=c.t("letter_from_past"), subtitle=c.date(now.date(), "long"), on_back=app.pop)


# --------------------------------------------------------------------------- writing / rescheduling
def editor(app, letter_id: str | None = None):
    c = app.ctx()
    p = app.profile
    letter = p.get_item("letters", letter_id) if letter_id else None
    now = util.now()
    st = app.state()
    if "day" not in st:
        dt = _deliver_dt(letter) if letter else None
        st.update(title=(letter or {}).get("title", ""), body=(letter or {}).get("body", ""), preset=None if dt else 30,
                  day=dt.date() if dt else app.today() + timedelta(days=30), time=util.fmt_hhmm(dt.hour, dt.minute) if dt else "09:00")
    reschedule = bool(letter) and reminders.letter_state(letter, now) == "sealed"
    tomorrow = now.date() + timedelta(days=1)

    def set_preset(days: int) -> None:
        st["preset"], st["day"] = days, now.date() + timedelta(days=days)
        app.refresh()

    def custom() -> None:
        def chosen(d: date) -> None:
            st["preset"], st["day"] = None, d
            app.refresh()

        lists.pick_date(app, c, st["day"] if st["day"] >= tomorrow else tomorrow, chosen, min_day=now.date())

    def set_time(v: str) -> None:
        st["time"] = v
        app.refresh()

    def save() -> None:
        if not reschedule and not (st["body"] or "").strip():
            app.toast(c.t("err_empty"), error=True)
            return
        h, m = util.parse_hhmm(st["time"], (9, 0))
        when = datetime.combine(st["day"], datetime.min.time()).replace(hour=h, minute=m)
        if when <= now:
            app.toast(c.t("err_future"), error=True)
            return
        fields = dict(deliver_at=when.isoformat(timespec="minutes"), notified=False, opened_at=None)
        if letter:
            p.update_item("letters", letter_id, **fields, **({} if reschedule else dict(title=st["title"].strip(), body=st["body"].strip())))
        else:
            p.add_item("letters", title=st["title"].strip(), body=st["body"].strip(), **fields)
        app.resync()
        app.toast(c.t("toast_letter_sealed"))
        app.pop()

    def delete() -> None:
        p.delete_item("letters", letter_id)
        app.resync()
        app.toast(c.t("deleted"))
        app.pop()

    body: list[Any] = []
    if reschedule:
        body.append(kit.card(c, kit.row(c, [kit.icon(c, "LOCK", 20, "t_sand"), kit.text(c, c.t("letter_sealed_note"), 13.5, color="muted", expand=True)], spacing=10),
                             bg="t_sand_soft", border=False))
    else:
        body += [kit.field(c, c.t("f_letter_title"), st["title"], on_change=lambda v: st.__setitem__("title", v)),
                 kit.field(c, c.t("f_letter_body"), st["body"], on_change=lambda v: st.__setitem__("body", v), multiline=True, lines=8)]
        prompts = [kit.text(c, c.t("letter_prompts"), 13, "bold", "muted")] + [
            kit.text(c, f"•  {fa if c.lang == 'fa' else en}", 13, color="muted") for fa, en in qc.LETTER_PROMPTS]
        body.append(kit.card(c, kit.col(c, prompts, spacing=4), bg="surface2", border=False))
    opts = [(str(d), fa if c.lang == "fa" else en) for d, fa, en in qc.LETTER_PRESETS]
    chips = kit.row(c, [kit.chip(c, label, st["preset"] == int(k), (lambda e, k=k: set_preset(int(k)))) for k, label in opts]
                    + [kit.chip(c, c.t("letter_custom"), st["preset"] is None, lambda e: custom(), "EVENT")], spacing=8, wrap=True, run_spacing=8)
    h, m = util.parse_hhmm(st["time"], (9, 0))
    when = datetime.combine(st["day"], datetime.min.time()).replace(hour=h, minute=m)
    body += [kit.text(c, c.t("f_letter_when"), 15, "bold"), chips,
             kit.card(c, kit.row(c, [kit.col(c, [kit.text(c, c.t("letter_time"), 13, color="muted"), kit.text(c, _when_text(c, when), 14.5, "medium")],
                                             spacing=4, expand=True), kit.time_stepper(c, st["time"], set_time)], spacing=12)),
             kit.button(c, c.t("letter_change_time") if reschedule else c.t("letter_seal"), lambda e: save(), "primary", "MAIL", expand=True)]
    if letter:
        body.append(kit.button(c, c.t("delete"), lambda e: app.confirm(c.t("confirm_delete_title"), c.t("confirm_delete_body"), delete, c.t("delete"),
                                                                       danger=True), "danger", "DELETE_OUTLINE", expand=True))
    return kit.screen(c, body, title=c.t("write_letter") if not letter else c.t("edit"), subtitle=c.t("space_letters"), on_back=app.pop)
