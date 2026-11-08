"""Settings, kept in ``config.json``.

Loading never fails: a missing file gives the defaults, and any value that
is the wrong type or out of range is replaced by its default with a warning.
A hand-edited typo can't stop the app from starting.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path
from typing import Any

from staticfx import themes
from staticfx.library.files import atomic_write

VERSION = 3
CHARACTERS = ("auto", "katakana", "ascii")
COLOURS = ("auto", "truecolor", "256")
FPS_RANGE = (5, 60)
SPEED_RANGE = (0.1, 5.0)
AUTO_RANGE = (3.0, 600.0)
LIST_LIMIT = 500


@dataclass
class Settings:
    effect: str = "matrix"
    theme: str = themes.DEFAULT
    speed: float = 1.0
    fps: int = 30
    crt: bool = False
    glitch: bool = False
    recolour: bool = False
    characters: str = "auto"  # "auto", "katakana" or "ascii"
    colour: str = "auto"  # "auto", "truecolor" or "256"
    allow_flashing: bool = False  # unlocks the Strobe theme
    auto_seconds: float = 12.0  # how long each effect plays in auto-cycle
    favorites: list[str] = field(default_factory=list)
    recent: list[str] = field(default_factory=list)
    keybinds: dict[str, str] = field(default_factory=dict)  # only the user's changes
    seen_welcome: bool = False
    imported_plugins: bool = False  # 1.x plugins folder already copied into effects/

    def to_json(self) -> str:
        return json.dumps({"version": VERSION, **asdict(self)}, indent=2) + "\n"


def _migrate(data: dict[str, Any]) -> dict[str, Any]:
    """Rename 1.x keys to their current names."""
    data = dict(data)
    if "rainbow" in data:
        data.setdefault("recolour", data.pop("rainbow"))
    if data.pop("use_256_color", False):
        data.setdefault("colour", "256")
    if data.pop("unicode", False):
        data.setdefault("characters", "katakana")
    if data.get("version", 1) < 2:
        data.pop("keybinds", None)  # 1.x saved the whole key map, which pinned old defaults
    return data


def _check(name: str, value: Any, default: Any) -> Any:
    """``value`` cleaned up for setting ``name``; raises ``ValueError`` if unusable."""
    if name == "theme":
        return themes.normalize(str(value))
    if name in ("characters", "colour"):
        options = CHARACTERS if name == "characters" else COLOURS
        if value not in options:
            raise ValueError(f"must be one of {', '.join(options)}")
        return value
    if isinstance(default, bool):
        if not isinstance(value, bool):
            raise ValueError("must be true or false")
        return value
    if isinstance(default, (int, float)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("must be a number")
        low, high = {"fps": FPS_RANGE, "speed": SPEED_RANGE, "auto_seconds": AUTO_RANGE}[name]
        value = min(high, max(low, value))
        return int(value) if isinstance(default, int) else float(value)
    if isinstance(default, list):
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ValueError("must be a list of effect names")
        return list(dict.fromkeys(value))[:LIST_LIMIT]
    if isinstance(default, dict):
        if not isinstance(value, dict):
            raise ValueError('must be an object like {"y": "crt"}')
        return {str(k): str(v) for k, v in value.items()}
    if not isinstance(value, str) or not value:
        raise ValueError("must be a non-empty string")
    return value


def load(path: Path) -> tuple[Settings, list[str]]:
    """Read ``path``. Returns the settings and warnings about anything ignored."""
    settings = Settings()
    if not path.exists():
        return settings, []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return settings, [f"{path.name} is unreadable ({exc}); using default settings"]
    if not isinstance(data, dict):
        return settings, [f"{path.name} is not a JSON object; using default settings"]

    warnings = []
    data = _migrate(data)
    for f in fields(Settings):
        if f.name not in data:
            continue
        default = getattr(settings, f.name)
        try:
            setattr(settings, f.name, _check(f.name, data[f.name], default))
        except ValueError as exc:
            warnings.append(f"{path.name}: ignoring '{f.name}' ({exc})")
    return settings, warnings


def save(settings: Settings, path: Path) -> None:
    atomic_write(path, settings.to_json())
