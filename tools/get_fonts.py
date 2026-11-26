"""Download the Vazirmatn font (Regular / Medium / Bold) into src/assets/fonts.

    python tools/get_fonts.py

The app works without it (it then uses the system font); with it, Persian text looks much nicer.
Vazirmatn is © Saber Rastikerdar, SIL Open Font License 1.1 — https://github.com/rastikerdar/vazirmatn
"""
from __future__ import annotations

import ssl
import sys
import urllib.request
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / "src" / "assets" / "fonts"
FILES = ["Vazirmatn-Regular.ttf", "Vazirmatn-Medium.ttf", "Vazirmatn-Bold.ttf"]
BASES = [
    "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/fonts/ttf/",
    "https://raw.githubusercontent.com/rastikerdar/vazirmatn/v33.003/fonts/ttf/",
    "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/",
]


def context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def fetch(name: str, ctx: ssl.SSLContext) -> bool:
    for base in BASES:
        try:
            with urllib.request.urlopen(base + name, timeout=60, context=ctx) as r:  # noqa: S310
                data = r.read()
            if len(data) > 50_000:  # a real font, not an error page
                (DEST / name).write_bytes(data)
                return True
        except Exception as e:  # noqa: BLE001
            print(f"  {base}{name}: {e}")
    return False


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    ctx = context()
    ok = True
    for name in FILES:
        if (DEST / name).is_file():
            print(f"already there: {name}")
            continue
        print(f"downloading {name} …")
        ok = fetch(name, ctx) and ok
    print("done" if ok else "some files could not be downloaded — the app will use the system font")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
