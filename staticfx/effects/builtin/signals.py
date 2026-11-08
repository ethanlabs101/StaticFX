"""Broken signals: TV static, a failing test card, scope traces, lightning, a spectrum."""

from __future__ import annotations

import math
import random

from staticfx.core.color import clamp
from staticfx.core.frame import Frame
from staticfx.core.glyphs import tech_glyphs
from staticfx.effects.base import Effect
from staticfx.themes import Theme

NOISE_SHADE = " .:-=+*#%@"


class StaticNoise(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.t = 0.0

    def advance(self, dt: float) -> None:
        self.t += dt

    def render(self, frame: Frame, theme: Theme) -> None:
        palette = self.palette(theme)
        top = len(palette) - 1
        random = self.rng.random
        band = (self.t * 0.22) % 1.4 * self.height - self.height * 0.2

        for y in range(self.height):
            # A slow dark roll-bar drifts down the screen.
            dim = 0.45 if abs(y - band) < max(1.5, self.height * 0.06) else 1.0

            for x in range(self.width):
                v = random() ** 0.8 * dim
                index = int(v * 9)

                if index:
                    frame.put(x, y, NOISE_SHADE[index], palette[int(v * top)])


class TVGlitch(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.t = 0.0
        self.roll = 0.0
        self.roll_speed = 0.0
        self.tears: list[list[float]] = []
        self.cooldown = 0.0

    def on_resize(self) -> None:
        self.tears = []

    def advance(self, dt: float) -> None:
        rng = self.rng
        self.t += dt
        self.cooldown -= dt
        self.roll += self.roll_speed * dt
        self.roll_speed *= max(0.0, 1.0 - 3.0 * dt)

        for tear in self.tears:
            tear[3] -= dt

        self.tears = [tear for tear in self.tears if tear[3] > 0.0]

        if self.cooldown <= 0.0:
            self.cooldown = rng.uniform(0.08, 0.5)

            for _ in range(rng.randint(1, 3)):
                self.tears.append(
                    [
                        rng.randrange(self.height),
                        rng.randint(1, max(1, self.height // 7)),
                        rng.randint(-self.width // 4, max(1, self.width // 4)),
                        rng.uniform(0.06, 0.3),
                    ]
                )

            if rng.random() < 0.12:
                self.roll_speed = rng.uniform(15.0, 40.0)

    def render(self, frame: Frame, theme: Theme) -> None:
        rng = self.rng
        palette = self.palette(theme)
        top = len(palette) - 1
        roll = int(self.roll)
        shifts = {}

        for start, size, shift, _ in self.tears:
            for row in range(int(start), int(start + size)):
                shifts[row % self.height] = int(shift)

        for y in range(self.height):
            row_shift = shifts.get(y)
            noisy = row_shift is not None and rng.random() < 0.55

            for x in range(self.width):
                if noisy:
                    v = rng.random()
                    char = NOISE_SHADE[int(v * 9)]
                else:
                    sx = x - (row_shift or 0)
                    checker = ((sx // 6) + ((y + roll) // 3)) & 1
                    v = 0.5 if checker else 0.14

                    if rng.random() < 0.04:
                        v = rng.random()

                    char = NOISE_SHADE[int(v * 9)]

                if char != " ":
                    frame.put(x, y, char, palette[int(v * top)])


class SignalScramble(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.t = 0.0
        self.pool = tech_glyphs(unicode)
        self.bursts: list[list[float]] = []
        self.cooldown = 0.0

    def on_resize(self) -> None:
        self.bursts = []

    def advance(self, dt: float) -> None:
        rng = self.rng
        self.t += dt
        self.cooldown -= dt

        for burst in self.bursts:
            burst[2] -= dt

        self.bursts = [burst for burst in self.bursts if burst[2] > 0.0]

        if self.cooldown <= 0.0:
            self.cooldown = rng.uniform(0.15, 0.7)
            start = rng.randrange(self.width)
            self.bursts.append(
                [start, start + rng.randint(4, max(5, self.width // 3)), rng.uniform(0.1, 0.4)]
            )

    def _wave(self, x: float, which: int) -> float:
        t = self.t
        cy = (self.height - 1) / 2
        amp = self.height * (0.32 - 0.07 * which)

        return cy + amp * (
            math.sin(x * (0.11 + 0.04 * which) + t * (2.0 + which))
            * (0.6 + 0.4 * math.sin(x * 0.03 - t * 0.8))
            + 0.25 * math.sin(x * 0.37 + t * 5.0)
        )

    def render(self, frame: Frame, theme: Theme) -> None:
        rng = self.rng
        tones = (0.95, 0.65, 0.4)

        for which, tone in enumerate(tones):
            color = self.color_at(theme, tone)

            for x in range(self.width):
                y = self._wave(x, which)
                slope = self._wave(x + 1, which) - y
                char = "\\" if slope > 0.7 else "/" if slope < -0.7 else "-"
                frame.put(x, round(y), char, color)

        bright = theme.bright

        for start, end, _ in self.bursts:
            for x in range(int(start), min(self.width, int(end))):
                jitter = rng.randint(-3, 3)
                y = round(self._wave(x, 0)) + jitter
                frame.put(x, y, rng.choice(self.pool), bright)
                frame.put(
                    x, y + rng.choice((-1, 1)), rng.choice(self.pool), self.color_at(theme, 0.5)
                )


class WaveBars(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.levels: list[float] = []
        self.targets: list[float] = []
        self.peaks: list[float] = []
        self.t = 0.0

    def on_resize(self) -> None:
        count = max(1, self.width // 3)
        self.levels = [0.0] * count
        self.targets = [0.0] * count
        self.peaks = [0.0] * count

    def advance(self, dt: float) -> None:
        rng = self.rng
        count = len(self.levels)
        self.t += dt

        for i in range(count):
            if rng.random() < 5.0 * dt:
                shape = 0.3 + 0.7 * math.sin(math.pi * (i + 0.5) / count)
                self.targets[i] = shape * rng.random() ** 0.6

            gain = 14.0 if self.targets[i] > self.levels[i] else 4.0
            self.levels[i] += (self.targets[i] - self.levels[i]) * min(1.0, gain * dt)
            self.peaks[i] = max(self.levels[i], self.peaks[i] - 0.35 * dt)

    def render(self, frame: Frame, theme: Theme) -> None:
        block = "█" if self.unicode else "#"
        height = self.height

        for i, level in enumerate(self.levels):
            filled = int(level * (height - 1) + 0.5)
            peak = int(self.peaks[i] * (height - 1) + 0.5)

            for row in range(filled):
                y = height - 1 - row
                color = self.color_at(theme, 0.25 + 0.75 * (row / max(1, height - 1)))

                for dx in (0, 1):
                    frame.put(i * 3 + dx, y, block, color)

            if peak > 0:
                for dx in (0, 1):
                    frame.put(i * 3 + dx, height - 1 - peak, "=", theme.bright)


class ElectricStorm(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.bolts: list[dict] = []
        self.flash = 0.0
        self.cooldown = 0.3

    def on_resize(self) -> None:
        self.bolts = []

    def _make_bolt(self) -> dict:
        rng = self.rng
        x = rng.randrange(self.width)
        cells: list[tuple[int, int, str]] = []
        stack = [(x, 0, 1.0)]

        while stack:
            bx, by, vigor = stack.pop()

            while by < self.height and 0 <= bx < self.width:
                step = rng.choice((-1, 0, 0, 1))
                char = "/" if step < 0 else "\\" if step > 0 else "|"
                cells.append((bx, by, char))
                bx += step
                by += 1

                if vigor > 0.5 and rng.random() < 0.07:
                    stack.append((bx, by, vigor * 0.5))

                if vigor < 0.5 and rng.random() < 0.12:
                    break

        life = rng.uniform(0.25, 0.5)
        return {"cells": cells, "life": life, "max": life}

    def advance(self, dt: float) -> None:
        rng = self.rng
        self.cooldown -= dt
        self.flash = max(0.0, self.flash - dt * 4.0)

        if self.cooldown <= 0.0:
            self.cooldown = rng.uniform(0.35, 1.6)

            for _ in range(rng.choice((1, 1, 2))):
                self.bolts.append(self._make_bolt())

            self.flash = 1.0

        for bolt in self.bolts:
            bolt["life"] -= dt

        self.bolts = [bolt for bolt in self.bolts if bolt["life"] > 0.0]

    def render(self, frame: Frame, theme: Theme) -> None:
        rng = self.rng

        # Ambient crackle, brighter right after a strike.
        density = 0.004 + 0.05 * self.flash
        color = self.color_at(theme, 0.2 + 0.4 * self.flash)

        for _ in range(int(self.width * self.height * density)):
            frame.put(
                rng.randrange(self.width), rng.randrange(self.height), rng.choice(".:'`"), color
            )

        for bolt in self.bolts:
            fade = clamp(bolt["life"] / bolt["max"])
            bolt_color = theme.bright if fade > 0.5 else self.color_at(theme, 0.4 + fade)

            for x, y, char in bolt["cells"]:
                frame.put(x, y, char, bolt_color)
