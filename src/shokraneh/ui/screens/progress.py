"""Progress tab: the month's energy & mood, what shapes it, and the monthly review with ideas to improve."""
from __future__ import annotations

from typing import Any

from ... import ai, analytics, coach, jalali, reports
from ...i18n import register
from .. import compat as C
from .. import kit
from . import inbox

register({
    "tab_progress_sub": ("حال و انرژی تو در طول ماه", "Your energy and mood through the month"),
    "prog_avg": ("میانگین", "Average"),
    "prog_best": ("بهترین", "Best"),
    "prog_logged": ("روز ثبت‌شده", "days logged"),
    "prog_vs_prev": ("{x} نسبت به ماه قبل", "{x} vs last month"),
    "prog_empty_t": ("برای این ماه هنوز داده‌ای نیست", "No data for this month yet"),
    "prog_empty_b": ("هر روز انرژی و حالت رو ثبت کن تا اینجا نمودارش ساخته بشه.", "Log your energy every day and your chart will build up here."),
    "prog_chart": ("انرژی و حال روزانه", "Daily energy & mood"),
    "prog_tap_day": ("روی هر ستون بزن تا همون روز رو ببینی.", "Tap a bar to open that day."),
    "prog_weekday": ("میانگین بر اساس روز هفته", "Average by weekday"),
    "prog_review": ("مرور ماه", "Monthly review"),
    "prog_review_ai": ("نوشته‌ی هوش مصنوعی", "Written by AI"),
    "prog_review_offline": ("برآمده از آمار تو", "Based on your numbers"),
    "prog_ask_ai": ("ایده‌های هوش مصنوعی برای این ماه", "AI ideas for this month"),
    "prog_save": ("ذخیره‌ی مرور در پیام‌ها", "Save the review to Messages"),
    "prog_this_month": ("این ماه", "This month"),
    "prog_writing": ("در حال نوشتن…", "Writing…"),
})


def _month_nav(app, c: kit.Ctx, label: str, offset: int) -> Any:
    st = app.state()

    def shift(n: int) -> None:
        st["pm"] = min(0, st.get("pm", 0) + n)
        app.refresh()

    nxt = kit.icon_button(c, c.dir_icon("next"), (lambda e: shift(1)) if offset < 0 else None, "text" if offset < 0 else "faint")
    return kit.card(c, kit.row(c, [kit.icon_button(c, c.dir_icon("prev"), lambda e: shift(-1), "text"),
                                   kit.text(c, label, 17, "bold", align="center", expand=True), nxt], spacing=0), padding=C.pad(6, 4, 6, 4))


def _stats(c: kit.Ctx, ms: dict) -> Any:
    s = ms["summary"]
    best = s["best"]
    cards = [kit.stat(c, c.fnum(s["avg"]), c.t("prog_avg"), "good"),
             kit.stat(c, c.n(best[1]) if best else "—", c.t("prog_best"), "sand"),
             kit.stat(c, c.n(s["logged"]), c.t("prog_logged"), "sky")]
    return kit.row(c, cards, spacing=10, v="start")


def _weekday_card(c: kit.Ctx, ms: dict, week_start: int) -> Any:
    prof = ms["weekday"]
    order = [(week_start + i) % 7 for i in range(7)]
    lo = min(prof, key=prof.get)
    bars = []
    for wd in order:
        v = prof.get(wd)
        h = 84
        fill = kit.box(c, None, height=max(8, round(h * v / 10)), bg=c.energy(v), radius=8) if v is not None else None
        track = kit.box(c, fill, height=h, bg="surface2", radius=8, align=C.align(0, 1))
        label = kit.text(c, jalali.WEEKDAYS_SHORT["fa" if c.lang == "fa" else "en"][wd], 11.5, "bold" if wd == lo else "regular", "bad" if wd == lo else "muted", align="center")
        val = kit.text(c, c.fnum(v) if v is not None else "·", 11, color="faint", align="center")
        bars.append(kit.col(c, [val, track, label], spacing=4, h="stretch", expand=True))
    return kit.card(c, kit.col(c, [kit.text(c, c.t("prog_weekday"), 15, "bold"), kit.row(c, bars, spacing=6, v="end")], spacing=12))


def content(app, c: kit.Ctx):
    from . import cal

    p = app.profile
    st = app.state()
    offset = st.get("pm", 0)
    today = app.today()
    jal = app.jal
    day = jalali.shift_month(today, offset, jal) if offset else today
    ms = reports.month_overview(p.data, day, jal, today)
    label = jalali.month_label(ms["start"], c.lang, jal)
    body: list[Any] = [_month_nav(app, c, label, offset)]
    s = ms["summary"]

    if s["avg"] is None:
        body.append(kit.empty(c, "INSIGHTS", c.t("prog_empty_t"), c.t("prog_empty_b")))
    else:
        body.append(_stats(c, ms))
        if ms.get("prev_avg") is not None:
            diff = round(s["avg"] - ms["prev_avg"], 1)
            sign = "+" if diff > 0 else "−" if diff < 0 else ""
            body.append(kit.text(c, c.t("prog_vs_prev", x=f"{sign}{c.fnum(abs(diff))}"), 12.5, color="muted", align="center"))
        chart = kit.col(c, [kit.text(c, c.t("prog_chart"), 15, "bold"),
                            kit.energy_chart(c, ms["series"], 150, on_tap=lambda d: app.push(cal.day_view, day=d), today=today),
                            kit.text(c, c.t("prog_tap_day"), 11.5, color="faint")], spacing=12)
        body.append(kit.card(c, chart))
        if len(ms["weekday"]) >= 3:
            body.append(_weekday_card(c, ms, app.week_start))

    # review: the stored (possibly AI-written) message for this month, otherwise the offline one computed live
    key = reports.month_key(ms["start"], jal)
    stored = reports.find_message(p.data, "monthly", key)
    if stored:
        sections, source = stored["sections"], stored.get("source")
    else:
        sections, source = coach.monthly_review(ms, c.lang, p.name, jal)["sections"], "offline"
    body.append(kit.row(c, [kit.text(c, c.t("prog_review"), 18, "bold", expand=True),
                            kit.pill(c, c.t("prog_review_ai" if source == "ai" else "prog_review_offline"), "lavender" if source == "ai" else "sage")], spacing=8))
    body += inbox.render_sections(c, sections)

    if offset == 0:
        ready = ai.is_ready(p.setting("ai") or {})
        busy = bool(st.get("busy"))

        def generate() -> None:
            st["busy"] = True
            app.refresh()
            args = (p, "monthly", today, app.lang, jal, app.week_start, p.name)

            def done(msg: Any, err: Exception | None) -> None:
                st["busy"] = False
                if err is not None:
                    app.toast(app.t("error_generic"), error=True)
                app.refresh()

            app.bg(lambda: reports.generate_now(*args), done=done)

        label_key = "prog_writing" if busy else ("prog_ask_ai" if ready else "prog_save")
        body.append(kit.button(c, c.t(label_key), lambda e: generate(), "soft", "AUTO_AWESOME" if ready else "MAIL_OUTLINE", expand=True, disabled=busy))
    return c.t("tab_progress"), c.t("tab_progress_sub"), [], body
