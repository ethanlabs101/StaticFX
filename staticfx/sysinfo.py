"""System information (fastfetch / neofetch) drawn over an effect."""

from __future__ import annotations

import re
import shutil
import subprocess
import threading
from collections.abc import Callable

from staticfx.core.frame import Frame
from staticfx.themes import Theme

TOOLS = {"fastfetch": ["fastfetch", "--pipe"], "neofetch": ["neofetch", "--stdout"]}
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
TIMEOUT = 10


def system_info(tool: str | None = None) -> str:
    """Output of ``tool`` (or the first one installed), without colour codes.

    Raises ``RuntimeError`` with a readable message if nothing usable is installed.
    """
    names = [tool] if tool else list(TOOLS)
    for name in names:
        if shutil.which(name):
            try:
                result = subprocess.run(
                    TOOLS[name],
                    capture_output=True,
                    stdin=subprocess.DEVNULL,  # the app owns the keyboard
                    text=True,
                    timeout=TIMEOUT,
                    check=True,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                raise RuntimeError(f"{name} failed: {exc}") from None
            return ANSI.sub("", result.stdout).expandtabs()
    wanted = tool or "fastfetch or neofetch"
    raise RuntimeError(f"{wanted} is not installed")


def overlay(frame: Frame, theme: Theme, text: str) -> None:
    """Dim the effect and print ``text`` over it, vertically centred on the left."""
    frame.dim(0.35)
    lines = [line.rstrip() for line in text.strip("\n").splitlines()]
    top = max(0, (frame.height - len(lines)) // 2)
    for y, line in enumerate(lines[: frame.height], top):
        frame.fill(2, y, len(line) + 2, 1)
        label, sep, value = line.partition(":")
        if sep and len(label) < 24:  # "OS: Arch Linux": colour the label
            frame.text(3, y, label + sep, theme.accent)
            frame.text(4 + len(label), y, value, theme.bright)
        else:
            frame.text(3, y, line, theme.bright)


class SystemInfo:
    """The in-app overlay: shown or hidden, and fetched once per session.

    fastfetch can take a second or more, so the first fetch runs on a thread
    and the effect keeps animating meanwhile. A failure is kept in ``error``
    for the app to report; the next toggle tries again.
    """

    def __init__(
        self, tool: str | None = None, fetch: Callable[[str | None], str] = system_info
    ) -> None:
        self.tool = tool
        self.fetch = fetch
        self.visible = False
        self.text: str | None = None
        self.error: str | None = None
        self._thread: threading.Thread | None = None

    @property
    def loading(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def show(self, text: str) -> None:
        """Show ``text`` straight away, for when it was fetched up front."""
        self.text, self.error, self.visible = text, None, True

    def toggle(self) -> None:
        self.visible = not self.visible
        if self.visible and self.text is None and not self.loading:
            self.error = None
            self._thread = threading.Thread(target=self._load, daemon=True)
            self._thread.start()

    def wait(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def _load(self) -> None:
        try:
            self.text = self.fetch(self.tool)
        except RuntimeError as exc:
            self.error = str(exc)
