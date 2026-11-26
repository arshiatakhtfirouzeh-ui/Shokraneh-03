"""Root screen: header + the current tab + bottom navigation."""
from __future__ import annotations

from ... import reminders, util
from ...i18n import register
from .. import kit

register({
    "tab_home": ("امروز", "Today"),
    "tab_spaces": ("فضاها", "Spaces"),
    "tab_progress": ("پیشرفت", "Progress"),
    "tab_inbox": ("پیام‌ها", "Messages"),
})

TABS = [("home", "HOME_OUTLINED", "tab_home"), ("spaces", "GRID_VIEW", "tab_spaces"),
        ("progress", "INSIGHTS", "tab_progress"), ("inbox", "MAIL_OUTLINE", "tab_inbox")]


def view(app):
    from . import home, inbox, progress, spaces

    c = app.ctx()
    tab = app.tab if app.tab in ("home", "spaces", "progress", "inbox") else "home"
    mod = {"home": home, "spaces": spaces, "progress": progress, "inbox": inbox}[tab]
    title, subtitle, actions, body = mod.content(app, c)
    data = app.profile.data
    badges = {"inbox": app.profile.unread_count() > 0,
              "spaces": bool(reminders.letters_in_state(data, util.now(), "arrived"))}
    nav = kit.nav_bar(c, [(k, icon, c.t(label)) for k, icon, label in TABS], tab, app.go, badges)
    return kit.screen(c, body, title=title, subtitle=subtitle, actions=actions, bottom=nav, main=True)
