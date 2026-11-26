"""UI strings. Every key maps to (Persian, English). Use t("key", lang, name="…") for {placeholders}."""
from __future__ import annotations

LANGUAGES = {"fa": "فارسی", "en": "English"}
RTL_LANGS = {"fa"}

# key: (fa, en)
STRINGS: dict[str, tuple[str, str]] = {
    # ---- general
    "app_name": ("شکرانه", "Shokraneh"),
    "app_tagline": ("دفتر شکرگزاری و آرامش تو", "Your journal of gratitude and calm"),
    "toast_new_report": ("پیام تازه‌ای برات آماده شد ✨", "A new message is ready for you ✨"),
    "back": ("بازگشت", "Back"),
    "close": ("بستن", "Close"),
    "delete": ("حذف", "Delete"),
    "edit": ("ویرایش", "Edit"),
    "add": ("افزودن", "Add"),
    "ok": ("باشه", "OK"),
    "no": ("نه", "No"),
    "error_generic": ("مشکلی پیش اومد. دوباره امتحان کن.", "Something went wrong. Please try again."),
    "err_empty": ("اول یه چیزی بنویس.", "Write something first."),
    "creator_by": ("ساخته‌شده توسط {name}", "Made by {name}"),
    "copyright_line": ("© {y} {name} — تمامی حقوق محفوظ است.", "© {y} {name}. All rights reserved."),
    "saved": ("ذخیره شد ✓", "Saved ✓"),
    "deleted": ("حذف شد", "Deleted"),
    "confirm_delete_title": ("حذف بشه؟", "Delete this?"),
    "confirm_delete_body": ("این کار قابل برگشت نیست.", "This can't be undone."),
    # ---- notifications / reminders
    "notif_morning_title": ("صبح بخیر ☀️", "Good morning ☀️"),
    "notif_morning_body": ("یه لحظه برای شکرگزاری صبحگاهی وقت بذار.", "Take a moment for your morning gratitude."),
    "notif_night_title": ("شب بخیر 🌙", "Good evening 🌙"),
    "notif_night_body": ("وقتشه امروز رو مرور کنی و شکرگزاری شبانه‌ت رو بنویسی.", "Time to look back on today and write your evening gratitude."),
    "notif_letter_title": ("نامه‌ای از خودت رسید ✉️", "A letter from your past self ✉️"),
    "notif_letter_body": ("نامه‌ای که برای امروز نوشته بودی آماده‌ی خوندنه.", "The letter you wrote for today is ready to open."),
    "notif_test_title": ("آزمایش اعلان", "Notification test"),
    "notif_test_body": ("اگه این پیام رو می‌بینی، اعلان‌ها کار می‌کنن 🌿", "If you can read this, notifications work 🌿"),
}


def register(table: dict[str, tuple[str, str]]) -> None:
    """Screens add their own strings next to their code; a key may not be redefined with different text."""
    for key, pair in table.items():
        if key in STRINGS and STRINGS[key] != pair:
            raise KeyError(f"i18n key defined twice with different text: {key}")
        STRINGS[key] = pair


def register(more: dict[str, tuple[str, str]]) -> None:
    """Screens register their own strings next to their code; a clash with different text is a bug."""
    for key, pair in more.items():
        old = STRINGS.get(key)
        if old is not None and old != pair:
            raise ValueError(f"i18n key {key!r} registered twice with different text")
        STRINGS[key] = pair


def t(key: str, lang: str = "fa", **kw) -> str:
    pair = STRINGS.get(key)
    if pair is None:
        return key  # visible in the UI during development; guarded by tests
    text = pair[0] if lang == "fa" else pair[1]
    if kw:
        try:
            return text.format(**kw)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def is_rtl(lang: str) -> bool:
    return lang in RTL_LANGS
