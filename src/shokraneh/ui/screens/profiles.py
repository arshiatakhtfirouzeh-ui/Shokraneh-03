"""Profile picker (several people can use one device; each has completely separate data)."""
from __future__ import annotations

from typing import Any

from ...i18n import register
from .. import kit

register({
    "profiles_title": ("چه کسی می‌نویسه؟", "Who's writing?"),
    "profiles_sub": ("هر پروفایل نوشته‌های جدا و مخصوص خودش رو داره", "Each profile keeps its own writing, completely separate"),
    "profiles_add": ("افزودن پروفایل", "Add a profile"),
    "profiles_pin": ("با رمز قفل شده", "Protected by a PIN"),
})


def view(app):
    from . import onboarding

    c = app.ctx()
    cards: list[Any] = []
    for p in app.store.profile_list():
        sub = c.t("profiles_pin") if p["has_pin"] else None
        lock = kit.icon(c, "LOCK", 18, "faint") if p["has_pin"] else None
        info = kit.col(c, [kit.text(c, p["name"], 17, "medium", max_lines=1), kit.text(c, sub, 12.5, color="muted") if sub else None], spacing=2, expand=True)
        cards.append(kit.card(c, kit.row(c, [kit.avatar(c, p["avatar"], 50), info, lock], spacing=14), on_click=(lambda e, pid=p["id"]: app.enter_profile(pid))))
    body = [*cards, kit.button(c, c.t("profiles_add"), lambda e: app.push(onboarding.view, add=True), "soft", "PERSON_ADD", expand=True)]
    return kit.screen(c, body, title=c.t("profiles_title"), subtitle=c.t("profiles_sub"))
