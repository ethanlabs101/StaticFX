"""Frame -> ANSI escape sequences.

Each frame is encoded row by row and only rows that changed since the last
frame are written. Busy effects change nearly every row, so the saving there
is small (under 10% across the built-ins), but paused effects, slow ones and
still parts of the screen cost almost nothing to redraw.
"""

from __future__ import annotations

from staticfx.core.color import RGB
from staticfx.core.frame import Cell, Frame

ESC = "\x1b"
RESET = f"{ESC}[0m"
CLEAR_EOL = f"{ESC}[K"

_CUBE = (0, 95, 135, 175, 215, 255)


def _cube_index(value: int) -> int:
    return min(range(6), key=lambda i: abs(_CUBE[i] - value))


def xterm256(color: RGB) -> int:
    """Nearest xterm-256 palette index (6x6x6 cube or the grey ramp)."""
    r, g, b = color
    if r == g == b:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return 232 + (r - 8) * 24 // 247
    return 16 + 36 * _cube_index(r) + 6 * _cube_index(g) + _cube_index(b)


class Renderer:
    def __init__(self, truecolor: bool = True) -> None:
        self.truecolor = truecolor
        self._sgr: dict[RGB, str] = {}
        self._previous: list[str] = []

    def invalidate(self) -> None:
        """Forget what is on screen; the next frame is written in full."""
        self._previous = []

    def _color(self, color: RGB) -> str:
        sequence = self._sgr.get(color)
        if sequence is None:
            if len(self._sgr) > 20_000:  # animated palettes produce endless new colours
                self._sgr.clear()
            if self.truecolor:
                sequence = f"{ESC}[38;2;{color.r};{color.g};{color.b}m"
            else:
                sequence = f"{ESC}[38;5;{xterm256(color)}m"
            self._sgr[color] = sequence
        return sequence

    def encode_row(self, row: list[Cell]) -> str:
        parts: list[str] = []
        current: RGB | None = None
        for cell in row:
            char = cell.char
            if char != " " and cell.color != current:
                current = cell.color
                parts.append(self._color(current))
            parts.append(char)
        parts.append(RESET)
        parts.append(CLEAR_EOL)
        return "".join(parts)

    def full(self, frame: Frame) -> str:
        """The whole frame as one string, with no cursor positioning."""
        return "\n".join(self.encode_row(row) for row in frame.cells)

    def diff(self, frame: Frame) -> str:
        """Only the rows that changed since the previous call, with cursor moves."""
        rows = [self.encode_row(row) for row in frame.cells]
        previous = self._previous
        if len(previous) != len(rows):
            previous = [""] * len(rows)
        out = [f"{ESC}[{y + 1};1H{line}" for y, line in enumerate(rows) if line != previous[y]]
        self._previous = rows
        return "".join(out)
