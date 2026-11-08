"""The drawing surface: a grid of coloured characters."""

from __future__ import annotations

from staticfx.core.color import BLACK, RGB


class Cell:
    __slots__ = ("char", "color")

    def __init__(self, char: str = " ", color: RGB = BLACK) -> None:
        self.char = char
        self.color = color

    def __repr__(self) -> str:
        return f"Cell({self.char!r}, {self.color})"


class Frame:
    """A ``width`` x ``height`` grid of :class:`Cell`.

    A space is "empty": the renderer skips its colour, and effects treat it as
    transparent. Effects write to ``cells`` directly in hot loops; everything
    else should use :meth:`put` and :meth:`text`, which clip to the frame.
    """

    def __init__(self, width: int, height: int) -> None:
        self.width = max(1, int(width))
        self.height = max(1, int(height))
        self.cells = self._blank()

    def _blank(self) -> list[list[Cell]]:
        return [[Cell() for _ in range(self.width)] for _ in range(self.height)]

    def resize(self, width: int, height: int) -> None:
        width, height = max(1, int(width)), max(1, int(height))
        if (width, height) != (self.width, self.height):
            self.width, self.height = width, height
            self.cells = self._blank()

    def clear(self) -> None:
        for row in self.cells:
            for cell in row:
                cell.char = " "
                cell.color = BLACK

    def put(self, x: int, y: int, char: str, color: RGB) -> None:
        if 0 <= x < self.width and 0 <= y < self.height:
            cell = self.cells[y][x]
            cell.char = char
            cell.color = color

    def char_at(self, x: int, y: int) -> str:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.cells[y][x].char
        return " "

    def text(self, x: int, y: int, text: str, color: RGB) -> None:
        """Write ``text`` starting at ``(x, y)``, clipped to the frame."""
        if not 0 <= y < self.height or x >= self.width:
            return
        row = self.cells[y]
        start = max(0, -x)
        for offset, char in enumerate(text[start : self.width - x], start):
            cell = row[x + offset]
            cell.char = char
            cell.color = color

    def fill(self, x: int, y: int, width: int, height: int, char: str = " ") -> None:
        """Fill a rectangle (clipped) with ``char``; used to blank panel backgrounds."""
        for row in self.cells[max(0, y) : max(0, y + height)]:
            for cell in row[max(0, x) : max(0, x + width)]:
                cell.char = char

    def dim(self, factor: float) -> None:
        """Darken everything already drawn; used behind modal panels."""
        for row in self.cells:
            for cell in row:
                if cell.char != " ":
                    c = cell.color
                    cell.color = RGB(int(c.r * factor), int(c.g * factor), int(c.b * factor))

    def lines(self) -> list[str]:
        """Plain text of each row, for tests and ``staticfx render``."""
        return ["".join(cell.char for cell in row) for row in self.cells]
