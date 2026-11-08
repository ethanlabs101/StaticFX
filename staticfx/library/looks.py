"""Looks: an effect plus a theme, speed and filters, saved under a name."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from staticfx import themes
from staticfx.library.files import atomic_write, clean_name

SPEED_MIN, SPEED_MAX = 0.1, 5.0


@dataclass(frozen=True)
class Look:
    name: str
    effect: str
    theme: str = themes.DEFAULT
    speed: float = 1.0
    crt: bool = False
    glitch: bool = False
    recolour: bool = False
    note: str = ""  # a short description shown in the menu (built-in looks only)


BUILTIN_LOOKS = (
    Look("Classic Matrix", "matrix", "matrix", note="Where it all started"),
    Look(
        "Terminal Breach",
        "decrypt_scramble",
        "matrix",
        crt=True,
        glitch=True,
        note="Movie-hacker decryption on a CRT",
    ),
    Look("Cyber Rain", "matrix", "cyberpunk", crt=True, recolour=True, note="Neon rain"),
    Look(
        "System Override", "terminal_boot", "toxic", glitch=True, note="A boot sequence going wrong"
    ),
    Look(
        "Signal Intercept",
        "signal_scramble",
        "mono",
        crt=True,
        glitch=True,
        note="Black-and-white scope traces",
    ),
    Look("Neon Intrusion", "circuit", "cyberpunk", glitch=True, note="Glitching circuit traces"),
    Look("Synthwave", "grid_wave", "rose", crt=True, note="An endless neon floor"),
    Look("Deep Sea", "ocean_waves", "ocean", speed=0.7, note="Slow rolling waves"),
    Look("Campfire", "fire", "inferno", note="Pull up a chair"),
    Look("Deep Space", "starfield", "arctic", speed=0.6, note="Drifting through the stars"),
    Look("Winter Night", "snowfall", "arctic", note="Quiet snow"),
    Look("Hanami", "sakura_rain", "sakura", note="Cherry blossom season"),
)


class LookStore:
    """The user's saved looks, kept in ``looks.json``."""

    def __init__(self, path: Path | None) -> None:
        self.path = path  # None keeps looks in memory only
        self.looks: list[Look] = []

    def load(self) -> list[str]:
        """Read the file. Returns problems; a bad file or entry is skipped, never fatal."""
        self.looks = []
        if self.path is None or not self.path.exists():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            entries = data["looks"]
            if not isinstance(entries, list):
                raise TypeError
        except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError):
            return [f"{self.path.name} is unreadable; your saved looks were not loaded"]

        problems = []
        for entry in entries:
            try:
                theme = themes.normalize(str(entry.get("theme", themes.DEFAULT)))
                self.looks.append(
                    Look(
                        name=clean_name(entry["name"]) or "Untitled",
                        effect=str(entry["effect"]),
                        theme=theme,
                        speed=min(SPEED_MAX, max(SPEED_MIN, float(entry.get("speed", 1.0)))),
                        crt=bool(entry.get("crt", False)),
                        glitch=bool(entry.get("glitch", False)),
                        # "recolor" is the 1.x spelling
                        recolour=bool(entry.get("recolour", entry.get("recolor", False))),
                    )
                )
            except (AttributeError, KeyError, TypeError, ValueError):
                problems.append(f"{self.path.name}: skipped a malformed look")
        return problems

    def save(self) -> None:
        if self.path is None:
            return
        looks = []
        for look in self.looks:
            data = asdict(look)
            del data["note"]
            looks.append(data)
        atomic_write(self.path, json.dumps({"version": 2, "looks": looks}, indent=2) + "\n")

    def find(self, name: str) -> Look | None:
        wanted = name.strip().lower()
        return next((look for look in self.looks if look.name.lower() == wanted), None)

    def put(self, look: Look) -> bool:
        """Add ``look``, replacing one with the same name. True if it replaced one."""
        existing = self.find(look.name)
        if existing is not None:
            self.looks[self.looks.index(existing)] = look
        else:
            self.looks.append(look)
        self.save()
        return existing is not None

    def remove(self, name: str) -> None:
        existing = self.find(name)
        if existing is not None:
            self.looks.remove(existing)
            self.save()


def find_look(name: str, store: LookStore) -> Look | None:
    """A saved look by name, falling back to the built-in ones."""
    wanted = name.strip().lower()
    builtin = next((look for look in BUILTIN_LOOKS if look.name.lower() == wanted), None)
    return store.find(name) or builtin
