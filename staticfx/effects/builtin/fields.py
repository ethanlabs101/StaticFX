"""Effects that compute a brightness for every cell: plasma, tunnels, galaxies, aurora."""

from __future__ import annotations

import math
import random

from staticfx.core.color import clamp
from staticfx.core.frame import Frame
from staticfx.effects.base import Effect
from staticfx.themes import Theme

SHADE = " .:-=+*#%@"


class FieldEffect(Effect):
    """Per-cell scalar field mapped through a character ramp + theme colours.

    Subclasses implement ``value(x, y)`` returning 0..1 (anything <= the first
    ramp step stays blank/transparent). Cached coordinate tables:

    * ``xs[x]`` / ``ys[y]``  - aspect-corrected coordinates (y spans -1..1)
    * ``rr[y][x]`` / ``aa[y][x]`` - polar radius / angle (radians) from centre
    """

    shade = SHADE
    speed = 1.0
    stars = False

    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)

        self.t = 0.0
        self.seed = rng.uniform(0.0, 1000.0)

        self.xs: list[float] = []
        self.ys: list[float] = []
        self.rr: list[list[float]] = []
        self.aa: list[list[float]] = []
        self.star_cells: list[tuple[int, int, str, float]] = []

    def on_resize(self) -> None:
        width, height = self.width, self.height
        cx = (width - 1) / 2
        cy = (height - 1) / 2
        half = max(1.0, height / 2)

        # Terminal cells are ~2x taller than wide.
        self.xs = [(x - cx) * 0.5 / half for x in range(width)]
        self.ys = [(y - cy) / half for y in range(height)]

        self.rr = [[math.hypot(px, py) for px in self.xs] for py in self.ys]
        self.aa = [[math.atan2(py, px) for px in self.xs] for py in self.ys]

        self.star_cells = []

        if self.stars:
            rng = self.rng
            glyphs = "..+*"

            for _ in range(max(8, width * height // 40)):
                self.star_cells.append(
                    (
                        rng.randrange(width),
                        rng.randrange(height),
                        rng.choice(glyphs),
                        rng.uniform(0.0, math.tau),
                    )
                )

        self.prepare_static()

    def prepare_static(self) -> None:
        """Hook: build extra tables after a resize."""

    def prepare(self) -> None:
        """Hook: per-frame setup before ``value`` is called."""

    def advance(self, dt: float) -> None:
        self.t += dt * self.speed
        self.step(dt)

    def step(self, dt: float) -> None:
        """Hook for effects with extra state."""

    def value(self, x: int, y: int) -> float:
        raise NotImplementedError

    def star_visible(self, x: int, y: int) -> bool:
        return True

    def render(self, frame: Frame, theme: Theme) -> None:
        self.prepare()

        palette = self.palette(theme)
        top = len(palette) - 1
        shade = self.shade
        shade_max = len(shade) - 1
        value = self.value
        put = frame.put

        for y in range(self.height):
            for x in range(self.width):
                v = value(x, y)

                if v <= 0.0:
                    continue

                v = min(v, 1.0)

                index = int(v * shade_max + 0.5)

                if index > 0:
                    put(x, y, shade[index], palette[int(v * top + 0.5)])

        if self.star_cells:
            self._draw_stars(frame, theme)

    def _draw_stars(self, frame: Frame, theme: Theme) -> None:
        for x, y, char, phase in self.star_cells:
            if not self.star_visible(x, y):
                continue

            if frame.char_at(x, y) != " ":
                continue

            twinkle = 0.55 + 0.45 * math.sin(self.t * 2.2 + phase)
            frame.put(x, y, char, self.color_at(theme, 0.25 + 0.6 * twinkle))


def _frac(value: float) -> float:
    return value - math.floor(value)


class Plasma(FieldEffect):
    speed = 0.9

    def value(self, x: int, y: int) -> float:
        px = self.xs[x] * 3.0
        py = self.ys[y] * 3.0
        t = self.t

        total = (
            math.sin(px * 1.7 + t)
            + math.sin(py * 2.1 - t * 1.3)
            + math.sin((px + py) * 1.3 + t * 0.7)
            + math.sin(math.hypot(px - 1.5 * math.sin(t * 0.5), py - 1.5 * math.cos(t * 0.4)) * 2.2)
        )

        return (total + 4.0) / 8.0


class RipplePond(FieldEffect):
    speed = 1.0

    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.drops: list[list[float]] = []
        self.cooldown = 0.0

    def prepare_static(self) -> None:
        self.drops = []
        self.cooldown = 0.0

    def step(self, dt: float) -> None:
        self.cooldown -= dt

        if self.cooldown <= 0.0 and self.xs:
            self.cooldown = self.rng.uniform(0.5, 1.4)
            self.drops.append(
                [self.rng.uniform(self.xs[0], self.xs[-1]), self.rng.uniform(-0.9, 0.9), 0.0]
            )

        for drop in self.drops:
            drop[2] += dt

        self.drops = [drop for drop in self.drops if drop[2] < 5.5]

    def value(self, x: int, y: int) -> float:
        px = self.xs[x]
        py = self.ys[y]
        total = 0.0

        for dx, dy, age in self.drops:
            radius = age * 0.55
            ring = math.hypot(px - dx, py - dy) - radius
            total += math.exp(-((ring / 0.07) ** 2)) * math.exp(-age * 0.55)
            total += (
                0.35 * math.exp(-((ring / 0.2) ** 2)) * math.cos(ring * 38.0) * math.exp(-age * 0.8)
            )

        return total


class LavaLamp(FieldEffect):
    speed = 0.5
    shade = " .:-=+*#%@"

    def prepare(self) -> None:
        t = self.t
        xmax = abs(self.xs[0]) * 0.7 if self.xs else 1.0
        self._blobs = [
            (
                math.sin(t * (0.7 + i * 0.23) + i * 1.7) * xmax,
                math.sin(t * (0.5 + i * 0.31) + i * 2.3) * 0.7,
                0.16 + 0.05 * ((i * 7) % 5),
            )
            for i in range(6)
        ]

    def value(self, x: int, y: int) -> float:
        px = self.xs[x]
        py = self.ys[y]
        total = 0.0

        for bx, by, radius in self._blobs:
            d2 = (px - bx) ** 2 + (py - by) ** 2
            total += radius * radius / (d2 + 0.004)

        edge = clamp((total - 0.7) / 1.1)
        return edge * edge * (3.0 - 2.0 * edge)


class HeatHaze(FieldEffect):
    speed = 1.0

    def value(self, x: int, y: int) -> float:
        px = self.xs[x]
        py = self.ys[y]
        t = self.t

        warped = py + 0.09 * math.sin(px * 9.0 + t * 3.0 + py * 5.0)
        bands = 0.5 + 0.5 * math.sin(warped * 14.0 - t * 4.0 + math.sin(px * 5.0) * 1.5)
        height_fade = (py + 1.0) / 2.0

        return bands * (0.15 + 0.85 * height_fade)


class OceanWaves(FieldEffect):
    speed = 1.0

    def prepare(self) -> None:
        height = self.height
        t = self.t
        self._surface = [
            height * 0.42
            + height * 0.07 * math.sin(px * 2.3 + t * 1.1)
            + height * 0.04 * math.sin(px * 5.1 - t * 1.7)
            + height * 0.02 * math.sin(px * 9.0 + t * 2.4)
            for px in self.xs
        ]

    def value(self, x: int, y: int) -> float:
        depth = y - self._surface[x]

        if depth < 0.0:
            return 0.0

        if depth < 1.0:
            return 1.0

        texture = 0.12 * math.sin(self.xs[x] * 14.0 - self.t * 2.0 + depth * 1.4)
        return max(0.0, 0.18 + 0.55 * math.exp(-depth * 0.2) + texture)


class Tunnel(FieldEffect):
    speed = 1.0

    def value(self, x: int, y: int) -> float:
        r = max(self.rr[y][x], 0.02)
        depth = 0.35 / r + self.t * 2.0
        sector = math.floor(self.aa[y][x] / math.pi * 4.0)
        checker = (int(depth * 1.5) + sector) & 1

        return (0.3 + 0.7 * checker) * min(1.0, r * 2.4) ** 0.8


class Kaleidoscope(FieldEffect):
    speed = 0.8

    def value(self, x: int, y: int) -> float:
        segment = math.tau / 6.0
        angle = abs((self.aa[y][x] % segment) - segment / 2.0)
        r = self.rr[y][x]
        u = r * math.cos(angle)
        v = r * math.sin(angle)
        t = self.t

        pattern = math.sin(u * 9.0 + t * 1.3) * math.cos(v * 9.0 - t) + 0.5 * math.sin(
            r * 6.0 - t * 2.0
        )

        return (pattern + 1.5) / 3.0


class GridWave(FieldEffect):
    speed = 1.0

    def value(self, x: int, y: int) -> float:
        py = self.ys[y]

        if py < 0.05:
            return 0.0

        depth = 1.0 / py
        t = self.t
        px = self.xs[x] + 0.12 * math.sin(depth * 1.5 + t * 1.2)
        thickness = 0.05 + 0.03 * py

        across = _frac(px * depth * 1.4)
        along = _frac(depth * 1.2 - t * 2.2)

        on_line = across < thickness or across > 1.0 - thickness or along < thickness * 2.2

        if not on_line:
            return 0.0

        return min(1.0, py * 2.6) ** 0.7


class Aurora(FieldEffect):
    speed = 1.0
    shade = " .:;|!lI#"

    def value(self, x: int, y: int) -> float:
        t = self.t
        height = self.height

        center = height * (
            0.33 + 0.10 * math.sin(x * 0.07 + t * 0.35) + 0.05 * math.sin(x * 0.17 - t * 0.5)
        )

        d = (y - center) / (height * 0.16)
        curtain = math.exp(-d * d * (0.3 if d < 0 else 1.0))
        streak = 0.55 + 0.45 * math.sin(x * 0.5 + t * 1.1 + math.sin(x * 0.13 + t * 0.3) * 3.0)

        return curtain * streak


class Nebula(FieldEffect):
    speed = 0.6
    stars = True

    def value(self, x: int, y: int) -> float:
        px = self.xs[x]
        py = self.ys[y]
        t = self.t

        cloud = math.sin(px * 2.1 + 1.7 * math.sin(py * 2.6 + t * 0.35) + t * 0.2) * math.sin(
            py * 2.9 - 1.3 * math.sin(px * 1.9 - t * 0.3)
        )

        return (0.5 + 0.5 * cloud) ** 1.8 * 0.9


class Wormhole(FieldEffect):
    speed = 1.0

    def value(self, x: int, y: int) -> float:
        r = max(self.rr[y][x], 0.02)
        angle = self.aa[y][x]
        depth = 0.25 / r

        spiral = 0.5 + 0.5 * math.sin(depth * 5.0 - self.t * 3.0 + angle * 3.0)
        body = (0.2 + 0.8 * spiral) * min(1.0, r * 3.0)
        core = max(0.0, (0.12 - r) / 0.12)

        return max(body, core)


class BlackHole(FieldEffect):
    speed = 1.0
    stars = True

    def star_visible(self, x: int, y: int) -> bool:
        return self.rr[y][x] > 0.3

    def value(self, x: int, y: int) -> float:
        px = self.xs[x]
        py = self.ys[y]
        r = self.rr[y][x]

        if r < 0.15:
            return 0.0

        photon = math.exp(-(((r - 0.19) / 0.025) ** 2))
        flat = math.hypot(px, py * 3.2)
        disk = math.exp(-(((flat - 0.55) / 0.16) ** 2))
        swirl = 0.5 + 0.5 * math.sin(self.aa[y][x] * 3.0 - self.t * 2.5 + flat * 14.0)

        return max(photon, disk * (0.3 + 0.7 * swirl))


class Galaxy(FieldEffect):
    speed = 1.0
    stars = True

    def value(self, x: int, y: int) -> float:
        r = self.rr[y][x]
        arms = 0.5 + 0.5 * math.cos(2.0 * (self.aa[y][x] - r * 4.5 + self.t * 0.25))
        falloff = math.exp(-r * 2.2)
        core = math.exp(-r * r * 40.0)

        return falloff * arms * arms * 1.25 + core
