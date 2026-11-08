"""The interface every effect implements."""

from __future__ import annotations

import random

from staticfx.core.color import RGB
from staticfx.core.frame import Frame
from staticfx.themes import Theme

PALETTE_STEPS = 48


class Effect:
    """Base class for all effects.

    Subclasses override any of:

    * :meth:`on_resize` - rebuild size-dependent state (``width``/``height``
      are already set). Also called by the default :meth:`on_reset`.
    * :meth:`on_reset` - restart the animation from scratch.
    * :meth:`advance` - move the simulation forward ``dt`` seconds.
    * :meth:`render` - draw into the frame. Spaces are transparent, so draw
      only what is visible.

    The app calls the public :meth:`resize`, :meth:`reset`, :meth:`update`
    and :meth:`draw`, which guarantee ``advance`` and ``render`` are never
    called before the first resize or with a non-positive ``dt``.
    """

    #: Restrict output to 7-bit ASCII. Set by the registry after construction.
    ascii_only = False
    #: May trade resolution for frame rate. Set by the interactive app; effects
    #: that have nothing to trade ignore it.
    adaptive = False

    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        self.rng = rng
        self.unicode = unicode  # allow katakana and other non-ASCII glyphs
        self.width = 0
        self.height = 0
        self._palette_theme: Theme | None = None
        self._palette: list[RGB] = []

    def resize(self, width: int, height: int) -> None:
        self.width, self.height = max(1, int(width)), max(1, int(height))
        self.on_resize()

    def reset(self) -> None:
        self.on_reset()

    def update(self, dt: float) -> None:
        if dt > 0.0 and self.width:
            self.advance(dt)

    def draw(self, frame: Frame, theme: Theme) -> None:
        if self.width:
            self.render(frame, theme)

    def on_resize(self) -> None:
        pass

    def on_reset(self) -> None:
        if self.width:
            self.on_resize()

    def advance(self, dt: float) -> None:
        pass

    def render(self, frame: Frame, theme: Theme) -> None:
        raise NotImplementedError

    def palette(self, theme: Theme) -> list[RGB]:
        """``PALETTE_STEPS`` colours sampled along the theme ramp (cached)."""
        if theme is not self._palette_theme:
            last = PALETTE_STEPS - 1
            self._palette = [theme.ramp(i / last) for i in range(PALETTE_STEPS)]
            self._palette_theme = theme
        return self._palette

    def color_at(self, theme: Theme, value: float) -> RGB:
        """Theme colour for a brightness in 0..1."""
        palette = self.palette(theme)
        if value <= 0.0:
            return palette[0]
        if value >= 1.0:
            return palette[-1]
        return palette[int(value * (PALETTE_STEPS - 1) + 0.5)]
