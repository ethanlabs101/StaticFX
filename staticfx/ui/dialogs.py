"""Small modal dialogs: a text prompt and a yes/no confirmation."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from staticfx.library.files import NAME_LIMIT, clean_name
from staticfx.ui.screen import Screen
from staticfx.ui.widgets import Canvas

if TYPE_CHECKING:
    from staticfx.app.app import App


class Prompt(Screen):
    """Asks for one line of text. ``on_submit`` runs only if the user presses Enter."""

    help = (("Enter", "confirm"), ("Esc", "cancel"))

    def __init__(
        self, app: App, title: str, on_submit: Callable[[str], None], text: str = ""
    ) -> None:
        super().__init__(app)
        self.title = title
        self.text = text[:NAME_LIMIT]
        self.on_submit = on_submit
        self.error = ""

    def handle(self, key: str) -> None:
        if key in ("escape", "ctrl-c"):
            self.close()
        elif key == "enter":
            value = clean_name(self.text)
            if not value:
                self.error = "Type a name first"
                return
            self.close()
            self.on_submit(value)
        elif key == "backspace":
            self.text = self.text[:-1]
        elif len(self.text) < NAME_LIMIT and (
            key == "space" or (len(key) == 1 and key.isprintable())
        ):
            self.text += " " if key == "space" else key
            self.error = ""

    def draw(self, canvas: Canvas) -> None:
        s = canvas.style
        width = min(canvas.width - 4, NAME_LIMIT + 8)
        x, y = (canvas.width - width) // 2, canvas.height // 2 - 3
        canvas.box(x, y, width, 6, self.title)
        canvas.text(x + 2, y + 2, self.text[-(width - 6) :] + "_", s.selected, width - 4)
        canvas.text(x + 2, y + 3, self.error, s.accent, width - 4)
        canvas.text(x + 2, y + 4, "Enter save   Esc cancel", s.dim, width - 4)


class Confirm(Screen):
    """A yes/no question. ``on_yes`` runs only if the user presses y."""

    help = (("y", "yes"), ("n  Esc", "no"))

    def __init__(self, app: App, title: str, lines: list[str], on_yes: Callable[[], None]) -> None:
        super().__init__(app)
        self.title = title
        self.lines = lines
        self.on_yes = on_yes

    def handle(self, key: str) -> None:
        if key in ("y", "Y"):
            self.close()
            self.on_yes()
        elif key in ("n", "N", "escape", "ctrl-c", "enter"):
            self.close()

    def draw(self, canvas: Canvas) -> None:
        s = canvas.style
        width = min(canvas.width - 4, max(36, *(len(line) + 6 for line in self.lines)))
        height = len(self.lines) + 5
        x, y = (canvas.width - width) // 2, (canvas.height - height) // 2
        canvas.box(x, y, width, height, self.title)
        for i, line in enumerate(self.lines):
            canvas.text(x + 3, y + 2 + i, line, s.text, width - 6)
        canvas.text(x + 3, y + height - 2, "y yes   n no", s.accent, width - 6)


def ask_look_name(app: App) -> None:
    """Prompt for a name and save the current effect, theme and filters as a look."""

    def save(name: str) -> None:
        replaced = app.looks.put(app.current_look(name))
        looks = app.keymap.label("looks", app.ascii_only)
        app.toast(f"Look {'updated' if replaced else 'saved'}: {name} ({looks} to recall it)")

    app.push(Prompt(app, "Save this look as", save))
