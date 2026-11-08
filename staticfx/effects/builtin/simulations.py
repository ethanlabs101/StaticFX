"""Grids that evolve step by step: cellular automata, Langton's ant, a maze, fire and smoke."""

from __future__ import annotations

import random
from collections import deque

from staticfx.core.frame import Frame
from staticfx.effects.base import Effect
from staticfx.themes import Theme

MAX_STEPS_PER_FRAME = 12


class GridSimulation(Effect):
    """Fixed-timestep simulation over ``grid[y][x]``.

    ``advance`` runs as many ``step`` calls as the elapsed time covers, capped
    so a slow frame can't trigger a long catch-up burst.
    """

    interval = 0.1
    empty: object = 0

    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.grid: list[list] = []
        self.timer = 0.0

    def on_resize(self) -> None:
        self.grid = [[self.empty] * self.width for _ in range(self.height)]
        self.timer = 0.0
        self.seed_grid()

    def seed_grid(self) -> None:
        """Populate the freshly built grid."""

    def step(self) -> None:
        raise NotImplementedError

    def advance(self, dt: float) -> None:
        self.timer += dt
        for _ in range(MAX_STEPS_PER_FRAME):
            if self.timer < self.interval:
                return
            self.timer -= self.interval
            self.step()
        self.timer = 0.0


# Cellular automata
class LifeLike(GridSimulation):
    """Birth/survival rule automaton (Conway's Life is B3/S23).

    Cells fade out over a few steps (``trail``) so motion reads clearly, and
    the board reseeds itself when it dies out or settles into a short loop.
    """

    interval = 0.09

    def __init__(
        self,
        rng: random.Random,
        unicode: bool = False,
        birth: frozenset[int] | set[int] = frozenset({3}),
        survive: frozenset[int] | set[int] = frozenset({2, 3}),
        fill: float = 0.28,
        interval: float | None = None,
        trail: float = 0.82,
    ) -> None:
        super().__init__(rng, unicode)

        self.birth = frozenset(birth)
        self.survive = frozenset(survive)
        self.fill = fill
        self.trail = trail

        if interval is not None:
            self.interval = interval

        self.glow: list[list[float]] = []
        self.history: deque[int] = deque(maxlen=14)
        self.hold = 0.0

    def seed_grid(self) -> None:
        fill = self.fill
        self.grid = [
            [1 if self.rng.random() < fill else 0 for _ in range(self.width)]
            for _ in range(self.height)
        ]
        self.glow = [[float(c) for c in row] for row in self.grid]
        self.history.clear()
        self.hold = 0.0

    def step(self) -> None:
        width, height = self.width, self.height
        grid = self.grid
        birth, survive = self.birth, self.survive
        trail = self.trail
        new_grid: list[list[int]] = []
        population = 0

        for y in range(height):
            above = grid[(y - 1) % height]
            row = grid[y]
            below = grid[(y + 1) % height]
            glow_row = self.glow[y]
            out = []

            for x in range(width):
                left = x - 1
                right = (x + 1) % width
                total = (
                    above[left]
                    + above[x]
                    + above[right]
                    + row[left]
                    + row[right]
                    + below[left]
                    + below[x]
                    + below[right]
                )

                alive = 1 if (total in survive if row[x] else total in birth) else 0
                population += alive
                out.append(alive)
                glow_row[x] = 1.0 if alive else glow_row[x] * trail

            new_grid.append(out)

        self.grid = new_grid

        signature = hash((population, tuple(map(tuple, new_grid[:: max(1, height // 6)]))))

        if population == 0 or signature in self.history:
            self.hold += self.interval
        else:
            self.hold = 0.0

        self.history.append(signature)

        if self.hold > 1.6 or population < width * height * 0.003:
            self.seed_grid()

    def render(self, frame: Frame, theme: Theme) -> None:
        palette = self.palette(theme)
        top = len(palette) - 1

        for y, row in enumerate(self.glow):
            for x, glow in enumerate(row):
                if glow < 0.08:
                    continue

                char = "#" if glow >= 0.99 else "+" if glow > 0.5 else "."
                frame.put(x, y, char, palette[int((0.2 + 0.8 * glow) * top)])


class Rule30(GridSimulation):
    interval = 0.05

    def __init__(self, rng: random.Random, unicode: bool = False, rule: int = 30) -> None:
        super().__init__(rng, unicode)
        self.rule = rule & 0xFF

    def seed_grid(self) -> None:
        first = [0] * self.width
        first[self.width // 2] = 1
        self.grid = [first]

        while len(self.grid) < self.height:
            self.step()

    def step(self) -> None:
        previous = self.grid[-1]
        width = len(previous)
        rule = self.rule

        row = [
            (rule >> (previous[i - 1] << 2 | previous[i] << 1 | previous[(i + 1) % width])) & 1
            for i in range(width)
        ]

        self.grid.append(row)

        if len(self.grid) > self.height:
            self.grid.pop(0)

    def render(self, frame: Frame, theme: Theme) -> None:
        rows = len(self.grid)

        for y, row in enumerate(self.grid):
            recency = (y + 1) / rows
            color = self.color_at(theme, 0.25 + 0.75 * recency)

            for x, cell in enumerate(row):
                if cell:
                    frame.put(x, y, "#", color)


class LangtonAnt(GridSimulation):
    """Langton's ant, generalised to multi-colour turn rules (e.g. "RLLR")."""

    interval = 0.03

    DIRECTIONS = ((0, -1), (1, 0), (0, 1), (-1, 0))

    def __init__(
        self,
        rng: random.Random,
        unicode: bool = False,
        rule: str = "RL",
        ants: int = 1,
        moves: int = 40,
    ) -> None:
        super().__init__(rng, unicode)

        self.rule = rule
        self.ant_count = ants
        self.moves = moves
        self.ants: list[list[int]] = []
        self.total = 0

    def seed_grid(self) -> None:
        rng = self.rng
        self.total = 0
        self.ants = [
            [
                (self.width // 2 + (rng.randint(-6, 6) if self.ant_count > 1 else 0)) % self.width,
                (self.height // 2 + (rng.randint(-3, 3) if self.ant_count > 1 else 0))
                % self.height,
                rng.randrange(4),
            ]
            for _ in range(self.ant_count)
        ]

    def step(self) -> None:
        grid = self.grid
        rule = self.rule
        colors = len(rule)
        width, height = self.width, self.height

        for _ in range(self.moves):
            for ant in self.ants:
                x, y, heading = ant
                value = grid[y][x]
                heading = (heading + (1 if rule[value] == "R" else 3)) % 4
                grid[y][x] = (value + 1) % colors
                dx, dy = self.DIRECTIONS[heading]
                ant[0] = (x + dx) % width
                ant[1] = (y + dy) % height
                ant[2] = heading

        self.total += self.moves * len(self.ants)

        if self.total > 220_000:
            self.on_resize()

    def render(self, frame: Frame, theme: Theme) -> None:
        colors = len(self.rule)
        glyphs = ".:+*#%@&"
        palette = self.palette(theme)
        top = len(palette) - 1

        for y, row in enumerate(self.grid):
            for x, value in enumerate(row):
                if value:
                    tone = 0.3 + 0.55 * value / max(1, colors - 1)
                    frame.put(x, y, glyphs[min(value, len(glyphs) - 1)], palette[int(tone * top)])

        for x, y, _ in self.ants:
            frame.put(x, y, "@", theme.bright)


class Maze(GridSimulation):
    """Depth-first maze that is carved live, then regenerated."""

    interval = 0.012

    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.stack: list[tuple[int, int]] = []
        self.finished = 0.0

    empty = 1  # wall

    def seed_grid(self) -> None:
        self.stack = []
        self.finished = 0.0

        if self.width >= 5 and self.height >= 5:
            self.grid[1][1] = 0
            self.stack.append((1, 1))

    def step(self) -> None:
        if not self.stack:
            self.finished += self.interval * 6

            if self.finished > 3.5 and self.width >= 5 and self.height >= 5:
                self.on_resize()

            return

        rng = self.rng
        grid = self.grid

        for _ in range(3):
            if not self.stack:
                return

            x, y = self.stack[-1]
            options = [
                (x + dx * 2, y + dy * 2, dx, dy)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                if 1 <= x + dx * 2 < self.width - 1
                and 1 <= y + dy * 2 < self.height - 1
                and grid[y + dy * 2][x + dx * 2]
            ]

            if options:
                nx, ny, dx, dy = rng.choice(options)
                grid[y + dy][x + dx] = 0
                grid[ny][nx] = 0
                self.stack.append((nx, ny))
            else:
                self.stack.pop()

    def render(self, frame: Frame, theme: Theme) -> None:
        wall = self.color_at(theme, 0.45)
        char = "█" if self.unicode else "#"

        for y, row in enumerate(self.grid):
            for x, cell in enumerate(row):
                if cell:
                    frame.put(x, y, char, wall)

        if self.stack:
            x, y = self.stack[-1]
            frame.put(x, y, "@", theme.bright)


# Heat simulations (fire, smoke)
class Fire(GridSimulation):
    empty = 0.0
    interval = 0.04

    shade = " .,:;+*xX#%@"

    def step(self) -> None:
        rng = self.rng
        grid = self.grid
        width, height = self.width, self.height
        cooling = 3.6 / max(8, height)

        bottom = grid[-1]

        for x in range(width):
            bottom[x] = rng.uniform(0.75, 1.0) if rng.random() > 0.06 else 0.2

        for y in range(height - 1):
            row = grid[y]
            below = grid[y + 1]
            below2 = grid[min(y + 2, height - 1)]

            for x in range(width):
                heat = (below[x - 1] + below[x] + below[(x + 1) % width] + below2[x]) * 0.25
                row[x] = max(0.0, heat - rng.uniform(0.0, cooling))

    def render(self, frame: Frame, theme: Theme) -> None:
        palette = self.palette(theme)
        top = len(palette) - 1
        shade = self.shade
        last = len(shade) - 1

        for y, row in enumerate(self.grid):
            for x, heat in enumerate(row):
                index = int(heat * last + 0.5)

                if index > 0:
                    frame.put(x, y, shade[index], palette[int(min(1.0, heat) * top)])


class Smoke(GridSimulation):
    empty = 0.0
    interval = 0.06

    shade = " .:-=+*oO0"

    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.wind = 0

    def step(self) -> None:
        rng = self.rng
        grid = self.grid
        width, height = self.width, self.height

        if rng.random() < 0.08:
            self.wind = rng.choice((-1, 0, 0, 1))

        bottom = grid[-1]

        for x in range(width):
            bottom[x] *= 0.5

        if rng.random() < 0.55:
            center = rng.randrange(width)

            for dx in range(-rng.randint(1, 4), rng.randint(2, 5)):
                bottom[(center + dx) % width] = rng.uniform(0.6, 0.95)

        wind = self.wind

        for y in range(height - 1):
            row = grid[y]
            below = grid[y + 1]

            for x in range(width):
                source = x + wind
                mixed = (
                    below[(source - 1) % width]
                    + below[source % width]
                    + below[(source + 1) % width]
                ) / 3.0
                row[x] = mixed * 0.94 - 0.004

    def render(self, frame: Frame, theme: Theme) -> None:
        palette = self.palette(theme)
        top = len(palette) - 1
        shade = self.shade
        last = len(shade) - 1

        for y, row in enumerate(self.grid):
            for x, density in enumerate(row):
                index = int(density * last + 0.5)

                if index > 0:
                    frame.put(
                        x, y, shade[index], palette[int((0.15 + 0.6 * min(1.0, density)) * top)]
                    )
