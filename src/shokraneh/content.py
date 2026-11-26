"""Static content: questionnaires, tags, affirmations, prompts (no Flet imports)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Question:
    id: str
    kind: str  # "list" (several short lines) | "text" (free text) | "feeling" (chips + text)
    count: int  # number of lines when kind == "list"
    fa: str
    en: str
    hint_fa: str
    hint_en: str
    icon: str  # semantic icon key; the UI maps it to a real icon

    def title(self, lang: str) -> str:
        return self.fa if lang == "fa" else self.en

    def hint(self, lang: str) -> str:
        return self.hint_fa if lang == "fa" else self.hint_en


def _q(id, kind, count, fa, en, hint_fa, hint_en, icon):
    return Question(id, kind, count, fa, en, hint_fa, hint_en, icon)


MORNING = (
    _q("m1", "list", 5, "امروز بابت چه ۵ نعمتی شکرگزارم؟", "What 5 blessings am I grateful for today?",
       "از چیزهای کوچیک شروع کن: یه چای گرم، یه پیام مهربون، سلامتی…",
       "Start small: a warm tea, a kind message, your health…", "heart"),
    _q("m2", "list", 3, "امروز بابت چه ۳ ویژگی خودم شکرگزارم؟", "What 3 qualities of mine am I grateful for today?",
       "چیزی که توی خودت دوست داری؛ مثلاً صبوری، شوخ‌طبعی، پشتکار.",
       "Something you like in yourself — patience, humor, persistence.", "star"),
    _q("m3", "list", 3, "امروز چه ۳ اتفاق خوبی می‌تونه برام بیفته؟", "What 3 good things could happen to me today?",
       "تصور کن امروز خوب پیش میره؛ چه اتفاق‌هایی می‌افته؟",
       "Imagine today going well — what could happen?", "sparkle"),
    _q("m4", "feeling", 0, "امروز می‌خوام چه احساسی داشته باشم؟", "How do I want to feel today?",
       "یه حس رو انتخاب کن یا با کلمه‌های خودت بنویس.",
       "Pick a feeling or write it in your own words.", "mood"),
    _q("m5", "list", 3, "۳ هدف مهم امروز من چیه؟", "What are my 3 most important goals today?",
       "ساده و قابل انجام؛ مثلاً «۲۰ دقیقه مطالعه».",
       "Simple and doable — e.g. “read for 20 minutes”.", "flag"),
    _q("m6", "text", 0, "امروز چه کار خوبی برای دیگران انجام می‌دم؟", "What good deed will I do for others today?",
       "کوچیک هم عالیه: یه تماس، یه کمک، یه لبخند.",
       "Small counts: a call, a favor, a smile.", "hands"),
    _q("m7", "text", 0, "جمله انگیزشی و مثبت امروز من چیه؟", "What is my positive, motivating sentence for today?",
       "جمله‌ای که امروز بهت انرژی بده.",
       "A sentence that will carry you through today.", "quote"),
)

NIGHT = (
    _q("n1", "list", 5, "امروز چه ۵ اتفاق خوبی برام افتاد؟", "What 5 good things happened to me today?",
       "حتی ساده‌ترین لحظه‌ها حساب میشن.", "Even the simplest moments count.", "party"),
    _q("n2", "text", 0, "امروز چه کسی باعث خوشحالی من شد؟", "Who made me happy today?",
       "یه نفر، یه خاطره یا یه پیام.", "A person, a memory or a message.", "person"),
    _q("n3", "text", 0, "امروز به چه چیزی در خودم افتخار می‌کنم؟", "What am I proud of in myself today?",
       "یه تلاش، یه رفتار یا یه تصمیم.", "An effort, a behavior or a decision.", "trophy"),
    _q("n4", "text", 0, "امروز چه چیز جدیدی یاد گرفتم؟", "What new thing did I learn today?",
       "می‌تونه یه واژه، یه مهارت یا یه نکته درباره‌ی خودت باشه.",
       "A word, a skill, or something about yourself.", "bulb"),
    _q("n5", "text", 0, "امروز چه اشتباهی کردم و ازش چی یاد گرفتم؟", "What mistake did I make today, and what did I learn from it?",
       "بدون سرزنش؛ فقط ببین دفعه‌ی بعد چی رو متفاوت انجام می‌دی.",
       "No blame — just notice what you'd do differently next time.", "growth"),
    _q("n6", "text", 0, "امروز چه کار خوبی برای خودم یا دیگران انجام دادم؟", "What good thing did I do for myself or others today?",
       "کار کوچیک هم حساب میشه.", "Small things count too.", "gift"),
    _q("n7", "text", 0, "امروز چه چیزی ناراحتم کرد و چطور می‌تونم باهاش کنار بیام؟", "What upset me today, and how can I cope with it?",
       "اسمش رو بذار، بعد یه راه کوچیک برای کنار اومدن بنویس.",
       "Name it, then write one small way to cope.", "cloud"),
    _q("n8", "text", 0, "فردا دوست دارم چه چیزی رو بهتر انجام بدم؟", "What would I like to do better tomorrow?",
       "یه قدم مشخص و کوچیک.", "One clear, small step.", "sunrise"),
    _q("n9", "text", 0, "امشب بابت چی از خدا تشکر می‌کنم؟", "What am I thanking God for tonight?",
       "با کلمه‌های خودت بگو.", "Say it in your own words.", "pray"),
)

QUESTIONS = {"morning": MORNING, "night": NIGHT}


def question_by_id(qid: str) -> Question | None:
    for q in MORNING + NIGHT:
        if q.id == qid:
            return q
    return None


# id -> (fa, en)
FEELINGS = {
    "calm": ("آرام", "Calm"),
    "joyful": ("شاد", "Joyful"),
    "confident": ("مطمئن", "Confident"),
    "grateful": ("سپاسگزار", "Grateful"),
    "energetic": ("پرانرژی", "Energetic"),
    "loved": ("دوست‌داشته‌شده", "Loved"),
    "hopeful": ("امیدوار", "Hopeful"),
    "focused": ("متمرکز", "Focused"),
    "peaceful": ("آسوده", "At peace"),
    "brave": ("شجاع", "Brave"),
}

# What shaped today's energy (used for the correlation insights).
TAGS = {
    "sleep": ("خواب", "Sleep"),
    "food": ("تغذیه", "Food"),
    "movement": ("حرکت و ورزش", "Movement"),
    "nature": ("طبیعت", "Nature"),
    "social": ("معاشرت", "Social time"),
    "family": ("خانواده", "Family"),
    "work": ("کار و درس", "Work/Study"),
    "rest": ("استراحت", "Rest"),
    "spiritual": ("معنویت", "Spiritual"),
    "stress": ("استرس", "Stress"),
}

RELATIONS = {
    "family": ("خانواده", "Family"),
    "partner": ("شریک زندگی", "Partner"),
    "friend": ("دوست", "Friend"),
    "mentor": ("استاد/راهنما", "Mentor"),
    "colleague": ("همکار", "Colleague"),
    "other": ("دیگر", "Other"),
}

WIN_CATEGORIES = {
    "personal": ("شخصی", "Personal"),
    "work": ("کار و تحصیل", "Work/Study"),
    "health": ("سلامت", "Health"),
    "relationships": ("روابط", "Relationships"),
    "spiritual": ("معنوی", "Spiritual"),
    "other": ("دیگر", "Other"),
}

# Conversation openers for the "Talking with God" space: (fa, en)
GOD_STARTERS = (
    ("خدایا، ممنونم بابت…", "God, thank You for…"),
    ("خدایا، امروز دلم می‌خواد بهت بگم…", "God, today I want to tell You…"),
    ("خدایا، کمکم کن…", "God, please help me…"),
    ("خدایا، نگرانم از…", "God, I'm worried about…"),
    ("خدایا، ازت می‌خوام…", "God, I ask You for…"),
    ("خدایا، منو ببخش بابت…", "God, forgive me for…"),
)

# (days, fa, en) presets for "letter to my future self"
LETTER_PRESETS = (
    (7, "یک هفته دیگه", "In a week"),
    (30, "یک ماه دیگه", "In a month"),
    (90, "سه ماه دیگه", "In 3 months"),
    (182, "شش ماه دیگه", "In 6 months"),
    (365, "یک سال دیگه", "In a year"),
)

LETTER_PROMPTS = (
    ("الان چه حالی دارم و چی توی ذهنمه؟", "How am I feeling right now, and what's on my mind?"),
    ("برای چی شکرگزارم؟", "What am I grateful for?"),
    ("چه رویاهایی دارم و امیدوارم تا اون موقع چی شده باشه؟", "What do I dream of, and what do I hope has happened by then?"),
    ("چه توصیه‌ای به خودِ آینده‌م دارم؟", "What advice do I have for my future self?"),
)

AFFIRMATIONS = {
    "fa": (
        "همین امروز، همین‌طور که هستم، برای شروع کافیه.",
        "من لایق آرامش و شادی‌ام.",
        "هر قدم کوچیک، بازم یه قدمه.",
        "یه نفس عمیق می‌کشم و به لحظه‌ی حال برمی‌گردم.",
        "بابت چیزهایی که دارم شکرگزارم و برای چیزهایی که می‌خوام تلاش می‌کنم.",
        "از روزهای سخت قبلی رد شدم؛ بازم می‌تونم.",
        "امروز یه کار کوچیک و مهربونانه انجام می‌دم.",
        "لازم نیست بی‌نقص باشم؛ صادق و پیگیر بودن کافیه.",
        "حواسم رو به خوبی‌هایی می‌دم که امروز دست خودمه.",
        "اجازه دارم استراحت کنم و دوباره شروع کنم.",
        "امروز با خودم مهربونم.",
        "خوبی‌ها رو می‌بینم، حتی وقتی کوچیکن.",
        "اون چیزی که مال منه به موقعش میاد؛ من سهم امروزم رو انجام می‌دم.",
        "می‌تونم از اشتباهم درس بگیرم و ادامه بدم.",
        "امروز به کسی که دوستش دارم محبتم رو نشون می‌دم.",
        "آرامش یه انتخاب کوچیکه که همین الان می‌تونم بکنم.",
        "هر کاری از دستم برمیومد کردم؛ بقیه‌ش رو به خدا می‌سپارم.",
        "دلم پر از قدردانیه.",
        "هر روز یه فرصت تازه‌ست.",
        "می‌تونم برای احساساتم جا باز کنم، بدون اینکه ازشون بترسم.",
        "با صبر و ثبات به جایی که می‌خوام می‌رسم.",
        "امروز یه چیز تازه یاد می‌گیرم.",
        "کنارم آدم‌هایی هستن که دوستم دارن.",
        "شکرگزاری چشمم رو به خوبی‌ها باز می‌کنه.",
    ),
    "en": (
        "Today, exactly as I am, is enough to begin.",
        "I deserve peace and joy.",
        "Every small step is still a step.",
        "I breathe deeply and come back to the present moment.",
        "I'm grateful for what I have, and I work toward what I want.",
        "I've come through hard days before, and I can again.",
        "Today I will do one small, kind thing.",
        "I don't need to be perfect — honest and consistent is enough.",
        "I give my attention to the good things I can influence today.",
        "I'm allowed to rest and begin again.",
        "Today I'm gentle with myself.",
        "I notice the good, even when it's small.",
        "What is meant for me will find me; I'll do my part today.",
        "I can learn from my mistakes and keep going.",
        "Today I'll show love to someone who matters to me.",
        "Calm is a small choice I can make right now.",
        "I've done what I could; the rest I entrust to God.",
        "My heart is full of gratitude.",
        "Every day is a fresh chance.",
        "I can make room for my feelings without being afraid of them.",
        "With patience and consistency I get where I want to be.",
        "Today I'll learn something new.",
        "I'm surrounded by people who care about me.",
        "Gratitude opens my eyes to the good.",
    ),
}


def day_affirmation(day: date, lang: str) -> str:
    items = AFFIRMATIONS["fa" if lang == "fa" else "en"]
    return items[day.toordinal() % len(items)]


def label(table: dict, key: str, lang: str) -> str:
    """Localized label for a key of FEELINGS / TAGS / RELATIONS / WIN_CATEGORIES."""
    pair = table.get(key)
    if not pair:
        return key
    return pair[0] if lang == "fa" else pair[1]
