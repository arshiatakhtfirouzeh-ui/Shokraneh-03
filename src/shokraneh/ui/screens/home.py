"""Today tab."""
from __future__ import annotations

import random
from datetime import date, timedelta

from ... import analytics, content as qc, reminders, today as today_mod, util
from ...i18n import register
from .. import compat as C
from .. import kit

register({
    "greet_morning": ("صبح بخیر", "Good morning"),
    "greet_noon": ("ظهر بخیر", "Good afternoon"),
    "greet_evening": ("عصر بخیر", "Good evening"),
    "greet_night": ("شب بخیر", "Good evening"),
    "calendar": ("تقویم", "Calendar"),
    "settings": ("تنظیمات", "Settings"),
    "morning_title": ("شکرگزاری صبح", "Morning gratitude"),
    "night_title": ("شکرگزاری شب", "Evening gratitude"),
    "home_q_count": ("{n} سؤال · حدود {m} دقیقه", "{n} questions · about {m} min"),
    "home_progress": ("{a} از {n} پاسخ", "{a} of {n} answered"),
    "home_done": ("کامل شد ✓", "Completed ✓"),
    "start": ("شروع", "Start"),
    "continue": ("ادامه", "Continue"),
    "review": ("مرور", "Review"),
    "open": ("باز کن", "Open"),
    "home_letter_banner": ("نامه‌ای از خودت رسیده؛ وقتشه بخونیش.", "A letter from your past self has arrived."),
    "home_report_banner": ("گزارش تازه‌ای برات آماده‌ست.", "A new report is ready for you."),
    "home_energy_ask": ("امروز انرژی و حالت چنده؟", "How are your energy and mood today?"),
    "home_energy_sub": ("یه عدد از ۱ تا ۱۰ انتخاب کن؛ ۵ ثانیه بیشتر وقت نمی‌گیره.", "Pick a number from 1 to 10 — it takes five seconds."),
    "home_energy_logged": ("انرژی و حال امروز", "Today's energy & mood"),
    "details": ("جزئیات", "Details"),
    "stat_streak": ("روز پیاپی", "day streak"),
    "stat_week": ("ثبت این هفته", "entries this week"),
    "stat_energy": ("میانگین انرژی هفته", "weekly avg energy"),
    "memory_title": ("یادی از گذشته", "A memory"),
    "memory_sub": ("{date} بابت این شکرگزار بودی:", "On {date} you were grateful for:"),
    "hero_0": ("امروز رو شروع کن؛ یه قدم کوچیک کافیه.", "Start your day — one small step is enough."),
    "hero_1": ("شروع خوبی بود، ادامه بده.", "A good start — keep going."),
    "hero_2": ("فقط یه قدم تا کامل شدنِ امروز.", "Just one step from a complete day."),
    "hero_3": ("امروزت کامل شد؛ دمت گرم 🌿", "Your day is complete — well done 🌿"),
    "hero_of": ("{d} از {t} کار امروز", "{d} of {t} check-ins today"),
})


def _greeting(c: kit.Ctx) -> str:
    h = util.now().hour
    return c.t("greet_morning" if 4 <= h < 12 else "greet_noon" if 12 <= h < 17 else "greet_evening" if 17 <= h < 21 else "greet_night")


def _banner(c: kit.Ctx, icon: str, message: str, label: str, on_click, tone: str) -> object:
    fg, soft = c.tone(tone)
    return kit.card(c, kit.row(c, [kit.badge(c, icon, tone, 40), kit.text(c, message, 14.5, "medium", expand=True),
                                   kit.button(c, label, on_click, "soft", size="sm")], spacing=12),
                    bg=soft, border=False, padding=C.pad(14, 12, 12, 12))


def _practice_card(app, c: kit.Ctx, kind: str):
    from . import questions

    qs = qc.MORNING if kind == "morning" else qc.NIGHT
    entry = app.profile.entry(kind, app.today())
    answered = sum(1 for q in qs if entry and q.id in entry["answers"])
    n = len(qs)
    morning = kind == "morning"
    tone = "sand" if morning else "lavender"
    if answered == 0:
        sub, cta = c.t("home_q_count", n=c.n(n), m=c.n(3 if morning else 4)), c.t("start")
    elif answered < n:
        sub, cta = c.t("home_progress", a=c.n(answered), n=c.n(n)), c.t("continue")
    else:
        sub, cta = c.t("home_done"), c.t("review")
    head = kit.row(c, [kit.badge(c, "WB_SUNNY" if morning else "NIGHTLIGHT_ROUND", tone, 48),
                       kit.col(c, [kit.text(c, c.t("morning_title" if morning else "night_title"), 17, "bold"),
                                   kit.text(c, sub, 13, color="muted")], spacing=2, expand=True)], spacing=14)
    parts = [head]
    if 0 < answered < n:
        parts.append(kit.progress_bar(c, answered / n, 6, f"t_{tone}"))
    parts.append(kit.button(c, cta, lambda e: app.push(questions.view, kind=kind, day=app.today()),
                            "primary" if answered < n else "soft", expand=True))
    fg, soft = c.tone(tone)
    return kit.card(c, kit.col(c, parts, spacing=12), tint=tone,
                    gradient=None if c.glassy else C.gradient([soft, c.pal["surface"]], (-1, -1), (0.6, 1)))


def _energy_card(app, c: kit.Ctx):
    from . import energy

    today = app.today()
    e = app.profile.energy(today)
    if e:
        s = e["score"]
        fg = "#10181A" if c.dark else ("#FFFFFF" if s <= 3 or s >= 8 else "#2A2418")
        num = kit.box(c, kit.text(c, c.n(s), 26, "bold", fg, align="center"), width=58, height=58, bg=c.energy(s), radius=18, align=C.center())
        sub = " · ".join([qc.label(qc.TAGS, t, c.lang) for t in e.get("tags", [])]) or e.get("note") or c.t("home_energy_sub")
        info = kit.col(c, [kit.text(c, c.t("home_energy_logged"), 15.5, "bold"), kit.text(c, sub, 12.5, color="muted", max_lines=2)], spacing=3, expand=True)
        return kit.card(c, kit.row(c, [num, info, kit.link(c, c.t("details"), lambda ev: energy.sheet(app, today))], spacing=14))
    return kit.card(c, kit.col(c, [kit.text(c, c.t("home_energy_ask"), 17, "bold"), kit.text(c, c.t("home_energy_sub"), 13, color="muted"),
                                   kit.energy_picker(c, None, lambda i: energy.quick_pick(app, today, i))], spacing=12))


def _stats(app, c: kit.Ctx, today: date):
    data = app.profile.data
    cur, _best = analytics.streaks(data, today)
    start = today - timedelta(days=6)
    entries = sum(len(analytics.entries_between(data, k, start, today)) for k in ("morning", "night"))
    avg = analytics.energy_summary(analytics.energy_series(data, start, today))["avg"]
    return kit.row(c, [kit.stat(c, c.n(cur), c.t("stat_streak"), "warn", "LOCAL_FIRE_DEPARTMENT"),
                       kit.stat(c, c.n(entries), c.t("stat_week"), "sky", "EDIT_NOTE"),
                       kit.stat(c, c.fnum(avg) if avg is not None else "—", c.t("stat_energy"), "good", "SENTIMENT_SATISFIED_ALT")],
                   spacing=10, v="start")


def _glass_button(c: kit.Ctx, icon_name: str, on_click, tip: str):
    return kit.box(c, kit.icon(c, icon_name, 22, "on_accent"), width=44, height=44, radius=22, bg="glass", align=C.center(), on_click=on_click,
                   tooltip=tip)


def _hero(app, c: kit.Ctx, today: date, greeting: str):
    from . import cal, settings

    p = app.profile
    st = today_mod.status(p, today)
    done, total = st["done"], st["total"]
    top = kit.row(c, [
        kit.box(c, kit.text(c, p.avatar, 24, align="center"), width=50, height=50, radius=25, bg="glass", align=C.center()),
        kit.col(c, [kit.text(c, greeting, 13.5, "medium", "on_accent", max_lines=1), kit.text(c, p.name, 22, "bold", "on_accent", max_lines=1)],
                spacing=1, expand=True),
        _glass_button(c, "CALENDAR_MONTH", lambda e: app.push(cal.view), c.t("calendar")),
        _glass_button(c, "SETTINGS_OUTLINED", lambda e: app.push(settings.view), c.t("settings")),
    ], spacing=10)
    ring = kit.ring(c, done / total, 88, 9, center=kit.text(c, f"{c.n(done)}/{c.n(total)}", 19, "bold", "on_accent", align="center"))
    info = kit.col(c, [kit.text(c, c.date(today, "long"), 13, "medium", "on_accent"),
                       kit.text(c, c.t(f"hero_{done}"), 15.5, "bold", "on_accent")], spacing=4, expand=True)
    return kit.hero(c, kit.col(c, [top, kit.row(c, [ring, info], spacing=16)], spacing=18), padding=C.pad(18, 18, 18, 20))


def _memory(app, c: kit.Ctx, today: date):
    data = app.profile.data
    cutoff = today - timedelta(days=7)
    pool: list[tuple[date, str]] = []
    for kind, qid in (("morning", "m1"), ("morning", "m2"), ("night", "n1")):
        for key, entry in data[kind].items():
            d = analytics._to_day(key)
            if d and d <= cutoff:
                pool += [(d, i) for i in analytics._flatten(entry.get("answers", {}).get(qid)) if len(i) > 2]
    if not pool:
        return None
    d, item = random.Random(today.toordinal()).choice(sorted(pool))
    return kit.card(c, kit.col(c, [kit.row(c, [kit.icon(c, "HISTORY", 20, "t_lavender"), kit.text(c, c.t("memory_title"), 14, "bold", "t_lavender")], spacing=8),
                                   kit.text(c, c.t("memory_sub", date=c.date(d, "medium")), 12.5, color="muted"),
                                   kit.text(c, f"«{item}»", 16, "medium")], spacing=6), bg="t_lavender_soft", border=False)


def content(app, c: kit.Ctx):
    from . import letters

    p = app.profile
    today = app.today()
    now = util.now()
    body = [_hero(app, c, today, _greeting(c))]
    arrived = reminders.letters_in_state(p.data, now, "arrived")
    if arrived:
        body.append(_banner(c, "MAIL", c.t("home_letter_banner"), c.t("open"), lambda e: app.push(letters.read, letter_id=arrived[0]["id"]), "rose"))
    if p.unread_count():
        body.append(_banner(c, "AUTO_AWESOME", c.t("home_report_banner"), c.t("open"), lambda e: app.go("inbox"), "sky"))
    body.append(kit.quote_card(c, qc.day_affirmation(today, c.lang)))
    body.append(_stats(app, c, today))
    order = ["night", "morning"] if (now.hour >= 17 or now.hour < 4) else ["morning", "night"]
    body += [_practice_card(app, c, k) for k in order]
    body.append(_energy_card(app, c))
    mem = _memory(app, c, today)
    if mem is not None:
        body.append(mem)
    return None, None, [], body
