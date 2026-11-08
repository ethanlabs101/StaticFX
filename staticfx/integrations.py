"""System information (fastfetch / neofetch) drawn over an effect."""

from __future__ import annotations

import re
import shutil
import subprocess

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
                    TOOLS[name], capture_output=True, text=True, timeout=TIMEOUT, check=True
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
