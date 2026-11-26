"""Energy / mood check-in: quick pick, details dialog and the 'remember your own lessons' moment on low days."""
from __future__ import annotations

import random
from datetime import date

from ... import content as qc
from ...i18n import register
from .. import compat as C
from .. import kit

register({
    "energy_title": ("انرژی و حالت", "Energy & mood"),
    "energy_scale_low": ("۱ = خیلی کم", "1 = very low"),
    "energy_scale_high": ("۱۰ = عالی", "10 = excellent"),
    "energy_tags_q": ("چی روی حالت اثر داشت؟ (اختیاری)", "What shaped your day? (optional)"),
    "energy_note": ("یادداشت کوتاه (اختیاری)", "A short note (optional)"),
    "save": ("ذخیره", "Save"),
    "cancel": ("انصراف", "Cancel"),
    "yes": ("بله", "Yes"),
    "later": ("بعداً", "Later"),
    "thanks": ("ممنون", "Thanks"),
    "energy_saved": ("ثبت شد 🌿", "Saved 🌿"),
    "energy_high_msg": ("چه روز خوبی! یادت بمونه چی باعثش شد.", "A great day! Remember what made it so."),
    "energy_low_msg": ("روزهای کم‌انرژی هم می‌گذرن؛ امروز یه کار کوچیک و مهربونانه برای خودت بکن.", "Low days pass too. Do one small, kind thing for yourself today."),
    "energy_recall_title": ("یادت باشه…", "Remember…"),
    "energy_recall_body": ("روزی که سخت بود، این درس رو برای خودت نوشتی:", "On a hard day you wrote this lesson for yourself:"),
})


def _lesson(p) -> str | None:
    lessons = [h["lesson"].strip() for h in p.items("hard_days") if (h.get("lesson") or "").strip()]
    return random.choice(lessons) if lessons else None


def after_pick(app, day: date, score: int) -> None:
    c = app.ctx()
    app.refresh()
    if score <= 3:
        lesson = _lesson(app.profile)
        if lesson:
            body = kit.col(c, [kit.text(c, c.t("energy_recall_body"), 14, color="muted"), kit.text(c, f"«{lesson}»", 16, "medium")], spacing=10)
            app.dialog(c.t("energy_recall_title"), body, [(c.t("thanks"), None, "primary")])
        else:
            app.toast(c.t("energy_low_msg"))
    elif score >= 8:
        app.toast(c.t("energy_high_msg"))
    else:
        app.toast(c.t("energy_saved"))


def quick_pick(app, day: date, score: int) -> None:
    p = app.profile
    old = p.energy(day) or {}
    p.set_energy(day, score, old.get("tags"), old.get("note", ""))
    after_pick(app, day, score)


def sheet(app, day: date) -> None:
    """Dialog with the picker, optional tags and a note."""
    c = app.ctx()
    p = app.profile
    cur = p.energy(day) or {}
    st = {"score": cur.get("score"), "tags": set(cur.get("tags", [])), "note": cur.get("note", "")}
    host = kit.box(c, None)

    def render() -> None:
        tag_opts = [(k, qc.label(qc.TAGS, k, c.lang)) for k in qc.TAGS]
        host.content = kit.col(c, [
            kit.energy_picker(c, st["score"], pick),
            kit.row(c, [kit.text(c, c.t("energy_scale_low"), 11.5, color="faint", expand=True),
                        kit.text(c, c.t("energy_scale_high"), 11.5, color="faint")], spacing=4),
            kit.text(c, c.t("energy_tags_q"), 13.5, "medium"),
            kit.chips(c, tag_opts, st["tags"], toggle, multi=True),
            kit.field(c, c.t("energy_note"), st["note"], on_change=lambda v: st.__setitem__("note", v), multiline=True, lines=2),
        ], spacing=14)

    def pick(i: int) -> None:
        st["score"] = i
        render()
        app.page.update()

    def toggle(k: str) -> None:
        st["tags"] ^= {k}
        render()
        app.page.update()

    def save() -> None:
        if st["score"] is None:
            return
        p.set_energy(day, st["score"], sorted(st["tags"]), st["note"])
        after_pick(app, day, st["score"])

    render()
    app.dialog(c.t("energy_title"), host, [(c.t("cancel"), None, "ghost"), (c.t("save"), save, "primary")])
