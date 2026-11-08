"""Short lists with live preview: themes and looks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from staticfx import themes
from staticfx.core.color import RGB, hsv
from staticfx.library.looks import BUILTIN_LOOKS, Look
from staticfx.ui.dialogs import Confirm, ask_look_name
from staticfx.ui.screen import Screen
from staticfx.ui.widgets import Canvas, Cursor

if TYPE_CHECKING:
    from staticfx.app.app import App


@dataclass
class Entry:
    key: str
    label: str
    note: str = ""
    heading: bool = False  # a section title, skipped by the cursor
    swatch: tuple[RGB, ...] = ()  # colours shown as a strip on the right


class Picker(Screen):
    """A left-docked list; the highlighted entry is previewed as you move."""

    title = ""
    footer = "Enter choose   Esc close"
    width = 46

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.cursor = Cursor()  # over selectable entries
        self.view = Cursor()  # over every row, for scrolling
        self.entries: list[Entry] = []
        self.rows = 10

    def selectable(self) -> list[int]:
        return [i for i, e in enumerate(self.entries) if not e.heading]

    @property
    def current(self) -> Entry | None:
        choices = self.selectable()
        return self.entries[choices[self.cursor.index]] if choices else None

    def select(self, key: str) -> None:
        for n, i in enumerate(self.selectable()):
            if self.entries[i].key == key:
                self.cursor.index = n
        self.hover()

    def hover(self) -> None:
        """Preview the current entry."""

    def choose(self, entry: Entry) -> None:
        """Apply the entry the user picked."""

    def extra_key(self, key: str) -> None:
        """Keys beyond navigation, Enter and Esc."""

    def handle(self, key: str) -> None:
        if key in ("escape", "ctrl-c", "q"):
            self.close()
        elif self.cursor.handle(key, len(self.selectable()), self.rows):
            self.hover()
        elif key == "enter" and self.current is not None:
            entry = self.current
            self.close()
            self.choose(entry)
        else:
            self.extra_key(key)

    def draw(self, canvas: Canvas) -> None:
        c, s = canvas.chrome, canvas.style
        w = min(canvas.width - 2, self.width)
        h = min(canvas.height - 2, len(self.entries) + 5)
        x, y = 1, 1
        canvas.box(x, y, w, h, self.title)
        self.rows = h - 5
        choices = self.selectable()
        chosen = choices[self.cursor.index] if choices else -1
        self.view.index = max(0, chosen)  # scroll over all rows, headings included
        for row, i in enumerate(self.view.window(self.rows, len(self.entries)), y + 1):
            entry = self.entries[i]
            if entry.heading:
                canvas.text(x + 2, row, entry.label, s.dim, w - 4)
                continue
            selected = i == chosen
            marker = c.cursor if selected else " "
            right = x + w - 3  # one column in from the scrollbar
            if entry.swatch:
                right -= len(entry.swatch)
                block = "#" if self.app.ascii_only else "█"
                for offset, colour in enumerate(entry.swatch):
                    canvas.frame.put(right + offset, row, block, colour)
                right -= 1
            note_width = min(len(entry.note), (w - 8) // 2)
            label_colour = s.selected if selected else s.text
            canvas.text(
                x + 2, row, f"{marker} {entry.label}", label_colour, right - x - 3 - note_width
            )
            canvas.text(right - note_width, row, entry.note, s.dim, note_width)
        canvas.scrollbar(x + w - 2, y + 1, self.rows, self.view.first, len(self.entries))
        canvas.rule(x, y + h - 3, w)
        canvas.text(x + 2, y + h - 2, self.footer, s.dim, w - 4)


SWATCH_WIDTH = 12


def swatch(theme_name: str) -> tuple[RGB, ...]:
    """A strip of colours along the theme's ramp (or around the hue wheel, for animated ones)."""
    if theme_name in themes.STATIC_THEMES:
        theme = themes.STATIC_THEMES[theme_name]
        return tuple(theme.ramp(0.15 + 0.85 * i / (SWATCH_WIDTH - 1)) for i in range(SWATCH_WIDTH))
    return tuple(hsv(i / SWATCH_WIDTH) for i in range(SWATCH_WIDTH))


class ThemePicker(Picker):
    title = "Themes"
    help = (("↑ ↓", "preview a theme"), ("Enter", "keep it"), ("Esc", "go back to the old one"))

    def __init__(self, app: App) -> None:
        super().__init__(app)
        notes = {"rainbow": "animated", "strobe": "flashing"}
        self.entries = [
            Entry(name, themes.LABELS[name], notes.get(name, ""), swatch=swatch(name))
            for name in app.theme_names()
        ]
        self.select(app.player.theme_name)

    def hover(self) -> None:
        if self.current is not None:
            self.app.player.preview_theme = self.current.key

    def on_close(self) -> None:
        self.app.player.preview_theme = None

    def choose(self, entry: Entry) -> None:
        self.app.set_theme(entry.key)
        self.app.toast(f"Theme: {entry.label}")


class LookPicker(Picker):
    title = "Looks"
    footer = "Enter apply   s save current   d delete   Esc close"
    width = 60
    help = (
        ("↑ ↓", "preview a look"),
        ("Enter", "apply it"),
        ("s", "save what's playing now as a look"),
        ("d  Del", "delete one of your looks"),
    )

    def __init__(self, app: App) -> None:
        super().__init__(app)
        self.looks: dict[str, Look] = {}
        self.rebuild()

    def rebuild(self) -> None:
        mine = self.app.looks.looks
        entries = [Entry("", "Your looks", heading=True)]
        if not mine:
            entries.append(Entry("", "  none yet: press s to save one", heading=True))
        for look in mine:
            entries.append(
                Entry(
                    f"mine:{look.name}",
                    look.name,
                    self.app.registry[look.effect].label
                    if look.effect in self.app.registry
                    else "missing effect",
                )
            )
        entries.append(Entry("", "Built in", heading=True))
        entries += [Entry(f"builtin:{look.name}", look.name, look.note) for look in BUILTIN_LOOKS]
        self.entries = entries
        self.looks = {f"mine:{look.name}": look for look in mine}
        self.looks.update({f"builtin:{look.name}": look for look in BUILTIN_LOOKS})
        self.cursor.clamp(len(self.selectable()))
        self.hover()

    def hover(self) -> None:
        player = self.app.player
        look = self.looks.get(self.current.key) if self.current else None
        if look is None or (look.theme == "strobe" and not self.app.settings.allow_flashing):
            player.preview(None)
            player.preview_theme = None
            return
        player.preview(look.effect)
        player.preview_theme = look.theme

    def on_close(self) -> None:
        self.app.player.preview(None)
        self.app.player.preview_theme = None

    def choose(self, entry: Entry) -> None:
        self.app.apply_look(self.looks[entry.key])

    def extra_key(self, key: str) -> None:
        entry = self.current
        if key.lower() == "s":
            self.close()
            ask_look_name(self.app)
        elif key in ("d", "D", "delete") and entry is not None:
            if not entry.key.startswith("mine:"):
                self.app.toast("Built-in looks can't be deleted")
                return
            name = self.looks[entry.key].name

            def confirmed() -> None:
                self.app.looks.remove(name)
                self.rebuild()

            self.app.push(
                Confirm(self.app, "Delete look", [f"Delete the look '{name}'?"], confirmed)
            )
