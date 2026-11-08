"""What is on screen: the current effect, theme, speed and filters."""

from __future__ import annotations

import random
from collections import OrderedDict

from staticfx import themes
from staticfx.core.frame import Frame
from staticfx.effects.base import Effect
from staticfx.effects.registry import Registry
from staticfx.postfx import PostFX
from staticfx.themes import Strobe, Theme

SPEED_MIN, SPEED_MAX = 0.1, 5.0
SPEED_STEP = 1.2
RAINBOW_SPEED = 0.18  # hue turns per second
PREVIEW_CACHE = 6


class Player:
    """Owns the playing effect and anything that changes how it looks.

    Menus can *preview* an effect or theme without committing to it: the
    preview is drawn instead of the real choice until it is cleared.
    """

    def __init__(
        self,
        registry: Registry,
        rng: random.Random,
        *,
        unicode: bool = False,
        ascii_only: bool = False,
    ) -> None:
        self.registry = registry
        self.rng = rng
        self.unicode = unicode
        self.ascii_only = ascii_only
        self.width, self.height = 80, 24
        self.speed = 1.0
        self.paused = False
        self.post = PostFX(rng=rng)
        self.adaptive = False  # trade resolution for frame rate (interactive only)

        self.theme_name = themes.DEFAULT
        self.preview_theme: str | None = None
        self._strobe = Strobe(rng)
        self._clock = 0.0

        self.key = ""
        self.effect: Effect | None = None
        self.preview_key: str | None = None
        self._previews: OrderedDict[str, Effect] = OrderedDict()
        self.override: Effect | None = None  # drawn instead of anything else (the Studio)

    def _build(self, key: str) -> Effect:
        effect = self.registry.make(key, self.rng, unicode=self.unicode, ascii_only=self.ascii_only)
        effect.adaptive = self.adaptive
        effect.resize(self.width, self.height)
        return effect

    def play(self, key: str) -> None:
        """Switch to effect ``key`` (raises ``KeyError`` if there's no such effect)."""
        self.effect = self._build(key)
        self.key = key
        self.preview_key = None

    def reload(self) -> None:
        """Rebuild the current effect, e.g. after its recipe was edited and saved."""
        self._previews.clear()
        if self.key in self.registry:
            self.play(self.key)

    def restart(self) -> None:
        if self.effect is not None:
            self.effect.reset()

    def preview(self, key: str | None) -> None:
        """Show ``key`` instead of the current effect (``None`` stops previewing).

        Recently previewed effects are kept alive, so scrolling back and forth
        in a menu doesn't restart them every time.
        """
        if key is None or key == self.key or key not in self.registry:
            self.preview_key = None
            return
        if key not in self._previews:
            self._previews[key] = self._build(key)
            while len(self._previews) > PREVIEW_CACHE:
                self._previews.popitem(last=False)
        self._previews.move_to_end(key)
        self.preview_key = key

    @property
    def showing(self) -> Effect | None:
        if self.override is not None:
            return self.override
        if self.preview_key is not None:
            return self._previews[self.preview_key]
        return self.effect

    def set_theme(self, name: str) -> None:
        self.theme_name = themes.normalize(name)

    def theme(self) -> Theme:
        name = self.preview_theme or self.theme_name
        if name == "rainbow":
            return themes.rainbow(self._clock * RAINBOW_SPEED)
        if name == "strobe":
            return self._strobe.theme()
        return themes.STATIC_THEMES[name]

    def faster(self) -> None:
        self.speed = min(SPEED_MAX, self.speed * SPEED_STEP)

    def slower(self) -> None:
        self.speed = max(SPEED_MIN, self.speed / SPEED_STEP)

    def resize(self, width: int, height: int) -> None:
        self.width, self.height = width, height
        for effect in (self.effect, self.override, *self._previews.values()):
            if effect is not None:
                effect.resize(width, height)

    def update(self, dt: float) -> None:
        self._clock += dt
        if (self.preview_theme or self.theme_name) == "strobe":
            self._strobe.update(dt)
        self.post.update(dt)
        effect = self.showing
        if effect is not None and not self.paused:
            effect.update(dt * self.speed)

    def draw(self, frame: Frame) -> Theme:
        """Draw the effect and filters into ``frame``; returns the theme used."""
        theme = self.theme()
        frame.clear()
        effect = self.showing
        if effect is not None:
            effect.draw(frame, theme)
        self.post.apply(frame)
        return theme
