"""Settings hub and its sections: appearance, reminders, AI reports, security, backup & data, about."""
from __future__ import annotations

import json
from datetime import date
from typing import Any, Callable

from ... import __version__, ai, config, jalali, notify, util
from ... import store as store_mod
from ...i18n import register
from .. import compat as C
from .. import files, kit, theme

register({
    # ---- hub
    "set_profile_hint": ("پروفایل فعلی", "Current profile"),
    "set_edit_profile": ("ویرایش پروفایل", "Edit profile"),
    "set_lock_now": ("قفل کن", "Lock now"),
    "set_look": ("ظاهر و زبان", "Appearance & language"),
    "set_reminders": ("یادآورها", "Reminders"),
    "set_ai": ("هوش مصنوعی", "AI reports"),
    "set_security": ("امنیت و رمز", "Security & PIN"),
    "set_data": ("پشتیبان‌گیری و داده‌ها", "Backup & data"),
    "set_about": ("درباره و حریم خصوصی", "About & privacy"),
    "set_off": ("خاموش", "Off"),
    "set_on": ("روشن", "On"),
    "set_sum_m": ("صبح {t}", "Morning {t}"),
    "set_sum_n": ("شب {t}", "Evening {t}"),
    "set_version": ("نسخه {v}", "Version {v}"),
    # ---- look
    "set_language": ("زبان", "Language"),
    "set_cal_jalali": ("شمسی", "Jalali"),
    "set_cal_greg": ("میلادی", "Gregorian"),
    "set_auto": ("خودکار", "Auto"),
    "set_week_start": ("شروع هفته", "Week starts on"),
    "set_theme": ("حالت نمایش", "Theme"),
    "set_theme_system": ("مثل سیستم", "System"),
    "set_theme_light": ("روشن", "Light"),
    "set_theme_dark": ("تیره", "Dark"),
    "set_accent": ("رنگ اصلی", "Accent colour"),
    "set_rtl": ("اصلاح چیدمان راست‌به‌چپ", "Fix right-to-left layout"),
    "set_rtl_sub": ("اگه صفحه‌ها برعکس یا به‌هم‌ریخته دیده می‌شن روشنش کن.", "Turn on if screens look mirrored or misaligned."),
    # ---- reminders
    "set_rem_morning": ("یادآور صبح", "Morning reminder"),
    "set_rem_night": ("یادآور شب", "Evening reminder"),
    "set_rem_letters": ("نامه‌های آینده هم در همون زمانی که خودت انتخاب کردی یادآوری می‌شن.", "Letters to your future self remind you at the time you chose for each."),
    "set_notif_native_ok": ("اعلان‌های دستگاه فعاله. اگه چیزی نمی‌آد، اجازه‌ی اعلان رو بده.", "Device notifications are available. If nothing shows up, allow notifications."),
    "set_notif_inapp": ("در این نسخه یادآورها فقط وقتی برنامه بازه نشون داده می‌شن. برای اعلان واقعی روی گوشی، نسخه‌ی «اعلان» رو بساز (توضیحش توی README هست).",
                        "In this build reminders show only while the app is open. For real phone notifications build the 'notifications' version (see the README)."),
    "set_notif_desktop_ok": ("اعلان‌های دسکتاپ فعاله؛ برنامه باید باز (یا کوچک‌شده) باشه.", "Desktop notifications are on; the app has to be running (it may be minimised)."),
    "set_notif_desktop_no": ("روی این سیستم اعلان دسکتاپ در دسترس نیست؛ یادآورها داخل برنامه نشون داده می‌شن.", "Desktop notifications aren't available here; reminders appear inside the app."),
    "set_notif_allow": ("اجازه‌ی اعلان", "Allow notifications"),
    "set_notif_test": ("آزمایش اعلان", "Test notification"),
    "set_notif_sent": ("اعلان آزمایشی فرستاده شد", "Test notification sent"),
    "set_notif_fail": ("اعلان فرستاده نشد. {why}", "Could not send the notification. {why}"),
    "set_notif_granted": ("اجازه‌ی اعلان ثبت شد", "Notification permission granted"),
    "set_notif_denied": ("اجازه داده نشد", "Permission not granted"),
    # ---- AI
    "set_ai_provider": ("چه کسی گزارش‌ها رو بنویسه؟", "Who writes the reports?"),
    "set_ai_note": ("گزارش‌های هفتگی و ماهانه همیشه با مربیِ آفلاین ساخته می‌شن. اگه بخوای می‌تونی یه هوش مصنوعیِ آنلاین هم وصل کنی تا گزارش‌ها دقیق‌تر و شخصی‌تر بشن.",
                    "Weekly and monthly reports are always available from the offline coach. You can optionally connect an online AI for richer, more personal reports."),
    "set_ai_privacy": ("وقتی هوش مصنوعیِ آنلاین روشنه، متن نوشته‌های همون بازه (بدون اسمِ عزیزانت) برای ساختنِ گزارش به سرویسی که انتخاب کردی فرستاده می‌شه.",
                       "While online AI is on, the text you wrote in that period (without your loved ones' names) is sent to the service you chose to write the report."),
    "set_ai_key": ("کلید API", "API key"),
    "set_ai_key_hint": ("فقط روی همین دستگاه و داخل فایل پروفایل ذخیره می‌شه (رمزگذاری نمی‌شه) و توی پشتیبان نمی‌آد.",
                        "Stored only on this device, inside the profile file (not encrypted), and never included in backups."),
    "set_ai_model": ("نام مدل", "Model name"),
    "set_ai_base": ("نشانی سرویس (اختیاری)", "Service address (optional)"),
    "set_ai_base_hint": ("برای درگاه، پروکسی یا سرور محلی مثل Ollama", "For a gateway, proxy or a local server such as Ollama"),
    "set_ai_consent": ("موافقم نوشته‌هام برای ساختنِ گزارش به این سرویس فرستاده بشه", "I agree to send my writing to this service to create reports"),
    "set_ai_test": ("آزمایش اتصال", "Test connection"),
    "set_ai_testing": ("در حال آزمایش…", "Testing…"),
    "set_ai_ok": ("اتصال برقراره ✅", "Connected ✅"),
    "set_ai_incomplete": ("کلید یا رضایت کامل نیست", "The key or the consent is missing"),
    "set_ai_active": ("فعال", "Active"),
    # ---- security
    "set_pin_on": ("رمز فعاله", "PIN is on"),
    "set_pin_off": ("رمز تنظیم نشده", "No PIN set"),
    "set_autolock": ("وقتی برنامه به پس‌زمینه می‌ره، دوباره قفل می‌شه.", "The app locks again when it goes to the background."),
    "set_delete_profile": ("حذف این پروفایل", "Delete this profile"),
    "set_delete_profile_body": ("همه‌ی نوشته‌های این پروفایل برای همیشه پاک می‌شن. اگه لازمشون داری اول پشتیبان بگیر.",
                                "Everything in this profile will be erased for good. Make a backup first if you need it."),
    # ---- data
    "set_export_file": ("ذخیره‌ی پشتیبان (فایل)", "Save a backup (file)"),
    "set_import_file": ("بازیابی از فایل", "Restore from a file"),
    "set_export_text": ("نمایش پشتیبان به‌صورت متن", "Show backup as text"),
    "set_import_text": ("بازیابی از متن", "Restore from pasted text"),
    "set_data_note": ("پشتیبان شامل همه‌ی نوشته‌ها و لیست‌هاست؛ کلید API و تنظیمات توش نیست. فایل رمزگذاری نمی‌شه، پس جای امنی نگهش دار.",
                      "A backup holds everything you wrote; the API key and settings are not included. The file isn't encrypted, so keep it somewhere safe."),
    "set_data_summary": ("{d} روز نوشته‌شده · {i} مورد در فضاها", "{d} days written · {i} items in spaces"),
    "set_export_done": ("پشتیبان ذخیره شد", "Backup saved"),
    "set_file_unavailable": ("انتخاب فایل روی این دستگاه کار نکرد؛ از گزینه‌ی «متن» استفاده کن.", "The file picker isn't available here — use the text option instead."),
    "set_copy_hint": ("این متن همه‌ی نوشته‌هاته؛ کپی و جای امنی نگهش دار.", "This text holds everything you wrote; copy it and keep it somewhere safe."),
    "set_copy": ("کپی", "Copy"),
    "set_copied": ("کپی شد", "Copied"),
    "set_copy_fail": ("کپی خودکار نشد؛ متن رو انتخاب و دستی کپی کن.", "Couldn't copy automatically — select the text and copy it yourself."),
    "set_paste_hint": ("متن پشتیبان رو اینجا بچسبون", "Paste the backup text here"),
    "set_restore_title": ("بازیابی پشتیبان", "Restore a backup"),
    "set_restore_body": ("«ادغام» فقط موارد تازه رو اضافه می‌کنه و چیزی پاک نمی‌شه. «جایگزینی» همه‌ی نوشته‌های فعلی این پروفایل رو با پشتیبان عوض می‌کنه.",
                         "'Merge' only adds what is new and deletes nothing. 'Replace' swaps everything in this profile for the backup."),
    "set_merge": ("ادغام", "Merge"),
    "set_replace": ("جایگزینی", "Replace"),
    "set_replace_confirm": ("نوشته‌های فعلی این پروفایل با پشتیبان جایگزین می‌شن. مطمئنی؟", "Everything now in this profile will be replaced by the backup. Are you sure?"),
    "set_restore_done": ("بازیابی شد ({n} مورد)", "Restored ({n} items)"),
    "set_restore_bad": ("این فایل یا متن، پشتیبانِ شکرانه نیست.", "This file or text isn't a Shokraneh backup."),
    "set_wipe": ("پاک کردنِ همه‌ی نوشته‌ها", "Erase everything I wrote"),
    "set_wipe_body": ("همه‌ی نوشته‌ها، لیست‌ها، نامه‌ها و گزارش‌های این پروفایل پاک می‌شن. تنظیمات می‌مونه.",
                      "All entries, lists, letters and reports in this profile will be erased. Your settings stay."),
    "set_wiped": ("پاک شد", "Erased"),
    # ---- about
    "set_about_1": ("نوشته‌هات فقط روی همین دستگاه ذخیره می‌شن؛ برنامه حساب کاربری و ردیابی نداره.", "Everything you write is stored only on this device; the app has no account and no tracking."),
    "set_about_2": ("هوش مصنوعیِ آنلاین فقط وقتی کار می‌کنه که خودت کلید بدی و رضایت بدی.", "Online AI works only after you provide a key and give your consent."),
    "set_about_3": ("رمز فقط صفحه‌ی برنامه رو قفل می‌کنه؛ فایل‌ها رمزگذاری نمی‌شن.", "The PIN only locks the app screen; files are not encrypted."),
    "set_about_4": ("گزارش‌های برنامه جای درمان یا مشاوره‌ی پزشکی رو نمی‌گیرن؛ اگه حالت خیلی بده، با یه آدم مورد اعتماد یا یه متخصص حرف بزن.",
                    "The reports are not therapy or medical advice; if you are struggling, please talk to someone you trust or a professional."),
    "set_about_5": ("ساخته‌شده با Flet (پایتون).", "Built with Flet (Python)."),
    # ---- glass look
    "set_glass": ("سبک ظاهر", "Look & feel"),
    "set_glass_full": ("شیشه‌ای", "Glass"),
    "set_glass_lite": ("سبک", "Light"),
    "set_glass_off": ("ساده", "Plain"),
    "set_glass_note": ("«شیشه‌ای» پشت نوار پایین و پنجره‌ها بلور دارد. اگه گوشی‌ت کند شد «سبک» (بدون بلور) یا «ساده» (بدون شفافیت) رو بزن.",
                       "“Glass” blurs what is behind the tab bar and dialogs. If your phone feels slow pick “Light” (no blur) or “Plain” (no transparency)."),
    "set_island": ("جزیره‌ی پویا", "Dynamic island"),
    "set_island_sub": ("قرص بالای صفحه که خلاصه‌ی امروز و پیام‌ها را نشان می‌دهد", "The pill at the top that shows today's summary and messages"),
    # ---- creator & copyright
    "set_creator": ("سازنده", "Creator"),
    "creator_role": ("سازنده و طراح برنامه", "Creator & designer of the app"),
    "copyright_title": ("حقوق مالکیت و کپی‌رایت", "Ownership & copyright"),
    "copyright_1": ("این برنامه — شامل کد منبع، طراحی رابط کاربری، پرسش‌ها و متن‌ها، نمادها و نام «شکرانه» — اثر فکری و مالکیتِ انحصاریِ {name} است و "
                    "مشمول قوانین حمایت از حقوق پدیدآورندگان نرم‌افزارهای رایانه‌ای و حقوق مؤلفان، مصنفان و هنرمندان در ایران است.",
                    "This app — including its source code, interface design, questions and texts, icons and the name “Shokraneh” — is the intellectual "
                    "property and exclusive work of {name}, protected by the applicable copyright laws, including Iran's laws on the rights of software "
                    "authors and of authors, composers and artists."),
    "copyright_2": ("هرگونه کپی‌برداری، تکثیر، انتشار، توزیع، فروش، ترجمه، اقتباس، مهندسی معکوس یا بازنشر تمام یا بخشی از برنامه بدون اجازه‌ی کتبیِ "
                    "سازنده ممنوع است و جرم محسوب می‌شود؛ متخلفان از راه مراجع قانونی پیگیری می‌شوند.",
                    "Any copying, reproduction, publication, distribution, sale, translation, adaptation, reverse engineering or re-release of all or "
                    "part of the app without the creator's written permission is prohibited and is a legal offence; violations will be pursued "
                    "through the proper legal channels."),
    "copyright_3": ("نوشته‌ها و اطلاعات شخصی‌ای که خودت در برنامه ثبت می‌کنی، متعلق به خودت است و فقط روی دستگاه خودت می‌ماند.",
                    "The entries and personal information you write in the app belong to you and stay on your own device."),
    "copyright_4": ("کتابخانه‌ها و فونت‌های متن‌بازِ به‌کاررفته (از جمله Flet و Vazirmatn) مالکیتِ سازندگانشان هستند و تحت مجوزهای خودشان استفاده می‌شوند.",
                    "The open-source libraries and fonts used (including Flet and Vazirmatn) belong to their authors and are used under their own licences."),
    "copyright_5": ("درخواست مجوز استفاده یا همکاری باید مستقیم از سازنده انجام شود.",
                    "Requests for a licence to use or cooperate must be made directly to the creator."),
})

SECTIONS = [("look", "PALETTE", "lavender"), ("reminders", "NOTIFICATIONS_ACTIVE", "sand"), ("ai", "AUTO_AWESOME", "sky"),
            ("security", "LOCK", "rose"), ("data", "BACKUP", "sage"), ("about", "INFO_OUTLINE", "good"), ("creator", "COPYRIGHT", "warn")]


def _label(c: kit.Ctx, key: str) -> Any:
    return kit.text(c, c.t(key), 13.5, "medium", "muted")


def _note(c: kit.Ctx, key: str, icon_name: str = "INFO_OUTLINE", size: float = 13) -> Any:
    return kit.row(c, [kit.icon(c, icon_name, 20, "faint"), kit.text(c, c.t(key), size, color="muted", expand=True)], spacing=10, v="start")


def _counts(data: dict) -> tuple[int, int]:
    days = len(set(data["morning"]) | set(data["night"]) | set(data["energy"]))
    items = sum(len(data[k]) for k in ("wishes", "wins", "god_talks", "prayers", "people", "hard_days", "letters"))
    return days, items


# --------------------------------------------------------------------------- hub
def _summary(app, c: kit.Ctx, key: str) -> str:
    p = app.profile
    if key == "look":
        cal = {"auto": c.t("set_auto"), "jalali": c.t("set_cal_jalali"), "gregorian": c.t("set_cal_greg")}.get(app.store.get("calendar", "auto"), "")
        theme_name = c.t(f"set_theme_{app.store.get('theme_mode', 'system')}")
        return f"{'فارسی' if app.lang == 'fa' else 'English'} · {cal} · {theme_name}"
    if key == "reminders":
        parts = []
        for kind, k in (("morning", "set_sum_m"), ("night", "set_sum_n")):
            cfg = p.setting(f"reminders.{kind}") or {}
            if cfg.get("enabled"):
                parts.append(c.t(k, t=c.n(cfg.get("time", ""))))
        return " · ".join(parts) or c.t("set_off")
    if key == "ai":
        cfg = p.setting("ai") or {}
        label = ai.PROVIDER_LABELS.get(cfg.get("provider"), ai.PROVIDER_LABELS["offline"])[0 if c.lang == "fa" else 1]
        return f"{label} · {c.t('set_ai_active')}" if ai.is_ready(cfg) else label
    if key == "security":
        return c.t("set_pin_on" if app.store.has_pin(p.id) else "set_pin_off")
    if key == "data":
        d, i = _counts(p.data)
        return c.t("set_data_summary", d=c.n(d), i=c.n(i))
    if key == "creator":
        return config.CREATOR_NAME
    return c.t("set_version", v=c.n(__version__))


def copyright_text(c: kit.Ctx) -> str:
    """'© 1405 <name> — all rights reserved' with the current year in the calendar of the language."""
    year = jalali.ymd(util.logical_today(), c.lang == "fa")[0]
    return c.t("copyright_line", y=c.n(year), name=config.CREATOR_NAME)


def _edit_profile(app) -> None:
    from . import onboarding

    c = app.ctx()
    p = app.profile
    buf = {"name": p.name, "avatar": p.avatar}
    holder = kit.box(c, None)

    def pick(a: str) -> None:
        buf["avatar"] = a
        draw()
        app.page.update()

    def draw() -> None:
        holder.content = kit.col(c, [kit.field(c, c.t("onb_name_label"), buf["name"], on_change=lambda v: buf.update(name=v), max_length=24),
                                     kit.text(c, c.t("onb_avatar"), 13.5, "medium", "muted"), onboarding.avatar_picker(c, buf["avatar"], pick)], spacing=12)

    def save() -> None:
        app.store.update_profile(p.id, name=buf["name"].strip() or p.name, avatar=buf["avatar"])
        app.refresh()

    draw()
    app.dialog(c.t("set_edit_profile"), holder, [(c.t("cancel"), None, "ghost"), (c.t("save"), save, "primary")])


def view(app):
    c = app.ctx()
    p = app.profile
    has_pin = app.store.has_pin(p.id)
    several = len(app.store.profile_list()) > 1
    who = kit.row(c, [kit.avatar(c, p.avatar, 56), kit.col(c, [kit.text(c, p.name, 18, "bold", max_lines=1), kit.text(c, c.t("set_profile_hint"), 12.5, color="muted")],
                                                         spacing=2, expand=True),
                      kit.icon_button(c, "EDIT", lambda e: _edit_profile(app), "muted", 20, c.t("set_edit_profile"))], spacing=14)
    actions = [kit.button(c, c.t("switch_profile"), lambda e: app.switch_profile(), "soft", "SWAP_HORIZ", expand=True, size="sm")]
    if has_pin:
        actions.append(kit.button(c, c.t("set_lock_now"), lambda e: app.lock_now(), "soft", "LOCK", expand=True, size="sm"))
    head = kit.card(c, kit.col(c, [who, kit.row(c, actions, spacing=8)], spacing=14))
    tiles = [kit.tile(c, c.t(f"set_{key}"), _summary(app, c, key), icon, tone, on_click=(lambda e, k=key: app.push(section, key=k)))
             for key, icon, tone in SECTIONS]
    footer = kit.text(c, copyright_text(c), 12, color="faint", align="center")
    return kit.screen(c, [head, *tiles, kit.space(c, 4), footer], title=c.t("settings"), on_back=app.pop)


def section(app, key: str):
    c = app.ctx()
    body = BUILDERS.get(key, _about)(app, c)
    return kit.screen(c, body, title=c.t(f"set_{key}"), on_back=app.pop)


# --------------------------------------------------------------------------- appearance & language
def _look(app, c: kit.Ctx) -> list[Any]:
    store, p = app.store, app.profile

    def set_app(key: str, value: Any) -> None:
        store.set(key, value)
        app.notifier.lang = app.lang
        app.apply_theme()
        app.refresh()
        if key == "language":
            app.resync()

    ref = {"5": date(2024, 1, 6), "6": date(2024, 1, 7), "0": date(2024, 1, 1)}  # Saturday, Sunday, Monday
    ws = p.setting("week_start")
    ws_opts = [("auto", c.t("set_auto"))] + [(k, jalali.weekday_name(d, c.lang, c.lang != "fa")) for k, d in ref.items()]

    def set_ws(k: str) -> None:
        p.set_setting("week_start", None if k == "auto" else int(k))
        app.refresh()

    cur = store.get("accent", "sage")
    swatches = []
    for name, (light, dark) in theme.ACCENTS.items():
        dot = kit.box(c, kit.icon(c, "CHECK", 20, "on_accent") if name == cur else None, width=44, height=44, radius=22, bg=dark if c.dark else light,
                      align=C.center(), on_click=(lambda e, n=name: set_app("accent", n)))
        swatches.append(kit.col(c, [dot, kit.text(c, theme.ACCENT_NAMES[name][0 if c.lang == "fa" else 1], 11.5, color="muted", align="center")], spacing=4, h="center"))

    body = [
        kit.card(c, kit.col(c, [
            _label(c, "set_language"), kit.segmented(c, [("fa", "فارسی"), ("en", "English")], app.lang, lambda k: set_app("language", k)),
            _label(c, "calendar"), kit.segmented(c, [("auto", c.t("set_auto")), ("jalali", c.t("set_cal_jalali")), ("gregorian", c.t("set_cal_greg"))],
                                                  store.get("calendar", "auto"), lambda k: set_app("calendar", k)),
            _label(c, "set_week_start"), kit.segmented(c, ws_opts, "auto" if ws is None else str(ws), set_ws)], spacing=10)),
        kit.card(c, kit.col(c, [
            _label(c, "set_theme"), kit.segmented(c, [("system", c.t("set_theme_system")), ("light", c.t("set_theme_light")), ("dark", c.t("set_theme_dark"))],
                                                  store.get("theme_mode", "system"), lambda k: set_app("theme_mode", k)),
            _label(c, "set_accent"), kit.row(c, swatches, spacing=14, wrap=True, run_spacing=12)], spacing=10)),
    ]
    body.append(kit.card(c, kit.col(c, [
        _label(c, "set_glass"), kit.segmented(c, [("full", c.t("set_glass_full")), ("lite", c.t("set_glass_lite")), ("off", c.t("set_glass_off"))],
                                              app.glass_style, lambda k: set_app("glass", k)),
        _note(c, "set_glass_note"), kit.divider(c),
        kit.switch_row(c, c.t("set_island"), app.island_on, lambda v: set_app("island", v), c.t("set_island_sub"), "AUTO_AWESOME")], spacing=10)))
    if c.rtl:
        body.append(kit.card(c, kit.switch_row(c, c.t("set_rtl"), bool(store.get("rtl_compat")), lambda v: set_app("rtl_compat", v), c.t("set_rtl_sub"), "SWAP_HORIZ")))
    return body


# --------------------------------------------------------------------------- reminders
def _notif_card(app, c: kit.Ctx) -> Any:
    n = app.notifier
    stt = n.status()
    android = stt["platform"] == "android"
    if stt["native"]:
        key = "set_notif_native_ok"
    elif android:
        key = "set_notif_inapp"
    else:
        key = "set_notif_desktop_ok" if stt["desktop_ok"] else "set_notif_desktop_no"

    def allow() -> None:
        async def run() -> None:
            ok = await n.request_permissions()
            app.toast(c.t("set_notif_granted" if ok else "set_notif_denied"), error=not ok)
            app.resync()
        app.run_async(run)

    def test() -> None:
        title, body = c.t("notif_test_title"), c.t("notif_test_body")
        if stt["native"]:
            async def run() -> None:
                ok = await n.test()
                app.toast(c.t("set_notif_sent") if ok else c.t("set_notif_fail", why=n.last_error), error=not ok)
            app.run_async(run)
        elif android:
            app.toast(f"{title}  {body}")  # no native plugin in this build: show what the in-app reminder looks like
        else:
            def done(ok: Any, err: Exception | None) -> None:
                good = bool(ok) and err is None
                app.toast(c.t("set_notif_sent") if good else c.t("set_notif_fail", why=""), error=not good)
            app.bg(lambda: notify.desktop_notify(title, body), done=done)

    btns = [kit.button(c, c.t("set_notif_allow"), lambda e: allow(), "soft", size="sm") if stt["native"] else None,
            kit.button(c, c.t("set_notif_test"), lambda e: test(), "soft", size="sm")]
    parts = [_note(c, key, "NOTIFICATIONS_ACTIVE"), kit.row(c, btns, spacing=8, wrap=True)]
    if stt["error"] and not stt["native"] and android:
        parts.append(kit.text(c, stt["error"], 11.5, color="faint"))
    return kit.card(c, kit.col(c, parts, spacing=12))


def _reminders(app, c: kit.Ctx) -> list[Any]:
    p = app.profile
    body: list[Any] = []
    for kind, icon_name in (("morning", "WB_SUNNY"), ("night", "NIGHTLIGHT_ROUND")):
        cfg = p.setting(f"reminders.{kind}") or {}
        on = bool(cfg.get("enabled"))
        when = cfg.get("time") or ("07:30" if kind == "morning" else "21:30")

        def toggle(v: bool, kind: str = kind) -> None:
            p.set_setting(f"reminders.{kind}.enabled", v)
            app.debounce("resync", 0.8, app.resync)
            app.refresh()

        def set_time(hhmm: str, kind: str = kind) -> None:
            p.set_setting(f"reminders.{kind}.time", hhmm)
            app.debounce("resync", 0.8, app.resync)
            app.refresh()

        parts = [kit.switch_row(c, c.t(f"set_rem_{kind}"), on, toggle, c.n(when) if on else None, icon_name)]
        if on:
            parts.append(kit.box(c, kit.time_stepper(c, when, set_time), align=C.center()))
        body.append(kit.card(c, kit.col(c, parts, spacing=10)))
    body += [_note(c, "set_rem_letters", "MAIL_OUTLINE"), _notif_card(app, c)]
    return body


# --------------------------------------------------------------------------- AI
def _ai(app, c: kit.Ctx) -> list[Any]:
    p = app.profile
    st = app.state()
    pending: dict[str, Any] = st.setdefault("pending", {})
    cfg = dict(p.setting("ai") or {})

    def flush() -> None:
        if pending:
            items = dict(pending)
            pending.clear()
            for k, v in items.items():
                p.set_setting(f"ai.{k}", v)

    app.on_leave(flush)

    def stage(key: str, value: Any) -> None:
        pending[key] = str(value).strip()
        app.debounce("ai_save", 0.8, flush)

    def set_provider(k: str) -> None:
        flush()
        p.set_setting("ai.provider", k)
        app.refresh()

    def set_consent(v: bool) -> None:
        flush()
        p.set_setting("ai.consent", v)
        app.refresh()

    def test() -> None:
        flush()
        live = dict(p.setting("ai") or {})
        if not ai.is_ready(live):
            return app.toast(c.t("set_ai_incomplete"), error=True)
        st["testing"] = True
        app.refresh()

        def done(res: Any, err: Exception | None) -> None:
            st["testing"] = False
            if err is None:
                app.toast(c.t("set_ai_ok"))
            else:
                app.toast(err.text(c.lang) if isinstance(err, ai.AIError) else c.t("error_generic"), error=True)
            app.refresh()

        app.bg(lambda: ai.ping(live), done=done)

    provider = cfg.get("provider") if cfg.get("provider") in ai.PROVIDERS else "offline"
    names = [(k, ai.PROVIDER_LABELS[k][0 if c.lang == "fa" else 1]) for k in ai.PROVIDERS]
    body: list[Any] = [kit.card(c, kit.col(c, [_label(c, "set_ai_provider"), kit.chips(c, names, provider, set_provider), _note(c, "set_ai_note")], spacing=12))]
    if provider != "offline":
        busy = bool(st.get("testing"))
        fields = [
            kit.field(c, c.t("set_ai_key"), str(cfg.get("api_key") or ""), on_change=lambda v: stage("api_key", v), password=True, reveal=True),
            kit.text(c, c.t("set_ai_key_hint"), 12, color="faint"),
            kit.field(c, c.t("set_ai_model"), str(cfg.get("model") or ""), on_change=lambda v: stage("model", v), hint=ai.DEFAULT_MODEL.get(provider)),
            kit.field(c, c.t("set_ai_base"), str(cfg.get("base_url") or ""), on_change=lambda v: stage("base_url", v), hint=ai.DEFAULT_BASE.get(provider)),
            kit.text(c, c.t("set_ai_base_hint"), 12, color="faint"),
        ]
        body += [kit.card(c, kit.col(c, fields, spacing=10)),
                 kit.card(c, kit.col(c, [_note(c, "set_ai_privacy", "SHIELD_OUTLINED"),
                                         kit.switch_row(c, c.t("set_ai_consent"), bool(cfg.get("consent")), set_consent),
                                         kit.button(c, c.t("set_ai_testing") if busy else c.t("set_ai_test"), lambda e: test(), "soft", "SEND", expand=True, disabled=busy)],
                                  spacing=14))]
    return body


# --------------------------------------------------------------------------- security
def _security(app, c: kit.Ctx) -> list[Any]:
    from . import lock

    p = app.profile
    has = app.store.has_pin(p.id)

    def delete_profile() -> None:
        app.store.delete_profile(p.id)
        app.profile = None
        app.store.set("last_profile", None)
        app.start()

    head = kit.row(c, [kit.badge(c, "LOCK", "rose" if has else "sky", 46),
                       kit.col(c, [kit.text(c, c.t("set_pin_on" if has else "set_pin_off"), 16, "bold"), kit.text(c, c.t("pin_note"), 12.5, color="muted")],
                               spacing=2, expand=True)], spacing=14)
    if has:
        btns = [kit.button(c, c.t("pin_title_change"), lambda e: app.push(lock.setup, mode="change"), "soft", size="sm"),
                kit.button(c, c.t("pin_title_remove"), lambda e: app.push(lock.setup, mode="remove"), "ghost", size="sm"),
                kit.button(c, c.t("set_lock_now"), lambda e: app.lock_now(), "soft", "LOCK", size="sm")]
    else:
        btns = [kit.button(c, c.t("pin_title_set"), lambda e: app.push(lock.setup, mode="set"), "primary", "LOCK", size="sm")]
    return [kit.card(c, kit.col(c, [head, kit.row(c, btns, spacing=8, wrap=True), _note(c, "set_autolock", "SCHEDULE", 12.5)], spacing=14)),
            kit.button(c, c.t("set_delete_profile"), lambda e: app.confirm(c.t("set_delete_profile"), c.t("set_delete_profile_body"), delete_profile, c.t("delete"), danger=True),
                       "danger", "DELETE_OUTLINE", expand=True)]


# --------------------------------------------------------------------------- backup & data
def _valid_backup(text: str) -> bool:
    try:
        payload = json.loads(text)
    except ValueError:
        return False
    return isinstance(payload, dict) and payload.get("format") == store_mod.BACKUP_FORMAT and isinstance(payload.get("data"), dict)


def _restore(app, c: kit.Ctx, text: str, mode: str) -> None:
    try:
        counts = app.profile.import_text(text, mode)
    except ValueError:
        return app.toast(c.t("set_restore_bad"), error=True)
    app.toast(c.t("set_restore_done", n=c.n(sum(counts.values()))))
    app.resync()
    app.refresh()


def _ask_mode(app, c: kit.Ctx, text: str) -> None:
    if not _valid_backup(text):
        return app.toast(c.t("set_restore_bad"), error=True)

    def replace() -> None:
        app.confirm(c.t("set_replace"), c.t("set_replace_confirm"), lambda: _restore(app, c, text, "replace"), c.t("set_replace"), danger=True)

    app.dialog(c.t("set_restore_title"), kit.text(c, c.t("set_restore_body"), 14, color="muted"),
               [(c.t("cancel"), None, "ghost"), (c.t("set_replace"), replace, "danger"), (c.t("set_merge"), lambda: _restore(app, c, text, "merge"), "primary")])


def _export_file(app, c: kit.Ctx) -> None:
    text = app.profile.export_text()
    name = f"shokraneh-backup-{util.now():%Y%m%d}.json"
    app.suppress_lock(180)  # the system dialog moves the app to the background; don't lock the user out

    async def run() -> None:
        try:
            path = await files.save(app.page, name, text.encode("utf-8"), c.t("set_export_file"))
        except Exception:
            return app.toast(c.t("set_file_unavailable"), error=True)
        if path:
            app.toast(c.t("set_export_done"))
    app.run_async(run)


def _import_file(app, c: kit.Ctx) -> None:
    app.suppress_lock(180)

    async def run() -> None:
        try:
            data = await files.pick(app.page, c.t("set_import_file"))
        except Exception:
            return app.toast(c.t("set_file_unavailable"), error=True)
        if data is None:
            return
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            return app.toast(c.t("set_restore_bad"), error=True)
        _ask_mode(app, c, text)
    app.run_async(run)


def _show_text(app, c: kit.Ctx) -> None:
    text = app.profile.export_text()

    async def copy() -> None:
        ok = await files.copy_text(app.page, text)
        app.toast(c.t("set_copied" if ok else "set_copy_fail"), error=not ok)

    body = kit.col(c, [kit.text(c, c.t("set_copy_hint"), 13, color="muted"), kit.field(c, None, text, multiline=True, lines=8, size=12)], spacing=10)
    app.dialog(c.t("set_export_text"), body, [(c.t("close"), None, "ghost"), (c.t("set_copy"), lambda: app.run_async(copy), "primary")])


def _paste_text(app, c: kit.Ctx) -> None:
    buf = {"text": ""}

    def go() -> None:
        _ask_mode(app, c, buf["text"].strip())

    field = kit.field(c, None, "", on_change=lambda v: buf.update(text=v), multiline=True, lines=6, hint=c.t("set_paste_hint"), size=12)
    app.dialog(c.t("set_import_text"), field, [(c.t("cancel"), None, "ghost"), (c.t("continue"), go, "primary")])


def _data(app, c: kit.Ctx) -> list[Any]:
    p = app.profile

    def wipe() -> None:
        p.wipe()
        app.resync()
        app.toast(c.t("set_wiped"))
        app.refresh()

    d, i = _counts(p.data)
    summary = kit.row(c, [kit.badge(c, "BACKUP", "sage", 44), kit.text(c, c.t("set_data_summary", d=c.n(d), i=c.n(i)), 15, "medium", expand=True)], spacing=14)
    return [
        kit.card(c, kit.col(c, [summary,
                                kit.button(c, c.t("set_export_file"), lambda e: _export_file(app, c), "primary", "FILE_DOWNLOAD", expand=True),
                                kit.button(c, c.t("set_import_file"), lambda e: _import_file(app, c), "soft", "FILE_UPLOAD", expand=True),
                                _note(c, "set_data_note", "SHIELD_OUTLINED", 12.5)], spacing=12)),
        kit.card(c, kit.col(c, [kit.button(c, c.t("set_export_text"), lambda e: _show_text(app, c), "ghost", "CONTENT_COPY", expand=True),
                                kit.button(c, c.t("set_import_text"), lambda e: _paste_text(app, c), "ghost", "EDIT_NOTE", expand=True)], spacing=8)),
        kit.button(c, c.t("set_wipe"), lambda e: app.confirm(c.t("set_wipe"), c.t("set_wipe_body"), wipe, c.t("delete"), danger=True), "danger", "DELETE_OUTLINE", expand=True),
    ]


# --------------------------------------------------------------------------- about
def _about(app, c: kit.Ctx) -> list[Any]:
    notes = [("SHIELD_OUTLINED", "set_about_1"), ("AUTO_AWESOME", "set_about_2"), ("LOCK", "set_about_3"), ("FAVORITE_BORDER", "set_about_4"), ("TUNE", "set_about_5")]
    head = kit.col(c, [kit.box(c, kit.badge(c, "SPA", "accent", 72, 34), align=C.center()), kit.text(c, c.t("app_name"), 22, "bold", align="center"),
                       kit.text(c, c.t("app_tagline"), 14, color="muted", align="center"), kit.text(c, c.t("set_version", v=c.n(__version__)), 12.5, color="faint", align="center"),
                       kit.text(c, c.t("creator_by", name=config.CREATOR_NAME), 12.5, "medium", "accent_strong", align="center")],
                   spacing=6, h="center")
    rows = [kit.row(c, [kit.icon(c, ic, 22, "accent_strong"), kit.text(c, c.t(k), 14, expand=True)], spacing=12, v="start") for ic, k in notes]
    return [head, kit.card(c, kit.col(c, rows, spacing=16), padding=18)]


# --------------------------------------------------------------------------- creator & copyright
def _creator(app, c: kit.Ctx) -> list[Any]:
    name = config.CREATOR_NAME
    monogram = kit.box(c, kit.text(c, name[:1], 34, "bold", "on_accent", align="center"), width=84, height=84, radius=42, bg="glass", align=C.center())
    hero = kit.hero(c, kit.col(c, [kit.box(c, monogram, align=C.center()),
                                   kit.text(c, name, 25, "bold", "on_accent", align="center"),
                                   kit.text(c, c.t("creator_role"), 14, "medium", "on_accent", align="center"),
                                   kit.space(c, 2),
                                   kit.text(c, f"{c.t('app_name')} · {c.t('set_version', v=c.n(__version__))}", 12.5, color="on_accent", align="center")],
                                  spacing=6, h="center"), padding=C.pad(20, 28, 20, 26))
    paragraphs = [kit.text(c, c.t(k, name=name), 13.5, color="text" if k in ("copyright_1", "copyright_2") else "muted") for k in
                  ("copyright_1", "copyright_2", "copyright_3", "copyright_4", "copyright_5")]
    legal = kit.card(c, kit.col(c, [
        kit.row(c, [kit.badge(c, "GAVEL", "warn", 38), kit.text(c, c.t("copyright_title"), 16, "bold", expand=True)], spacing=12),
        *paragraphs, kit.divider(c), kit.text(c, copyright_text(c), 13.5, "bold", "accent_strong", align="center")], spacing=12), padding=18)
    return [hero, legal]


BUILDERS: dict[str, Callable[[Any, kit.Ctx], list[Any]]] = {
    "look": _look, "reminders": _reminders, "ai": _ai, "security": _security, "data": _data, "about": _about, "creator": _creator,
}
