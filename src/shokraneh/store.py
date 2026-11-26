"""Local, per-profile JSON storage with atomic writes (no Flet imports)."""
from __future__ import annotations

import copy
import json
import os
import shutil
import threading
import time
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Any

from . import security, util

SCHEMA_VERSION = 1
BACKUP_FORMAT = "shokraneh-backup"
DATED = ("morning", "night", "energy")
LISTS = ("wishes", "wins", "god_talks", "prayers", "people", "hard_days", "letters", "messages")

APP_DEFAULTS: dict[str, Any] = {
    "version": SCHEMA_VERSION,
    "language": "fa",
    "calendar": "auto",  # auto | jalali | gregorian
    "theme_mode": "system",  # system | light | dark
    "accent": "sage",
    "rtl_compat": False,  # manual mirroring fallback (see ui/kit.py)
    "profiles": [],
    "last_profile": None,
    "onboarded": False,
}

PROFILE_DEFAULTS: dict[str, Any] = {
    "version": SCHEMA_VERSION,
    "settings": {
        "reminders": {
            "morning": {"enabled": True, "time": "07:30"},
            "night": {"enabled": True, "time": "21:30"},
        },
        "week_start": None,  # None = automatic (Saturday for Jalali, Monday otherwise)
        "ai": {"provider": "offline", "api_key": "", "model": "", "base_url": "", "consent": False},
    },
    "morning": {},
    "night": {},
    "energy": {},
    "wishes": [],
    "wins": [],
    "god_talks": [],
    "prayers": [],
    "people": [],
    "hard_days": [],
    "letters": [],
    "messages": [],
    "reviews": {},
    "meta": {"created": None, "last_open": None, "tour_seen": False, "fired": {}},
}


# --------------------------------------------------------------------------- helpers
def deep_merge(defaults: Any, data: Any) -> Any:
    """Return `data` completed with keys/values from `defaults` (recursively)."""
    if isinstance(defaults, dict):
        src = data if isinstance(data, dict) else {}
        out = {k: (deep_merge(v, src[k]) if k in src else copy.deepcopy(v)) for k, v in defaults.items()}
        for k, v in src.items():
            out.setdefault(k, v)
        return out
    if isinstance(defaults, list):
        return data if isinstance(data, list) else copy.deepcopy(defaults)
    if defaults is None:
        return data
    if isinstance(data, type(defaults)) or (isinstance(defaults, float) and isinstance(data, int)):
        return data
    return copy.deepcopy(defaults)


def _bak(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".bak")


def read_json(path: Path) -> Any:
    """Read JSON; fall back to the .bak copy. Returns None when nothing is readable."""
    for candidate in (path, _bak(path)):
        try:
            with open(candidate, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            continue
    return None


def write_json_atomic(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    payload = json.dumps(obj, ensure_ascii=False, indent=1)
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(payload)
        fh.flush()
        try:
            os.fsync(fh.fileno())
        except OSError:
            pass
    if path.exists():
        try:  # only keep a *valid* previous version as the backup
            json.loads(path.read_text(encoding="utf-8"))
            shutil.copy2(path, _bak(path))
        except (OSError, ValueError):
            pass
    os.replace(tmp, path)


def _quarantine_if_corrupt(path: Path) -> None:
    """Never silently overwrite an unreadable file: keep a copy for manual recovery."""
    if not path.exists():
        return
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        try:
            shutil.copy2(path, path.with_suffix(path.suffix + f".corrupt-{int(time.time())}"))
        except OSError:
            pass


def load_json(path: Path) -> Any:
    """Quarantine an unreadable file (kept for manual recovery), then read it or its .bak."""
    _quarantine_if_corrupt(path)
    return read_json(path)


def _key(day: date | str) -> str:
    return day if isinstance(day, str) else day.isoformat()


def _clean_answer(a: Any) -> Any:
    if isinstance(a, (list, tuple)):
        return [str(x).strip() for x in a]
    return str(a or "").strip()


def _has_content(a: Any) -> bool:
    return any(a) if isinstance(a, list) else bool(a)


# --------------------------------------------------------------------------- profile
class Profile:
    """All data of one user. Every mutating method persists immediately."""

    def __init__(self, store: "Store", pid: str, path: Path, data: dict):
        self.store = store
        self.id = pid
        self.path = path
        self.data = data
        self._lock = threading.RLock()
        self._defer = 0
        self._dirty = False

    # ---- persistence
    def save(self) -> None:
        with self._lock:
            self._dirty = True
            if self._defer == 0:
                self._flush()

    def _flush(self) -> None:
        write_json_atomic(self.path, self.data)
        self._dirty = False

    @contextmanager
    def batch(self):
        """Group several mutations into a single disk write."""
        with self._lock:
            self._defer += 1
            try:
                yield self
            finally:
                self._defer -= 1
                if self._defer == 0 and self._dirty:
                    self._flush()

    # ---- identity
    @property
    def name(self) -> str:
        rec = self.store.profile_record(self.id) or {}
        return rec.get("name", "")

    @property
    def avatar(self) -> str:
        rec = self.store.profile_record(self.id) or {}
        return rec.get("avatar", "🌿")

    # ---- settings (dotted paths, e.g. "reminders.morning.time")
    def setting(self, dotted: str, default: Any = None) -> Any:
        cur: Any = self.data.get("settings", {})
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    def set_setting(self, dotted: str, value: Any) -> None:
        with self._lock:
            parts = dotted.split(".")
            cur = self.data.setdefault("settings", {})
            for p in parts[:-1]:
                nxt = cur.get(p)
                if not isinstance(nxt, dict):
                    nxt = cur[p] = {}
                cur = nxt
            cur[parts[-1]] = value
            self.save()

    # ---- dated entries (morning / night / energy)
    def entry(self, kind: str, day: date | str) -> dict | None:
        return self.data[kind].get(_key(day))

    def save_entry(self, kind: str, day: date | str, answers: dict) -> dict | None:
        """Store answers for a day; an entry without any content is removed."""
        clean = {qid: _clean_answer(a) for qid, a in answers.items()}
        clean = {qid: a for qid, a in clean.items() if _has_content(a)}
        key = _key(day)
        with self._lock:
            if not clean:
                if self.data[kind].pop(key, None) is not None:
                    self.save()
                return None
            old = self.data[kind].get(key) or {}
            ts = util.now().isoformat()
            e = {"answers": clean, "created": old.get("created", ts), "updated": ts}
            self.data[kind][key] = e
            self.save()
            return e

    def energy(self, day: date | str) -> dict | None:
        return self.data["energy"].get(_key(day))

    def set_energy(self, day: date | str, score: int, tags=None, note: str = "") -> dict:
        score = int(util.clamp(int(score), 1, 10))
        with self._lock:
            e = {"score": score, "tags": list(tags or []), "note": (note or "").strip(), "ts": util.now().isoformat()}
            self.data["energy"][_key(day)] = e
            self.save()
            return e

    def delete_energy(self, day: date | str) -> None:
        with self._lock:
            if self.data["energy"].pop(_key(day), None) is not None:
                self.save()

    # ---- list collections (wishes, wins, prayers, people, hard days, letters, ...)
    def items(self, coll: str) -> list[dict]:
        return self.data[coll]

    def get_item(self, coll: str, item_id: str) -> dict | None:
        return next((i for i in self.data[coll] if i.get("id") == item_id), None)

    def add_item(self, coll: str, **fields) -> dict:
        with self._lock:
            item = {"id": util.uid(coll[:2] + "_"), "created": util.now().isoformat(), **fields}
            self.data[coll].append(item)
            self.save()
            return item

    def update_item(self, coll: str, item_id: str, **fields) -> dict | None:
        with self._lock:
            item = self.get_item(coll, item_id)
            if item is None:
                return None
            item.update(fields)
            self.save()
            return item

    def delete_item(self, coll: str, item_id: str) -> bool:
        with self._lock:
            before = len(self.data[coll])
            self.data[coll] = [i for i in self.data[coll] if i.get("id") != item_id]
            changed = len(self.data[coll]) != before
            if changed:
                self.save()
            return changed

    # ---- inbox messages (weekly reports etc.)
    def add_message(
        self, kind: str, title: str, sections: list[dict], source: str = "offline", period: str = "", **extra
    ) -> dict:
        return self.add_item(
            "messages", kind=kind, title=title, sections=sections, source=source, period=period, read=False, **extra
        )

    def snapshot(self) -> dict:
        """A deep copy of the data for background workers (reports, AI) so the UI thread can keep editing."""
        with self._lock:
            return copy.deepcopy(self.data)

    def unread_count(self) -> int:
        return sum(1 for m in self.data["messages"] if not m.get("read"))

    def mark_read(self, msg_id: str) -> None:
        self.update_item("messages", msg_id, read=True)

    def message_for_period(self, kind: str, period: str) -> dict | None:
        return next((m for m in self.data["messages"] if m.get("kind") == kind and m.get("period") == period), None)

    # ---- export / import
    def export_text(self) -> str:
        data = {k: v for k, v in self.data.items() if k != "settings"}
        payload = {
            "format": BACKUP_FORMAT,
            "version": SCHEMA_VERSION,
            "exported": util.now().isoformat(),
            "profile": {"name": self.name, "avatar": self.avatar},
            "data": data,
        }
        return json.dumps(payload, ensure_ascii=False, indent=1)

    def import_text(self, text: str, mode: str = "merge") -> dict[str, int]:
        """Import a backup made by export_text(). mode: 'merge' | 'replace'. Returns added counts."""
        try:
            payload = json.loads(text)
        except ValueError as exc:
            raise ValueError("not-json") from exc
        if not isinstance(payload, dict) or payload.get("format") != BACKUP_FORMAT or not isinstance(payload.get("data"), dict):
            raise ValueError("bad-format")
        incoming = deep_merge({k: v for k, v in PROFILE_DEFAULTS.items() if k != "settings"}, payload["data"])
        for c in LISTS:  # tolerate hand-edited / damaged files: keep only well-formed records
            incoming[c] = [i for i in incoming[c] if isinstance(i, dict)]
        for c in DATED:
            incoming[c] = {k: v for k, v in incoming[c].items() if isinstance(v, dict)}
        if not isinstance(incoming.get("reviews"), dict):
            incoming["reviews"] = {}
        counts: dict[str, int] = {}
        with self._lock:
            if mode == "replace":
                settings = self.data.get("settings", {})
                self.data = {**incoming, "settings": settings}
                counts = {c: len(self.data[c]) for c in LISTS}
                counts.update({c: len(self.data[c]) for c in DATED})
            else:
                for c in DATED:
                    added = 0
                    for day, entry in incoming[c].items():
                        mine = self.data[c].get(day)
                        stamp = lambda e: (e or {}).get("updated") or (e or {}).get("ts") or ""
                        if mine is None or stamp(entry) > stamp(mine):
                            added += mine is None
                            self.data[c][day] = entry
                    counts[c] = added
                for c in LISTS:
                    have = {i.get("id") for i in self.data[c]}
                    new = [i for i in incoming[c] if i.get("id") not in have]
                    self.data[c].extend(new)
                    counts[c] = len(new)
                for k, v in incoming.get("reviews", {}).items():
                    self.data["reviews"].setdefault(k, v)
            self.save()
        return counts

    def wipe(self) -> None:
        """Erase all content of this profile (settings are kept)."""
        with self._lock:
            settings = self.data.get("settings", {})
            self.data = deep_merge(PROFILE_DEFAULTS, {"settings": settings})
            self.data["meta"]["created"] = util.now().isoformat()
            self.save()


# --------------------------------------------------------------------------- store
class Store:
    """Device-level storage: app settings + a set of independent user profiles."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.profiles_dir = self.root / "profiles"
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        self._app_path = self.root / "app.json"
        self._lock = threading.RLock()
        self._open: dict[str, Profile] = {}
        raw = load_json(self._app_path)
        self.app: dict[str, Any] = deep_merge(APP_DEFAULTS, raw if isinstance(raw, dict) else {})

    # ---- app-level settings
    def save_app(self) -> None:
        with self._lock:
            write_json_atomic(self._app_path, self.app)

    def get(self, key: str, default: Any = None) -> Any:
        return self.app.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.app[key] = value
        self.save_app()

    # ---- profiles
    def profile_record(self, pid: str) -> dict | None:
        return next((p for p in self.app["profiles"] if p["id"] == pid), None)

    def profile_list(self) -> list[dict]:
        return [
            {"id": p["id"], "name": p["name"], "avatar": p.get("avatar", "🌿"), "has_pin": bool(p.get("pin"))}
            for p in self.app["profiles"]
        ]

    def create_profile(self, name: str, avatar: str = "🌿") -> dict:
        with self._lock:
            rec = {"id": util.uid("p_"), "name": name.strip() or "—", "avatar": avatar, "created": util.now().isoformat(), "pin": None}
            self.app["profiles"].append(rec)
            if not self.app.get("last_profile"):
                self.app["last_profile"] = rec["id"]
            self.save_app()
            return rec

    def update_profile(self, pid: str, **fields) -> None:
        with self._lock:
            rec = self.profile_record(pid)
            if rec:
                rec.update({k: v for k, v in fields.items() if k in ("name", "avatar")})
                self.save_app()

    def delete_profile(self, pid: str) -> None:
        with self._lock:
            self.app["profiles"] = [p for p in self.app["profiles"] if p["id"] != pid]
            if self.app.get("last_profile") == pid:
                self.app["last_profile"] = self.app["profiles"][0]["id"] if self.app["profiles"] else None
            self._open.pop(pid, None)
            path = self.profiles_dir / f"{pid}.json"
            for f in (path, _bak(path)):
                try:
                    f.unlink()
                except OSError:
                    pass
            self.save_app()

    def has_pin(self, pid: str) -> bool:
        rec = self.profile_record(pid)
        return bool(rec and rec.get("pin"))

    def set_pin(self, pid: str, pin: str | None) -> None:
        rec = self.profile_record(pid)
        if rec is not None:
            rec["pin"] = security.hash_pin(pin) if pin else None
            self.save_app()

    def check_pin(self, pid: str, pin: str) -> bool:
        rec = self.profile_record(pid)
        if not rec or not rec.get("pin"):
            return True
        return security.verify_pin(pin, rec["pin"])

    def open_profile(self, pid: str) -> Profile:
        with self._lock:
            if pid in self._open:
                return self._open[pid]
            path = self.profiles_dir / f"{pid}.json"
            raw = load_json(path)
            data = deep_merge(PROFILE_DEFAULTS, raw if isinstance(raw, dict) else {})
            if not data["meta"].get("created"):
                data["meta"]["created"] = util.now().isoformat()
            prof = Profile(self, pid, path, data)
            self._open[pid] = prof
            self.app["last_profile"] = pid
            self.save_app()
            return prof

    def close_profile(self, pid: str) -> None:
        self._open.pop(pid, None)
