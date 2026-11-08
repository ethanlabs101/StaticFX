"""24-bit colour value and the handful of operations effects actually use."""

from __future__ import annotations

import colorsys
from itertools import pairwise
from typing import NamedTuple


class RGB(NamedTuple):
    """An sRGB colour with 0-255 channels.

    A NamedTuple rather than a dataclass: colours are created per cell per
    frame, and tuples are the cheapest immutable, hashable value in CPython.
    Callers are expected to pass in-range ints; use :func:`rgb` to clamp.
    """

    r: int
    g: int
    b: int


BLACK = RGB(0, 0, 0)
WHITE = RGB(255, 255, 255)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return low if value < low else high if value > high else value


def rgb(r: float, g: float, b: float) -> RGB:
    """Build a colour from arbitrary numbers, rounding and clamping to 0-255."""
    return RGB(
        int(clamp(round(r), 0, 255)), int(clamp(round(g), 0, 255)), int(clamp(round(b), 0, 255))
    )


def lerp(a: RGB, b: RGB, t: float) -> RGB:
    t = clamp(t)
    return RGB(
        int(a.r + (b.r - a.r) * t + 0.5),
        int(a.g + (b.g - a.g) * t + 0.5),
        int(a.b + (b.b - a.b) * t + 0.5),
    )


def scale(color: RGB, factor: float) -> RGB:
    """Darken (factor < 1) or brighten (factor > 1) by multiplying each channel."""
    return rgb(color.r * factor, color.g * factor, color.b * factor)


def tint(color: RGB, amount: float) -> RGB:
    """Mix towards white by ``amount`` (0 = unchanged, 1 = white)."""
    return lerp(color, WHITE, amount)


def hsv(h: float, s: float = 1.0, v: float = 1.0) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, clamp(s), clamp(v))
    return RGB(int(r * 255 + 0.5), int(g * 255 + 0.5), int(b * 255 + 0.5))


def hue_of(color: RGB) -> float:
    return colorsys.rgb_to_hsv(color.r / 255, color.g / 255, color.b / 255)[0]


def gradient(stops: list[tuple[float, RGB]], t: float) -> RGB:
    """Sample a piecewise-linear gradient given ``(position, colour)`` stops."""
    t = clamp(t)
    for (p0, c0), (p1, c1) in pairwise(stops):
        if t <= p1:
            return c0 if p1 == p0 else lerp(c0, c1, (t - p0) / (p1 - p0))
    return stops[-1][1]


def parse_hex(text: str) -> RGB:
    """Parse ``#rgb`` or ``#rrggbb`` (the ``#`` is optional)."""
    value = text.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"not a hex colour: {text!r}")
    try:
        return RGB(int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))
    except ValueError:
        raise ValueError(f"not a hex colour: {text!r}") from None


def to_hex(color: RGB) -> str:
    return f"#{color.r:02x}{color.g:02x}{color.b:02x}"
