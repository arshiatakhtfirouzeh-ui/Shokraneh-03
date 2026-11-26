"""Personal lists — wishes, achievements, prayers, talks with God, loved ones, hard days.

One generic list screen + one generic editor, driven by the `SPACES` table below.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dfield
from datetime import date
from typing import Any, Callable

from ... import content as qc
from ... import util
from ...i18n import register
from .. import compat as C
from .. import kit

register({
    # ---- titles / subtitles / icons
    "space_wishes": ("آرزوها", "Wishes"),
    "space_wishes_sub": ("چیزهایی که دوست دارم برام اتفاق بیفته", "What I hope will come true"),
    "space_wins": ("موفقیت‌ها", "Achievements"),
    "space_wins_sub": ("هر پیروزیِ کوچیک و بزرگ", "Every small and big victory"),
    "space_god": ("صحبت با خدا", "Talking with God"),
    "space_god_sub": ("خلوتی ساده، با کلمات خودت", "A quiet talk, in your own words"),
    "space_prayers": ("دعاها", "Prayers"),
    "space_prayers_sub": ("دعاهایی که کردم و دعاهای مستجاب‌شده", "My prayers, and the ones answered"),
    "space_people": ("عزیزانم", "People I love"),
    "space_people_sub": ("کسانی که شکرگزارشونم و نمی‌خوام از دستشون بدم", "People I'm grateful for and never want to lose"),
    "space_hard": ("روزهای سخت", "Hard days"),
    "space_hard_sub": ("درسی که از روزهای سخت گرفتم", "What the hard days taught me"),
    "space_letters": ("نامه به آینده", "Letter to my future self"),
    "space_letters_sub": ("امروز می‌نویسم؛ سر وقتش بهم می‌رسه", "I write today; it reaches me when the time comes"),
    # ---- add buttons
    "add_wish": ("آرزوی تازه", "New wish"),
    "add_win": ("موفقیت تازه", "New achievement"),
    "add_god": ("صحبت تازه", "New talk"),
    "add_prayer": ("دعای تازه", "New prayer"),
    "add_person": ("افزودنِ یه عزیز", "Add someone dear"),
    "add_hard": ("ثبتِ یه روز سخت", "Record a hard day"),
    # ---- empty states
    "empty_wishes_t": ("هنوز آرزویی ننوشتی", "No wishes yet"),
    "empty_wishes_b": ("آرزوهات رو بنویس؛ نوشتنشون قدم اوله.", "Write your wishes down — that's the first step."),
    "empty_wins_t": ("لیست موفقیت‌ها خالیه", "Your achievements list is empty"),
    "empty_wins_b": ("هر چیزی که بهش افتخار می‌کنی رو اینجا جمع کن.", "Collect everything you're proud of here."),
    "empty_god_t": ("اینجا جای خلوت تو با خداست", "This is your quiet place with God"),
    "empty_god_b": ("هر چی تو دلته بنویس؛ لازم نیست قشنگ باشه.", "Write whatever is in your heart; it doesn't have to be pretty."),
    "empty_prayers_t": ("هنوز دعایی ننوشتی", "No prayers yet"),
    "empty_prayers_b": ("دعاهات رو بنویس تا وقتی مستجاب شدن، شکرش رو بکنی.", "Write your prayers so you can give thanks when they're answered."),
    "empty_people_t": ("عزیزانت رو اینجا نگه دار", "Keep your loved ones here"),
    "empty_people_b": ("اسم کسانی که دوستشون داری رو بنویس و بابتشون شکرگزاری کن.", "Add the people you love and give thanks for them."),
    "empty_hard_t": ("روز سختی ثبت نشده", "No hard days recorded"),
    "empty_hard_b": ("وقتی روز سختی داشتی، درسش رو اینجا بنویس تا بعداً یادت بمونه.", "When a day is hard, write its lesson here so you remember it later."),
    # ---- field labels / hints
    "f_wish_text": ("آرزوم…", "My wish…"),
    "f_wish_hint": ("مثلاً: یه سفر به شمال با خانواده", "e.g. A trip with my family"),
    "f_wish_note": ("چرا برام مهمه؟ (اختیاری)", "Why does it matter to me? (optional)"),
    "f_win_text": ("چه موفقیتی داشتم؟", "What did I achieve?"),
    "f_win_hint": ("هر چقدر هم کوچیک", "No matter how small"),
    "f_category": ("دسته", "Category"),
    "f_date": ("تاریخ", "Date"),
    "f_prayer_text": ("دعام…", "My prayer…"),
    "f_prayer_note": ("یادداشت (اختیاری)", "Note (optional)"),
    "f_god_text": ("به خدا چی می‌خوای بگی؟", "What would you like to tell God?"),
    "f_god_starters": ("برای شروع", "To begin"),
    "f_person_name": ("اسم", "Name"),
    "f_relation": ("نسبت", "Relationship"),
    "f_person_grat": ("بابت چی ازش ممنونم؟", "What am I grateful to them for?"),
    "f_person_grat_hint": ("مثلاً: همیشه گوش شنوا بوده", "e.g. They've always listened to me"),
    "f_person_keep": ("چرا نمی‌خوام از دستش بدم؟", "Why would I never want to lose them?"),
    "f_person_keep_hint": ("شکرگزارم که هست…", "I'm grateful that they are in my life…"),
    "f_hard_what": ("چی شد؟", "What happened?"),
    "f_hard_what_hint": ("کوتاه، بدون قضاوت", "Short, without judging"),
    "f_hard_lesson": ("چه درسی ازش گرفتم؟", "What lesson did I take from it?"),
    "f_hard_lesson_hint": ("این جمله بعداً بهت یادآوری می‌شه", "You'll be reminded of this line later"),
    "f_hard_next": ("دفعه‌ی بعد چی کمکم می‌کنه؟ (اختیاری)", "What will help me next time? (optional)"),
    "choose_date": ("انتخاب تاریخ", "Choose a date"),
    # ---- list UI
    "section_fulfilled": ("محقق‌شده‌ها", "Fulfilled"),
    "section_answered": ("مستجاب‌شده‌ها", "Answered"),
    "toast_wish_done": ("چه عالی! آرزوت محقق شد 🎉", "Wonderful! Your wish came true 🎉"),
    "toast_prayer_done": ("شکر! دعات مستجاب شد 🤲", "Gratitude! Your prayer was answered 🤲"),
    "mark_done": ("علامت‌گذاری", "Mark"),
    "last_contact": ("آخرین سر زدن: {d}", "Last reached out: {d}"),
    "last_contact_none": ("هنوز ثبت نشده", "Not recorded yet"),
    "days_ago": ("{n} روز پیش", "{n} days ago"),
    "today_word": ("امروز", "today"),
    "reached_out": ("سر زدم", "I reached out"),
    "toast_reached": ("عالیه! محبتت رو نشون دادی 💛", "Lovely — you showed you care 💛"),
    "lesson_label": ("درسی که گرفتم", "My lesson"),
    "next_label": ("دفعه‌ی بعد", "Next time"),
    "grateful_for": ("بابت: {x}", "Grateful for: {x}"),
})


@dataclass
class F:
    key: str
    kind: str  # text | area | chips | date | starters
    label: str  # i18n key
    hint: str | None = None
    options: dict | None = None
    lines: int = 4


@dataclass
class Space:
    coll: str
    icon: str
    tone: str
    fields: list[F]
    required_any: tuple[str, ...]
    add: str
    split: tuple[str, str] | None = None  # (done flag, section title key): finished items go to a lower section
    new_extra: Callable[[Any], dict] = dfield(default=lambda app: {})
    defaults: Callable[[Any], dict] = dfield(default=lambda app: {})

    @property
    def title(self) -> str:
        return f"space_{self.key}"

    @property
    def key(self) -> str:
        return {"wishes": "wishes", "wins": "wins", "god_talks": "god", "prayers": "prayers", "people": "people", "hard_days": "hard"}[self.coll]


def _today_iso(app) -> str:
    return app.today().isoformat()


SPACES: dict[str, Space] = {
    "wishes": Space("wishes", "AUTO_AWESOME", "lavender",
                    [F("text", "area", "f_wish_text", "f_wish_hint", lines=3), F("note", "area", "f_wish_note", lines=3)],
                    ("text",), "add_wish", split=("done", "section_fulfilled"), new_extra=lambda app: {"done": False}),
    "wins": Space("wins", "EMOJI_EVENTS", "sand",
                  [F("text", "area", "f_win_text", "f_win_hint", lines=3), F("category", "chips", "f_category", options=qc.WIN_CATEGORIES),
                   F("date", "date", "f_date")], ("text",), "add_win",
                  defaults=lambda app: {"category": "personal", "date": _today_iso(app)}),
    "god_talks": Space("god_talks", "FORUM", "sky",
                       [F("starters", "starters", "f_god_starters"), F("text", "area", "f_god_text", lines=8)], ("text",), "add_god"),
    "prayers": Space("prayers", "SELF_IMPROVEMENT", "sage",
                     [F("text", "area", "f_prayer_text", lines=4), F("note", "area", "f_prayer_note", lines=2)],
                     ("text",), "add_prayer", split=("answered", "section_answered"), new_extra=lambda app: {"answered": False}),
    "people": Space("people", "FAVORITE", "rose",
                    [F("name", "text", "f_person_name"), F("relation", "chips", "f_relation", options=qc.RELATIONS),
                     F("gratitude", "area", "f_person_grat", "f_person_grat_hint", lines=3),
                     F("keep", "area", "f_person_keep", "f_person_keep_hint", lines=3)],
                    ("name",), "add_person", defaults=lambda app: {"relation": "family"}, new_extra=lambda app: {"last_reached": None}),
    "hard_days": Space("hard_days", "PSYCHOLOGY", "warn",
                       [F("date", "date", "f_date"), F("what", "area", "f_hard_what", "f_hard_what_hint", lines=3),
                        F("lesson", "area", "f_hard_lesson", "f_hard_lesson_hint", lines=3), F("next", "area", "f_hard_next", lines=2)],
                       ("what", "lesson"), "add_hard", defaults=lambda app: {"date": _today_iso(app)}),
}


# --------------------------------------------------------------------------- helpers
def day_text(c: kit.Ctx, iso: str | None, style: str = "medium") -> str:
    if not iso:
        return ""
    try:
        return c.date(util.parse_day(iso[:10]), style)
    except ValueError:
        return ""


def _check(c: kit.Ctx, on: bool, on_click: Callable) -> Any:
    inner = kit.icon(c, "CHECK", 18, "on_accent") if on else None
    return kit.box(c, inner, width=30, height=30, radius=15, bg="accent" if on else None, border=not on, border_color="accent",
                   align=C.center(), on_click=on_click)


def _edit(app, coll: str, item_id: str) -> Callable:
    return lambda e: app.push(editor, coll=coll, item_id=item_id)


# --------------------------------------------------------------------------- item cards
def _card_toggle(app, c: kit.Ctx, spec: Space, item: dict) -> Any:
    flag = spec.split[0]
    done = bool(item.get(flag))

    def toggle(e: Any) -> None:
        now_done = not done
        app.profile.update_item(spec.coll, item["id"], **{flag: now_done, f"{flag}_at": _today_iso(app) if now_done else None})
        if now_done:
            app.toast(c.t("toast_wish_done" if spec.coll == "wishes" else "toast_prayer_done"))
        app.refresh()

    note = (item.get("note") or "").strip()
    body = kit.col(c, [kit.text(c, item.get("text", ""), 16, "medium", "muted" if done else "text", max_lines=4),
                       kit.text(c, note, 13, color="muted", max_lines=2) if note else None,
                       kit.text(c, day_text(c, item.get(f"{flag}_at")), 12, color="faint") if done and item.get(f"{flag}_at") else None],
                   spacing=4, expand=True)
    return kit.card(c, kit.row(c, [_check(c, done, toggle), body], spacing=14, v="start"), on_click=_edit(app, spec.coll, item["id"]),
                    padding=C.pad(16, 14, 16, 14))


def _card_win(app, c: kit.Ctx, spec: Space, item: dict) -> Any:
    cat = qc.label(qc.WIN_CATEGORIES, item.get("category", "other"), c.lang)
    meta = kit.row(c, [kit.pill(c, cat, "sand"), kit.text(c, day_text(c, item.get("date") or item.get("created")), 12, color="faint")], spacing=8)
    body = kit.col(c, [kit.text(c, item.get("text", ""), 16, "medium", max_lines=4), meta], spacing=8, expand=True)
    return kit.card(c, kit.row(c, [kit.badge(c, "EMOJI_EVENTS", "sand", 42), body], spacing=14, v="start"),
                    on_click=_edit(app, spec.coll, item["id"]), padding=C.pad(14, 14, 16, 14))


def _card_god(app, c: kit.Ctx, spec: Space, item: dict) -> Any:
    stamp = day_text(c, item.get("created"), "medium")
    body = kit.col(c, [kit.row(c, [kit.icon(c, "FORUM", 16, "t_sky"), kit.text(c, stamp, 12.5, "medium", "t_sky")], spacing=6),
                       kit.text(c, item.get("text", ""), 15.5, max_lines=7)], spacing=8)
    return kit.card(c, body, on_click=_edit(app, spec.coll, item["id"]), bg="t_sky_soft", border=False, padding=C.pad(18, 14, 18, 16))


def _card_person(app, c: kit.Ctx, spec: Space, item: dict) -> Any:
    last = item.get("last_reached")
    if last:
        gap = (app.today() - util.parse_day(last[:10])).days
        when = c.t("today_word") if gap <= 0 else c.t("days_ago", n=c.n(gap))
        last_line = c.t("last_contact", d=when)
    else:
        last_line = c.t("last_contact", d=c.t("last_contact_none"))

    def reached(e: Any) -> None:
        app.profile.update_item("people", item["id"], last_reached=_today_iso(app))
        app.toast(c.t("toast_reached"))
        app.refresh()

    grat = (item.get("gratitude") or "").strip()
    head = kit.row(c, [kit.text(c, item.get("name", ""), 17, "bold", max_lines=1),
                       kit.pill(c, qc.label(qc.RELATIONS, item.get("relation", "other"), c.lang), "rose")], spacing=8, wrap=True, run_spacing=4)
    body = kit.col(c, [head, kit.text(c, c.t("grateful_for", x=grat), 13.5, color="muted", max_lines=2) if grat else None,
                       kit.text(c, last_line, 12, color="faint")], spacing=4, expand=True)
    initial = (item.get("name") or "?").strip()[:1]
    av = kit.box(c, kit.text(c, initial, 19, "bold", "t_rose", align="center"), width=46, height=46, radius=23, bg="t_rose_soft", align=C.center())
    return kit.card(c, kit.row(c, [av, body, kit.button(c, c.t("reached_out"), reached, "soft", size="sm")], spacing=12),
                    on_click=_edit(app, spec.coll, item["id"]), padding=C.pad(14, 14, 12, 14))


def _card_hard(app, c: kit.Ctx, spec: Space, item: dict) -> Any:
    what = (item.get("what") or "").strip()
    lesson = (item.get("lesson") or "").strip()
    nxt = (item.get("next") or "").strip()
    parts: list[Any] = [kit.text(c, day_text(c, item.get("date") or item.get("created")), 12.5, "medium", "faint")]
    if what:
        parts.append(kit.text(c, what, 15, max_lines=3))
    if lesson:
        box = kit.col(c, [kit.row(c, [kit.icon(c, "LIGHTBULB", 16, "t_warn"), kit.text(c, c.t("lesson_label"), 12.5, "bold", "t_warn")], spacing=6),
                          kit.text(c, lesson, 15.5, "medium", max_lines=4)], spacing=4)
        parts.append(kit.box(c, box, padding=C.pad(14, 10, 14, 12), bg="t_warn_soft", radius=14))
    if nxt:
        parts.append(kit.text(c, f"{c.t('next_label')}: {nxt}", 13, color="muted", max_lines=2))
    return kit.card(c, kit.col(c, parts, spacing=8), on_click=_edit(app, spec.coll, item["id"]))


RENDER = {"wishes": _card_toggle, "prayers": _card_toggle, "wins": _card_win, "god_talks": _card_god, "people": _card_person, "hard_days": _card_hard}


def _sort(spec: Space, items: list[dict]) -> list[dict]:
    key = {"wins": lambda i: (i.get("date") or "", i.get("created") or ""), "hard_days": lambda i: (i.get("date") or "", i.get("created") or ""),
           "people": lambda i: (i.get("name") or "").lower()}.get(spec.coll, lambda i: i.get("created") or "")
    return sorted(items, key=key, reverse=spec.coll != "people")


# --------------------------------------------------------------------------- list screen
def view(app, coll: str):
    c = app.ctx()
    spec = SPACES[coll]
    items = _sort(spec, list(app.profile.items(coll)))
    body: list[Any] = [kit.button(c, c.t(spec.add), lambda e: app.push(editor, coll=coll), "soft", "ADD", expand=True)]
    render = RENDER[coll]
    if not items:
        body.append(kit.empty(c, spec.icon, c.t(f"empty_{spec.key}_t"), c.t(f"empty_{spec.key}_b")))
    elif spec.split:
        flag, section = spec.split
        active = [i for i in items if not i.get(flag)]
        done = [i for i in items if i.get(flag)]
        body += [render(app, c, spec, i) for i in active]
        if done:
            body.append(kit.section_title(c, f"{c.t(section)} · {c.n(len(done))}"))
            body += [render(app, c, spec, i) for i in done]
    else:
        body += [render(app, c, spec, i) for i in items]
    return kit.screen(c, body, title=c.t(spec.title), subtitle=c.t(f"{spec.title}_sub"), on_back=app.pop)


# --------------------------------------------------------------------------- editor
def pick_date(app, c: kit.Ctx, current: date, on_pick: Callable[[date], None], min_day: date | None = None, max_day: date | None = None) -> None:
    chosen = {"d": current}
    picker = kit.DatePicker(c, current, lambda d: chosen.__setitem__("d", d), min_day=min_day, max_day=max_day, page=app.page)
    app.dialog(c.t("choose_date"), picker.host, [(c.t("cancel"), None, "ghost"), (c.t("ok"), lambda: on_pick(chosen["d"]), "primary")])


def _field_ui(app, c: kit.Ctx, spec: Space, f: F, st: dict) -> Any:
    vals = st["vals"]
    label = c.t(f.label)
    if f.kind == "text":
        return kit.field(c, label, vals.get(f.key, ""), on_change=lambda v, k=f.key: vals.__setitem__(k, v), hint=c.t(f.hint) if f.hint else None)
    if f.kind == "area":
        return kit.field(c, label, vals.get(f.key, ""), on_change=lambda v, k=f.key: vals.__setitem__(k, v), multiline=True, lines=f.lines,
                         hint=c.t(f.hint) if f.hint else None)
    if f.kind == "chips":
        def pick(k: str, key: str = f.key) -> None:
            vals[key] = k
            app.refresh()

        opts = [(k, qc.label(f.options, k, c.lang)) for k in f.options]
        return kit.col(c, [kit.text(c, label, 13.5, "medium", "muted"), kit.chips(c, opts, vals.get(f.key), pick)], spacing=8)
    if f.kind == "date":
        cur = util.parse_day((vals.get(f.key) or _today_iso(app))[:10])

        def chosen(d: date, key: str = f.key) -> None:
            vals[key] = d.isoformat()
            app.refresh()

        btn = kit.button(c, c.date(cur, "long"), lambda e: pick_date(app, c, cur, chosen, max_day=app.today()), "outline", "EVENT")
        return kit.col(c, [kit.text(c, label, 13.5, "medium", "muted"), btn], spacing=8, h="start")
    if f.kind == "starters":
        def starter(i: int) -> None:
            fa, en = qc.GOD_STARTERS[i]
            line = fa if c.lang == "fa" else en
            cur = vals.get("text", "").rstrip()
            vals["text"] = f"{cur}\n\n{line} " if cur else f"{line} "
            app.refresh()

        opts = [(str(i), (fa if c.lang == "fa" else en)) for i, (fa, en) in enumerate(qc.GOD_STARTERS)]
        return kit.col(c, [kit.text(c, label, 13.5, "medium", "muted"), kit.chips(c, opts, None, lambda k: starter(int(k)))], spacing=8)
    return None


def editor(app, coll: str, item_id: str | None = None):
    c = app.ctx()
    spec = SPACES[coll]
    p = app.profile
    item = p.get_item(coll, item_id) if item_id else None
    st = app.state()
    if "vals" not in st:
        st["vals"] = {f.key: (item.get(f.key) if item else spec.defaults(app).get(f.key, "")) or "" for f in spec.fields if f.kind != "starters"}

    def save() -> None:
        vals = {k: (v.strip() if isinstance(v, str) else v) for k, v in st["vals"].items()}
        if not any(vals.get(k) for k in spec.required_any):
            app.toast(c.t("err_empty"), error=True)
            return
        if item:
            p.update_item(coll, item_id, **vals)
        else:
            p.add_item(coll, **spec.new_extra(app), **vals)
        app.toast(c.t("saved"))
        app.pop()

    def delete() -> None:
        p.delete_item(coll, item_id)
        app.toast(c.t("deleted"))
        app.pop()

    body = [_field_ui(app, c, spec, f, st) for f in spec.fields]
    body.append(kit.button(c, c.t("save"), lambda e: save(), "primary", "CHECK", expand=True))
    if item:
        body.append(kit.button(c, c.t("delete"), lambda e: app.confirm(c.t("confirm_delete_title"), c.t("confirm_delete_body"), delete,
                                                                       c.t("delete"), danger=True), "danger", "DELETE_OUTLINE", expand=True))
    title = c.t("edit") if item else c.t(spec.add)
    return kit.screen(c, body, title=title, subtitle=c.t(spec.title), on_back=app.pop)
