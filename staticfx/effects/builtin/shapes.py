"""Wireframes and curves: a cube, a tesseract, spirographs, Lissajous figures, a DNA helix."""

from __future__ import annotations

import itertools
import math
import random

from staticfx.core.color import clamp
from staticfx.core.frame import Frame
from staticfx.effects.base import Effect
from staticfx.effects.builtin.geometry import (
    CUBE_EDGES,
    Projected,
    Vec3,
    cube_vertices,
    line_points,
    project,
    rotate,
)
from staticfx.themes import Theme


def _draw_segment(
    effect: Effect, frame: Frame, theme: Theme, a: Projected, b: Projected, tone: float
) -> None:
    """Draw one edge between two projected points, shaded by depth."""
    chars = "#" if tone > 0.66 else "+" if tone > 0.38 else "."
    color = effect.color_at(theme, 0.2 + 0.8 * tone)

    for x, y in line_points(int(a.x), int(a.y), int(b.x), int(b.y), limit=512):
        frame.put(x, y, chars, color)


class Cube(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.t = 0.0
        self.vertices = cube_vertices(1.6)
        self.focal = 40.0

    def on_resize(self) -> None:
        self.focal = max(8.0, min(self.height * 3.2, self.width * 1.1))

    def advance(self, dt: float) -> None:
        self.t += dt

    def render(self, frame: Frame, theme: Theme) -> None:
        t = self.t
        rotated = [rotate(v, t * 0.7, t * 1.1, t * 0.3) for v in self.vertices]
        points = [project(v, self.width, self.height, self.focal, 4.0) for v in rotated]

        for start, end in CUBE_EDGES:
            a, b = points[start], points[end]

            if a is None or b is None:
                continue

            depth = (a.depth + b.depth) / 2
            _draw_segment(self, frame, theme, a, b, clamp(1.6 - (depth - 2.6) / 2.4))

        for point in points:
            if point is not None:
                frame.put(int(point.x), int(point.y), "@", theme.bright)


def _rotate_4d(
    point: tuple[float, ...], angle_xw: float, angle_zw: float, angle_xy: float
) -> tuple[float, float, float, float]:
    x, y, z, w = point

    c, s = math.cos(angle_xw), math.sin(angle_xw)
    x, w = x * c - w * s, x * s + w * c

    c, s = math.cos(angle_zw), math.sin(angle_zw)
    z, w = z * c - w * s, z * s + w * c

    c, s = math.cos(angle_xy), math.sin(angle_xy)
    x, y = x * c - y * s, x * s + y * c

    return x, y, z, w


class Tesseract(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.t = 0.0
        self.focal = 40.0
        self.vertices = [
            tuple(0.7 * s for s in signs) for signs in itertools.product((-1, 1), repeat=4)
        ]
        self.edges = [
            (i, j)
            for i in range(16)
            for j in range(i + 1, 16)
            if sum(a != b for a, b in zip(self.vertices[i], self.vertices[j], strict=True)) == 1
        ]

    def on_resize(self) -> None:
        self.focal = max(8.0, min(self.height * 3.0, self.width * 1.0))

    def advance(self, dt: float) -> None:
        self.t += dt

    def render(self, frame: Frame, theme: Theme) -> None:
        t = self.t
        projected = []

        for vertex in self.vertices:
            x, y, z, w = _rotate_4d(vertex, t * 0.55, t * 0.8, t * 0.25)
            scale = 1.0 / (2.2 - w)
            point3 = Vec3(x * scale * 2.2, y * scale * 2.2, z * scale * 2.2)

            point3 = rotate(point3, t * 0.3, t * 0.4, 0.0)
            projected.append((project(point3, self.width, self.height, self.focal, 4.0), w))

        for start, end in self.edges:
            (a, wa), (b, wb) = projected[start], projected[end]

            if a is None or b is None:
                continue

            tone = clamp(0.55 + 0.35 * (wa + wb))
            _draw_segment(self, frame, theme, a, b, tone)

        for point, _ in projected:
            if point is not None:
                frame.put(int(point.x), int(point.y), "@", theme.bright)


class Spirograph(Effect):
    RATIOS = ((5, 3), (7, 3), (8, 3), (7, 5), (9, 4), (11, 4), (5, 2), (13, 5))

    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.theta = 0.0
        self.pick()

    def pick(self) -> None:
        big, small = self.rng.choice(self.RATIOS)
        self.big = float(big)
        self.small = float(small)
        self.offset = self.small * self.rng.uniform(0.6, 1.0)
        self.limit = (self.big - self.small) + self.offset
        self.span = math.tau * (self.small / math.gcd(big, small))

    def on_reset(self) -> None:
        self.theta = 0.0
        self.pick()

    def advance(self, dt: float) -> None:
        self.theta += dt * 1.8

        if self.theta > self.span * 3.2:
            self.on_reset()

    def render(self, frame: Frame, theme: Theme) -> None:
        samples = 520
        tail = min(self.span, 14.0)
        scale = (self.height / 2 - 1.0) / self.limit
        cx = (self.width - 1) / 2
        cy = (self.height - 1) / 2
        ratio = (self.big - self.small) / self.small

        for index in range(samples):
            fraction = index / samples
            angle = self.theta - tail * (1.0 - fraction)

            if angle < 0:
                continue

            px = (self.big - self.small) * math.cos(angle) + self.offset * math.cos(ratio * angle)
            py = (self.big - self.small) * math.sin(angle) - self.offset * math.sin(ratio * angle)
            tone = 0.15 + 0.85 * fraction
            char = (
                "@" if index == samples - 1 else "*" if tone > 0.6 else "+" if tone > 0.35 else "."
            )

            frame.put(
                int(cx + px * scale * 2.0), int(cy + py * scale), char, self.color_at(theme, tone)
            )


class Lissajous(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.t = 0.0
        self.a = 3
        self.b = 2
        self.pick()

    def pick(self) -> None:
        self.a, self.b = self.rng.choice(
            ((3, 2), (3, 4), (5, 4), (5, 6), (1, 2), (2, 3), (4, 5), (5, 3))
        )

    def on_reset(self) -> None:
        self.t = 0.0
        self.pick()

    def advance(self, dt: float) -> None:
        self.t += dt

    def render(self, frame: Frame, theme: Theme) -> None:
        samples = 640
        cx = (self.width - 1) / 2
        cy = (self.height - 1) / 2
        ax = cx - 1.0
        ay = cy - 0.5
        drift = self.t * 0.35
        head = (self.t * 1.6) % 1.0

        for index in range(samples):
            u = math.tau * index / samples
            x = math.sin(self.a * u + drift)
            y = math.sin(self.b * u)
            fraction = ((index / samples) - head) % 1.0
            tone = 0.15 + 0.85 * (1.0 - fraction)
            char = "@" if fraction < 0.01 else "*" if tone > 0.6 else "+" if tone > 0.35 else "."

            frame.put(int(cx + x * ax), int(cy + y * ay), char, self.color_at(theme, tone))


class DNAHelix(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.t = 0.0

    def advance(self, dt: float) -> None:
        self.t += dt

    def render(self, frame: Frame, theme: Theme) -> None:
        cx = (self.width - 1) / 2
        amplitude = max(3.0, min(self.width * 0.22, 14.0))
        draw_list = []

        for y in range(self.height):
            phase = y * 0.42 + self.t * 2.2
            sine, cosine = math.sin(phase), math.cos(phase)

            if y % 3 == 0:
                left = int(cx - amplitude * sine)
                right = int(cx + amplitude * sine)
                rung = self.color_at(theme, 0.3)

                for x in range(min(left, right) + 1, max(left, right)):
                    frame.put(x, y, "-", rung)

            draw_list.append((cosine, int(cx + amplitude * sine), y))
            draw_list.append((-cosine, int(cx - amplitude * sine), y))

        for depth, x, y in sorted(draw_list):
            near = 0.5 + 0.5 * depth
            char = "@" if near > 0.8 else "O" if near > 0.5 else "o"
            frame.put(x, y, char, self.color_at(theme, 0.25 + 0.75 * near))
