"""Jalali (Solar Hijri) calendar arithmetic and localized date formatting."""
from __future__ import annotations

from datetime import date, timedelta

_G_D_M = (0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334)


def gregorian_to_jalali(gy: int, gm: int, gd: int) -> tuple[int, int, int]:
    gy2 = gy + 1 if gm > 2 else gy
    days = (
        355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + _G_D_M[gm - 1]
    )
    jy = -1595 + 33 * (days // 12053)
    days %= 12053
    jy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        jy += (days - 1) // 365
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + days // 31
        jd = 1 + days % 31
    else:
        jm = 7 + (days - 186) // 30
        jd = 1 + (days - 186) % 30
    return jy, jm, jd


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> tuple[int, int, int]:
    jy += 1595
    days = (
        -355668
        + 365 * jy
        + (jy // 33) * 8
        + ((jy % 33) + 3) // 4
        + jd
        + ((jm - 1) * 31 if jm < 7 else ((jm - 7) * 30) + 186)
    )
    gy = 400 * (days // 146097)
    days %= 146097
    if days > 36524:
        days -= 1
        gy += 100 * (days // 36524)
        days %= 36524
        if days >= 365:
            days += 1
    gy += 4 * (days // 1461)
    days %= 1461
    if days > 365:
        gy += (days - 1) // 365
        days = (days - 1) % 365
    gd = days + 1
    leap = (gy % 4 == 0 and gy % 100 != 0) or gy % 400 == 0
    sal_a = (0, 31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    gm = 0
    while gm < 13 and gd > sal_a[gm]:
        gd -= sal_a[gm]
        gm += 1
    return gy, gm, gd


def to_jalali(d: date) -> tuple[int, int, int]:
    return gregorian_to_jalali(d.year, d.month, d.day)


def from_jalali(jy: int, jm: int, jd: int) -> date:
    return date(*jalali_to_gregorian(jy, jm, jd))


def is_leap(jy: int) -> bool:
    """True when Esfand has 30 days in Jalali year `jy`."""
    return gregorian_to_jalali(*jalali_to_gregorian(jy, 12, 30)) == (jy, 12, 30)


def month_len(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_leap(jy) else 29


# --------------------------------------------------------------------------- names
J_MONTHS = {
    "fa": ("فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"),
    "en": ("Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar", "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand"),
}
G_MONTHS = {
    "fa": ("ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن", "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"),
    "en": ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"),
}
G_MONTHS_SHORT_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
# indexed by Python's date.weekday(): Monday=0 ... Sunday=6
WEEKDAYS = {
    "fa": ("دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"),
    "en": ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"),
}
WEEKDAYS_SHORT = {
    "fa": ("د", "س", "چ", "پ", "ج", "ش", "ی"),
    "en": ("Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"),
}


def use_jalali(lang: str, cal: str) -> bool:
    return cal == "jalali" or (cal == "auto" and lang == "fa")


def default_week_start(jalali: bool) -> int:
    """Python weekday number of the first day of the week (Saturday=5, Monday=0)."""
    return 5 if jalali else 0


def ymd(d: date, jalali: bool) -> tuple[int, int, int]:
    return to_jalali(d) if jalali else (d.year, d.month, d.day)


def month_name(m: int, lang: str, jalali: bool, short: bool = False) -> str:
    lang = lang if lang in ("fa", "en") else "en"
    if jalali:
        return J_MONTHS[lang][m - 1]
    if short and lang == "en":
        return G_MONTHS_SHORT_EN[m - 1]
    return G_MONTHS[lang][m - 1]


def weekday_name(d: date, lang: str, short: bool = False) -> str:
    lang = lang if lang in ("fa", "en") else "en"
    return (WEEKDAYS_SHORT if short else WEEKDAYS)[lang][d.weekday()]


def _digits(v, lang: str) -> str:
    from .util import digits

    return digits(v, lang)


def format_day(d: date, lang: str, jalali: bool, style: str = "long") -> str:
    """style: long | medium | short | dm (day + month) | weekday."""
    y, m, dd = ymd(d, jalali)
    if style == "weekday":
        return weekday_name(d, lang)
    if style == "short":
        return _digits(f"{y}/{m:02d}/{dd:02d}", lang) if (lang == "fa" or jalali) else f"{y}-{m:02d}-{dd:02d}"
    mon = month_name(m, lang, jalali, short=(style == "dm" and lang == "en"))
    if style == "dm":
        return f"{_digits(dd, lang)} {mon}"
    if style == "medium":
        return f"{_digits(dd, lang)} {mon} {_digits(y, lang)}"
    wd = weekday_name(d, lang)
    if lang == "fa":
        return f"{wd} {_digits(dd, lang)} {mon} {_digits(y, lang)}"
    return f"{wd}, {dd} {mon} {y}"


def month_label(d: date, lang: str, jalali: bool) -> str:
    y, m, _ = ymd(d, jalali)
    return f"{month_name(m, lang, jalali)} {_digits(y, lang)}"


def month_bounds(d: date, jalali: bool) -> tuple[date, date]:
    """First and last day of the (Jalali or Gregorian) month containing `d`."""
    if jalali:
        jy, jm, _ = to_jalali(d)
        return from_jalali(jy, jm, 1), from_jalali(jy, jm, month_len(jy, jm))
    first = d.replace(day=1)
    nxt = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    return first, nxt - timedelta(days=1)


def shift_month(d: date, n: int, jalali: bool) -> date:
    """First day of the month `n` months away from the month containing `d`."""
    if jalali:
        jy, jm, _ = to_jalali(d)
        idx = jy * 12 + (jm - 1) + n
        y, m = divmod(idx, 12)
        return from_jalali(y, m + 1, 1)
    idx = d.year * 12 + (d.month - 1) + n
    y, m = divmod(idx, 12)
    return date(y, m + 1, 1)


def week_start_of(d: date, week_start: int) -> date:
    return d - timedelta(days=(d.weekday() - week_start) % 7)


def weekday_headers(lang: str, week_start: int) -> list[str]:
    names = WEEKDAYS_SHORT["fa" if lang == "fa" else "en"]
    return [names[(week_start + i) % 7] for i in range(7)]


def month_matrix(d: date, jalali: bool, week_start: int) -> list[list[date | None]]:
    start, end = month_bounds(d, jalali)
    cells: list[date | None] = [None] * ((start.weekday() - week_start) % 7)
    cells += [start + timedelta(days=i) for i in range((end - start).days + 1)]
    while len(cells) % 7:
        cells.append(None)
    return [cells[i : i + 7] for i in range(0, len(cells), 7)]
