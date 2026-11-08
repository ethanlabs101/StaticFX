"""The base class for everything that takes over the keyboard."""

from __future__ import annotations

from typing import TYPE_CHECKING

from staticfx.ui.widgets import Canvas

if TYPE_CHECKING:
    from staticfx.app.app import App


class Screen:
    """One layer of the UI. The app keeps a stack; the top screen gets every key.

    ``help`` lists ``(keys, what they do)`` for the help screen, so each
    screen documents its own controls next to the code that handles them.
    """

    help: tuple[tuple[str, str], ...] = ()

    def __init__(self, app: App) -> None:
        self.app = app

    def handle(self, key: str) -> None:
        """React to one key press."""

    def update(self, dt: float) -> None:
        """Advance any animation the screen owns."""

    def draw(self, canvas: Canvas) -> None:
        """Draw on top of the effect (and of the screens below)."""

    def close(self) -> None:
        """Remove this screen from the stack."""
        self.app.pop(self)

    def on_close(self) -> None:
        """Called after the screen is removed; undo any previews here."""
