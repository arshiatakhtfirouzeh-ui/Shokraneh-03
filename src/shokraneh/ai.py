"""Optional online AI (Anthropic or any OpenAI-compatible endpoint) for the weekly / monthly messages.

* Standard library only (urllib + certifi if installed) so the Android build needs nothing extra.
* Everything here BLOCKS; the UI calls it from a worker thread.
* Nothing is ever sent unless the person turned the provider on, ticked the consent box and pasted a key.
  The offline coach (coach.py) is always the fallback.
"""
from __future__ import annotations

import ipaddress
import json
import re
import socket
import ssl
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import urlparse

from . import coach, content, jalali, util

PROVIDERS = ("offline", "anthropic", "openai")
PROVIDER_LABELS = {
    "offline": ("مربی آفلاین (بدون اینترنت)", "Offline coach (no internet)"),
    "anthropic": ("Claude (Anthropic)", "Claude (Anthropic)"),
    "openai": ("سازگار با OpenAI (یا سرور محلی)", "OpenAI-compatible (or local server)"),
}
DEFAULT_MODEL = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-4o-mini"}
DEFAULT_BASE = {"anthropic": "https://api.anthropic.com", "openai": "https://api.openai.com/v1"}
ANTHROPIC_VERSION = "2023-06-01"
TIMEOUT = 90
USER_AGENT = "Shokraneh/1.0 (+gratitude journal)"

ERROR_TEXT = {
    "config": ("تنظیمات هوش مصنوعی کامل نیست (کلید یا رضایت).", "AI settings are incomplete (key or consent)."),
    "url": ("نشانی سرویس معتبر نیست (باید با https شروع بشه).", "The service address is not valid (it must start with https)."),
    "auth": ("کلید API پذیرفته نشد. کلید رو دوباره بررسی کن.", "The API key was rejected. Please check the key."),
    "notfound": ("مدل یا نشانی پیدا نشد. اسم مدل و نشانی رو بررسی کن.", "Model or address not found. Check the model name and address."),
    "badrequest": ("سرویس درخواست رو نپذیرفت. اسم مدل رو بررسی کن.", "The service rejected the request. Check the model name."),
    "rate": ("سقف استفاده پر شده؛ کمی بعد دوباره امتحان کن.", "Usage limit reached; try again in a little while."),
    "server": ("سرویس موقتاً در دسترس نیست.", "The service is temporarily unavailable."),
    "timeout": ("پاسخ دیر رسید. اینترنت رو بررسی کن و دوباره تلاش کن.", "The reply took too long. Check your connection and retry."),
    "network": ("اتصال به اینترنت برقرار نشد.", "Could not connect to the internet."),
    "parse": ("پاسخ هوش مصنوعی قابل خوندن نبود.", "The AI reply could not be read."),
    "http": ("خطای ناشناخته از سرویس.", "Unknown error from the service."),
}


class AIError(Exception):
    def __init__(self, code: str, detail: str = ""):
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail

    def text(self, lang: str) -> str:
        return error_text(self.code, lang)


def error_text(code: str, lang: str) -> str:
    pair = ERROR_TEXT.get(code) or ERROR_TEXT["http"]
    return pair[0] if lang == "fa" else pair[1]


# --------------------------------------------------------------------------- config helpers
def _is_local(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return False
    if host == "localhost" or host.endswith(".local"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_loopback or ip.is_private
    except ValueError:
        return False


def effective(cfg: dict) -> dict:
    """The cfg with defaults filled in."""
    cfg = cfg or {}
    provider = cfg.get("provider") if cfg.get("provider") in PROVIDERS else "offline"
    return {
        "provider": provider,
        "api_key": str(cfg.get("api_key") or "").strip(),
        "model": str(cfg.get("model") or "").strip() or DEFAULT_MODEL.get(provider, ""),
        "base_url": str(cfg.get("base_url") or "").strip() or DEFAULT_BASE.get(provider, ""),
        "consent": bool(cfg.get("consent")),
    }


def is_ready(cfg: dict) -> bool:
    c = effective(cfg)
    if c["provider"] == "offline" or not c["consent"]:
        return False
    if c["provider"] == "anthropic":
        return bool(c["api_key"])
    return bool(c["api_key"]) or _is_local(c["base_url"])  # local servers (Ollama, LM Studio) need no key


def _check_url(url: str) -> None:
    p = urlparse(url)
    if p.scheme == "https" and p.hostname:
        return
    if p.scheme == "http" and p.hostname and _is_local(url):
        return
    raise AIError("url", url)


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # type: ignore

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


# --------------------------------------------------------------------------- HTTP
def _http_code(status: int) -> str:
    if status in (401, 403):
        return "auth"
    if status in (404, 410):
        return "notfound"
    if status in (400, 422):
        return "badrequest"
    if status == 429:
        return "rate"
    if status >= 500:
        return "server"
    return "http"


def _error_detail(err: urllib.error.HTTPError) -> str:
    try:
        raw = err.read().decode("utf-8", "replace")
    except Exception:
        return ""
    try:
        obj = json.loads(raw)
        e = obj.get("error", obj) if isinstance(obj, dict) else obj
        if isinstance(e, dict):
            return str(e.get("message") or e.get("type") or "")[:300]
        return str(e)[:300]
    except ValueError:
        return raw[:300]


def _post(url: str, headers: dict, body: dict, timeout: float = TIMEOUT) -> Any:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json", "User-Agent": USER_AGENT, **headers},
    )
    kwargs: dict[str, Any] = {"timeout": timeout}
    if url.lower().startswith("https"):
        kwargs["context"] = _ssl_context()
    try:
        with urllib.request.urlopen(req, **kwargs) as resp:  # noqa: S310 - scheme validated by _check_url
            raw = resp.read()
    except urllib.error.HTTPError as e:
        raise AIError(_http_code(e.code), _error_detail(e)) from None
    except urllib.error.URLError as e:
        if isinstance(e.reason, (socket.timeout, TimeoutError)):
            raise AIError("timeout") from None
        raise AIError("network", str(e.reason)) from None
    except (socket.timeout, TimeoutError):
        raise AIError("timeout") from None
    except (OSError, ValueError) as e:
        raise AIError("network", str(e)) from None
    try:
        return json.loads(raw.decode("utf-8"))
    except ValueError:
        raise AIError("parse", "the service did not return JSON") from None


def _endpoint(base: str, tail: str, version_prefix: str) -> str:
    """Join base + tail while tolerating bases that already end with the version or the full endpoint."""
    base = base.rstrip("/")
    if base.endswith(tail):
        return base
    if version_prefix and base.endswith("/" + version_prefix):
        return f"{base}/{tail}"
    if version_prefix:
        return f"{base}/{version_prefix}/{tail}"
    return f"{base}/{tail}"


def complete(cfg: dict, system: str, user: str, max_tokens: int = 2500) -> str:
    """One blocking chat completion; returns the model's text."""
    c = effective(cfg)
    if c["provider"] == "offline":
        raise AIError("config")
    _check_url(c["base_url"])
    if c["provider"] == "anthropic":
        if not c["api_key"]:
            raise AIError("config")
        out = _post(
            _endpoint(c["base_url"], "messages", "v1"),
            {"x-api-key": c["api_key"], "anthropic-version": ANTHROPIC_VERSION},
            {
                "model": c["model"],
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        parts = out.get("content") if isinstance(out, dict) else None
        text = "".join(p.get("text", "") for p in (parts or []) if isinstance(p, dict) and p.get("type") == "text")
    else:  # OpenAI-compatible: no max_tokens / temperature on purpose (newer models reject them)
        headers = {"Authorization": f"Bearer {c['api_key']}"} if c["api_key"] else {}
        out = _post(
            _endpoint(c["base_url"], "chat/completions", ""),
            headers,
            {
                "model": c["model"],
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
        )
        choices = out.get("choices") if isinstance(out, dict) else None
        msg = (choices[0] or {}).get("message") if choices else None
        text = (msg or {}).get("content") or ""
        if isinstance(text, list):  # some servers return content parts
            text = "".join(p.get("text", "") for p in text if isinstance(p, dict))
    if not str(text).strip():
        raise AIError("parse", "empty reply")
    return str(text)


def ping(cfg: dict) -> str:
    """Tiny round-trip used by Settings → 'Test connection'. Returns the reply (shortened)."""
    return util.shorten(complete(cfg, "You are a connectivity test.", "Reply with the single word: ok", max_tokens=16), 60)


# --------------------------------------------------------------------------- reply parsing
_FENCE_OPEN = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*")
_FENCE_CLOSE = re.compile(r"\s*```\s*$")


def extract_json(text: str) -> Any | None:
    t = _FENCE_CLOSE.sub("", _FENCE_OPEN.sub("", text.strip())).strip()
    try:
        return json.loads(t)
    except ValueError:
        pass
    start = t.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(t)):
            ch = t[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(t[start : i + 1])
                    except ValueError:
                        break
        start = t.find("{", start + 1)
    return None


def _clean(x: Any, limit: int) -> str:
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        x = str(x)
    if not isinstance(x, str):
        return ""
    s = re.sub(r"\s+\n", "\n", x.replace("\r", "")).strip()
    return s[:limit]


def normalize_report(obj: Any, default_title: str = "") -> dict:
    if not isinstance(obj, dict):
        raise AIError("parse", "not an object")
    sections: list[dict] = []
    for s in obj.get("sections") or []:
        if not isinstance(s, dict):
            continue
        h = _clean(s.get("h") or s.get("heading") or s.get("title"), 80)
        text = _clean(s.get("text") or s.get("body"), 1600)
        raw_items = s.get("items") or s.get("bullets") or []
        items = [_clean(i, 500) for i in raw_items] if isinstance(raw_items, list) else []
        items = [i for i in items if i][:8]
        sec: dict[str, Any] = {}
        if h:
            sec["h"] = h
        if text:
            sec["text"] = text
        if items:
            sec["items"] = items
        if "text" in sec or "items" in sec:
            sections.append(sec)
    if not sections:
        raise AIError("parse", "no sections")
    return {"title": _clean(obj.get("title"), 120) or default_title, "sections": sections[:8], "source": "ai"}


def parse_reply(text: str, default_title: str = "") -> dict:
    obj = extract_json(text)
    if obj is None:
        raise AIError("parse", "no JSON found")
    return normalize_report(obj, default_title)


# --------------------------------------------------------------------------- prompts
_LANG_NAME = {"fa": "Persian (Farsi) — natural, warm, polite everyday Persian, not stiff or bookish", "en": "English"}

_SCHEMA = (
    'Return ONLY valid JSON, no markdown fences, in exactly this shape: '
    '{"title": string, "sections": [{"h": string, "text": string} or {"h": string, "items": [string, ...]}]}.'
)

_RULES = (
    "Rules: be kind, but do not flatter. Only use facts that are in the JSON; never invent events, people or numbers. "
    "You are a journaling coach, not a doctor: no diagnosis, no medical or medication advice. "
    "Keep every item short and concrete. Quote the person's own words sparingly and exactly. "
    "If safety_flag is true, keep your tone especially gentle, leave out criticism, and do not mention the flag or quote "
    "any worrying text — the app adds its own support note."
)


def _pair(p) -> dict | None:
    return {"day": p[0].isoformat(), "score": p[1]} if p else None


def _series(series) -> list[list]:
    return [[d.isoformat(), s] for d, s in series if s is not None]


def _entries(texts: list[dict], lang: str, budget: int = 6500) -> tuple[dict, list[dict]]:
    legend: dict[str, str] = {}
    rows: list[dict] = []
    used = 0
    for t in sorted(texts, key=lambda x: (x["day"], x["kind"], x["qid"])):
        q = content.question_by_id(t["qid"])
        ans = " | ".join(util.shorten(i, 160) for i in t["items"])
        size = len(ans) + 28
        if q and t["qid"] not in legend:
            size += len(q.title(lang))
        if used + size > budget:
            break
        used += size
        if q:
            legend.setdefault(t["qid"], q.title(lang))
        rows.append({"d": t["day"].isoformat(), "q": t["qid"], "a": ans})
    return legend, rows


def weekly_payload(dg: dict, lang: str, name: str = "") -> dict:
    legend, rows = _entries(dg["texts"], lang)
    return {
        "person": name or None,
        "week": {"start": dg["start"].isoformat(), "end": dg["end"].isoformat(), "days": dg["days"]},
        "counts": {
            "morning_entries": dg["morning_days"],
            "night_entries": dg["night_days"],
            "energy_logged_days": dg["energy_days"],
            "good_deed_days": dg["deed_days"],
            "achievements_added": dg["wins_added"],
            "wishes_fulfilled": dg["wishes_done"],
            "hard_days": len(dg["hard_days"]),
            "lessons_written": dg["lessons"],
            "talks_with_god": dg["god_talks"],
            "activity_streak_days": dg["streak"],
        },
        "energy_1_to_10": {
            "average": dg["avg"],
            "best": _pair(dg["best"]),
            "worst": _pair(dg["worst"]),
            "second_half_minus_first_half": dg["delta"],
            "daily": _series(dg["series"]),
            "tags_on_low_days": [{"tag": t, "days": c} for t, c in dg["low_tags"]],
        },
        "writing": {
            "avg_words_per_answer": dg["avg_words"],
            "share_of_one_word_list_items": round(dg["generic_ratio"], 2),
            "repeated_gratitude_items": [{"text": t, "times": c} for t, c in dg["repeats"]],
            "answers_per_question": dg["answered"],
        },
        "hard_days": [
            {"what": util.shorten(str(h.get("what") or h.get("title") or ""), 140), "lesson": util.shorten(str(h.get("lesson") or ""), 160)}
            for h in dg["hard_days"][:4]
        ],
        "loved_ones_not_contacted_for_3_weeks": len(dg["neglected"]),
        "safety_flag": bool(dg["safety"]),
        "question_legend": legend,
        "entries": rows,
    }


def month_payload(ms: dict, lang: str, name: str = "") -> dict:
    s = ms["summary"]
    wd = {jalali.WEEKDAYS["en"][i]: v for i, v in ms["weekday"].items()}
    tag_effects = [{"tag": content.TAGS[t["tag"]][1], "avg_energy_difference": t["delta"], "days_tagged": t["n"]} for t in ms["tags"]]
    habit_names = {"morning": "wrote morning gratitude", "prev_night": "wrote the night review the evening before", "deed": "wrote a good deed"}
    habits = [{"habit": habit_names.get(e["key"], e["key"]), "avg_energy_difference": e["delta"], "days": e["n"]} for e in ms["effects"]]
    return {
        "person": name or None,
        "month": {"start": ms["start"].isoformat(), "end": ms["end"].isoformat(), "days": ms["days"]},
        "energy_1_to_10": {
            "logged_days": s["logged"],
            "average": s["avg"],
            "best": _pair(s["best"]),
            "worst": _pair(s["worst"]),
            "std_dev": s.get("stdev"),
            "previous_month_average": ms.get("prev_avg"),
            "daily": _series(ms["series"]),
        },
        "average_energy_by_weekday": wd,
        "tag_effects": tag_effects,
        "habit_effects": habits,
        "journaling": {
            "morning_entries": ms["morning_days"],
            "night_entries": ms["night_days"],
            "hard_days": ms["hard_days"],
            "lessons_written": ms["lessons"],
        },
        "several_very_low_days_recently": bool(ms.get("low_streak")),
        "safety_flag": bool(ms.get("safety")),
    }


def weekly_prompt(dg: dict, lang: str, name: str = "") -> tuple[str, str]:
    system = (
        "You are a warm, honest journaling coach inside a gratitude-journal app. You receive a JSON summary of one "
        "person's past week (energy scores 1-10, counts, and what they wrote). "
        f"Write a short weekly message addressed to the person as \"you\", in {_LANG_NAME[lang]}. "
        "Use 5 sections: (1) a short overview of the week; (2) what went well, 2-4 items; "
        "(3) honest, constructive criticism, 2-4 items — name specific patterns such as vague or repeated answers, skipped questions, "
        "avoided topics or habits linked to low-energy days, and say how to improve each; "
        "(4) next week's plan, exactly 3 small concrete steps; (5) one warm closing line. "
        + _RULES
        + " "
        + _SCHEMA
    )
    return system, json.dumps(weekly_payload(dg, lang, name), ensure_ascii=False)


def monthly_prompt(ms: dict, lang: str, name: str = "") -> tuple[str, str]:
    system = (
        "You are a warm, honest wellbeing-journaling coach inside a gratitude-journal app. You receive a JSON summary of one "
        "person's month: daily energy/mood scores (1-10), weekday averages, how tagged activities and journaling habits relate "
        "to their energy, and counts. "
        f"Write a monthly review addressed to the person as \"you\", in {_LANG_NAME[lang]}. "
        "Use 4 sections: (1) an overview of the month and the trend versus last month if available; "
        "(2) patterns you can actually see in the numbers (say they are patterns, not proof); "
        "(3) 4-6 practical suggestions to improve their daily mood and energy, each tied to something in their data "
        "(small, specific, doable this week — sleep, daylight, movement, rest, connection, planning around low weekdays, and so on); "
        "(4) one warm closing line. "
        + _RULES
        + " "
        + _SCHEMA
    )
    return system, json.dumps(month_payload(ms, lang, name), ensure_ascii=False)


# --------------------------------------------------------------------------- public generators
def generate_weekly(cfg: dict, dg: dict, lang: str, name: str = "", jal: bool = True) -> dict:
    lang = "fa" if lang == "fa" else "en"
    system, user = weekly_prompt(dg, lang, name)
    return parse_reply(complete(cfg, system, user), coach.weekly_title(dg["start"], dg["end"], lang, jal))


def generate_monthly(cfg: dict, ms: dict, lang: str, name: str = "", jal: bool = True) -> dict:
    lang = "fa" if lang == "fa" else "en"
    system, user = monthly_prompt(ms, lang, name)
    return parse_reply(complete(cfg, system, user), coach.monthly_title(ms["start"], lang, jal))
