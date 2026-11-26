"""What has been done today (no Flet imports) - used by the home hero and the dynamic island."""
from __future__ import annotations

from datetime import date
from typing import Any

from . import analytics
from . import content as qc


def _progress(profile: Any, kind: str, day: date) -> tuple[int, int]:
    qs = qc.MORNING if kind == "morning" else qc.NIGHT
    entry = profile.entry(kind, day)
    answered = sum(1 for q in qs if entry and q.id in entry.get("answers", {}))
    return answered, len(qs)


def status(profile: Any, day: date) -> dict:
    """morning / night: (answered, total); energy: bool; done: 0..3 finished check-ins; streak: current streak in days."""
    m_a, m_n = _progress(profile, "morning", day)
    n_a, n_n = _progress(profile, "night", day)
    energy = profile.energy(day) is not None
    morning_done, night_done = m_a >= m_n > 0, n_a >= n_n > 0
    streak, _best = analytics.streaks(profile.data, day)
    return {
        "morning": (m_a, m_n), "night": (n_a, n_n), "energy": energy,
        "morning_done": morning_done, "night_done": night_done,
        "done": int(morning_done) + int(night_done) + int(energy), "total": 3, "streak": streak,
    }
