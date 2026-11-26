"""When weekly / monthly messages are due, and how they are built and stored.

Pure logic + blocking calls: run `run_pending` / `generate_now` / `regenerate` from a worker thread.
AI first when the person enabled it, otherwise (or on any AI failure) the offline coach.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from . import ai, analytics, coach, jalali, util

KINDS = ("weekly", "monthly")


# --------------------------------------------------------------------------- periods
def week_bounds(day: date, week_start: int) -> tuple[date, date]:
    s = jalali.week_start_of(day, week_start)
    return s, s + timedelta(days=6)


def last_complete_week(today: date, week_start: int) -> tuple[date, date]:
    s, _ = week_bounds(today, week_start)
    return s - timedelta(days=7), s - timedelta(days=1)


def week_key(start: date) -> str:
    return "W" + start.isoformat()


def month_key(start: date, jal: bool) -> str:
    y, m, _ = jalali.ymd(start, jal)
    return f"{'J' if jal else 'G'}{y:04d}-{m:02d}"


def last_complete_month(today: date, jal: bool) -> tuple[date, date]:
    first, _ = jalali.month_bounds(today, jal)
    return jalali.month_bounds(jalali.shift_month(first, -1, jal), jal)


def previous_month(start: date, jal: bool) -> tuple[date, date]:
    return jalali.month_bounds(jalali.shift_month(start, -1, jal), jal)


def has_activity(data: dict, start: date, end: date) -> bool:
    return any(analytics.entries_between(data, k, start, end) for k in ("morning", "night", "energy"))


def find_message(data: dict, kind: str, period: str) -> dict | None:
    return next((m for m in data.get("messages", []) if m.get("kind") == kind and m.get("period") == period), None)


def pending(data: dict, today: date, jal: bool, week_start: int) -> list[dict]:
    """Finished periods that have activity but no final message yet (partial ones are rebuilt)."""
    out: list[dict] = []
    ws, we = last_complete_week(today, week_start)
    key = week_key(ws)
    m = find_message(data, "weekly", key)
    if (m is None or m.get("partial")) and has_activity(data, ws, we):
        out.append({"kind": "weekly", "start": ws, "end": we, "period": key})
    ms, me = last_complete_month(today, jal)
    key = month_key(ms, jal)
    m = find_message(data, "monthly", key)
    if (m is None or m.get("partial")) and has_activity(data, ms, me):
        out.append({"kind": "monthly", "start": ms, "end": me, "period": key})
    return out


# --------------------------------------------------------------------------- views
def month_overview(data: dict, day: date, jal: bool, today: date | None = None) -> dict:
    """Stats of the month containing `day` (for the Progress screen)."""
    start, end = jalali.month_bounds(day, jal)
    return analytics.month_stats(data, start, end, prev=previous_month(start, jal), today=today or day)


# --------------------------------------------------------------------------- building
def _ai_cfg(data: dict) -> dict:
    return (data.get("settings") or {}).get("ai") or {}


def _with_safety(rep: dict, safety: bool, lang: str) -> dict:
    """Online replies never write the support note themselves; the app appends a fixed, calm one."""
    if safety and rep.get("source") == "ai":
        note = {"h": coach.heading("note", lang), "text": coach._f("safety", lang)}
        rep = {**rep, "sections": [*rep["sections"], note]}
    return rep


def build_weekly(data: dict, start: date, end: date, today: date, lang: str, jal: bool, name: str = "", use_ai: bool = True) -> tuple[dict, str]:
    """-> (report, ai_error_code). The code is '' when no AI was attempted or it worked."""
    lang = "fa" if lang == "fa" else "en"
    dg = analytics.week_digest(data, start, end, today)
    cfg = _ai_cfg(data)
    err = ""
    rep = None
    if use_ai and ai.is_ready(cfg):
        try:
            rep = ai.generate_weekly(cfg, dg, lang, name, jal)
        except ai.AIError as e:
            err = e.code
        except Exception:  # never let a provider hiccup break the app
            err = "http"
    if rep is None:
        rep = coach.weekly_report(dg, lang, name, jal)
    return _with_safety(rep, dg["safety"], lang), err


def build_monthly(data: dict, start: date, end: date, today: date, lang: str, jal: bool, name: str = "", use_ai: bool = True) -> tuple[dict, str]:
    lang = "fa" if lang == "fa" else "en"
    ms = analytics.month_stats(data, start, end, prev=previous_month(start, jal), today=today)
    cfg = _ai_cfg(data)
    err = ""
    rep = None
    if use_ai and ai.is_ready(cfg):
        try:
            rep = ai.generate_monthly(cfg, ms, lang, name, jal)
        except ai.AIError as e:
            err = e.code
        except Exception:
            err = "http"
    if rep is None:
        rep = coach.monthly_review(ms, lang, name, jal)
    return _with_safety(rep, ms["safety"], lang), err


def build(kind: str, data: dict, start: date, end: date, today: date, lang: str, jal: bool, name: str = "", use_ai: bool = True) -> tuple[dict, str]:
    fn = build_weekly if kind == "weekly" else build_monthly
    return fn(data, start, end, today, lang, jal, name, use_ai)


# --------------------------------------------------------------------------- storing
def save(profile, kind: str, period: str, report: dict, start: date, end: date, partial: bool = False, ai_error: str = "") -> dict:
    fields: dict[str, Any] = {
        "title": report["title"],
        "sections": report["sections"],
        "source": report.get("source", "offline"),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "partial": partial,
        "ai_error": ai_error,
        "updated": util.now().isoformat(),
    }
    existing = profile.message_for_period(kind, period)
    if existing:
        profile.update_item("messages", existing["id"], read=False, **fields)
        return profile.get_item("messages", existing["id"])
    return profile.add_message(
        kind, fields.pop("title"), fields.pop("sections"), fields.pop("source"), period, **fields
    )


# --------------------------------------------------------------------------- entry points (blocking)
def run_pending(profile, today: date, lang: str, jal: bool, week_start: int, name: str = "", use_ai: bool = True) -> list[dict]:
    data = profile.snapshot()
    made = []
    for p in pending(data, today, jal, week_start):
        rep, err = build(p["kind"], data, p["start"], p["end"], today, lang, jal, name, use_ai)
        made.append(save(profile, p["kind"], p["period"], rep, p["start"], p["end"], False, err))
    return made


def generate_now(profile, kind: str, today: date, lang: str, jal: bool, week_start: int, name: str = "", use_ai: bool = True,
                 day: date | None = None) -> dict:
    """Report for the week / month containing `day` (default: today); flagged partial until the period is over."""
    data = profile.snapshot()
    day = day or today
    if kind == "weekly":
        start, full_end = week_bounds(day, week_start)
        end, period = min(full_end, today), week_key(start)
    else:
        start, full_end = jalali.month_bounds(day, jal)
        end, period = full_end, month_key(start, jal)
    rep, err = build(kind, data, start, end, today, lang, jal, name, use_ai)
    return save(profile, kind, period, rep, start, full_end, partial=today <= full_end, ai_error=err)


def regenerate(profile, msg_id: str, today: date, lang: str, jal: bool, name: str = "", use_ai: bool = True) -> dict | None:
    """Rebuild a stored message (e.g. 'retry with AI' or after changing language)."""
    msg = profile.get_item("messages", msg_id)
    if not msg or msg.get("kind") not in KINDS:
        return None
    start, full_end = util.parse_day(msg["start"]), util.parse_day(msg["end"])
    data = profile.snapshot()
    end = min(full_end, today) if msg["kind"] == "weekly" else full_end
    rep, err = build(msg["kind"], data, start, end, today, lang, jal, name, use_ai)
    return save(profile, msg["kind"], msg["period"], rep, start, full_end, partial=today <= full_end, ai_error=err)
