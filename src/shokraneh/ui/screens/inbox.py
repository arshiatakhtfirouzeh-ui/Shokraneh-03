"""Messages tab (weekly report / monthly review) and the shared renderer for report sections."""
from __future__ import annotations

from typing import Any

from ... import ai, reports
from ...i18n import register
from .. import compat as C
from .. import kit
from . import lists

register({
    "tab_inbox_sub": ("گزارش‌ها و پیام‌های هوشمند", "Reports and smart messages"),
    "inbox_weekly_btn": ("گزارش این هفته", "This week's report"),
    "inbox_monthly_btn": ("مرور این ماه", "This month's review"),
    "inbox_empty_t": ("هنوز پیامی نداری", "No messages yet"),
    "inbox_empty_b": ("هر هفته یه گزارش خلاصه و صادقانه از نوشته‌هات اینجا می‌رسه؛ می‌تونی همین حالا هم یکی بسازی.",
                      "Each week a short, honest report on what you wrote arrives here — you can also create one right now."),
    "msg_ai": ("هوش مصنوعی", "AI"),
    "msg_offline": ("مربی آفلاین", "Offline coach"),
    "msg_partial": ("هنوز در جریانه", "In progress"),
    "msg_writing": ("در حال نوشتن…", "Writing…"),
    "msg_ai_failed": ("هوش مصنوعی در دسترس نبود، برای همین خلاصه‌ی آفلاین نشون داده شد. {why}", "AI wasn't available, so the offline summary is shown. {why}"),
    "msg_retry_ai": ("دوباره با هوش مصنوعی", "Retry with AI"),
    "msg_regenerate": ("بازنویسی", "Regenerate"),
    "msg_ai_off_hint": ("برای گزارش‌های دقیق‌تر می‌تونی هوش مصنوعی رو در تنظیمات روشن کنی.", "For richer reports you can turn on AI in Settings."),
    "msg_ai_on_hint": ("هوش مصنوعی روشنه و گزارش‌ها رو می‌نویسه.", "AI is on and writes your reports."),
    "msg_kind_weekly": ("گزارش هفتگی", "Weekly report"),
    "msg_kind_monthly": ("مرور ماهانه", "Monthly review"),
    "msg_missing": ("این پیام پیدا نشد.", "This message could not be found."),
    "toast_report_ready": ("آماده شد ✨", "Ready ✨"),
})


def render_sections(c: kit.Ctx, sections: list[dict]) -> list[Any]:
    """Report sections -> cards (heading + paragraph / bullet list). A section without a heading is a closing line."""
    out: list[Any] = []
    for s in sections:
        head = s.get("h")
        parts: list[Any] = [kit.text(c, head, 16, "bold")] if head else []
        if s.get("text"):
            parts.append(kit.text(c, s["text"], 15 if head else 14.5, color="text" if head else "muted", selectable=True, italic=not head))
        for it in s.get("items", []):
            dot = kit.box(c, kit.box(c, None, width=6, height=6, radius=3, bg="accent"), padding=C.pad(0, 8, 0, 0))
            parts.append(kit.row(c, [dot, kit.text(c, it, 14.5, expand=True, selectable=True)], spacing=10, v="start"))
        if not parts:
            continue
        out.append(kit.card(c, kit.col(c, parts, spacing=10), padding=18) if head else kit.box(c, kit.col(c, parts), padding=C.pad(8, 4, 8, 4)))
    return out


def source_pill(c: kit.Ctx, msg: dict) -> Any:
    ai_made = msg.get("source") == "ai"
    return kit.pill(c, c.t("msg_ai" if ai_made else "msg_offline"), "lavender" if ai_made else "sage")


def _generate(app, kind: str) -> None:
    st = app.state()
    if st.get("busy"):
        return
    st["busy"] = True
    app.refresh()
    p, lang, jal, ws, name, today = app.profile, app.lang, app.jal, app.week_start, app.profile.name, app.today()

    def done(msg: Any, err: Exception | None) -> None:
        st["busy"] = False
        app.toast(app.t("toast_report_ready") if err is None else app.t("error_generic"), error=err is not None)
        app.refresh()

    app.bg(lambda: reports.generate_now(p, kind, today, lang, jal, ws, name), done=done)


def content(app, c: kit.Ctx):
    p = app.profile
    st = app.state()
    busy = bool(st.get("busy"))
    ready = ai.is_ready(p.setting("ai") or {})
    msgs = sorted(p.items("messages"), key=lambda m: m.get("updated") or m.get("created") or "", reverse=True)
    body: list[Any] = [kit.row(c, [
        kit.button(c, c.t("msg_writing") if busy else c.t("inbox_weekly_btn"), lambda e: _generate(app, "weekly"), "soft", "AUTO_AWESOME", expand=True, disabled=busy),
        kit.button(c, c.t("inbox_monthly_btn"), lambda e: _generate(app, "monthly"), "soft", "INSIGHTS", expand=True, disabled=busy)], spacing=10),
        kit.text(c, c.t("msg_ai_on_hint" if ready else "msg_ai_off_hint"), 12.5, color="muted")]
    if not msgs:
        body.append(kit.empty(c, "MAIL_OUTLINE", c.t("inbox_empty_t"), c.t("inbox_empty_b")))
    for m in msgs:
        kind = c.t("msg_kind_monthly" if m.get("kind") == "monthly" else "msg_kind_weekly")
        sub = f"{kind} · {c.t('msg_ai') if m.get('source') == 'ai' else c.t('msg_offline')}"
        if m.get("partial"):
            sub += f" · {c.t('msg_partial')}"
        dot = kit.box(c, None, width=10, height=10, radius=5, bg="bad") if not m.get("read") else None
        body.append(kit.tile(c, m.get("title", ""), sub, "INSIGHTS" if m.get("kind") == "monthly" else "AUTO_AWESOME",
                             "lavender" if m.get("source") == "ai" else "sky", trailing=dot, on_click=lambda e, i=m["id"]: app.push(message, msg_id=i)))
    return c.t("tab_inbox"), c.t("tab_inbox_sub"), [], body


def message(app, msg_id: str):
    c = app.ctx()
    p = app.profile
    m = p.get_item("messages", msg_id)
    if m is None:
        return kit.screen(c, [kit.empty(c, "MAIL_OUTLINE", c.t("inbox_empty_t"), c.t("msg_missing"))], title=c.t("tab_inbox"), on_back=app.pop)
    if not m.get("read"):
        p.mark_read(msg_id)
    st = app.state()
    busy = bool(st.get("busy"))
    ready = ai.is_ready(p.setting("ai") or {})
    lang, jal, name, today = app.lang, app.jal, p.name, app.today()

    def regenerate() -> None:
        st["busy"] = True
        app.refresh()

        def done(msg: Any, err: Exception | None) -> None:
            st["busy"] = False
            if err is not None:
                app.toast(app.t("error_generic"), error=True)
            app.refresh()

        app.bg(lambda: reports.regenerate(p, msg_id, today, lang, jal, name), done=done)

    def delete() -> None:
        p.delete_item("messages", msg_id)
        app.toast(c.t("deleted"))
        app.pop()

    meta = [source_pill(c, m)]
    if m.get("partial"):
        meta.append(kit.pill(c, c.t("msg_partial"), "warn"))
    body: list[Any] = [kit.row(c, meta, spacing=8), *render_sections(c, m.get("sections", []))]
    if m.get("ai_error"):
        why = ai.error_text(m["ai_error"], lang)
        body.append(kit.card(c, kit.row(c, [kit.icon(c, "INFO_OUTLINE", 20, "t_warn"), kit.text(c, c.t("msg_ai_failed", why=why), 13, color="muted", expand=True)],
                                        spacing=10, v="start"), bg="t_warn_soft", border=False))
    retry = bool(m.get("ai_error")) and ready
    body.append(kit.button(c, c.t("msg_writing") if busy else c.t("msg_retry_ai" if retry else "msg_regenerate"), lambda e: regenerate(), "soft", "REFRESH",
                           expand=True, disabled=busy))
    actions = [kit.icon_button(c, "DELETE_OUTLINE", lambda e: app.confirm(c.t("confirm_delete_title"), c.t("confirm_delete_body"), delete, c.t("delete"), danger=True),
                               "muted", 22, c.t("delete"))]
    return kit.screen(c, body, title=m.get("title", ""), subtitle=lists.day_text(c, m.get("updated") or m.get("created"), "medium"), on_back=app.pop, actions=actions)
