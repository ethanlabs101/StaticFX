"""Where user data lives, and writing it safely."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

NAME_LIMIT = 40


def default_data_dir() -> Path:
    """``$XDG_CONFIG_HOME/staticfx``, falling back to ``~/.config/staticfx``."""
    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else Path.home() / ".config") / "staticfx"


def atomic_write(path: Path, text: str) -> None:
    """Write ``text`` so that ``path`` is never left half-written.

    The data goes to a temporary file in the same directory, which is then
    renamed over the target; a rename within one filesystem is atomic.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temp, path)
    except BaseException:
        Path(temp).unlink(missing_ok=True)
        raise


def clean_name(name: str) -> str:
    """Collapse whitespace and cap the length of a user-supplied name."""
    return " ".join(str(name).split())[:NAME_LIMIT]


def slugify(name: str) -> str:
    """A safe file stem: lowercase letters, digits and underscores."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug[:32] or "effect"
