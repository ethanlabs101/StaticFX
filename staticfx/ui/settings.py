"""Settings and key bindings, changed in place and saved straight away."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from staticfx import themes
from staticfx.app.keymap import ACTIONS, RESERVED, key_label
from staticfx.library.config import CHARACTERS, COLOURS
from staticfx.ui.dialogs import Confirm
from staticfx.ui.screen import Screen
from staticfx.ui.widgets import Canvas, Cursor

if TYPE_CHECKING:
    from staticfx.app.app import App

N = TypeVar("N", int, float)

FPS_CHOICES = [10, 15, 20, 24, 30, 45, 60]
AUTO_CHOICES = [5.0, 8.0, 12.0, 20.0, 30.0, 60.0, 120.0, 300.0]
FLASH_WARNING = [
    "The Strobe theme flashes rapidly and can",
    "trigger seizures in people with photosensitive",
    "epilepsy. Unlock it anyway?",
]


@dataclass
class Row:
    label: str
    value: Callable[[], str] = str
    change: Callable[[int], None] | None = None
    on_enter: Callable[[], None] | None = None
    hint: str = ""
    heading: bool = False
    action: str | None = None  # set on key-binding rows


def step_choice(options: Sequence[N], current: float, step: int) -> N:
    """The option after (or before) ``current``, stopping at the ends."""
    nearest = min(range(len(options)), key=lambda i: abs(options[i] - current))
    return options[max(0, min(len(options) - 1, nearest + step))]


class SettingsScreen(Screen):
    help = (
        ("↑ ↓", "choose a setting"),
        ("← →", "change it"),
        ("Enter", "on a key binding: press the new key"),
        ("Backspace", "on a key binding: unbind it"),
        ("Esc", "close"),
    )

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.cursor = Cursor()
        self.view = Cursor()
        self.capturing: str | None = None  # the action waiting for a new key
        self.rows: list[Row] = []
        self.visible_rows = 10
        self.rebuild()

    def rebuild(self) -> None:
        app, s = self.app, self.app.settings
        rows = [
            Row("Display", heading=True),
            Row(
                "Frame rate",
                lambda: f"{s.fps} fps",
                self.change_fps,
                hint="lower it if your terminal can't keep up",
            ),
            Row(
                "Characters",
                lambda: s.characters,
                self.change_characters,
                hint="auto, katakana in rain effects, or plain ASCII",
            ),
            Row(
                "Colours",
                lambda: s.colour,
                self.change_colour,
                hint="use 256 if colours look wrong in your terminal",
            ),
            Row(
                "Auto-cycle every",
                lambda: f"{s.auto_seconds:g}s",
                self.change_auto,
                hint=f"{app.keymap.label('auto', app.ascii_only)} turns auto-cycle on",
            ),
            Row(
                "Allow flashing",
                lambda: "yes" if s.allow_flashing else "no",
                self.toggle_flashing,
                hint="unlocks the Strobe theme (photosensitivity warning)",
            ),
            Row("Keys", heading=True),
        ]
        rows += [self.key_row(action, description) for action, (_, description) in ACTIONS.items()]
        rows.append(Row("Reset all keys", lambda: "", on_enter=self.confirm_reset))
        if app.data_dir is not None:
            rows += [
                Row("Files", heading=True),
                Row(
                    "Data folder",
                    lambda: self.short_path(app.data_dir),
                    hint="effects/, looks.json, config.json",
                ),
            ]
        self.rows = rows

    def key_row(self, action: str, description: str) -> Row:
        return Row(
            description,
            lambda: self.keys_text(action),
            on_enter=lambda: self.start_capture(action),
            hint="Enter to set a key, Backspace to unbind",
            action=action,
        )

    @staticmethod
    def short_path(path: Path | None) -> str:
        if path is None:
            return "(none)"
        home = str(Path.home())
        text = str(path)
        return "~" + text[len(home) :] if text.startswith(home) else text

    def keys_text(self, action: str) -> str:
        if self.capturing == action:
            return "press a key..."
        keys = self.app.keymap.keys_for(action)
        return " / ".join(key_label(k, self.app.ascii_only) for k in keys) or "(unbound)"

    def selectable(self) -> list[Row]:
        return [row for row in self.rows if not row.heading]

    @property
    def current(self) -> Row:
        return self.selectable()[self.cursor.index]

    def changed(self, setting: str = "") -> None:
        """Mark settings for saving; a setting changed here outlives command-line overrides."""
        if setting:
            self.app.keep(setting)
        self.app.dirty = True

    def change_fps(self, step: int) -> None:
        self.app.settings.fps = step_choice(FPS_CHOICES, self.app.settings.fps, step)
        self.changed("fps")

    def change_auto(self, step: int) -> None:
        s = self.app.settings
        s.auto_seconds = step_choice(AUTO_CHOICES, s.auto_seconds, step)
        self.changed("auto_seconds")

    def change_characters(self, step: int) -> None:
        s = self.app.settings
        s.characters = CHARACTERS[(CHARACTERS.index(s.characters) + step) % len(CHARACTERS)]
        self.app.apply_characters()
        self.changed("characters")

    def change_colour(self, step: int) -> None:
        s = self.app.settings
        s.colour = COLOURS[(COLOURS.index(s.colour) + step) % len(COLOURS)]
        self.changed("colour")

    def toggle_flashing(self, _step: int = 0) -> None:
        app = self.app
        if app.settings.allow_flashing:
            app.settings.allow_flashing = False
            if app.player.theme_name == "strobe":
                app.set_theme(themes.DEFAULT)
            self.changed()
            return

        def unlock() -> None:
            app.settings.allow_flashing = True
            app.toast("Strobe unlocked: find it in the theme menu")
            self.changed()

        app.push(Confirm(app, "Photosensitivity warning", FLASH_WARNING, unlock))

    def start_capture(self, action: str) -> None:
        self.capturing = action

    def capture(self, key: str) -> None:
        action, self.capturing = self.capturing, None
        if action is None or key == "escape":
            return
        if key in RESERVED:
            self.app.toast(f"{key_label(key)} is reserved and can't be bound")
            return
        keymap = self.app.keymap
        keymap.unbind(action)  # the new key replaces the old ones
        lost = keymap.bind(key, action)
        if lost:
            self.app.toast(f"{key_label(key)} no longer does: {ACTIONS[lost][1]}")
        self.changed()

    def confirm_reset(self) -> None:
        def reset() -> None:
            self.app.keymap.reset()
            self.app.toast("Keys reset to the defaults")
            self.changed()

        self.app.push(
            Confirm(self.app, "Reset keys", ["Put every key back to its default?"], reset)
        )

    def handle(self, key: str) -> None:
        if self.capturing is not None:
            self.capture(key)
            return
        row = self.current
        if key in ("escape", "ctrl-c", "q"):
            self.close()
        elif self.cursor.handle(key, len(self.selectable()), self.visible_rows):
            pass
        elif key in ("left", "right") and row.change is not None:
            row.change(-1 if key == "left" else 1)
        elif key == "enter" and row.on_enter is not None:
            row.on_enter()
        elif key in ("enter", "space") and row.change is not None:
            row.change(1)
        elif key in ("backspace", "delete") and row.action is not None:
            self.app.keymap.unbind(row.action)
            self.changed()

    def draw(self, canvas: Canvas) -> None:
        c, s = canvas.chrome, canvas.style
        w, h = min(canvas.width - 2, 64), canvas.height - 2
        x, y = 1, 1
        canvas.box(x, y, w, h, "Settings")
        self.visible_rows = h - 5
        current = self.current
        self.view.index = self.rows.index(current)
        for line, i in enumerate(self.view.window(self.visible_rows, len(self.rows)), y + 1):
            row = self.rows[i]
            if row.heading:
                canvas.text(x + 2, line, f"{c.h * 2} {row.label} ", s.dim, w - 4)
                continue
            selected = row is current
            value = row.value()
            if selected and row.change is not None:
                value = f"{c.arrow_left} {value} {c.arrow_right}"
            colour = s.selected if selected else s.text
            value_width = min(len(value), w // 2)
            label = f"{c.cursor if selected else ' '} {row.label}"
            canvas.text(x + 2, line, label, colour, w - 6 - value_width)
            value_colour = (
                s.accent if self.capturing and selected else colour if selected else s.dim
            )
            canvas.text(x + w - 3 - value_width, line, value, value_colour, value_width)
        canvas.scrollbar(x + w - 2, y + 1, self.visible_rows, self.view.first, len(self.rows))
        canvas.rule(x, y + h - 4, w)
        hint = "Press the new key (Esc cancels)" if self.capturing else current.hint
        canvas.text(x + 2, y + h - 3, hint, s.text, w - 4)
        canvas.text(x + 2, y + h - 2, "← → change   Enter select   Esc close", s.dim, w - 4)
