"""Run the real ``staticfx`` in a pseudo-terminal and read back what's on screen.

The tiny emulator understands exactly what StaticFX writes (cursor moves,
clears, colours, mode switches), which is enough to assert on screen text.
"""

from __future__ import annotations

import codecs
import fcntl
import os
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path

SEQUENCE = re.compile(r"\x1b\[([?0-9;]*)([A-Za-z])")
UNFINISHED = re.compile(r"\x1b(\[[?0-9;]*)?$")
KEYS = {
    "up": "\x1b[A",
    "down": "\x1b[B",
    "right": "\x1b[C",
    "left": "\x1b[D",
    "enter": "\r",
    "escape": "\x1b",
    "tab": "\t",
    "backspace": "\x7f",
    "delete": "\x1b[3~",
    "pageup": "\x1b[5~",
    "pagedown": "\x1b[6~",
    "space": " ",
}


class Screen:
    def __init__(self, width: int, height: int) -> None:
        self.width, self.height = width, height
        self.rows = [[" "] * width for _ in range(height)]
        self.x = self.y = 0
        self.alternate = False
        self.cursor_visible = True
        self._partial = ""  # an escape sequence split across two reads
        self.new_size: tuple[int, int] | None = None
        self.clears = 0

    def resize(self, width: int, height: int) -> None:
        """Take the new size at the app's next clear.

        Output already on its way was laid out for the old size; applying it
        to the new grid scrambles the screen, which macOS pipes made obvious.
        """
        self.new_size = (width, height)

    def feed(self, data: str) -> None:
        data, self._partial = self._partial + data, ""
        unfinished = UNFINISHED.search(data)
        if unfinished:
            data, self._partial = data[: unfinished.start()], unfinished.group()
        pos = 0
        while pos < len(data):
            match = SEQUENCE.match(data, pos) if data[pos] == "\x1b" else None
            if match:
                self._control(match.group(1), match.group(2))
                pos = match.end()
                continue
            char = data[pos]
            pos += 1
            if char == "\r":
                self.x = 0
            elif char == "\n":
                self.y = min(self.height - 1, self.y + 1)
            elif char >= " " and 0 <= self.y < self.height and self.x < self.width:
                self.rows[self.y][self.x] = char
                self.x += 1

    def _control(self, params: str, final: str) -> None:
        if final == "H":
            row, _, col = params.partition(";")
            self.y, self.x = int(row or 1) - 1, int(col or 1) - 1
        elif final == "K" and 0 <= self.y < self.height:
            self.rows[self.y][self.x :] = [" "] * (self.width - self.x)
        elif final == "J":
            if self.new_size:
                (self.width, self.height), self.new_size = self.new_size, None
            self.rows = [[" "] * self.width for _ in range(self.height)]
            self.clears += 1
        elif final in "hl" and params == "?1049":
            self.alternate = final == "h"
        elif final in "hl" and params == "?25":
            self.cursor_visible = final == "h"

    def text(self) -> str:
        return "\n".join("".join(row) for row in self.rows)


class Session:
    """``staticfx`` running in a pty of ``width`` x ``height``."""

    def __init__(self, data_dir: Path, *args: str, width: int = 100, height: int = 30) -> None:
        self.screen = Screen(width, height)
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
        env = {**os.environ, "TERM": "xterm-256color", "COLORTERM": "truecolor", "LANG": "C.UTF-8"}
        env.pop("COLUMNS", None)
        env.pop("LINES", None)
        self.process = subprocess.Popen(
            [sys.executable, "-m", "staticfx", "--data-dir", str(data_dir), *args],
            stdin=slave,
            stdout=slave,
            stderr=subprocess.PIPE,
            env=env,
            start_new_session=True,
            cwd=Path(__file__).resolve().parent.parent,
        )
        os.close(slave)
        self.master = master
        self.raw = ""
        self._decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")

    def pump(self, seconds: float = 0.4) -> str:
        """Read output for ``seconds``; returns the screen text afterwards."""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            ready, _, _ = select.select([self.master], [], [], 0.05)
            if ready:
                try:
                    chunk = self._decoder.decode(os.read(self.master, 65536))
                except OSError:
                    break
                self.raw += chunk
                self.screen.feed(chunk)
        return self.screen.text()

    def press(self, *keys: str, wait: float = 0.35) -> str:
        for key in keys:
            os.write(self.master, KEYS.get(key, key).encode())
            self.pump(0.08)
        return self.pump(wait)

    def type(self, text: str, wait: float = 0.35) -> str:
        os.write(self.master, text.encode())
        return self.pump(wait)

    def resize(self, width: int, height: int) -> str:
        clears = self.screen.clears
        self.screen.resize(width, height)
        fcntl.ioctl(self.master, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
        end = time.monotonic() + 3.0
        while self.screen.clears == clears and time.monotonic() < end:
            self.pump(0.05)
        return self.pump(0.3)

    def wait_exit(self, timeout: float = 5.0) -> int:
        end = time.monotonic() + timeout
        while self.process.poll() is None and time.monotonic() < end:
            self.pump(0.1)
        if self.process.poll() is None:
            self.kill()
            raise AssertionError("staticfx did not exit")
        return self.process.returncode

    def kill(self) -> None:
        if self.process.poll() is None:
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait()

    def close(self) -> None:
        self.kill()
        os.close(self.master)
        if self.process.stderr:
            self.process.stderr.close()
