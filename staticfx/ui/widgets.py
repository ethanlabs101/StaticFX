"""Drawing primitives shared by every screen: box characters, colours, panels, lists."""

from __future__ import annotations

from dataclasses import dataclass

from staticfx.core.color import RGB, scale, tint
from staticfx.core.frame import Frame
from staticfx.themes import Theme


@dataclass(frozen=True)
class Chrome:
    """Characters for borders and markers, with an ASCII-only variant."""

    tl: str
    tr: str
    bl: str
    br: str
    h: str
    v: str
    left_tee: str
    right_tee: str
    top_tee: str
    bottom_tee: str
    cursor: str
    star: str
    dot: str
    ellipsis: str
    thumb: str
    track: str
    arrow_left: str
    arrow_right: str


UNICODE = Chrome(
    "╭", "╮", "╰", "╯", "─", "│", "├", "┤", "┬", "┴", "▶", "★", "·", "…", "█", "│", "◂", "▸"
)  # fmt: skip
ASCII = Chrome(
    "+", "+", "+", "+", "-", "|", "+", "+", "+", "+", ">", "*", "-", "~", "#", "|", "<", ">"
)  # fmt: skip


@dataclass(frozen=True)
class Style:
    border: RGB
    title: RGB
    text: RGB
    dim: RGB
    selected: RGB
    accent: RGB

    @classmethod
    def from_theme(cls, theme: Theme) -> Style:
        """Panel colours that match the theme.

        Animated themes would make menus flicker, so they get a neutral grey
        scheme instead.
        """
        if theme.key in ("rainbow", "strobe"):
            return cls(
                border=RGB(140, 140, 150),
                title=RGB(255, 255, 255),
                text=RGB(210, 210, 215),
                dim=RGB(120, 120, 128),
                selected=RGB(255, 255, 255),
                accent=RGB(255, 210, 90),
            )
        return cls(
            border=tint(theme.ramp(0.5), 0.2),
            title=tint(theme.bright, 0.5),
            text=tint(theme.ramp(0.75), 0.25),
            dim=scale(theme.ramp(0.55), 0.8),
            selected=tint(theme.bright, 0.6),
            accent=theme.accent,
        )


# UI text uses a few Unicode symbols; terminals without UTF-8 get these instead.
ASCII_TEXT = str.maketrans("←→↑↓×★·…◂▸▶─", "<>^vx*-~<>>-")


def fit(text: str, width: int, ellipsis: str = "…") -> str:
    """``text`` cut to ``width`` columns, marked with an ellipsis when cut."""
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    return text[: width - 1] + ellipsis


class Canvas:
    """A frame plus the chrome and style to draw panels on it."""

    def __init__(self, frame: Frame, chrome: Chrome, style: Style) -> None:
        self.frame = frame
        self.chrome = chrome
        self.style = style

    @property
    def width(self) -> int:
        return self.frame.width

    @property
    def height(self) -> int:
        return self.frame.height

    def text(self, x: int, y: int, text: str, color: RGB, width: int | None = None) -> None:
        if self.chrome is ASCII:  # anything without an ASCII stand-in becomes "?"
            text = text.translate(ASCII_TEXT).encode("ascii", "replace").decode()
        if width is not None:
            text = fit(text, width, self.chrome.ellipsis).ljust(width)
        self.frame.text(x, y, text, color)

    def box(self, x: int, y: int, w: int, h: int, title: str = "", note: str = "") -> None:
        """A bordered panel with its inside cleared, an optional title on the
        top-left and a note (e.g. a count) on the top-right."""
        c, s = self.chrome, self.style
        self.frame.fill(x + 1, y + 1, w - 2, h - 2)
        top = c.tl + c.h * (w - 2) + c.tr
        self.frame.text(x, y, top, s.border)
        for row in range(y + 1, y + h - 1):
            self.frame.text(x, row, c.v, s.border)
            self.frame.text(x + w - 1, row, c.v, s.border)
        self.frame.text(x, y + h - 1, c.bl + c.h * (w - 2) + c.br, s.border)
        if title:
            self.text(x + 2, y, f" {fit(title, w - 6, c.ellipsis)} ", s.title)
        if note:
            note = f" {note} "
            self.text(x + w - 2 - len(note), y, note, s.dim)

    def rule(self, x: int, y: int, w: int, split: int | None = None, joint: str = "") -> None:
        """A horizontal divider across a box of width ``w``, joining its sides.

        ``split`` marks a column where a vertical divider meets the rule.
        """
        c = self.chrome
        line = list(c.left_tee + c.h * (w - 2) + c.right_tee)
        if split is not None:
            line[split] = joint
        self.frame.text(x, y, "".join(line), self.style.border)

    def column(self, x: int, top: int, bottom: int) -> None:
        for row in range(top, bottom):
            self.frame.text(x, row, self.chrome.v, self.style.border)

    def scrollbar(self, x: int, top: int, rows: int, first: int, total: int) -> None:
        if total <= rows:
            return
        thumb = top + round(first / max(1, total - rows) * (rows - 1))
        for row in range(top, top + rows):
            self.frame.text(
                x, row, self.chrome.thumb if row == thumb else self.chrome.track, self.style.dim
            )


class Cursor:
    """A selected index in a scrolling list, and which item is shown first."""

    def __init__(self) -> None:
        self.index = 0
        self.first = 0

    def clamp(self, count: int) -> None:
        self.index = max(0, min(self.index, count - 1))

    def move(self, delta: int, count: int, wrap: bool = False) -> None:
        if count == 0:
            self.index = 0
        elif wrap:
            self.index = (self.index + delta) % count
        else:
            self.index = max(0, min(count - 1, self.index + delta))

    def handle(self, key: str, count: int, page: int) -> bool:
        """Apply a navigation key; returns False if ``key`` isn't one."""
        moves = {"up": -1, "down": 1, "pageup": -page, "pagedown": page}
        if key in moves:
            self.move(moves[key], count, wrap=key in ("up", "down"))
        elif key == "home":
            self.index = 0
        elif key == "end":
            self.index = max(0, count - 1)
        else:
            return False
        return True

    def window(self, rows: int, count: int) -> range:
        """The indexes to draw in ``rows`` lines, scrolled to keep the cursor visible."""
        self.clamp(count)
        if self.index < self.first:
            self.first = self.index
        elif self.index >= self.first + rows:
            self.first = self.index - rows + 1
        self.first = max(0, min(self.first, count - rows))
        return range(self.first, min(count, self.first + rows))
