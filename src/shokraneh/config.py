"""Paths and global constants (no Flet imports)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

APP_ID = "shokraneh"
CREATOR_NAME = "ارشیا تخت فیروزه"  # shown in the "Creator" section and the copyright notice
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"

# Content width cap (px) so the app also looks good in a wide desktop window.
MAX_CONTENT_WIDTH = 720


def is_android() -> bool:
    if sys.platform == "android":
        return True
    return "ANDROID_ROOT" in os.environ and "ANDROID_DATA" in os.environ


def data_root() -> Path:
    """Folder where all user data lives.

    Priority: SHOKRANEH_DATA_DIR (dev/tests) -> FLET_APP_STORAGE_DATA (set by
    `flet run` and by built apps; private to the app on Android) -> OS default.
    """
    override = os.environ.get("SHOKRANEH_DATA_DIR")
    if override:
        return Path(override)
    flet_dir = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_dir:
        return Path(flet_dir) / APP_ID
    home = Path.home()
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = home / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", home / ".local" / "share"))
    return base / "Shokraneh"
