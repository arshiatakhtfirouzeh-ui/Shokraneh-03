"""Calendar (a month grid with activity dots) and the day detail screen."""
from __future__ import annotations

from datetime import date
from typing import Any

from ... import analytics, jalali
from ... import content as qc
from ...i18n import register
from .. import compat as C
from .. import kit
from . import lists

register({
    "cal_today_btn": ("امروز", "Today"),
    "cal_legend_morning": ("صبح", "Morning"),
    "cal_legend_night": ("شب", "Evening"),
    "cal_legend_energy": ("انرژی", "Energy"),
    "cal_summary": ("{m} صبح · {n} شب · {e} ثبت انرژی", "{m} mornings · {n} evenings · {e} energy logs"),
    "day_future": ("این روز هنوز نرسیده.", "This day hasn't come yet."),
    "day_nothing": ("هنوز چیزی ننوشتی.", "Nothing written yet."),
    "day_write": ("نوشتن", "Write"),
    "day_energy_log": ("ثبت انرژی و حال", "Log energy & mood"),
    "day_hard_title": ("روز سخت", "Hard day"),
    "day_wins_title": ("موفقیت‌های این روز", "Achievements of this day"),
})


def _dot(c: kit.Ctx, color: str) -> Any:
    return kit.box(c, None, width=6, height=6, radius=3, bg=color)


def view(app):
    c = app.ctx()
    st = app.state()
    jal = app.jal
    today = app.today()
    data = app.profile.data
    cursor = st.setdefault("cursor", jalali.month_bounds(today, jal)[0])
    start, end = jalali.month_bounds(cursor, jal)

    def shift(n: int) -> None:
        st["cursor"] = jalali.shift_month(cursor, n, jal)
        app.refresh()

    def go_today() -> None:
        st["cursor"] = jalali.month_bounds(today, jal)[0]
        app.refresh()

    nav = kit.card(c, kit.row(c, [kit.icon_button(c, c.dir_icon("prev"), lambda e: shift(-1), "text"),
                                  kit.text(c, jalali.month_label(cursor, c.lang, jal), 17, "bold", align="center", expand=True),
                                  kit.icon_button(c, c.dir_icon("next"), lambda e: shift(1), "text")], spacing=0), padding=C.pad(6, 4, 6, 4))
    names = kit.row(c, [kit.box(c, kit.text(c, h, 12, color="faint", align="center"), expand=True, align=C.center())
                        for h in jalali.weekday_headers(c.lang, c.week_start)], spacing=2)
    weeks = []
    for week in jalali.month_matrix(cursor, jal, c.week_start):
        cells = []
        for d in week:
            if d is None:
                cells.append(kit.box(c, None, expand=True, height=54))
                continue
            key = d.isoformat()
            dots = []
            if data["morning"].get(key):
                dots.append(_dot(c, c.c("accent")))
            if data["night"].get(key):
                dots.append(_dot(c, c.c("t_lavender")))
            e = data["energy"].get(key)
            if e:
                dots.append(_dot(c, c.energy(e["score"])))
            future = d > today
            is_today = d == today
            inner = kit.col(c, [kit.text(c, c.n(c.day_num(d)), 14.5, "bold" if is_today else "regular", "accent_strong" if is_today else ("faint" if future else "text"), align="center"),
                                kit.row(c, dots or [kit.space(c, 6)], spacing=3, align="center")], spacing=4, h="center", align="center")
            cells.append(kit.box(c, inner, expand=True, height=54, radius=14, bg="accent_soft" if is_today else None, border=is_today, border_color="accent",
                                 align=C.center(), on_click=None if future else (lambda ev, d=d: app.push(day_view, day=d))))
        weeks.append(kit.row(c, cells, spacing=2))
    n_m = len(analytics.entries_between(data, "morning", start, end))
    n_n = len(analytics.entries_between(data, "night", start, end))
    n_e = len(analytics.entries_between(data, "energy", start, end))
    legend = kit.row(c, [kit.row(c, [_dot(c, c.c("accent")), kit.text(c, c.t("cal_legend_morning"), 12, color="muted")], spacing=6),
                         kit.row(c, [_dot(c, c.c("t_lavender")), kit.text(c, c.t("cal_legend_night"), 12, color="muted")], spacing=6),
                         kit.row(c, [_dot(c, c.c("good")), kit.text(c, c.t("cal_legend_energy"), 12, color="muted")], spacing=6)], spacing=16, align="center")
    body = [nav, kit.card(c, kit.col(c, [names, *weeks], spacing=4), padding=C.pad(10, 12, 10, 12)), legend,
            kit.text(c, c.t("cal_summary", m=c.n(n_m), n=c.n(n_n), e=c.n(n_e)), 13, color="muted", align="center")]
    actions = [kit.button(c, c.t("cal_today_btn"), lambda e: go_today(), "soft", size="sm")]
    return kit.screen(c, body, title=c.t("calendar"), on_back=app.pop, actions=actions)


# --------------------------------------------------------------------------- one day
def _answer_lines(c: kit.Ctx, q, ans: Any) -> list[Any]:
    if isinstance(ans, list):
        return [kit.text(c, f"•  {x}", 15) for x in ans if str(x).strip()]
    text = qc.label(qc.FEELINGS, ans, c.lang) if q.kind == "feeling" else str(ans)
    return [kit.text(c, text, 15)]


def _entry_card(app, c: kit.Ctx, kind: str, day: date, future: bool) -> Any:
    from . import questions

    qs = qc.MORNING if kind == "morning" else qc.NIGHT
    entry = app.profile.entry(kind, day)
    morning = kind == "morning"
    tone = "sand" if morning else "lavender"
    title = c.t("morning_title" if morning else "night_title")
    head = kit.row(c, [kit.badge(c, "WB_SUNNY" if morning else "NIGHTLIGHT_ROUND", tone, 40), kit.text(c, title, 16, "bold", expand=True),
                       None if future else kit.button(c, c.t("edit") if entry else c.t("day_write"), lambda e: app.push(questions.view, kind=kind, day=day), "soft", size="sm")],
                   spacing=12)
    parts: list[Any] = [head]
    if entry:
        for q in qs:
            ans = entry["answers"].get(q.id)
            if ans:
                parts += [kit.text(c, q.title(c.lang), 12.5, "medium", "muted"), *_answer_lines(c, q, ans)]
    else:
        parts.append(kit.text(c, c.t("day_nothing"), 13.5, color="faint"))
    return kit.card(c, kit.col(c, parts, spacing=6))


def _energy_card(app, c: kit.Ctx, day: date, future: bool) -> Any:
    from . import energy

    e = app.profile.energy(day)
    if e:
        s = e["score"]
        fg = "#10181A" if c.dark else ("#FFFFFF" if s <= 3 or s >= 8 else "#2A2418")
        num = kit.box(c, kit.text(c, c.n(s), 24, "bold", fg, align="center"), width=54, height=54, bg=c.energy(s), radius=17, align=C.center())
        tags = " · ".join(qc.label(qc.TAGS, t, c.lang) for t in e.get("tags", []))
        info = kit.col(c, [kit.text(c, c.t("home_energy_logged"), 15, "bold"), kit.text(c, tags, 12.5, color="muted") if tags else None,
                           kit.text(c, e.get("note", ""), 13, max_lines=3) if e.get("note") else None], spacing=3, expand=True)
        return kit.card(c, kit.row(c, [num, info, kit.link(c, c.t("edit"), lambda ev: energy.sheet(app, day))], spacing=14))
    if future:
        return None
    return kit.card(c, kit.row(c, [kit.badge(c, "SENTIMENT_SATISFIED_ALT", "good", 40), kit.text(c, c.t("home_energy_ask"), 15, "medium", expand=True),
                                   kit.button(c, c.t("day_energy_log"), lambda ev: energy.sheet(app, day), "soft", size="sm")], spacing=12))


def day_view(app, day: date):
    c = app.ctx()
    p = app.profile
    future = day > app.today()
    body: list[Any] = []
    if future:
        body.append(kit.text(c, c.t("day_future"), 14, color="muted", align="center"))
    body += [_energy_card(app, c, day, future), _entry_card(app, c, "morning", day, future), _entry_card(app, c, "night", day, future)]
    key = day.isoformat()
    for h in [h for h in p.items("hard_days") if (h.get("date") or h.get("created", ""))[:10] == key]:
        body.append(lists.RENDER["hard_days"](app, c, lists.SPACES["hard_days"], h))
    wins = [w for w in p.items("wins") if (w.get("date") or w.get("created", ""))[:10] == key]
    if wins:
        body.append(kit.section_title(c, c.t("day_wins_title")))
        body += [lists.RENDER["wins"](app, c, lists.SPACES["wins"], w) for w in wins]
    return kit.screen(c, [b for b in body if b is not None], title=c.date(day, "long"), subtitle=jalali.weekday_name(day, c.lang), on_back=app.pop)
