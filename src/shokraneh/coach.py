"""Offline 'coach': turns analytics into weekly / monthly written reports (fa + en).

This is the always-available fallback of the optional online AI (see ai.py) and
produces the same message structure: {"title", "sections": [{"h", "text"|"items"}], "source"}.
"""
from __future__ import annotations

import random
from datetime import date

from . import content, jalali, util

# --------------------------------------------------------------------------- text tables
HEADINGS = {
    "glance": ("نگاه کلی", "At a glance"),
    "well": ("چی خوب پیش رفت", "What went well"),
    "feedback": ("بازخورد صادقانه", "Honest feedback"),
    "next": ("برای هفته‌ی بعد", "For next week"),
    "patterns": ("الگوهای این ماه", "Patterns this month"),
    "tips": ("پیشنهادهایی برای انرژی بهتر", "Ideas for better energy"),
    "note": ("یه حرف مهربون", "A gentle note"),
}

X = {
    "glance_e": (
        "این هفته {m} صبح و {n} شب از {days} روز رو نوشتی. میانگین انرژی‌ت {avg} از ۱۰ بود{trend}. بهترین روزت {best_day} ({best}) و کم‌انرژی‌ترین روزت {worst_day} ({worst}) بود.{streak}",
        "This week you wrote {m} morning and {n} night reflections out of {days} days. Your average energy was {avg}/10{trend}. Your best day was {best_day} ({best}); your lowest was {worst_day} ({worst}).{streak}",
    ),
    "glance_n": (
        "این هفته {m} صبح و {n} شب از {days} روز رو نوشتی. انرژی‌ت رو ثبت نکردی؛ با ثبت روزانه‌ش می‌تونم الگوهای انرژی‌ت رو نشونت بدم.{streak}",
        "This week you wrote {m} morning and {n} night reflections out of {days} days. You didn't log your energy, so I can't show energy patterns yet — it takes five seconds a day.{streak}",
    ),
    "glance_empty": (
        "این هفته هنوز چیزی ننوشتی. هیچ‌وقت دیر نیست؛ همین امروز فقط یه سؤال رو جواب بده.",
        "You haven't written anything this week yet. It's never too late — answer just one question today.",
    ),
    "trend_up": (" و توی نیمه‌ی دوم هفته بالاتر رفت", " and it rose in the second half of the week"),
    "trend_down": (" و توی نیمه‌ی دوم هفته پایین‌تر اومد", " and it dipped in the second half of the week"),
    "streak": (" رشته‌ی فعالیتت الان {s} روزه.", " Your activity streak is now {s} days."),
    # went well
    "w_morning": ("صبح‌هات منظم بود: {m} روز از {days}.", "Your mornings were consistent: {m} of {days} days."),
    "w_night": ("شب‌هات منظم بود: {n} روز از {days}.", "Your evenings were consistent: {n} of {days} days."),
    "w_deeds": ("{k} روز کار خوبی نوشتی؛ این عادت به زندگی معنا می‌ده.", "On {k} days you wrote down a good deed — that habit gives life meaning."),
    "w_wins": ("{k} موفقیت تازه به لیستت اضافه کردی.", "You added {k} new achievement(s) to your list."),
    "w_lessons": ("از {k} روز سخت یه درس نوشتی؛ یعنی داری از سختی‌ها رشد می‌گیری.", "You turned {k} hard day(s) into a lesson — that's real growth."),
    "w_wishes": ("{k} آرزوت رو «محقق‌شده» علامت زدی. تبریک!", "You marked {k} wish(es) as come true. Congratulations!"),
    "w_up": ("انرژی‌ت توی نیمه‌ی دوم هفته بالاتر رفت.", "Your energy rose in the second half of the week."),
    "w_themes2": ("بیشتر از همه بابت «{a}» و «{b}» شکرگزاری کردی.", "Your gratitude kept coming back to “{a}” and “{b}”."),
    "w_themes1": ("بیشتر از همه بابت «{a}» شکرگزاری کردی.", "Your gratitude kept coming back to “{a}”."),
    "w_god": ("{k} بار با خدا صحبت کردی؛ این خلوت می‌تونه آرامش‌بخش باشه.", "You talked with God {k} times; that quiet space can be calming."),
    "w_fallback": ("اینکه این هفته هم سراغ دفترت اومدی، خودش یه پیروزیه.", "Showing up for your journal this week is a win in itself."),
    # feedback
    "f_morning": (
        "صبح‌ها کم نوشتی ({m} از {days}). شکرگزاری صبح روی کل روز اثر می‌ذاره؛ یادآور صبح رو روشن کن و فقط همون سؤال اول رو جواب بده.",
        "You wrote few mornings ({m} of {days}). Morning gratitude shapes the whole day — turn on the morning reminder and just answer the first question.",
    ),
    "f_night": (
        "شب‌ها کم نوشتی ({n} از {days}). مرور شبانه جاییه که از روز درس می‌گیری؛ حتی دو سؤالش هم ارزشمنده.",
        "You wrote few evenings ({n} of {days}). The night review is where lessons form — even two questions help.",
    ),
    "f_energy": (
        "فقط {e} روز انرژی‌ت رو ثبت کردی. بدون این داده، گزارش ماهانه‌ت خالی می‌مونه؛ ثبتش ۵ ثانیه طول می‌کشه.",
        "You logged energy on only {e} day(s). Without it the monthly report stays empty — it takes five seconds.",
    ),
    "f_generic": (
        "بیشتر موردهای شکرگزاری‌ت یک‌کلمه‌ای بود ({pct}٪)، مثل «سلامتی» یا «خانواده». یه جزئیات اضافه کن: نه «خانواده»، بلکه «تلفن سه‌شنبه‌ی مامان».",
        "Most of your gratitude items were single words ({pct}%), like “health” or “family”. Add a detail: not “family” but “Tuesday's call with Mom”.",
    ),
    "f_shallow": (
        "جواب‌هات خیلی کوتاه بود (میانگین {w} کلمه). یه جمله‌ی کامل بنویس تا بعداً که برگشتی، حال اون روز رو یادت بیاره.",
        "Your answers were very short (about {w} words). Write a full sentence so you can feel that day again when you reread it.",
    ),
    "f_repeat": (
        "«{t}» {c} بار تکرار شد. تکرار بد نیست، ولی هر روز دنبال یه چیز تازه بگرد تا ذهنت یاد بگیره خوبی‌ها رو پیدا کنه.",
        "“{t}” appeared {c} times. Repetition isn't bad, but hunting for something new each day trains your mind to spot the good.",
    ),
    "f_lesson": (
        "به سؤال «اشتباه و درس» تقریباً جواب ندادی. همین سؤال بیشترین رشد رو می‌سازه؛ اگه سخته، فقط یه جمله بنویس.",
        "You barely answered the “mistake and lesson” question — it builds the most growth. If it's hard, write just one sentence.",
    ),
    "f_upset": (
        "کلمه‌ی «{w}» {c} بار توی بخش ناراحتی‌هات اومد. شاید وقتشه یه قدم کوچیک و مشخص براش بنویسی، نه فقط اسمش رو.",
        "“{w}” showed up {c} times in what upset you. Maybe it's time to write one small, concrete step for it — not just name it.",
    ),
    "f_goals": (
        "هدف‌های صبحت کوتاه و کلی بودن. هدف خوب «فعل + مقدار» داره؛ مثل «۲۰ دقیقه پیاده‌روی».",
        "Your morning goals were short and vague. A good goal has a verb and an amount — like “walk for 20 minutes”.",
    ),
    "f_people": (
        "مدتیه ({d} روز) به {name} سر نزدی. همین امروز یه پیام کوتاه براش بفرست.",
        "It's been {d} days since you reached out to {name}. Send a short message today.",
    ),
    "f_lowtag": (
        "روزهای کم‌انرژی‌ت بیشتر با «{tag}» همراه بود. ببین چطور می‌تونی برای اون یه سپر یا برنامه بذاری.",
        "Your low-energy days often came with “{tag}”. Think about how to plan a buffer around it.",
    ),
    "f_heavy": (
        "لحن بخشی از نوشته‌هات این هفته سنگین بود. برای تعادل، هر شب یه اتفاق خوب رو با جزئیات بنویس.",
        "Part of your writing this week sounded heavy. For balance, write one good moment in detail each night.",
    ),
    "f_none": (
        "ایراد جدی ندیدم! برای رشد بیشتر، هر روز یکی از جواب‌هات رو کمی با جزئیات و مثال بنویس.",
        "I found nothing serious to fix! To grow further, write one answer a day with more detail and an example.",
    ),
    # next week
    "n_morning": ("سه روز اول هفته فقط سؤال اول صبح رو جواب بده؛ کوچیک شروع کن تا ادامه‌دار بشه.", "For the first three days, answer only the first morning question — start small so it sticks."),
    "n_detail": ("هر شب برای یکی از اتفاق‌های خوب بنویس «چرا» اتفاق افتاد.", "Each night, pick one good moment and write why it happened."),
    "n_move": ("هر روز ۱۰ دقیقه پیاده‌روی یا نور آفتاب صبح؛ خیلی‌ها می‌گن انرژی‌شون بالاتر می‌ره.", "Get 10 minutes of walking or morning daylight each day — many people find it lifts their energy."),
    "n_people": ("به {name} پیام بده و بهش بگو چرا براش شکرگزاری.", "Message {name} and tell them why you're grateful for them."),
    "n_upset": ("برای «{w}» یه قدم کوچیک بنویس و فردا انجامش بده.", "Write one small step for “{w}” and do it tomorrow."),
    "n_log": ("هر روز یه ساعت ثابت انرژی‌ت رو ثبت کن تا عادت بشه.", "Log your energy at the same time each day until it becomes a habit."),
    "n_empty": ("فقط امروز یه سؤال رو جواب بده؛ همین برای شروع کافیه.", "Just answer one question today — that's enough to restart."),
    "closing": (
        "دفتر شکرگزاری فقط ثبت کردن نیست؛ تمرین دیدنِ خوبی‌هاست. هفته‌ی خوبی داشته باشی.",
        "A gratitude journal isn't just record-keeping — it's practice in noticing the good. Have a great week.",
    ),
    "safety": (
        "توی نوشته‌هات کلمه‌هایی دیدم که نشون می‌ده شاید روزهای خیلی سنگینی داری. اگه احساس ناامنی می‌کنی یا به آسیب زدن به خودت فکر می‌کنی، لطفاً همین الان با یه نفر مورد اعتمادت صحبت کن یا با اورژانس یا مرکز مشاوره‌ی شهرت تماس بگیر. تو لایق حمایتی.",
        "I noticed words in your notes that suggest you may be going through something very heavy. If you ever feel unsafe or think about hurting yourself, please talk to someone you trust or contact your local emergency or crisis service right now. You deserve support.",
    ),
    "lowstreak": (
        "چند روزه انرژی‌ت پایینه. اگه این حال ادامه داشت، صحبت با یه دوست مطمئن یا یه مشاور می‌تونه کمک کنه.",
        "Your energy has been low for several days. If this continues, talking to a trusted friend or a counselor can help.",
    ),
    # monthly
    "m_glance": (
        "این ماه {k} روز انرژی‌ت رو ثبت کردی. میانگین {avg} از ۱۰؛ بهترین روز {best_day} ({best}) و کم‌انرژی‌ترین {worst_day} ({worst}). {cmp}",
        "This month you logged energy on {k} days. Average {avg}/10; best day {best_day} ({best}), lowest {worst_day} ({worst}). {cmp}",
    ),
    "m_empty": ("این ماه هنوز انرژی‌ت رو ثبت نکردی. با ثبت روزانه، الگوهای انرژی‌ت اینجا نشون داده می‌شه.", "You haven't logged energy this month yet. Daily logs let your energy patterns show up here."),
    "cmp_up": ("نسبت به ماه قبل {x} امتیاز بالاتر.", "That's {x} points higher than last month."),
    "cmp_down": ("نسبت به ماه قبل {x} امتیاز پایین‌تر.", "That's {x} points lower than last month."),
    "cmp_same": ("تقریباً هم‌سطح ماه قبل.", "About the same as last month."),
    "p_dip": ("پایین‌ترین میانگین انرژی‌ت روزهای {wd} بود ({v}).", "Your lowest average energy fell on {wd}s ({v})."),
    "p_peak": ("بهترین روز هفته‌ت {wd} بود ({v}).", "Your best weekday was {wd} ({v})."),
    "p_tag_up": ("روزهایی که «{tag}» رو علامت زدی، انرژی‌ت به‌طور میانگین {x} امتیاز بیشتر بود.", "On days you tagged “{tag}”, your energy was {x} points higher on average."),
    "p_tag_down": ("روزهایی که «{tag}» رو علامت زدی، انرژی‌ت حدود {x} امتیاز کمتر بود.", "On days you tagged “{tag}”, your energy was about {x} points lower."),
    "p_morning": ("روزهایی که شکرگزاری صبح نوشتی، انرژی‌ت {x} امتیاز بیشتر بود.", "On days you wrote morning gratitude, your energy was {x} points higher."),
    "p_prevnight": ("بعد از شب‌هایی که مرور شبانه نوشتی، انرژی‌ت روز بعد {x} امتیاز بیشتر بود.", "After nights you wrote a review, your energy the next day was {x} points higher."),
    "p_deed": ("روزهایی که کار خوبی نوشتی، انرژی‌ت {x} امتیاز بیشتر بود.", "On days you wrote a good deed, your energy was {x} points higher."),
    "p_hard": ("{k} روز سخت داشتی و برای {l} تاش درس نوشتی.", "You had {k} hard day(s) and wrote a lesson for {l} of them."),
    "p_note": ("اینا الگو هستن، نه اثبات؛ خودت بهتر از هر کسی می‌دونی چی درسته.", "These are patterns, not proof — you know your life best."),
    "p_none": ("هنوز داده‌ی کافی برای الگوی مشخص ندارم؛ چند روز دیگه ثبت کنی دقیق‌تر می‌شه.", "Not enough data for clear patterns yet — a few more logged days will sharpen them."),
}

TIPS = {
    "light": ("۱۰ دقیقه‌ی اول روز بیرون برو یا کنار پنجره آفتاب بگیر؛ نور صبح به ساعت بدنت کمک می‌کنه.", "Get 10 minutes of daylight early in the day (outside or by a window) — it helps anchor your body clock."),
    "walk": ("روزی ۱۰ تا ۲۰ دقیقه پیاده‌روی سبک؛ لازم نیست ورزش سنگین باشه.", "Take a gentle 10–20 minute walk daily — it doesn't need to be a workout."),
    "sleep": ("ساعت خواب و بیداری‌ت رو تا حد ممکن ثابت نگه دار؛ ثبات اغلب از طول خواب هم مهم‌تره.", "Keep your sleep and wake times as steady as you can — consistency often matters as much as length."),
    "water": ("آب کافی بخور و یه میان‌وعده‌ی سالم دم‌دست داشته باش؛ کم‌آبی و افت قند انرژی رو می‌خوابونه.", "Drink enough water and keep a healthy snack handy — dehydration and sugar dips drain energy."),
    "breath": ("وقتی خسته یا تحت فشاری، ۳ دقیقه تنفس آرام: ۴ ثانیه دم، ۶ ثانیه بازدم.", "When drained or tense, try 3 minutes of slow breathing: in for 4, out for 6."),
    "connect": ("روزی یه تماس یا پیام کوتاه با کسی که دوستش داری؛ ارتباط واقعی خیلی‌ها رو شارژ می‌کنه.", "Send one short message or call to someone you care about each day — real connection recharges many people."),
    "small_win": ("هر روز یه کار کوچیک و شدنی رو تموم کن و تیکش بزن؛ حس پیشرفت، انگیزه می‌سازه.", "Finish one small, doable task a day and check it off — a sense of progress builds motivation."),
    "rest": ("وسط روز ۱۰ دقیقه استراحت واقعی بذار (بدون گوشی)؛ استراحت برنامه‌ریزی‌شده جلوی افت ناگهانی رو می‌گیره.", "Schedule a real 10-minute break mid-day (phone away) — planned rest prevents sudden crashes."),
    "screens": ("یه ساعت قبل از خواب صفحه‌ها رو کنار بذار تا خوابت عمیق‌تر بشه.", "Put screens away an hour before bed to help deeper sleep."),
    "pray": ("چند دقیقه دعا، مراقبه یا سکوت قبل از شروع روز؛ خیلی‌ها می‌گن ذهنشون آروم‌تر می‌شه.", "Take a few minutes of prayer, meditation or silence before the day starts — many find it settles the mind."),
    "reread": ("روزهای کم‌انرژی، بخش «روزهای سخت» رو بخون و یادت بیار قبلاً چطور رد شدی.", "On low days, reread your “Hard days” lessons and remember how you got through before."),
    "talk": ("اگه چند روزه انرژی‌ت پایینه، با یه دوست مطمئن یا یه مشاور حرف بزن؛ لازم نیست تنها بکشی.", "If your energy has been low for days, talk to a trusted friend or a counselor — you don't have to carry it alone."),
    "protect_peak": ("بهترین ساعت‌های روزت رو برای مهم‌ترین کارت نگه دار و کارهای کم‌اهمیت رو بذار برای ساعت‌های افت.", "Protect your best hours for your most important work and leave low-stakes tasks for your dips."),
    "keep_routine": ("برنامه‌ی فعلی‌ت جواب می‌ده؛ عوضش نکن و هر هفته فقط یه بهبود کوچیک اضافه کن.", "Your current routine is working — keep it and add just one small improvement a week."),
    "share": ("شکرگزاری‌ت رو با یه نفر شریک شو؛ هم حال اون خوب می‌شه هم حال خودت.", "Share your gratitude with someone — it lifts both of you."),
    "log": ("هر روز انرژی‌ت رو ثبت کن؛ با داده‌ی بیشتر می‌تونم الگوهای دقیق‌تری نشونت بدم.", "Log your energy every day — more data means sharper patterns."),
    "steady": ("نوسان انرژی‌ت زیاده؛ ساعت غذا، خواب و استراحت رو منظم‌تر کن تا روزهات یکنواخت‌تر بشن.", "Your energy swings a lot; steadier meal, sleep and rest times can smooth your days."),
    "buffer": ("روزهای {wd} برنامه‌ی سبک‌تری بذار یا یه کار دلخواه رو بذار اون روز.", "Plan a lighter load on {wd}s, or put something you enjoy on that day."),
    "tag_up": ("«{tag}» به انرژی‌ت کمک می‌کنه؛ برای هفته‌ی بعد حداقل دو بار توی برنامه‌ت بذارش.", "“{tag}” seems to help your energy — schedule it at least twice next week."),
    "tag_down": ("«{tag}» انرژی‌ت رو پایین می‌بره؛ ببین قبل و بعدش چی رو می‌تونی عوض کنی (مثلاً استراحت یا زمان‌بندی).", "“{tag}” seems to drain your energy — look at what you can change before and after it (rest, timing)."),
}

N_POOL = (
    ("قبل از خواب ۳ دقیقه فقط به خوبی‌های امروز فکر کن.", "Spend 3 minutes before bed thinking only about today's good things."),
    ("یه نفر رو با یه قدردانی کوتاه غافلگیر کن.", "Surprise someone with a short note of appreciation."),
    ("یه ساعت اول صبح گوشی رو کنار بذار.", "Keep your phone away for the first hour after waking."),
    ("هر روز یه کار کوچیک مهربونانه برای خودت انجام بده.", "Do one small kind thing for yourself each day."),
)


# --------------------------------------------------------------------------- helpers
def heading(key: str, lang: str) -> str:
    pair = HEADINGS[key]
    return pair[0] if lang == "fa" else pair[1]


def _f(key: str, lang: str, **kw) -> str:
    pair = X.get(key) or TIPS.get(key) or (key, key)
    return (pair[0] if lang == "fa" else pair[1]).format(**kw)


def _num(x: float, lang: str) -> str:
    s = f"{x:.1f}".rstrip("0").rstrip(".")
    s = util.digits(s, lang)
    return s.replace(".", "٫") if lang == "fa" else s


def _day(d: date, lang: str, jal: bool) -> str:
    return f"{jalali.weekday_name(d, lang)} {jalali.format_day(d, lang, jal, 'dm')}"


def _tag(tag: str, lang: str) -> str:
    return content.label(content.TAGS, tag, lang)


def _wd(i: int, lang: str) -> str:
    return jalali.WEEKDAYS["fa" if lang == "fa" else "en"][i]


# --------------------------------------------------------------------------- titles
def weekly_title(start: date, end: date, lang: str, jal: bool) -> str:
    a, b = jalali.format_day(start, lang, jal, "dm"), jalali.format_day(end, lang, jal, "dm")
    return f"گزارش هفته: {a} تا {b}" if lang == "fa" else f"Weekly report: {a} – {b}"


def monthly_title(start: date, lang: str, jal: bool) -> str:
    label = jalali.month_label(start, lang, jal)
    return f"مرور ماه {label}" if lang == "fa" else f"Monthly review · {label}"


# --------------------------------------------------------------------------- weekly
def weekly_report(d: dict, lang: str, name: str = "", jal: bool = True, seed: str = "") -> dict:
    lang = "fa" if lang == "fa" else "en"
    rnd = random.Random(seed or d["start"].isoformat())
    n = lambda v: util.digits(v, lang)
    days, m, nt = d["days"], d["morning_days"], d["night_days"]
    title = weekly_title(d["start"], d["end"], lang, jal)
    sections: list[dict] = []
    nothing = m == 0 and nt == 0 and d["energy_days"] == 0

    # --- glance
    streak = _f("streak", lang, s=n(d["streak"])) if d["streak"] >= 3 else ""
    if nothing:
        glance = _f("glance_empty", lang)
    elif d["avg"] is not None:
        trend = ""
        if d["delta"] is not None and d["delta"] >= 0.7:
            trend = _f("trend_up", lang)
        elif d["delta"] is not None and d["delta"] <= -0.7:
            trend = _f("trend_down", lang)
        (bd, bs), (wd_, ws) = d["best"], d["worst"]
        glance = _f("glance_e", lang, m=n(m), n=n(nt), days=n(days), avg=_num(d["avg"], lang), trend=trend,
                    best_day=_day(bd, lang, jal), best=n(bs), worst_day=_day(wd_, lang, jal), worst=n(ws), streak=streak)
    else:
        glance = _f("glance_n", lang, m=n(m), n=n(nt), days=n(days), streak=streak)
    sections.append({"h": heading("glance", lang), "text": glance.strip()})

    if not nothing:
        # --- went well
        well: list[str] = []
        if m >= 5: well.append(_f("w_morning", lang, m=n(m), days=n(days)))
        if nt >= 5: well.append(_f("w_night", lang, n=n(nt), days=n(days)))
        if d["deed_days"] >= 3: well.append(_f("w_deeds", lang, k=n(d["deed_days"])))
        if d["lessons"]: well.append(_f("w_lessons", lang, k=n(d["lessons"])))
        if d["wishes_done"]: well.append(_f("w_wishes", lang, k=n(d["wishes_done"])))
        if d["wins_added"]: well.append(_f("w_wins", lang, k=n(d["wins_added"])))
        if d["delta"] is not None and d["delta"] >= 0.7: well.append(_f("w_up", lang))
        th = [w for w, _ in d["themes"]]
        if len(th) >= 2: well.append(_f("w_themes2", lang, a=th[0], b=th[1]))
        elif th: well.append(_f("w_themes1", lang, a=th[0]))
        if d["god_talks"] >= 2: well.append(_f("w_god", lang, k=n(d["god_talks"])))
        sections.append({"h": heading("well", lang), "items": (well[:4] or [_f("w_fallback", lang)])})

        # --- honest feedback
        fb: list[str] = []
        if days >= 5 and m <= 2: fb.append(_f("f_morning", lang, m=n(m), days=n(days)))
        if days >= 5 and nt <= 2: fb.append(_f("f_night", lang, n=n(nt), days=n(days)))
        if days >= 5 and d["energy_days"] <= 2: fb.append(_f("f_energy", lang, e=n(d["energy_days"])))
        if d["list_items"] >= 6 and d["generic_ratio"] >= 0.5:
            fb.append(_f("f_generic", lang, pct=n(round(d["generic_ratio"] * 100))))
        if len(d["texts"]) >= 6 and d["avg_words"] < 3:
            fb.append(_f("f_shallow", lang, w=_num(d["avg_words"], lang)))
        if d["repeats"]:
            t, c = d["repeats"][0]
            fb.append(_f("f_repeat", lang, t=t, c=n(c)))
        if nt >= 3 and d["answered"].get("n5", 0) <= 1: fb.append(_f("f_lesson", lang))
        if d["upset_themes"]:
            w, c = d["upset_themes"][0]
            fb.append(_f("f_upset", lang, w=w, c=n(c)))
        if d["goal_words"] is not None and d["goal_words"] <= 2: fb.append(_f("f_goals", lang))
        if d["neglected"]:
            nm, gap = d["neglected"][0]
            fb.append(_f("f_people", lang, d=n(gap), name=nm))
        if d["low_tags"] and d["low_tags"][0][1] >= 2:
            fb.append(_f("f_lowtag", lang, tag=_tag(d["low_tags"][0][0], lang)))
        if d["negative_hits"] >= 6: fb.append(_f("f_heavy", lang))
        sections.append({"h": heading("feedback", lang), "items": (fb[:4] or [_f("f_none", lang)])})

    # --- next week
    nx: list[str] = []
    if nothing: nx.append(_f("n_empty", lang))
    if not nothing and m <= 2: nx.append(_f("n_morning", lang))
    if d["neglected"]: nx.append(_f("n_people", lang, name=d["neglected"][0][0]))
    if d["upset_themes"]: nx.append(_f("n_upset", lang, w=d["upset_themes"][0][0]))
    if d["generic_ratio"] >= 0.5: nx.append(_f("n_detail", lang))
    if d["avg"] is not None and d["avg"] < 5.5: nx.append(_f("n_move", lang))
    if d["energy_days"] <= 2 and not nothing: nx.append(_f("n_log", lang))
    pool = list(N_POOL)
    rnd.shuffle(pool)
    for fa, en in pool:
        if len(nx) >= 3:
            break
        nx.append(fa if lang == "fa" else en)
    sections.append({"h": heading("next", lang), "items": nx[:3]})

    # --- closing / safety
    if d.get("safety"):
        sections.append({"h": heading("note", lang), "text": _f("safety", lang)})
    closing = _f("closing", lang)
    if name:
        closing = f"{name}، {closing}" if lang == "fa" else f"{name}, {closing[0].lower()}{closing[1:]}"
    sections.append({"text": closing})
    return {"title": title, "sections": sections, "source": "offline"}


# --------------------------------------------------------------------------- monthly
def monthly_tips(ms: dict, lang: str, jal: bool = True) -> list[str]:
    lang = "fa" if lang == "fa" else "en"
    s = ms["summary"]
    avg = s["avg"]
    out: list[str] = []
    if ms.get("low_streak") or (avg is not None and avg < 4.5):
        out.append(_f("talk", lang))
    if s["logged"] < 10:
        out.append(_f("log", lang))
    if avg is not None:
        if avg < 5:
            out += [_f(k, lang) for k in ("sleep", "light", "walk", "rest")]
        elif avg < 7:
            out += [_f(k, lang) for k in ("protect_peak", "small_win", "breath")]
        else:
            out += [_f(k, lang) for k in ("keep_routine", "share")]
        wp = ms["weekday"]
        if len(wp) >= 3:
            low_wd = min(wp, key=wp.get)
            if avg - wp[low_wd] >= 1.2:
                out.append(_f("buffer", lang, wd=_wd(low_wd, lang)))
    for t in ms["tags"][:2]:
        out.append(_f("tag_up" if t["delta"] > 0 else "tag_down", lang, tag=_tag(t["tag"], lang)))
    if s.get("stdev", 0) >= 2.2:
        out.append(_f("steady", lang))
    if ms["hard_days"]:
        out.append(_f("reread", lang))
    if not out:
        out = [_f("connect", lang), _f("small_win", lang), _f("light", lang)]
    seen, uniq = set(), []
    for t in out:
        if t not in seen:
            seen.add(t)
            uniq.append(t)
    return uniq[:6]


def monthly_review(ms: dict, lang: str, name: str = "", jal: bool = True) -> dict:
    lang = "fa" if lang == "fa" else "en"
    n = lambda v: util.digits(v, lang)
    s = ms["summary"]
    title = monthly_title(ms["start"], lang, jal)
    sections: list[dict] = []
    if s["avg"] is None:
        sections.append({"h": heading("glance", lang), "text": _f("m_empty", lang)})
    else:
        cmp_ = ""
        if ms.get("prev_avg") is not None:
            diff = round(s["avg"] - ms["prev_avg"], 1)
            cmp_ = _f("cmp_up" if diff >= 0.5 else "cmp_down" if diff <= -0.5 else "cmp_same", lang, x=_num(abs(diff), lang))
        (bd, bs), (wd_, ws) = s["best"], s["worst"]
        sections.append({"h": heading("glance", lang), "text": _f(
            "m_glance", lang, k=n(s["logged"]), avg=_num(s["avg"], lang), best_day=_day(bd, lang, jal), best=n(bs),
            worst_day=_day(wd_, lang, jal), worst=n(ws), cmp=cmp_).strip()})
    pats: list[str] = []
    wp = ms["weekday"]
    if len(wp) >= 3:
        lo, hi = min(wp, key=wp.get), max(wp, key=wp.get)
        if wp[hi] - wp[lo] >= 1.0:
            pats.append(_f("p_peak", lang, wd=_wd(hi, lang), v=_num(wp[hi], lang)))
            pats.append(_f("p_dip", lang, wd=_wd(lo, lang), v=_num(wp[lo], lang)))
    for t in ms["tags"][:2]:
        pats.append(_f("p_tag_up" if t["delta"] > 0 else "p_tag_down", lang, tag=_tag(t["tag"], lang), x=_num(abs(t["delta"]), lang)))
    for e in ms["effects"]:
        if e["delta"] > 0:
            pats.append(_f({"morning": "p_morning", "prev_night": "p_prevnight", "deed": "p_deed"}[e["key"]], lang, x=_num(e["delta"], lang)))
    if ms["hard_days"]:
        pats.append(_f("p_hard", lang, k=n(ms["hard_days"]), l=n(ms["lessons"])))
    pats.append(_f("p_note", lang) if len(pats) > 0 else _f("p_none", lang))
    sections.append({"h": heading("patterns", lang), "items": pats})
    sections.append({"h": heading("tips", lang), "items": monthly_tips(ms, lang, jal)})
    if ms.get("safety"):
        sections.append({"h": heading("note", lang), "text": _f("safety", lang)})
    elif ms.get("low_streak"):
        sections.append({"h": heading("note", lang), "text": _f("lowstreak", lang)})
    return {"title": title, "sections": sections, "source": "offline"}
