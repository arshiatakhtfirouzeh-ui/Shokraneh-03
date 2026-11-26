"""Entry point.

Desktop:   python src/main.py        (or: flet run src/main.py)
Android:   flet build apk            (see README.md / .github/workflows/build-apk.yml)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # `import shokraneh` also works when started as a plain script

import flet as ft  # noqa: E402

from shokraneh import config  # noqa: E402
from shokraneh.ui.app import App  # noqa: E402

FONT_FILES = {"Vazir": "Vazirmatn-Regular.ttf", "VazirM": "Vazirmatn-Medium.ttf", "VazirB": "Vazirmatn-Bold.ttf"}


def available_fonts() -> dict[str, str]:
    """The Vazirmatn family is optional (tools/get_fonts.py downloads it); without it the system font is used."""
    found = {name: f"/fonts/{file}" for name, file in FONT_FILES.items() if (config.FONTS_DIR / file).is_file()}
    return found if len(found) == len(FONT_FILES) else {}


def main(page: ft.Page) -> None:
    fonts = available_fonts()
    if fonts:
        page.fonts = fonts
    page.title = "شکرانه"
    page.padding = 0
    try:  # desktop window size (ignored on phones)
        page.window.width, page.window.height = 440, 880
        page.window.min_width, page.window.min_height = 340, 560
    except Exception:
        pass
    try:
        App(page, fonts_ok=bool(fonts)).start()
    except Exception:  # show the problem on screen instead of a blank window (handy on a phone)
        import traceback

        page.add(ft.Text("Startup error — please report this:\n\n" + traceback.format_exc(), selectable=True, size=12))
        page.update()


if __name__ == "__main__":
    if hasattr(ft, "run"):
        ft.run(main, assets_dir="assets")
    else:  # older Flet
        ft.app(target=main, assets_dir="assets")
