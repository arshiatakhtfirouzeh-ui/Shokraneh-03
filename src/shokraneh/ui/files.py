"""Backup file / clipboard helpers.

Everything that touches Flet's file-picker and clipboard APIs lives here and is written defensively: if the API differs on
some platform the caller gets an exception (or False) and Settings falls back to the copy / paste route, which needs no
platform API at all.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path
from typing import Any

import flet as ft

from .. import config

MAX_BYTES = 25 * 1024 * 1024
_PICKERS: dict[int, Any] = {}


async def _maybe(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


def _mobile() -> bool:
    return config.is_android() or sys.platform == "ios"


def _add_service(page: Any, svc: Any) -> None:
    services = getattr(page, "services", None)
    if services is not None:
        if svc not in services:
            services.append(svc)
    else:  # older Flet: services lived in the overlay
        page.overlay.append(svc)
    page.update()


def _picker(page: Any) -> Any:
    pk = _PICKERS.get(id(page))
    if pk is None:
        pk = ft.FilePicker()
        _add_service(page, pk)
        _PICKERS[id(page)] = pk
    return pk


async def save(page: Any, file_name: str, data: bytes, title: str = "") -> str | None:
    """Let the user choose where to store `data`. Returns the path, or None if nothing was chosen. Raises if unavailable."""
    pk = _picker(page)
    if _mobile():  # Android / iOS write the bytes themselves
        res = await _maybe(pk.save_file(dialog_title=title or None, file_name=file_name, src_bytes=data))
        return str(res) if res else None
    res = await _maybe(pk.save_file(dialog_title=title or None, file_name=file_name))
    if not res:
        return None
    path = Path(str(res))
    if not path.suffix:
        path = path.with_suffix(".json")
    path.write_bytes(data)
    return str(path)


async def pick(page: Any, title: str = "") -> bytes | None:
    """Let the user choose a file; returns its bytes (None = cancelled). Raises if unavailable."""
    pk = _picker(page)
    try:
        res = await _maybe(pk.pick_files(dialog_title=title or None, allow_multiple=False, with_data=True))
    except TypeError:
        res = await _maybe(pk.pick_files(allow_multiple=False))
    chosen = res if isinstance(res, (list, tuple)) else getattr(res, "files", None)
    if not chosen:
        return None
    f = chosen[0]
    data = getattr(f, "bytes", None)
    if data:
        data = bytes(data)
    else:
        path = getattr(f, "path", None)
        if not path:
            return None
        if Path(path).stat().st_size > MAX_BYTES:
            raise ValueError("too-big")
        data = Path(path).read_bytes()
    if len(data) > MAX_BYTES:
        raise ValueError("too-big")
    return data


async def copy_text(page: Any, text: str) -> bool:
    """Put `text` on the clipboard using whichever clipboard API this Flet version has."""
    cb = getattr(page, "clipboard", None)
    if cb is not None and hasattr(cb, "set"):
        try:
            await _maybe(cb.set(text))
            return True
        except Exception:
            pass
    cls = getattr(ft, "Clipboard", None)
    if cls is not None:
        try:
            obj = cls()
            _add_service(page, obj)
            await _maybe(obj.set(text))
            return True
        except Exception:
            pass
    setter = getattr(page, "set_clipboard", None)
    if setter is not None:
        try:
            await _maybe(setter(text))
            return True
        except Exception:
            pass
    return False
