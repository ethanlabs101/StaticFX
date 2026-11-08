"""Every key, generated from the live key map and each screen's own list.

Because the main-view section is built from the current bindings, the help
screen is always right, including after the user rebinds keys.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from staticfx.app.keymap import ACTIONS, key_label
from staticfx.ui.browser import Browser
from staticfx.ui.pickers import LookPicker
from staticfx.ui.screen import Screen
from staticfx.ui.settings import SettingsScreen
from staticfx.ui.studio import Studio
from staticfx.ui.widgets import Canvas

if TYPE_CHECKING:
    from staticfx.app.app import App

WIDTH = 66
ALWAYS = (
    ("Esc", "close the current menu (twice in the main view: quit)"),
    ("Ctrl-C", "close the current menu, or quit"),
    ("Ctrl-Z", "suspend to the shell (fg comes back)"),
)


def help_lines(app: App) -> list[tuple[str, str, str]]:
    """``(kind, keys, text)`` rows; kind is "group", "row" or "note"."""
    lines: list[tuple[str, str, str]] = []
    group = ""
    for action, (action_group, description) in ACTIONS.items():
        if action_group != group:
            group = action_group
            lines.append(("group", group, ""))
        keys = app.keymap.keys_for(action)
        shown = " ".join(key_label(k, app.ascii_only) for k in keys) or "(unbound)"
        lines.append(("row", shown, description))
    lines.append(("group", "Anywhere", ""))
    lines += [("row", keys, text) for keys, text in ALWAYS]
    for title, screen in (
        ("Effect browser", Browser),
        ("Effect Studio", Studio),
        ("Looks", LookPicker),
        ("Settings", SettingsScreen),
    ):
        lines.append(("group", title, ""))
        lines += [("row", keys, text) for keys, text in screen.help]
    settings = app.keymap.label("settings", app.ascii_only)
    lines.append(
        ("note", "", f"Rebind keys in Settings ({settings}). Strobe is unlocked there too.")
    )
    return lines


class HelpScreen(Screen):
    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.lines = help_lines(app)
        self.scroll = 0
        self.rows = 10

    def handle(self, key: str) -> None:
        moves = {"up": -1, "down": 1, "pageup": -self.rows, "pagedown": self.rows}
        if key in moves:
            self.scroll += moves[key]
        elif key == "home":
            self.scroll = 0
        elif key == "end":
            self.scroll = len(self.lines)
        else:
            self.close()
        self.scroll = max(0, min(self.scroll, len(self.lines) - self.rows))

    def draw(self, canvas: Canvas) -> None:
        c, s = canvas.chrome, canvas.style
        w = min(canvas.width - 2, WIDTH)
        h = min(canvas.height - 2, len(self.lines) + 4)
        x, y = (canvas.width - w) // 2, (canvas.height - h) // 2
        canvas.box(x, y, w, h, "Keys")
        self.rows = h - 4
        self.scroll = max(0, min(self.scroll, len(self.lines) - self.rows))
        key_width = 16
        for line, (kind, keys, text) in enumerate(
            self.lines[self.scroll : self.scroll + self.rows], y + 1
        ):
            if kind == "group":
                canvas.text(x + 2, line, f"{c.h * 2} {keys} ", s.dim, w - 4)
            elif kind == "note":
                canvas.text(x + 2, line, text, s.accent, w - 4)
            else:
                canvas.text(x + 3, line, keys, s.selected, key_width)
                canvas.text(x + 3 + key_width, line, text, s.text, w - 6 - key_width)
        canvas.scrollbar(x + w - 2, y + 1, self.rows, self.scroll, len(self.lines))
        canvas.rule(x, y + h - 3, w)
        more = "  (more below)" if self.scroll + self.rows < len(self.lines) else ""
        canvas.text(x + 2, y + h - 2, f"↑ ↓ scroll   any other key closes{more}", s.dim, w - 4)
