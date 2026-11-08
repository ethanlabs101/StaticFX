"""Filters applied to the finished frame, on top of any effect and theme.

* **CRT** darkens every other row, like scanlines on a tube.
* **Glitch** occasionally tears a band of rows sideways.
* **Recolour** repaints everything with a diagonal rainbow, keeping each
  cell's original brightness so the effect's shading survives.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from staticfx.core.color import RGB, hsv
from staticfx.core.frame import Frame

SCANLINE_FACTOR = 0.7
GLITCH_CHANCE = 0.3  # per frame
RECOLOUR_SPEED = 0.15  # hue turns per second


def scanlines(frame: Frame) -> None:
    for row in frame.cells[1::2]:
        for cell in row:
            if cell.char != " ":
                r, g, b = cell.color
                cell.color = RGB(
                    int(r * SCANLINE_FACTOR), int(g * SCANLINE_FACTOR), int(b * SCANLINE_FACTOR)
                )


def tear(frame: Frame, rng: random.Random) -> None:
    """Shift one to three bands of rows sideways (blank where they slid away)."""
    width, height = frame.width, frame.height
    for _ in range(rng.randint(1, 3)):
        top = rng.randrange(height)
        shift = rng.choice((-1, 1)) * rng.randint(1, max(1, width // 16))
        for row in frame.cells[top : top + rng.randint(1, max(1, height // 8))]:
            snapshot = [(cell.char, cell.color) for cell in row]
            for x, cell in enumerate(row):
                source = x - shift
                if 0 <= source < width:
                    cell.char, cell.color = snapshot[source]
                else:
                    cell.char = " "


def recolour(frame: Frame, offset: float) -> None:
    span = max(1, frame.width + frame.height - 2)
    for y, row in enumerate(frame.cells):
        for x, cell in enumerate(row):
            if cell.char != " ":
                r, g, b = cell.color
                level = max(r, g, b) / 255
                cell.color = hsv((x + y) / span + offset, 1.0, 0.3 + 0.7 * level)


@dataclass
class PostFX:
    crt: bool = False
    glitch: bool = False
    recolour: bool = False
    rng: random.Random = field(default_factory=random.Random, repr=False)
    _hue: float = 0.0

    def update(self, dt: float) -> None:
        self._hue = (self._hue + dt * RECOLOUR_SPEED) % 1.0

    def apply(self, frame: Frame) -> None:
        if self.recolour:
            recolour(frame, self._hue)
        if self.crt:
            scanlines(frame)
        if self.glitch and self.rng.random() < GLITCH_CHANCE:
            tear(frame, self.rng)

    def active(self) -> list[str]:
        return [name for name in ("crt", "glitch", "recolour") if getattr(self, name)]
