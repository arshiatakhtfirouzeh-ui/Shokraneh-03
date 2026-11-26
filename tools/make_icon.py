"""Generate src/assets/icon.png (the app icon) with Pillow:  python tools/make_icon.py"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "src" / "assets" / "icon.png"
S = 1024


def leaf(a: tuple, b: tuple, width: float, n: int = 40) -> list:
    """A lens-shaped leaf from point a to point b (two quadratic curves bulging to either side)."""
    (ax, ay), (bx, by) = a, b
    mx, my = (ax + bx) / 2, (ay + by) / 2
    dx, dy = bx - ax, by - ay
    ln = (dx * dx + dy * dy) ** 0.5
    nx, ny = -dy / ln * width * 2, dx / ln * width * 2
    side1, side2 = [], []
    for i in range(n + 1):
        t = i / n
        for pts, k in ((side1, 1), (side2, -1)):
            cx_, cy_ = mx + nx * k, my + ny * k
            pts.append(((1 - t) ** 2 * ax + 2 * (1 - t) * t * cx_ + t * t * bx, (1 - t) ** 2 * ay + 2 * (1 - t) * t * cy_ + t * t * by))
    return side1 + side2[::-1]


def main() -> None:
    img = Image.new("RGB", (S, S), "#6E9C86")
    px = img.load()
    top, bottom = (126, 168, 146), (84, 128, 108)  # soft sage gradient
    for y in range(S):
        t = y / (S - 1)
        row = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        for x in range(S):
            px[x, y] = row
    d = ImageDraw.Draw(img, "RGBA")
    d.ellipse((S * 0.18, S * 0.18, S * 0.82, S * 0.82), fill=(255, 255, 255, 38))  # glow
    cx = S / 2
    cream = (250, 246, 236, 255)
    d.rounded_rectangle((cx - 13, S * 0.46, cx + 13, S * 0.77), radius=13, fill=cream)  # stem
    for sign in (-1, 1):  # two leaves, each a smooth lens shape
        d.polygon(leaf((cx, S * 0.55), (cx + sign * S * 0.24, S * 0.36), S * 0.075), fill=cream)
    d.ellipse((cx - 30, S * 0.24, cx + 30, S * 0.24 + 60), fill=(243, 201, 120, 255))  # a small warm sun
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
