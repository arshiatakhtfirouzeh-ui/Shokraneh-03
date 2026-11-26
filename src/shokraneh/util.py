"""Small dependency-free helpers shared across the app (no Flet imports)."""
from __future__ import annotations

import hashlib
import re
import secrets
import unicodedata
from datetime import date, datetime, timedelta
from typing import Iterator

DAY_START_HOUR = 3  # entries written before 03:00 still belong to "yesterday"

_FA = "۰۱۲۳۴۵۶۷۸۹"
_AR = "٠١٢٣٤٥٦٧٨٩"
_EN = "0123456789"
_TO_FA = str.maketrans(_EN, _FA)
_TO_EN = str.maketrans(_FA + _AR, _EN + _EN)

_AR_TO_FA = str.maketrans(
    {"ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه", "ە": "ه", "ة": "ه", "أ": "ا", "إ": "ا", "ٱ": "ا", "ؤ": "و"}
)
_DIACRITICS = re.compile("[ً-ٰٟۖ-ۭـ]")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)


def uid(prefix: str = "") -> str:
    """Short random id such as 'w_3fa91c0b2d'."""
    return f"{prefix}{secrets.token_hex(5)}"


def to_fa_digits(value) -> str:
    return str(value).translate(_TO_FA)


def to_en_digits(value) -> str:
    return str(value).translate(_TO_EN)


def digits(value, lang: str) -> str:
    """Render numbers with Persian digits when the UI language is Persian."""
    return to_fa_digits(value) if lang == "fa" else str(value)


def now() -> datetime:
    return datetime.now().replace(microsecond=0)


def logical_today(at: datetime | None = None, start_hour: int = DAY_START_HOUR) -> date:
    """The journaling 'day' for a moment in time (day rolls over at 03:00)."""
    at = at or datetime.now()
    return (at - timedelta(hours=start_hour)).date()


def iso_day(d: date) -> str:
    return d.isoformat()


def parse_day(s: str) -> date:
    return date.fromisoformat(s)


def parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def daterange(start: date, end: date) -> Iterator[date]:
    """Inclusive range of days."""
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def parse_hhmm(s, default: tuple[int, int] = (8, 0)) -> tuple[int, int]:
    try:
        h, m = to_en_digits(s).strip().split(":")
        h, m = int(h), int(m)
        if 0 <= h < 24 and 0 <= m < 60:
            return h, m
    except (ValueError, AttributeError):
        pass
    return default


def fmt_hhmm(h: int, m: int) -> str:
    return f"{h:02d}:{m:02d}"


def stable_int(key: str, mod: int = 2_000_000_000) -> int:
    """Deterministic positive int for a string (used as notification id)."""
    return int.from_bytes(hashlib.sha1(key.encode("utf-8")).digest()[:6], "big") % mod


def norm_text(s: str | None) -> str:
    """Normalize Persian/Arabic/English text for comparisons and keyword stats."""
    s = unicodedata.normalize("NFKC", s or "")
    s = s.translate(_AR_TO_FA).translate(_TO_EN)
    s = _DIACRITICS.sub("", s)
    s = s.replace("‌", "").replace("‍", "")
    s = _PUNCT.sub(" ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str | None) -> list[str]:
    return norm_text(s).split()


def shorten(s: str, limit: int = 140) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= limit else s[: limit - 1].rstrip() + "…"
