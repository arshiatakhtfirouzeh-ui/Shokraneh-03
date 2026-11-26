"""First-run welcome (language, name, emblem) and 'add a profile'."""
from __future__ import annotations

from typing import Any, Callable

from ... import config
from ...i18n import register
from .. import compat as C
from .. import kit

register({
    "onb_welcome": ("به «شکرانه» خوش اومدی", "Welcome to Shokraneh"),
    "onb_welcome_sub": ("جایی آروم برای دیدنِ خوبی‌های هر روز", "A calm place to notice the good in every day"),
    "onb_f1_t": ("صبح و شب", "Morning & evening"),
    "onb_f1_b": ("چند سؤال کوتاه که روزت رو شروع و تمام می‌کنه", "A few short questions to begin and close your day"),
    "onb_f2_t": ("فضاهای شخصی", "Personal spaces"),
    "onb_f2_b": ("آرزوها، دعاها، عزیزان، روزهای سخت و نامه به خودِ آینده", "Wishes, prayers, loved ones, hard days and letters to your future self"),
    "onb_f3_t": ("گزارش و پیشرفت", "Reports & progress"),
    "onb_f3_b": ("هر هفته یه گزارش مهربون و صادق، و هر ماه مرورِ انرژی و حالت", "A kind, honest report each week and a monthly look at your energy and mood"),
    "onb_lang": ("زبان برنامه", "App language"),
    "onb_name_t": ("اسمت چیه؟", "What should I call you?"),
    "onb_name_b": ("این اسم فقط توی همین برنامه نشون داده می‌شه.", "This name is only shown inside the app."),
    "onb_name_label": ("اسم", "Name"),
    "onb_name_required": ("اسمت رو بنویس", "Please enter a name"),
    "onb_avatar": ("یه نشونه انتخاب کن", "Pick an emblem"),
    "onb_ready_t": ("آماده‌ای 🌿", "You're all set 🌿"),
    "onb_ready_1": ("نوشته‌هات فقط روی همین دستگاه ذخیره می‌شن.", "Everything you write stays on this device."),
    "onb_ready_2": ("گزارشِ هوشمندِ آنلاین به‌صورت پیش‌فرض خاموشه؛ مربیِ آفلاین همیشه کار می‌کنه.", "Online AI is off by default; the offline coach always works."),
    "onb_ready_3": ("یادآورها و رمزِ قفل رو می‌تونی از تنظیمات عوض کنی.", "You can change reminders and set a PIN in Settings."),
    "onb_add_title": ("پروفایل تازه", "New profile"),
})

AVATARS = ["🌿", "🌸", "🌙", "🌊", "🍃", "⭐", "🦋", "🌻", "🍀", "🌈", "🐦", "🌷", "🌼", "🍂", "🐚"]


def avatar_picker(c: kit.Ctx, current: str, on_pick: Callable[[str], None]) -> Any:
    cells = []
    for a in AVATARS:
        sel = a == current
        cells.append(kit.box(c, kit.text(c, a, 24, align="center"), width=52, height=52, radius=26, bg="accent_soft" if sel else "surface2",
                             border=True, border_color="accent" if sel else "border", align=C.center(), on_click=(lambda e, a=a: on_pick(a))))
    return kit.row(c, cells, spacing=10, wrap=True, run_spacing=10)


def _feature(c: kit.Ctx, icon_name: str, tone: str, title: str, body: str) -> Any:
    text = kit.col(c, [kit.text(c, title, 15.5, "medium"), kit.text(c, body, 13, color="muted")], spacing=2, expand=True)
    return kit.row(c, [kit.badge(c, icon_name, tone, 44), text], spacing=14, v="start")


def view(app, add: bool = False):
    c = app.ctx()
    st = app.state()
    first = 1 if add else 0
    last = 1 if add else 2
    st.setdefault("step", first)
    st.setdefault("name", "")
    st.setdefault("avatar", AVATARS[0])
    st.setdefault("error", False)
    step = st["step"]

    def go(n: int) -> None:
        st["step"] = max(first, min(last, n))
        st["error"] = False
        app.refresh()

    def finish() -> None:
        rec = app.store.create_profile(st["name"].strip(), st["avatar"])
        app.store.set("onboarded", True)
        app.open_profile(rec["id"])

    def nxt(e: Any = None) -> None:
        if step == 1 and not st["name"].strip():
            st["error"] = True
            return app.refresh()
        if step >= last:
            return finish()
        go(step + 1)

    def set_lang(k: str) -> None:
        app.store.set("language", k)
        app.notifier.lang = k
        app.apply_theme()
        app.refresh()

    def set_avatar(a: str) -> None:
        st["avatar"] = a
        app.refresh()

    body: list[Any] = []
    if not add:
        body.append(kit.steps_bar(c, last + 1, step))
    if step == 0:
        body += [kit.space(c, 10), kit.box(c, kit.badge(c, "SPA", "accent", 84, 40), align=C.center()),
                 kit.text(c, c.t("onb_welcome"), 26, "bold", align="center"), kit.text(c, c.t("onb_welcome_sub"), 15, color="muted", align="center"),
                 kit.space(c, 6),
                 _feature(c, "WB_SUNNY", "sand", c.t("onb_f1_t"), c.t("onb_f1_b")),
                 _feature(c, "FAVORITE", "rose", c.t("onb_f2_t"), c.t("onb_f2_b")),
                 _feature(c, "AUTO_AWESOME", "lavender", c.t("onb_f3_t"), c.t("onb_f3_b")),
                 kit.space(c, 6), kit.text(c, c.t("onb_lang"), 14, "medium", "muted"),
                 kit.segmented(c, [("fa", "فارسی"), ("en", "English")], app.lang, set_lang),
                 kit.space(c, 6), kit.text(c, c.t("creator_by", name=config.CREATOR_NAME), 12.5, "medium", "faint", align="center")]
    elif step == 1:
        body += [kit.space(c, 6), kit.text(c, c.t("onb_name_t"), 24, "bold"), kit.text(c, c.t("onb_name_b"), 14, color="muted"),
                 kit.field(c, c.t("onb_name_label"), st["name"], on_change=lambda v: st.update(name=v), max_length=24, on_submit=nxt)]
        if st["error"]:
            body.append(kit.text(c, c.t("onb_name_required"), 13, "medium", "bad"))
        body += [kit.space(c, 4), kit.text(c, c.t("onb_avatar"), 14.5, "medium", "muted"), avatar_picker(c, st["avatar"], set_avatar)]
    else:
        notes = [("SHIELD_OUTLINED", "onb_ready_1"), ("AUTO_AWESOME", "onb_ready_2"), ("NOTIFICATIONS_ACTIVE", "onb_ready_3")]
        body += [kit.space(c, 10), kit.box(c, kit.avatar(c, st["avatar"], 84), align=C.center()),
                 kit.text(c, c.t("onb_ready_t"), 24, "bold", align="center"),
                 kit.text(c, st["name"].strip(), 16, color="muted", align="center"), kit.space(c, 6),
                 kit.card(c, kit.col(c, [kit.row(c, [kit.icon(c, ic, 22, "accent_strong"), kit.text(c, c.t(k), 14.5, expand=True)], spacing=12, v="start")
                                         for ic, k in notes], spacing=14), padding=18)]

    buttons = []
    if step > first:
        buttons.append(kit.button(c, c.t("back"), lambda e: go(step - 1), "ghost"))
    buttons.append(kit.button(c, c.t("start") if step >= last else c.t("continue"), nxt, "primary", expand=True))
    bottom = kit.box(c, kit.row(c, buttons, spacing=10), padding=C.pad(20, 8, 20, 18), radius=0)
    return kit.screen(c, body, title=c.t("onb_add_title") if add and step == first else None, on_back=app.pop if add and step == first else None,
                      bottom=bottom)
