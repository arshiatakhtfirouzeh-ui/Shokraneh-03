"""Spaces tab: the personal lists and the letters, as a calm two-column grid."""
from __future__ import annotations

from ... import reminders, util
from ...i18n import register
from .. import compat as C
from .. import kit
from . import lists

register({
    "tab_spaces_sub": ("فضاهای شخصی تو", "Your personal spaces"),
    "count_items": ("{n} مورد", "{n} items"),
    "count_none": ("هنوز خالیه", "Empty for now"),
    "count_letters": ("{n} نامه‌ی مهر‌شده", "{n} sealed"),
    "count_letters_arrived": ("{n} نامه رسیده!", "{n} arrived!"),
    "spaces_hint": ("هر جایی که دلت می‌خواد بنویس؛ همه‌چیز فقط روی همین دستگاه می‌مونه.", "Write wherever your heart leads — everything stays on this device."),
})

ORDER = ["wishes", "wins", "god_talks", "prayers", "people", "hard_days"]


def _tile(app, c: kit.Ctx, coll: str):
    spec = lists.SPACES[coll]
    n = len(app.profile.items(coll))
    sub = c.t("count_items", n=c.n(n)) if n else c.t("count_none")
    inner = kit.col(c, [kit.badge(c, spec.icon, spec.tone, 46), kit.space(c, 4), kit.text(c, c.t(spec.title), 16, "bold", max_lines=2),
                        kit.text(c, sub, 12.5, color="muted")], spacing=2)
    return kit.card(c, inner, on_click=lambda e: app.push(lists.view, coll=coll), expand=True, padding=16)


def _letters_tile(app, c: kit.Ctx):
    from . import letters

    now = util.now()
    data = app.profile.data
    arrived = len(reminders.letters_in_state(data, now, "arrived"))
    sealed = len(reminders.letters_in_state(data, now, "sealed"))
    sub = c.t("count_letters_arrived", n=c.n(arrived)) if arrived else (c.t("count_letters", n=c.n(sealed)) if sealed else c.t("count_none"))
    inner = kit.col(c, [kit.badge(c, "MAIL", "accent", 46), kit.space(c, 4), kit.text(c, c.t("space_letters"), 16, "bold", max_lines=2),
                        kit.text(c, sub, 12.5, "medium" if arrived else "regular", "t_rose" if arrived else "muted")], spacing=2)
    return kit.card(c, inner, on_click=lambda e: app.push(letters.view), expand=True, padding=16)


def content(app, c: kit.Ctx):
    tiles = [_tile(app, c, k) for k in ORDER] + [_letters_tile(app, c)]
    rows = []
    for i in range(0, len(tiles), 2):
        pair = tiles[i:i + 2]
        if len(pair) == 1:
            pair.append(kit.box(c, None, expand=True))
        rows.append(kit.row(c, pair, spacing=12, v="start"))
    body = [kit.text(c, c.t("spaces_hint"), 13.5, color="muted"), *rows]
    return c.t("tab_spaces"), c.t("tab_spaces_sub"), [], body
