"""Things that move: glyph rain, drifting particles, stars, meteors, fireworks, orbits."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from staticfx.core.color import RGB, clamp, tint
from staticfx.core.frame import Frame
from staticfx.core.glyphs import tech_glyphs
from staticfx.effects.base import Effect
from staticfx.themes import Theme

BLOCK_CHARS = list("#%@&8$X")
UNICODE_BLOCKS = list("█▓▒░")


@dataclass(slots=True)
class Particle:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 1.0
    char: str = "*"
    life: float = 1.0
    max_life: float = 1.0
    tone: float = 0.8
    phase: float = 0.0
    rocket: bool = False


class ParticleSystem(Effect):
    """Physics particles with gravity, lifetimes and an emitter hook."""

    gravity = 0.0

    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.particles: list[Particle] = []

    def spawn(self, particle: Particle) -> None:
        self.particles.append(particle)

    def emit(self, dt: float) -> None:
        """Override to spawn new particles each step."""

    def on_expire(self, particle: Particle) -> None:
        """Called once for each particle whose life ran out."""

    def in_bounds(self, particle: Particle) -> bool:
        return -4 <= particle.x < self.width + 4 and -4 <= particle.y < self.height + 4

    def on_resize(self) -> None:
        self.particles.clear()

    def advance(self, dt: float) -> None:
        self.emit(dt)

        gravity = self.gravity
        expired: list[Particle] = []
        survivors: list[Particle] = []

        for particle in self.particles:
            particle.vy += gravity * dt
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.life -= dt

            if particle.life <= 0.0:
                expired.append(particle)
            elif self.in_bounds(particle):
                survivors.append(particle)

        self.particles = survivors

        for particle in expired:
            self.on_expire(particle)

    def particle_color(self, theme: Theme, particle: Particle) -> RGB:
        fade = clamp(particle.life / particle.max_life)
        return self.color_at(theme, particle.tone * (0.3 + 0.7 * fade))

    def render(self, frame: Frame, theme: Theme) -> None:
        for particle in self.particles:
            x = int(particle.x)
            y = int(particle.y)

            if 0 <= x < self.width and 0 <= y < self.height:
                frame.put(x, y, particle.char, self.particle_color(theme, particle))


# Rain
class _Column:
    __slots__ = ("glyphs", "head", "length", "speed")

    def __init__(self) -> None:
        self.head = 0.0
        self.speed = 0.0
        self.length = 1
        self.glyphs: list[str] = []


class ColumnRain(Effect):
    """Falling glyph columns with a bright head and fading tail."""

    def __init__(
        self,
        rng: random.Random,
        unicode: bool = False,
        pool: str | None = None,
        speed: float = 14.0,
        trail: int | None = None,
        density: float = 1.0,
        corrupt: bool = False,
    ) -> None:
        super().__init__(rng, unicode)

        self.pool = pool or tech_glyphs(unicode)
        self.speed = max(0.5, float(speed))
        self.trail = None if trail is None else max(2, int(trail))
        self.density = clamp(float(density), 0.05, 1.0)
        self.corrupt = corrupt

        self.columns: list[_Column] = []
        self.glitch_timer = 1.0
        self.glitch_hold = 0.0
        self.glitch_rect: tuple[int, int, int, int] | None = None

    def _recycle(self, column: _Column, initial: bool = False) -> None:
        height = self.height
        rng = self.rng

        if self.trail is not None:
            column.length = self.trail
        else:
            column.length = rng.randint(max(4, height // 4), max(8, int(height * 0.8)))

        gap = height * (1.0 / self.density)
        column.head = -rng.uniform(0.0, gap)

        if initial:
            column.head += rng.uniform(0.0, height)

        column.speed = self.speed * rng.uniform(0.45, 1.5)

        if len(column.glyphs) != height:
            column.glyphs = rng.choices(self.pool, k=height)

    def on_resize(self) -> None:
        self.columns = []

        for _ in range(self.width):
            column = _Column()
            self._recycle(column, initial=True)
            self.columns.append(column)

        self.glitch_rect = None
        self.glitch_timer = self.rng.uniform(1.0, 3.0)

    def advance(self, dt: float) -> None:
        rng = self.rng
        pool = self.pool
        height = self.height

        for column in self.columns:
            column.head += column.speed * dt

            if column.head - column.length > height:
                self._recycle(column)

            # Occasional glyph flicker inside the column.
            if rng.random() < 6.0 * dt:
                column.glyphs[rng.randrange(height)] = rng.choice(pool)

        if self.corrupt:
            self._advance_glitch(dt)

    def _advance_glitch(self, dt: float) -> None:
        rng = self.rng

        if self.glitch_rect is None:
            self.glitch_timer -= dt

            if self.glitch_timer <= 0.0 and self.width > 6 and self.height > 4:
                rect_w = rng.randint(3, max(4, self.width // 3))
                rect_h = rng.randint(1, max(2, self.height // 6))
                self.glitch_rect = (
                    rng.randint(0, max(0, self.width - rect_w)),
                    rng.randint(0, max(0, self.height - rect_h)),
                    rect_w,
                    rect_h,
                )
                self.glitch_hold = rng.uniform(0.12, 0.35)
                self.glitch_timer = rng.uniform(0.6, 2.5)
        else:
            self.glitch_hold -= dt

            if self.glitch_hold <= 0.0:
                self.glitch_rect = None

    def render(self, frame: Frame, theme: Theme) -> None:
        head_color = tint(theme.bright, 0.35)
        height = self.height

        for x, column in enumerate(self.columns):
            head = int(column.head)
            length = column.length

            for offset in range(length):
                y = head - offset

                if y < 0:
                    break

                if y >= height:
                    continue

                if offset == 0:
                    color = head_color
                else:
                    fraction = 1.0 - offset / length
                    color = self.color_at(theme, 0.08 + 0.82 * fraction**1.4)

                frame.put(x, y, column.glyphs[y], color)

        if self.corrupt and self.glitch_rect is not None:
            self._draw_glitch(frame, theme, self.glitch_rect)

    def _draw_glitch(self, frame: Frame, theme: Theme, rect: tuple[int, int, int, int]) -> None:
        rect_x, rect_y, rect_w, rect_h = rect
        blocks = UNICODE_BLOCKS if self.unicode else BLOCK_CHARS
        color = theme.accent

        for y in range(rect_y, rect_y + rect_h):
            for x in range(rect_x, rect_x + rect_w):
                frame.put(x, y, self.rng.choice(blocks), color)


# Ambient drifting particles (snow, sakura, embers, bubbles, confetti)
class DriftParticles(ParticleSystem):
    def __init__(
        self,
        rng: random.Random,
        unicode: bool = False,
        pool: str = "*+.",
        direction: int = 1,
        speed: tuple[float, float] = (2.0, 6.0),
        sway: float = 1.5,
        density: float = 0.03,
        twinkle: bool = False,
        tone: tuple[float, float] = (0.6, 1.0),
        multicolor: bool = False,
        count: int | None = None,
    ) -> None:
        super().__init__(rng, unicode)

        self.pool = list(pool)
        self.direction = 1 if direction > 0 else -1 if direction < 0 else 0
        self.speed_range = speed
        self.sway = sway
        self.density = density
        self.twinkle = twinkle
        self.tone_range = tone
        self.multicolor = multicolor
        self.count = count
        self.t = 0.0

    def _make(self, initial: bool) -> Particle:
        rng = self.rng
        width, height = self.width, self.height

        if initial or self.direction == 0:
            y = rng.uniform(0, height)
        elif self.direction > 0:
            y = -rng.uniform(0.0, 3.0)
        else:
            y = height + rng.uniform(0.0, 3.0)

        return Particle(
            x=rng.uniform(0, width),
            y=y,
            vy=rng.uniform(*self.speed_range) * self.direction,
            char=rng.choice(self.pool),
            tone=rng.uniform(*self.tone_range),
            phase=rng.uniform(0.0, math.tau),
            life=1.0,
            max_life=1.0,
        )

    def on_resize(self) -> None:
        count = self.count or max(10, int(self.width * self.height * self.density))
        self.particles = [self._make(True) for _ in range(count)]

    def advance(self, dt: float) -> None:
        self.t += dt
        width, height = self.width, self.height
        sway_t = self.t * 1.4

        for index, particle in enumerate(self.particles):
            particle.y += particle.vy * dt
            particle.x += math.sin(sway_t + particle.phase) * self.sway * dt
            particle.x %= width

            if (self.direction > 0 and particle.y >= height + 1) or (
                self.direction < 0 and particle.y < -1
            ):
                self.particles[index] = self._make(False)
            elif self.direction == 0:
                particle.y = (particle.y + math.sin(sway_t * 0.7 + particle.phase) * dt) % height

    def particle_color(self, theme: Theme, particle: Particle) -> RGB:
        if self.multicolor:
            colors = (theme.primary, theme.ramp(0.4), theme.accent, theme.bright, theme.ramp(0.85))
            return colors[int(particle.tone * 100) % len(colors)]

        tone = particle.tone

        if self.twinkle:
            tone *= 0.55 + 0.45 * math.sin(self.t * 4.0 + particle.phase)

        return self.color_at(theme, tone)


# Starfield / meteors
class Starfield(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False, speed: float = 0.45) -> None:
        super().__init__(rng, unicode)
        self.speed = speed
        self.stars: list[list[float]] = []

    def _star(self, near: bool = False) -> list[float]:
        rng = self.rng
        return [
            rng.uniform(-1.0, 1.0),
            rng.uniform(-1.0, 1.0),
            rng.uniform(0.05, 1.0) if near else 1.0,
        ]

    def on_resize(self) -> None:
        count = max(30, self.width * self.height // 14)
        self.stars = [self._star(near=True) for _ in range(count)]

    def advance(self, dt: float) -> None:
        for index, star in enumerate(self.stars):
            star[2] -= self.speed * dt * (1.3 - star[2] * 0.5)

            if star[2] <= 0.03:
                self.stars[index] = self._star()

    def render(self, frame: Frame, theme: Theme) -> None:
        cx = (self.width - 1) / 2
        cy = (self.height - 1) / 2

        for index, (sx, sy, z) in enumerate(self.stars):
            x = int(cx + sx / z * cx * 0.45)
            y = int(cy + sy / z * cy * 0.45)

            if not (0 <= x < self.width and 0 <= y < self.height):
                self.stars[index] = self._star()
                continue

            closeness = 1.0 - z
            char = "*" if z < 0.3 else "+" if z < 0.6 else "."
            frame.put(x, y, char, self.color_at(theme, 0.25 + 0.75 * closeness))


class MeteorShower(Effect):
    """Streaks across a dim, twinkling sky."""

    def __init__(self, rng: random.Random, unicode: bool = False, rate: float = 5.0) -> None:
        super().__init__(rng, unicode)
        self.rate = rate
        self.t = 0.0
        self.meteors: list[list[float]] = []  # [x, y, vx, vy, length]
        self.sky: list[tuple[int, int, str, float]] = []  # [x, y, glyph, phase]

    def on_resize(self) -> None:
        rng = self.rng
        self.meteors.clear()
        self.sky = [
            (
                rng.randrange(self.width),
                rng.randrange(self.height),
                rng.choice(".'`+"),
                rng.random(),
            )
            for _ in range(max(8, self.width * self.height // 45))
        ]

    def advance(self, dt: float) -> None:
        rng = self.rng
        self.t += dt

        if rng.random() < self.rate * dt * max(1.0, self.width / 80):
            speed = rng.uniform(14.0, 30.0)
            x = rng.uniform(0, self.width + self.height * 1.5)
            self.meteors.append([x, -2.0, -speed * 1.6, speed * 0.8, rng.randint(6, 16)])

        for meteor in self.meteors:
            meteor[0] += meteor[2] * dt
            meteor[1] += meteor[3] * dt
        self.meteors = [m for m in self.meteors if m[1] < self.height + 2 and m[0] > -m[4] * 2]

    def render(self, frame: Frame, theme: Theme) -> None:
        for sx, sy, glyph, phase in self.sky:
            twinkle = 0.5 + 0.5 * math.sin(self.t * 1.7 + phase * math.tau)
            frame.put(sx, sy, glyph, self.color_at(theme, 0.08 + 0.22 * twinkle))

        for x, y, vx, vy, length in self.meteors:
            major = max(abs(vx), abs(vy))
            dx, dy = vx / major, vy / major
            for index in range(int(length)):
                fade = 1.0 - index / length
                char = "*" if index == 0 else "+" if index < 3 else ":" if fade > 0.4 else "."
                frame.put(
                    int(x - dx * index),
                    int(y - dy * index),
                    char,
                    self.color_at(theme, 0.15 + 0.85 * fade),
                )


# Fireworks / fountain
class Fireworks(ParticleSystem):
    gravity = 9.0

    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.cooldown = 0.2

    def on_resize(self) -> None:
        super().on_resize()
        self.cooldown = 0.2

    def emit(self, dt: float) -> None:
        self.cooldown -= dt

        if self.cooldown > 0.0:
            return

        rng = self.rng
        # Launch more often on wide terminals so the sky never looks empty.
        self.cooldown = rng.uniform(0.3, 0.9) * 80 / max(40, self.width)
        target = rng.uniform(self.height * 0.12, self.height * 0.55)
        rise = max(2.0, self.height - target)
        vy = -math.sqrt(2.0 * self.gravity * rise)

        self.spawn(
            Particle(
                x=rng.uniform(self.width * 0.15, self.width * 0.85),
                y=self.height - 1.0,
                vx=rng.uniform(-2.0, 2.0),
                vy=vy,
                char="|",
                life=-vy / self.gravity,
                max_life=3.0,
                tone=0.9,
                rocket=True,
            )
        )

    def on_expire(self, particle: Particle) -> None:
        if not particle.rocket:
            return

        rng = self.rng
        count = rng.randint(40, 80)
        power = max(5.0, self.height * rng.uniform(0.18, 0.32))
        tone = rng.uniform(0.55, 1.0)
        chars = "*+o." if not self.unicode else "*+✦·"

        for index in range(count):
            angle = math.tau * index / count + rng.uniform(-0.1, 0.1)
            speed = power * rng.uniform(0.55, 1.0)
            life = rng.uniform(0.9, 1.7)

            self.spawn(
                Particle(
                    x=particle.x,
                    y=particle.y,
                    vx=math.cos(angle) * speed * 2.0,
                    vy=math.sin(angle) * speed,
                    char=rng.choice(chars),
                    life=life,
                    max_life=life,
                    tone=tone,
                )
            )

    def particle_color(self, theme: Theme, particle: Particle) -> RGB:
        if particle.rocket:
            return self.color_at(theme, 0.5)

        return super().particle_color(theme, particle)


class Fountain(ParticleSystem):
    gravity = 16.0

    def in_bounds(self, particle: Particle) -> bool:
        return -6 <= particle.x < self.width + 6 and particle.y < self.height

    def emit(self, dt: float) -> None:
        rng = self.rng
        count = int(rng.gauss(110.0 * dt, 1.0)) if dt > 0 else 0

        for _ in range(max(0, count)):
            reach = self.height * rng.uniform(0.35, 0.85)
            vy = -math.sqrt(2.0 * self.gravity * reach)

            self.spawn(
                Particle(
                    x=self.width / 2 + rng.gauss(0.0, 1.0),
                    y=self.height - 2.0,
                    vx=rng.gauss(0.0, 5.0),
                    vy=vy,
                    char=rng.choice("o.:*"),
                    life=6.0,
                    max_life=6.0,
                    tone=rng.uniform(0.55, 1.0),
                )
            )


# Orbiting particles: vortex / orbit dance / gravity well
class OrbitalParticles(Effect):
    """Particles in normalised polar space around the screen centre."""

    def __init__(self, rng: random.Random, unicode: bool = False, mode: str = "vortex") -> None:
        super().__init__(rng, unicode)
        self.mode = mode
        self.bodies: list[list[float]] = []  # [x, y, vx, vy] or [r, a, w, ring]

    def on_resize(self) -> None:
        rng = self.rng
        self.bodies = []

        if self.mode == "orbit":
            rings = max(3, min(9, self.height // 3))

            for ring in range(1, rings + 1):
                radius = 0.12 + 0.85 * ring / rings
                count = 3 + ring * 3
                omega = (1.5 if ring % 2 else -1.5) / math.sqrt(radius)
                offset = rng.uniform(0, math.tau)

                for index in range(count):
                    self.bodies.append(
                        [radius, offset + math.tau * index / count, omega, float(ring)]
                    )
        elif self.mode == "well":
            for _ in range(max(40, self.width * self.height // 30)):
                self.bodies.append(self._well_body())
        else:
            for _ in range(max(60, self.width * self.height // 22)):
                self.bodies.append(self._vortex_body(initial=True))

    def _vortex_body(self, initial: bool = False) -> list[float]:
        rng = self.rng
        radius = rng.uniform(0.05, 1.5) if initial else rng.uniform(1.0, 1.6)
        return [radius, rng.uniform(0, math.tau), 0.0, 0.0]

    def _well_body(self) -> list[float]:
        rng = self.rng
        angle = rng.uniform(0, math.tau)
        radius = rng.uniform(1.0, 1.5)
        tangent = rng.uniform(0.25, 0.7) * rng.choice((-1, 1))
        return [
            math.cos(angle) * radius,
            math.sin(angle) * radius,
            -math.sin(angle) * tangent,
            math.cos(angle) * tangent,
        ]

    def advance(self, dt: float) -> None:
        if self.mode == "orbit":
            for body in self.bodies:
                body[1] += body[2] * dt
        elif self.mode == "well":
            for index, body in enumerate(self.bodies):
                x, y, vx, vy = body
                dist2 = x * x + y * y + 0.02
                pull = 0.55 / (dist2 * math.sqrt(dist2))
                vx -= x * pull * dt
                vy -= y * pull * dt
                body[0] = x + vx * dt
                body[1] = y + vy * dt
                body[2], body[3] = vx, vy

                if dist2 < 0.025 or dist2 > 6.0:
                    self.bodies[index] = self._well_body()
        else:
            for index, body in enumerate(self.bodies):
                radius = body[0]
                body[1] += (0.9 / (radius + 0.18)) * dt
                body[0] = radius - (0.07 + 0.1 / (radius + 0.3)) * dt

                if body[0] < 0.03:
                    self.bodies[index] = self._vortex_body()

    def _to_screen(self, px: float, py: float) -> tuple[int, int]:
        half = self.height / 2
        return (int((self.width - 1) / 2 + px * half * 2.0), int((self.height - 1) / 2 + py * half))

    def render(self, frame: Frame, theme: Theme) -> None:
        if self.mode == "orbit":
            cx, cy = self._to_screen(0.0, 0.0)
            frame.put(cx, cy, "@", theme.bright)

        for body in self.bodies:
            if self.mode == "well":
                px, py = body[0], body[1]
                radius = math.hypot(px, py)
            else:
                radius = body[0]
                px = math.cos(body[1]) * radius
                py = math.sin(body[1]) * radius

            x, y = self._to_screen(px, py)
            near = clamp(1.0 - radius / 1.4)
            char = "@" if near > 0.8 else "O" if near > 0.55 else "o" if near > 0.3 else "."
            frame.put(x, y, char, self.color_at(theme, 0.2 + 0.8 * near))
