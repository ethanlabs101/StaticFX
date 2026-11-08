"""Keyboard input: raw bytes from the terminal -> key names.

Printable characters come back as themselves (``"a"``, ``"?"``). Everything
else gets a name: ``up``, ``down``, ``left``, ``right``, ``home``, ``end``,
``pageup``, ``pagedown``, ``delete``, ``enter``, ``tab``, ``shift-tab``,
``backspace``, ``escape``, ``space`` and ``ctrl-a`` .. ``ctrl-z``.
"""

from __future__ import annotations

import os
import select

_CSI_LETTER = {
    "A": "up",
    "B": "down",
    "C": "right",
    "D": "left",
    "H": "home",
    "F": "end",
    "Z": "shift-tab",
}
_CSI_TILDE = {
    "1": "home",
    "2": "insert",
    "3": "delete",
    "4": "end",
    "5": "pageup",
    "6": "pagedown",
    "7": "home",
    "8": "end",
}
_CONTROL = {"\r": "enter", "\n": "enter", "\t": "tab", "\x7f": "backspace", "\x08": "backspace"}

# How long to wait for the rest of an escape sequence before deciding the
# user pressed Esc on its own. Terminals send sequences in one write, so this
# only matters on very slow links.
ESCAPE_TIMEOUT = 0.03


def decode(data: str) -> tuple[list[str], str]:
    """Split ``data`` into key names.

    Returns ``(keys, rest)`` where ``rest`` is an incomplete escape sequence
    at the end of ``data`` that should be prepended to the next read.
    """
    keys: list[str] = []
    i, size = 0, len(data)
    while i < size:
        char = data[i]
        if char == "\x1b":
            if i + 1 == size:
                return keys, data[i:]
            if data[i + 1] in "[O":
                end = i + 2
                while end < size and (data[end].isdigit() or data[end] == ";"):
                    end += 1
                if end == size:
                    return keys, data[i:]
                final, params = data[end], data[i + 2 : end].split(";", maxsplit=1)[0]
                if final == "~":
                    keys.append(_CSI_TILDE.get(params, "unknown"))
                else:
                    keys.append(_CSI_LETTER.get(final, "unknown"))
                i = end + 1
                continue
            keys.append("escape")  # Esc, or Alt+key: the key follows separately
        elif char in _CONTROL:
            keys.append(_CONTROL[char])
        elif char == " ":
            keys.append("space")
        elif "\x01" <= char <= "\x1a":
            keys.append("ctrl-" + chr(ord(char) + 96))
        elif char.isprintable():
            keys.append(char)
        i += 1
    return keys, ""


class KeyReader:
    """Non-blocking reads from a terminal file descriptor."""

    def __init__(self, fd: int) -> None:
        self.fd = fd

    def _ready(self, timeout: float) -> bool:
        try:
            return bool(select.select([self.fd], [], [], timeout)[0])
        except (OSError, ValueError):
            return False

    def _read(self) -> str:
        try:
            return os.read(self.fd, 1024).decode("utf-8", errors="ignore")
        except OSError:
            return ""

    def read(self) -> list[str]:
        """All keys pressed since the last call (possibly none)."""
        data = ""
        while self._ready(0):
            chunk = self._read()
            if not chunk:
                break
            data += chunk
        if not data:
            return []
        keys, rest = decode(data)
        if rest and self._ready(ESCAPE_TIMEOUT):
            more, rest = decode(rest + self._read())
            keys += more
        if rest == "\x1b":  # a lone Esc that nothing followed
            keys.append("escape")
        # Anything else left over is a sequence that never completed; dropping
        # it is better than letting it swallow the next key press.
        return keys
