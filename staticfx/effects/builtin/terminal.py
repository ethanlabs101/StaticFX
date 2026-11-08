"""Retro computing: a boot log, decryption, a barcode scanner, circuit traces."""

from __future__ import annotations

import math
import random

from staticfx.core.color import clamp
from staticfx.core.frame import Frame
from staticfx.core.glyphs import HEX, tech_glyphs
from staticfx.effects.base import Effect
from staticfx.themes import Theme

SERVICES = (
    "udev",
    "journald",
    "network",
    "dbus",
    "cryptsetup",
    "sshd",
    "firewall",
    "audio daemon",
    "display manager",
    "scheduler",
    "time sync",
    "kernel modules",
    "power manager",
    "entropy pool",
    "mesh uplink",
    "neural cache",
)

DEVICES = ("/dev/sda1", "/dev/nvme0n1p2", "/dev/mapper/root", "/dev/loop7", "/dev/sr0")

WORDS = (
    "ACCESS GRANTED KERNEL PAYLOAD ROOT DECRYPT SECTOR HANDSHAKE TOKEN BYPASS FIREWALL NODE SIGNAL"
    " CIPHER BREACH UPLINK PROXY DAEMON SHELL EXPLOIT"
).split()


class TerminalBoot(Effect):
    TOTAL_LINES = 90

    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.lines: list[str] = []
        self.cooldown = 0.0
        self.emitted = 0
        self.hold = 0.0
        self.memory = 0
        self.t = 0.0

    def on_resize(self) -> None:
        self.lines = []
        self.emitted = 0
        self.hold = 0.0
        self.memory = 0
        self.cooldown = 0.0

    def _next_line(self) -> str:
        rng = self.rng
        n = self.emitted

        if n == 0:
            return "StaticFX BIOS v2.0  (C) 2026"
        if n == 1:
            return "CPU: Quantum Core @ 4.20GHz   Cores: 16"
        if n == 2:
            return "Memory test: 00000K"
        if n < 6:
            return f"Detecting {rng.choice(DEVICES)} ... found"

        roll = rng.random()
        service = rng.choice(SERVICES)

        if roll < 0.62:
            return f"[  OK  ] Started {service}."
        if roll < 0.78:
            return f"[ INFO ] Mounted {rng.choice(DEVICES)} on /mnt/{rng.randrange(9)}"
        if roll < 0.9:
            return f"[ WARN ] {service} responded slowly ({rng.randint(120, 900)}ms)"
        return f"[ .... ] Starting {service} ..."

    def advance(self, dt: float) -> None:
        self.t += dt

        if self.emitted >= self.TOTAL_LINES:
            self.hold += dt

            if self.hold > 2.5:
                self.on_resize()

            return

        self.cooldown -= dt

        while self.cooldown <= 0.0 and self.emitted < self.TOTAL_LINES:
            self.cooldown += self.rng.uniform(0.01, 0.16)
            self.lines.append(self._next_line())
            self.emitted += 1

        keep = max(1, self.height - 2)
        self.lines = self.lines[-keep:]

        if self.memory < 65536 and self.emitted < self.TOTAL_LINES:
            self.memory = min(65536, self.memory + int(dt * 40000))

    def render(self, frame: Frame, theme: Theme) -> None:
        text = theme.ramp(0.85)
        ok = theme.primary
        warn = theme.accent
        dim = self.color_at(theme, 0.4)

        for y, line in enumerate(self.lines):
            if line.startswith("Memory test"):
                line = f"Memory test: {self.memory:05d}K"

            frame.text(0, y, line, text)

            if line.startswith("[ "):
                tag = line[:8]
                frame.text(0, y, tag, warn if ("WARN" in tag or "...." in tag) else ok)
            elif line.startswith("StaticFX"):
                frame.text(0, y, line, theme.bright)

        # progress bar
        bar_row = self.height - 1
        width = max(4, min(self.width - 8, 50))
        fraction = clamp(self.emitted / self.TOTAL_LINES)
        filled = int(width * fraction)
        frame.text(0, bar_row, "[" + "#" * filled + "." * (width - filled) + "]", dim)
        frame.text(width + 3, bar_row, f"{int(fraction * 100):3d}%", text)

        if int(self.t * 2) % 2 == 0:
            cursor_y = min(self.height - 2, len(self.lines))
            frame.put(0, cursor_y, "_", theme.bright)


class DecryptScramble(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.pool = tech_glyphs(False)
        self.t = 0.0
        self.target: list[str] = []
        self.resolve: list[list[float]] = []
        self.scramble: list[list[str]] = []
        self.refresh = 0.0

    def on_resize(self) -> None:
        rng = self.rng
        self.t = 0.0
        self.target = []

        for _ in range(self.height):
            parts: list[str] = []
            length = 0

            while length < self.width:
                word = (
                    rng.choice(WORDS)
                    if rng.random() < 0.6
                    else "0x" + "".join(rng.choices(HEX, k=rng.choice((4, 8))))
                )
                parts.append(word)
                length += len(word) + 1

            self.target.append(" ".join(parts)[: self.width].ljust(self.width))

        duration = 5.0
        diagonal = max(1.0, self.height * 0.5 + self.width * 0.05)
        self.resolve = [
            [
                (y * 0.5 + x * 0.05) / diagonal * duration + rng.uniform(0.0, 1.2)
                for x in range(self.width)
            ]
            for y in range(self.height)
        ]
        self.scramble = [rng.choices(self.pool, k=self.width) for _ in range(self.height)]
        self.refresh = 0.0

    def advance(self, dt: float) -> None:
        self.t += dt
        self.refresh -= dt

        if self.refresh <= 0.0:
            self.refresh = 1.0 / 14.0
            rng = self.rng

            for row in self.scramble:
                for x in range(len(row)):
                    row[x] = rng.choice(self.pool)

        if self.t > 5.0 + 1.2 + 2.5:
            self.on_resize()

    def render(self, frame: Frame, theme: Theme) -> None:
        t = self.t
        scrambled = self.color_at(theme, 0.32)
        fresh = theme.bright
        done = self.color_at(theme, 0.85)

        for y in range(self.height):
            times = self.resolve[y]
            target = self.target[y]
            noise = self.scramble[y]

            for x in range(self.width):
                age = t - times[x]

                if age < 0.0:
                    frame.put(x, y, noise[x], scrambled)
                elif target[x] != " ":
                    frame.put(x, y, target[x], fresh if age < 0.35 else done)


class BarcodeScan(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.bars: list[bool] = []
        self.digits = ""
        self.t = 0.0

    def on_resize(self) -> None:
        rng = self.rng
        self.bars = []
        on = True

        while len(self.bars) < self.width:
            run = rng.choice((1, 1, 2, 2, 3, 4))
            self.bars.extend([on] * run)
            on = not on

        self.bars = self.bars[: self.width]
        self.digits = "".join(rng.choices("0123456789", k=max(1, self.width // 2)))

    def advance(self, dt: float) -> None:
        self.t += dt

    def render(self, frame: Frame, theme: Theme) -> None:
        top = max(0, int(self.height * 0.15))
        bottom = max(top + 1, int(self.height * 0.75))
        block = "█" if self.unicode else "#"
        laser = (0.5 + 0.5 * math.sin(self.t * 0.9)) * (self.width - 1)

        for x, on in enumerate(self.bars):
            if not on:
                continue

            distance = abs(x - laser)
            tone = 0.35 + 0.65 * clamp(1.0 - distance / 10.0)
            color = self.color_at(theme, tone)

            for y in range(top, bottom):
                frame.put(x, y, block, color)

        lx = int(laser)
        for y in range(max(0, top - 2), min(self.height, bottom + 2)):
            frame.put(lx, y, "|", theme.bright)

        label_row = min(self.height - 1, bottom + 1)
        start = max(0, (self.width - len(self.digits) * 2) // 2)

        for index, digit in enumerate(self.digits):
            frame.put(start + index * 2, label_row, digit, self.color_at(theme, 0.6))


# (old direction, new direction) -> the box-drawing corner joining them; y grows downwards.
CORNERS = {
    ((1, 0), (0, 1)): "┐",
    ((1, 0), (0, -1)): "┘",
    ((-1, 0), (0, 1)): "┌",
    ((-1, 0), (0, -1)): "└",
    ((0, 1), (1, 0)): "└",
    ((0, 1), (-1, 0)): "┘",
    ((0, -1), (1, 0)): "┌",
    ((0, -1), (-1, 0)): "┐",
}


class Circuit(Effect):
    def __init__(self, rng: random.Random, unicode: bool = False) -> None:
        super().__init__(rng, unicode)
        self.chars: list[list[str]] = []
        self.glow: list[list[float]] = []
        self.walkers: list[list[int]] = []
        self.timer = 0.0

    def on_resize(self) -> None:
        self.chars = [[" "] * self.width for _ in range(self.height)]
        self.glow = [[0.0] * self.width for _ in range(self.height)]
        self.walkers = [self._spawn() for _ in range(max(3, self.width * self.height // 260))]
        self.timer = 0.0

    def _spawn(self) -> list[int]:
        rng = self.rng
        dx, dy = rng.choice(((1, 0), (-1, 0), (0, 1), (0, -1)))
        return [rng.randrange(self.width), rng.randrange(self.height), dx, dy, rng.randint(12, 70)]

    def _glyph(self, direction: tuple[int, int], previous: tuple[int, int]) -> str:
        if direction != previous:
            return CORNERS[previous, direction] if self.unicode else "+"

        if direction[1] == 0:
            return "─" if self.unicode else "-"

        return "│" if self.unicode else "|"

    def advance(self, dt: float) -> None:
        rng = self.rng
        self.timer += dt

        while self.timer >= 0.035:
            self.timer -= 0.035

            for index, walker in enumerate(self.walkers):
                x, y, dx, dy, life = walker
                previous = (dx, dy)

                if rng.random() < 0.17:
                    dx, dy = (dy, dx) if rng.random() < 0.5 else (-dy, -dx)
                    self.chars[y][x] = self._glyph((dx, dy), previous)  # the bend

                x += dx
                y += dy
                life -= 1

                if not (0 <= x < self.width and 0 <= y < self.height) or life <= 0:
                    if 0 <= x - dx < self.width and 0 <= y - dy < self.height:
                        self.chars[y - dy][x - dx] = "o"
                        self.glow[y - dy][x - dx] = 1.0

                    self.walkers[index] = self._spawn()
                    continue

                self.chars[y][x] = self._glyph((dx, dy), (dx, dy))
                self.glow[y][x] = 1.0
                walker[0], walker[1], walker[2], walker[3], walker[4] = x, y, dx, dy, life

        decay = 1.0 - 0.16 * dt

        for y in range(self.height):
            glow_row = self.glow[y]
            char_row = self.chars[y]

            for x in range(self.width):
                if glow_row[x] > 0.0:
                    glow_row[x] *= decay

                    if glow_row[x] < 0.05:
                        glow_row[x] = 0.0
                        char_row[x] = " "

    def render(self, frame: Frame, theme: Theme) -> None:
        for y in range(self.height):
            for x in range(self.width):
                glow = self.glow[y][x]

                if glow > 0.0:
                    frame.put(x, y, self.chars[y][x], self.color_at(theme, 0.15 + 0.85 * glow))

        for x, y, *_ in self.walkers:
            frame.put(x, y, "@", theme.bright)
