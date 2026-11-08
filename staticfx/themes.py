"""Colour themes.

A theme is a colour ramp from 0.0 (darkest) to 1.0 (brightest) plus an
accent colour for highlights. Effects compute a brightness per cell and look
the colour up with :meth:`Theme.ramp`, which is why any effect works with any
theme.

Two themes are animated and rebuilt every frame: ``rainbow`` drifts through
the hue wheel and ``strobe`` flashes. Strobe is a photosensitivity risk, so
it is hidden unless the user opts in (see ``Settings.allow_flashing``).
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from staticfx.core.color import RGB, gradient, hsv, parse_hex

RAMP_SIZE = 256


@dataclass(eq=False)
class Theme:
    key: str
    label: str
    accent: RGB
    lut: tuple[RGB, ...] = field(repr=False)
    flashing: bool = False

    def ramp(self, value: float) -> RGB:
        if value <= 0.0:
            return self.lut[0]
        if value >= 1.0:
            return self.lut[-1]
        return self.lut[int(value * (RAMP_SIZE - 1))]

    @property
    def primary(self) -> RGB:
        return self.ramp(0.55)

    @property
    def bright(self) -> RGB:
        return self.lut[-1]


def _lut(curve: Callable[[float], RGB]) -> tuple[RGB, ...]:
    return tuple(curve(i / (RAMP_SIZE - 1)) for i in range(RAMP_SIZE))


def _from_hex(key: str, label: str, accent: str, ramp: str) -> Theme:
    """A theme from an accent colour and evenly spaced ramp colours, darkest first."""
    colours = [parse_hex(code) for code in ramp.split()]
    last = len(colours) - 1
    stops = [(i / last, colour) for i, colour in enumerate(colours)]
    return Theme(key, label, parse_hex(accent), _lut(lambda t: gradient(stops, t)))


# key, label, accent, ramp from dark to bright
_PALETTES = (
    ("matrix", "Matrix", "#78ff78", "#004614 #00ff46 #dcffdc"),
    ("cyberpunk", "Cyberpunk", "#ff00aa", "#371450 #b400ff #fff5ff"),
    ("ocean", "Ocean", "#50f0ff", "#0a2d4b #00b4ff #dcffff"),
    ("fire", "Fire", "#ffeb46", "#5a1400 #ff4600 #fffad2"),
    ("toxic", "Toxic", "#e6ff50", "#194b00 #64ff00 #f5ffdc"),
    ("sakura", "Sakura", "#ffaadc", "#4b0f32 #ff50aa #fff5fa"),
    ("amber", "Amber", "#ffdc50", "#4b2800 #ffaa00 #fff5c8"),
    ("mono", "Monochrome", "#ffffff", "#373737 #a0a0a0 #ffffff"),
    ("inferno", "Inferno", "#ffc85a", "#0a0000 #55000a #cd200a #ff7a14 #ffe87a"),
    ("arctic", "Arctic", "#98deff", "#000a14 #003e5c #2a98ca #98deff #ffffff"),
    ("rose", "Neon Rose", "#ff6eb4", "#14000a #5a0028 #dc1478 #ff6eb4 #ffdcf0"),
    ("sunset", "Sunset", "#ffb36b", "#120018 #5a1046 #c2305a #ff7a3c #ffd59a"),
    ("vaporwave", "Vaporwave", "#fffb96", "#12002a #5b2a86 #ff71ce #01cdfe #e6fffb"),
    ("dracula", "Dracula", "#50fa7b", "#1e1f29 #6272a4 #bd93f9 #ff79c6 #f8f8f2"),
    ("nord", "Nord", "#a3be8c", "#2e3440 #4c566a #5e81ac #88c0d0 #eceff4"),
    ("gruvbox", "Gruvbox", "#b8bb26", "#1d2021 #665c54 #d79921 #fe8019 #fbf1c7"),
    ("solarized", "Solarized", "#b58900", "#002b36 #073642 #268bd2 #2aa198 #fdf6e3"),
    ("catppuccin", "Catppuccin", "#f9e2af", "#1e1e2e #45475a #89b4fa #cba6f7 #f5e0dc"),
    ("tokyonight", "Tokyo Night", "#9ece6a", "#1a1b26 #414868 #7aa2f7 #bb9af7 #c0caf5"),
    ("forest", "Forest", "#d4ff7a", "#031a0c #0f4d26 #2e8b57 #9acd32 #f0ffe0"),
    ("blood", "Blood Moon", "#ff4040", "#120000 #4a0000 #a00010 #e0202a #ffd0d0"),
    ("gold", "Gold", "#ffe680", "#1a1000 #5c4000 #c99a00 #ffd34d #fff8dc"),
    ("lavender", "Lavender", "#e0c3fc", "#140c1e #3d2b5a #8a6fc4 #c8b6ff #f8f2ff"),
    ("copper", "Copper", "#ffb07a", "#140800 #4d2310 #b5622a #e8955a #ffe4cc"),
    ("bubblegum", "Bubblegum", "#fff07a", "#1a0712 #7a2a5c #ff6fb5 #8ef6ff #ffffff"),
)

STATIC_THEMES = {key: _from_hex(key, *rest) for key, *rest in _PALETTES}
ANIMATED = ("rainbow", "strobe")
LABELS = {
    **{k: t.label for k, t in STATIC_THEMES.items()},
    "rainbow": "Rainbow",
    "strobe": "Strobe",
}
ALIASES = {
    "monochrome": "mono",
    "cyber": "cyberpunk",
    "arctic blue": "arctic",
    "neon rose": "rose",
    "tokyo night": "tokyonight",
    "blood moon": "blood",
}
DEFAULT = "matrix"


def normalize(name: str) -> str:
    """Canonical key for ``name`` (case-insensitive, aliases resolved).

    Raises ``ValueError`` listing the valid names when there is no such theme.
    """
    key = name.strip().lower()
    key = ALIASES.get(key, key)
    if key not in LABELS:
        raise ValueError(f"unknown theme '{name}' (choose from: {', '.join(LABELS)})")
    return key


def names(allow_flashing: bool = False) -> list[str]:
    return [key for key in LABELS if allow_flashing or key != "strobe"]


def rainbow(position: float) -> Theme:
    """The hue wheel, rotated by ``position`` (advance it over time to animate)."""

    def curve(t: float) -> RGB:
        saturation = 1.0 if t < 0.92 else max(0.0, 1.0 - (t - 0.92) * 9.0)
        return hsv(position + t * 0.65, saturation, 0.12 + 0.88 * t**0.75)

    return Theme("rainbow", "Rainbow", hsv(position + 0.5), _lut(curve))


class Strobe:
    """Random hue jumps on a fast irregular beat, with a decaying flash."""

    def __init__(self, rng: random.Random) -> None:
        self.rng = rng
        self.hue = 0.0
        self.flash = 0.0
        self.white = False
        self._beat = 0.0

    def update(self, dt: float) -> None:
        self._beat -= dt
        if self._beat <= 0.0:
            self._beat = self.rng.uniform(0.07, 0.2)
            self.hue = self.rng.random()
            self.flash = 1.0
            self.white = self.rng.random() < 0.12
        self.flash *= 0.5 ** (dt * 13.0)

    def theme(self) -> Theme:
        hue, flash, white = self.hue, self.flash, self.white

        def curve(t: float) -> RGB:
            if white and flash > 0.5:
                saturation = 0.12
            else:
                saturation = 1.0 if t < 0.93 else max(0.0, 1.0 - (t - 0.93) * 10.0)
            return hsv(hue + t * 0.45, saturation, min(1.0, 0.12 + 0.88 * t**0.7 + flash * 0.35))

        return Theme("strobe", "Strobe", hsv(hue + 0.5), _lut(curve), flashing=True)
