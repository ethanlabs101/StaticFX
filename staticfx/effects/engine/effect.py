"""Rendering a :class:`Recipe` to the terminal."""

from __future__ import annotations

import math
import random
import time

from staticfx.core.color import BLACK, RGB, WHITE, gradient, hsv, tint
from staticfx.core.frame import Frame
from staticfx.core.glyphs import TECH
from staticfx.effects.base import Effect
from staticfx.effects.engine.filters import BLENDS, FILTERS
from staticfx.effects.engine.layers import LAYERS
from staticfx.effects.engine.recipe import ASCII_FALLBACK, Recipe
from staticfx.effects.engine.warps import WARPS
from staticfx.themes import Theme

# 4x4 ordered-dither thresholds, centred on zero.
BAYER = [
    [(v + 0.5) / 16.0 - 0.5 for v in row]
    for row in ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))
]

RAINBOW = [hsv(i / 256) for i in range(256)]

# Block sizes (columns, rows) the field is sampled at. Pure-Python maths per
# cell is the bottleneck, so big terminals sample every few cells and fill
# blocks; the adaptive mode steps through these as frame cost changes.
LEVELS = ((1, 1), (2, 1), (2, 2), (3, 2), (4, 2), (4, 3), (6, 3), (8, 4))
MAX_SAMPLES = 2400
SLOW_FRAME, FAST_FRAME = 0.045, 0.012  # seconds of render time


class EngineEffect(Effect):
    """Draws a recipe. The recipe is read every frame, so the Studio can edit
    it in place and see the change immediately."""

    def __init__(self, rng: random.Random, unicode: bool = False, *, recipe: Recipe) -> None:
        super().__init__(rng, unicode)
        self.recipe = recipe
        self.clock = self._start_time()
        self.level = 0
        self.cost = 0.0
        self.cooldown = 20
        self.step_x = self.step_y = 1
        self.blocks_x = self.blocks_y = 0
        self.xs: list[float] = []
        self.ys: list[float] = []
        self.angles: list[float] = []
        self.values: list[float] = []
        self.previous: list[float] = []
        self._duo: tuple[tuple[RGB, RGB] | None, list[RGB]] = (None, [])

    def _start_time(self) -> float:
        return (self.recipe.seed * 0.37) % 40.0

    def on_resize(self) -> None:
        self.level = 0
        while self.level < len(LEVELS) - 1:
            sx, sy = LEVELS[self.level]
            if math.ceil(self.width / sx) * math.ceil(self.height / sy) <= MAX_SAMPLES:
                break
            self.level += 1
        self._layout()

    def on_reset(self) -> None:
        self.clock = self._start_time()
        self.cooldown = 20
        super().on_reset()

    def _layout(self) -> None:
        w, h = self.width, self.height
        self.step_x, self.step_y = LEVELS[self.level]
        self.blocks_x = math.ceil(w / self.step_x)
        self.blocks_y = math.ceil(h / self.step_y)
        self.xs, self.ys, self.angles = [], [], []
        for by in range(self.blocks_y):
            ny = (by * self.step_y + self.step_y / 2 - h / 2) / max(1.0, h / 2)
            for bx in range(self.blocks_x):
                nx = (bx * self.step_x + self.step_x / 2 - w / 2) / max(1.0, float(h))
                self.xs.append(nx)
                self.ys.append(ny)
                self.angles.append(math.atan2(ny, nx) / math.tau + 0.5)
        self.values = [0.0] * len(self.xs)
        self.previous = [0.0] * len(self.xs)

    def advance(self, dt: float) -> None:
        self.clock += dt * self.recipe.speed
        if not self.adaptive:
            return
        self.cooldown -= 1
        if self.cooldown > 0:
            return
        if self.cost > SLOW_FRAME and self.level < len(LEVELS) - 1:
            self.level += 1
            self._layout()
            self.cooldown = 25
        elif self.cost < FAST_FRAME and self.level > 0:
            self.level -= 1
            self._layout()
            self.cooldown = 90

    def charset(self) -> str:
        chars = self.recipe.charset
        return ASCII_FALLBACK if self.ascii_only and not chars.isascii() else chars

    def _sample(self) -> None:
        """Fill ``self.values`` with the recipe's brightness at each sample point."""
        recipe, t = self.recipe, self.clock
        warps = [WARPS[s.kind].build(s.params, t) for s in recipe.warps]
        first = LAYERS[recipe.layers[0].kind].build(recipe.layers[0].params, t)
        rest = [(BLENDS[s.blend], LAYERS[s.kind].build(s.params, t)) for s in recipe.layers[1:]]
        filters = [FILTERS[s.kind].build(s.params, t) for s in recipe.filters]
        xs, ys, values = self.xs, self.ys, self.values

        for i in range(len(xs)):
            x, y = xs[i], ys[i]
            try:
                for warp in warps:
                    x, y = warp(x, y)
                v = first(x, y)
                for blend, layer in rest:
                    v = blend(v, layer, x, y)
                v = 0.0 if v < 0.0 else 1.0 if v > 1.0 else v
                for f in filters:
                    v = f(v)
                v = 0.0 if v < 0.0 else 1.0 if v > 1.0 else v
            except (ValueError, OverflowError, ZeroDivisionError):
                v = 0.0  # e.g. a negative number to a fractional power
            values[i] = v

    def _post(self) -> None:
        """Auto-gain, trails and pulsing on the sampled values."""
        recipe, values = self.recipe, self.values
        count = len(values)
        peak = max(values) if values else 0.0

        # Never let a recipe render dim or blank: stretch a dark field to full range,
        # and replace a completely black one with a gentle diagonal gradient.
        if peak < 0.6:
            if peak > 1e-6:
                gain = min(8.0, 0.95 / peak)
                for i in range(count):
                    values[i] = min(1.0, values[i] * gain)
            else:
                t, xs, ys = self.clock, self.xs, self.ys
                for i in range(count):
                    values[i] = (xs[i] * 3.1 + ys[i] * 2.3 + t * 0.3) % 1.0

        if recipe.trail:
            previous, decay = self.previous, recipe.trail
            for i in range(count):
                faded = previous[i] * decay
                values[i] = max(values[i], faded)
                previous[i] = values[i]

        if recipe.pulse:
            level = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(self.clock * recipe.pulse * 6))
            for i in range(count):
                values[i] *= level

    def _colours(self, theme: Theme) -> list[RGB]:
        """A colour per sample point."""
        palette, t = self.recipe.palette, self.clock
        values = self.values
        if palette.kind == "theme":
            lut = theme.lut
            return [lut[int(v * 255)] for v in values]
        if palette.kind == "duo":
            duo = self._duo_lut(palette.first, palette.second)
            return [duo[int(v * 255)] for v in values]
        out = []
        for i, v in enumerate(values):
            if palette.kind == "rainbow":
                hue = v * palette.spread + t * palette.drift + palette.offset
                k = 0.25 + 0.75 * v
            else:  # angular
                hue = self.angles[i] + t * 0.08 + v * 0.3
                k = 0.2 + 0.8 * v
            r, g, b = RAINBOW[int(hue * 255) & 255]
            out.append(RGB(int(r * k), int(g * k), int(b * k)))
        return out

    def _duo_lut(self, first: RGB, second: RGB) -> list[RGB]:
        if self._duo[0] != (first, second):
            stops = [(0.0, BLACK), (0.45, first), (0.85, second), (1.0, WHITE)]
            self._duo = ((first, second), [gradient(stops, i / 255) for i in range(256)])
        return self._duo[1]

    def render(self, frame: Frame, theme: Theme) -> None:
        started = time.perf_counter()
        self._sample()
        self._post()
        colours = self._colours(theme)

        recipe, rng = self.recipe, self.rng
        w, h = self.width, self.height
        sx, sy = self.step_x, self.step_y
        chars = self.charset()
        top = len(chars) - 1
        rnd, pool, pool_size = rng.random, TECH, len(TECH)
        cells, values = frame.cells, self.values
        i = 0

        for by in range(self.blocks_y):
            y0, y1 = by * sy, min(h, by * sy + sy)
            for bx in range(self.blocks_x):
                v, colour = values[i], colours[i]
                i += 1
                x0, x1 = bx * sx, min(w, bx * sx + sx)
                if recipe.glyph_rain:
                    if v > 0.16:
                        threshold = 0.35 + v * 0.6
                        for y in range(y0, y1):
                            for cell in cells[y][x0:x1]:
                                if rnd() < threshold:
                                    cell.char = pool[int(rnd() * pool_size)]
                                    cell.color = colour
                elif recipe.dither:
                    shifted = v * top + 0.5
                    for y in range(y0, y1):
                        bayer = BAYER[y & 3]
                        row = cells[y]
                        for x in range(x0, x1):
                            index = min(top, int(shifted + bayer[x & 3] * 1.2))
                            if index > 0:
                                cell = row[x]
                                cell.char = chars[index]
                                cell.color = colour
                else:
                    index = int(v * top + 0.5)
                    if index > 0:
                        char = chars[index]
                        for y in range(y0, y1):
                            for cell in cells[y][x0:x1]:
                                cell.char = char
                                cell.color = colour

        self._extras(frame, theme)
        self.cost = self.cost * 0.75 + (time.perf_counter() - started) * 0.25

    def _extras(self, frame: Frame, theme: Theme) -> None:
        recipe, rng = self.recipe, self.rng
        w, h, cells = self.width, self.height, frame.cells

        if recipe.scanlines:
            for row in cells[::2]:
                for cell in row:
                    if cell.char != " ":
                        r, g, b = cell.color
                        cell.color = RGB(r * 6 // 10, g * 6 // 10, b * 6 // 10)

        if recipe.glitch and rng.random() < 0.3:
            for _ in range(rng.randint(1, 3)):
                row = cells[rng.randrange(h)]
                shift = rng.randint(1, max(1, w // 6))
                snapshot = [(c.char, c.color) for c in row]
                for x, cell in enumerate(row):
                    cell.char, cell.color = snapshot[(x + shift) % w]

        if recipe.sparkle:
            colour = tint(theme.bright, 0.5)
            for _ in range(int(w * h * recipe.sparkle) + 1):
                cell = cells[rng.randrange(h)][rng.randrange(w)]
                cell.char = rng.choice("*+.'")
                cell.color = colour
