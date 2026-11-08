"""Owning the terminal while the app runs.

:class:`Terminal` switches to the alternate screen, hides the cursor and puts
the tty in a raw-ish mode, and guarantees all of that is undone however the
program exits - normal quit, exception, ``SIGTERM`` - and around a Ctrl-Z
suspend.

Signal generation (ISIG) is turned off, so Ctrl-C and Ctrl-Z arrive as
ordinary keys. That lets each screen decide what they mean: Ctrl-C in the
Studio asks before discarding work instead of killing the process.
"""

from __future__ import annotations

import os
import shutil
import signal
import sys
from types import FrameType
from typing import Any, TextIO

try:
    import termios
except ImportError:  # Windows
    termios = None  # type: ignore[assignment]

ESC = "\x1b"
ALT_SCREEN_ON = f"{ESC}[?1049h"
ALT_SCREEN_OFF = f"{ESC}[?1049l"
CURSOR_HIDE = f"{ESC}[?25l"
CURSOR_SHOW = f"{ESC}[?25h"
WRAP_OFF = f"{ESC}[?7l"
WRAP_ON = f"{ESC}[?7h"
CLEAR = f"{ESC}[2J{ESC}[H"
RESET = f"{ESC}[0m"

# Indexes into the list returned by termios.tcgetattr().
_IFLAG, _LFLAG, _CC = 0, 3, 6


def terminal_size() -> tuple[int, int]:
    """Current ``(columns, lines)``.

    Asks the tty directly: ``shutil.get_terminal_size`` prefers the
    ``COLUMNS``/``LINES`` environment variables, which go stale on resize.
    """
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            size = os.get_terminal_size(stream.fileno())
        except (OSError, ValueError, AttributeError):
            continue
        if size.columns > 0 and size.lines > 0:
            return size.columns, size.lines
    size = shutil.get_terminal_size((80, 24))
    return max(1, size.columns), max(1, size.lines)


def is_interactive() -> bool:
    try:
        return sys.stdin.isatty() and sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def supported() -> bool:
    """Interactive mode needs POSIX terminal control (Linux, macOS, WSL)."""
    return termios is not None


class Terminal:
    def __init__(self, out: TextIO | None = None, fd: int | None = None) -> None:
        self.out = out or sys.stdout
        self.fd = sys.stdin.fileno() if fd is None else fd
        self.resized = True  # the screen needs a full redraw (set on start and after fg)
        self._saved_mode: list | None = None
        self._saved_handlers: dict[int, Any] = {}
        self._active = False

    def __enter__(self) -> Terminal:
        self._saved_mode = termios.tcgetattr(self.fd)
        self._install_handlers()
        self._activate()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self._deactivate()
        for signum, handler in self._saved_handlers.items():
            signal.signal(signum, handler)
        self._saved_handlers.clear()

    def _activate(self) -> None:
        mode = termios.tcgetattr(self.fd)
        mode[_IFLAG] &= ~(termios.IXON | termios.ICRNL)
        mode[_LFLAG] &= ~(termios.ECHO | termios.ICANON | termios.ISIG | termios.IEXTEN)
        mode[_CC][termios.VMIN] = 1
        mode[_CC][termios.VTIME] = 0
        termios.tcsetattr(self.fd, termios.TCSAFLUSH, mode)
        self.write(ALT_SCREEN_ON + CURSOR_HIDE + WRAP_OFF + CLEAR)
        self._active = True
        self.resized = True

    def _deactivate(self) -> None:
        if not self._active:
            return
        self._active = False
        self.write(RESET + WRAP_ON + CURSOR_SHOW + ALT_SCREEN_OFF)
        if self._saved_mode is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self._saved_mode)

    def _install_handlers(self) -> None:
        wanted = {
            signal.SIGTERM: self._on_terminate,
            signal.SIGHUP: self._on_terminate,
            signal.SIGTSTP: self._on_stop,
            signal.SIGCONT: self._on_continue,
        }
        for signum, handler in wanted.items():
            self._saved_handlers[signum] = signal.signal(signum, handler)

    def _on_terminate(self, signum: int, _frame: FrameType | None) -> None:
        raise SystemExit(128 + signum)

    def _on_stop(self, _signum: int, _frame: FrameType | None) -> None:
        self.suspend()

    def _on_continue(self, _signum: int, _frame: FrameType | None) -> None:
        if not self._active:
            self._activate()

    def suspend(self) -> None:
        """Hand the terminal back to the shell and stop, like Ctrl-Z in any TUI.

        Execution continues here after ``fg``; the SIGCONT handler has
        restored the screen by then.
        """
        self._deactivate()
        signal.signal(signal.SIGTSTP, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGTSTP)
        signal.signal(signal.SIGTSTP, self._on_stop)
        if not self._active:  # SIGCONT can arrive before the handler is reinstalled
            self._activate()

    def write(self, data: str) -> None:
        self.out.write(data)
        self.out.flush()

    def size(self) -> tuple[int, int]:
        return terminal_size()
