"""Morning / evening gratitude: a calm one-question-at-a-time flow that autosaves as you type."""
from __future__ import annotations

from datetime import date

from ... import content as qc
from ...i18n import register
from .. import compat as C
from .. import kit

register({
    "wiz_next": ("بعدی", "Next"),
    "wiz_back": ("قبلی", "Back"),
    "wiz_finish": ("پایان و ذخیره", "Finish"),
    "wiz_step": ("سؤال {i} از {n}", "Question {i} of {n}"),
    "wiz_item_hint": ("مورد {i}", "Item {i}"),
    "wiz_text_hint": ("اینجا بنویس…", "Write here…"),
    "wiz_feeling_other": ("یا با کلمات خودت بنویس…", "Or write it in your own words…"),
    "wiz_saved_auto": ("همه‌چیز خودکار ذخیره می‌شه", "Everything is saved automatically"),
    "wiz_done_morning": ("صبحت قشنگ شروع شد ☀️", "A lovely start to your day ☀️"),
    "wiz_done_night": ("شب بخیر؛ امروز رو با دل آروم تموم کن 🌙", "Good night — close the day with a calm heart 🌙"),
    "wiz_done_night_body": ("هر چیزی که امروز نوشتی، در دفترت می‌مونه.", "Everything you wrote stays safely in your journal."),
    "wiz_review": ("مرور جواب‌ها", "Review answers"),
    "wiz_home": ("برگشت", "Done"),
})


def _save_fn(app, kind: str, day: date, st: dict):
    def save() -> None:
        app.profile.save_entry(kind, day, st["answers"])
    return save


def _list_inputs(app, c: kit.Ctx, q, st: dict, save) -> list:
    vals = [str(v) for v in (st["answers"].get(q.id) or [])]
    vals = (vals + [""] * q.count)[: q.count]
    st["answers"][q.id] = vals
    out = []
    for i in range(q.count):
        def changed(v: str, i: int = i) -> None:
            st["answers"][q.id][i] = v
            app.debounce("wiz", 1.0, save)

        num = kit.box(c, kit.text(c, c.n(i + 1), 13, "bold", "accent_strong", align="center"), width=30, height=30,
                      bg="accent_soft", radius=15, align=C.center())
        out.append(kit.row(c, [num, kit.field(c, value=vals[i], on_change=changed, hint=c.t("wiz_item_hint", i=c.n(i + 1)), expand=True)], spacing=10))
    return out


def _feeling_inputs(app, c: kit.Ctx, q, st: dict, save) -> list:
    cur = st["answers"].get(q.id, "")
    sel = cur if cur in qc.FEELINGS else None

    def pick(key: str) -> None:
        st["answers"][q.id] = "" if key == sel else key
        save()
        app.refresh()

    def typed(v: str) -> None:
        st["answers"][q.id] = v
        app.debounce("wiz", 1.0, save)

    opts = [(k, qc.label(qc.FEELINGS, k, c.lang)) for k in qc.FEELINGS]
    return [kit.chips(c, opts, sel, pick), kit.field(c, c.t("wiz_feeling_other"), "" if sel else cur, on_change=typed)]


def _text_inputs(app, c: kit.Ctx, q, st: dict, save) -> list:
    def changed(v: str) -> None:
        st["answers"][q.id] = v
        app.debounce("wiz", 1.0, save)

    return [kit.field(c, value=st["answers"].get(q.id, "") or "", on_change=changed, multiline=True, lines=5, hint=c.t("wiz_text_hint"))]


def _done(app, c: kit.Ctx, kind: str, day: date, st: dict, save) -> list:
    from . import energy

    morning = kind == "morning"
    body = [
        kit.box(c, kit.badge(c, "CHECK_CIRCLE_OUTLINE", "good", 84, 44), align=C.center()),
        kit.text(c, c.t("wiz_done_morning" if morning else "wiz_done_night"), 21, "bold", align="center"),
        kit.text(c, qc.day_affirmation(day, c.lang) if morning else c.t("wiz_done_night_body"), 15, color="muted", align="center"),
    ]
    if app.profile.energy(day) is None:
        body.append(kit.card(c, kit.col(c, [kit.text(c, c.t("home_energy_ask"), 16, "bold"),
                                            kit.energy_picker(c, None, lambda i: energy.quick_pick(app, day, i))], spacing=12)))

    def review() -> None:
        st["done"], st["step"] = False, 0
        app.refresh()

    body.append(kit.row(c, [kit.button(c, c.t("wiz_review"), lambda e: review(), "ghost", expand=True),
                            kit.button(c, c.t("wiz_home"), lambda e: app.pop(), "primary", expand=True)], spacing=10))
    return body


def view(app, kind: str, day: date):
    c = app.ctx()
    qs = qc.MORNING if kind == "morning" else qc.NIGHT
    st = app.state()
    if "answers" not in st:
        entry = app.profile.entry(kind, day)
        st["answers"] = {k: (list(v) if isinstance(v, list) else v) for k, v in (entry["answers"] if entry else {}).items()}
        st["step"] = next((i for i, q in enumerate(qs) if q.id not in st["answers"]), 0)
        st["done"] = False
    save = _save_fn(app, kind, day, st)
    app.on_leave(save)
    title = c.t("morning_title" if kind == "morning" else "night_title")
    sub = c.date(day, "long")

    if st["done"]:
        return kit.screen(c, _done(app, c, kind, day, st, save), title=title, subtitle=sub, on_back=app.pop)

    step = max(0, min(st["step"], len(qs) - 1))
    q = qs[step]

    def go(to: int) -> None:
        save()
        st["step"], st["done"] = to, False
        app.refresh()

    def finish() -> None:
        save()
        st["done"] = True
        app.refresh()

    maker = {"list": _list_inputs, "feeling": _feeling_inputs}.get(q.kind, _text_inputs)
    head = kit.card(c, kit.col(c, [
        kit.row(c, [kit.badge(c, q.icon, "accent", 44), kit.text(c, c.t("wiz_step", i=c.n(step + 1), n=c.n(len(qs))), 12.5, color="faint")], spacing=12),
        kit.text(c, q.title(c.lang), 20, "bold"), kit.text(c, q.hint(c.lang), 13.5, color="muted")], spacing=10), padding=18)
    last = step == len(qs) - 1
    nav = kit.row(c, [
        kit.button(c, c.t("wiz_back"), lambda e: go(step - 1), "ghost", expand=True) if step > 0 else None,
        kit.button(c, c.t("wiz_finish") if last else c.t("wiz_next"), (lambda e: finish()) if last else (lambda e: go(step + 1)), "primary", expand=True),
    ], spacing=10)
    body = [kit.steps_bar(c, len(qs), step), head, *maker(app, c, q, st, save), kit.space(c, 4), nav,
            kit.text(c, c.t("wiz_saved_auto"), 12, color="faint", align="center")]
    return kit.screen(c, body, title=title, subtitle=sub, on_back=app.pop)
