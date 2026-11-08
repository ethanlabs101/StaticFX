"""The user's own effects: ``.sfx`` files in ``<data dir>/effects``.

A ``.sfx`` file is JSON (documented in ``docs/EFFECT_FORMAT.md``)::

    {"format": "staticfx-effect", "version": 3, "name": "Neon Sunrise",
     "description": "", "created": "2026-11-07", "recipe": {...}}

The file name is the effect's identity: ``neon_sunrise.sfx`` plays as
``my_neon_sunrise``. Files from StaticFX 1.x are converted when read.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from staticfx.effects.engine import Recipe
from staticfx.library.files import atomic_write, clean_name, slugify
from staticfx.library.legacy import recipe_from_plugin, recipe_from_v2

FORMAT = "staticfx-effect"
VERSION = 3
SUFFIX = ".sfx"
DESCRIPTION_LIMIT = 200


@dataclass
class UserEffect:
    id: str
    name: str
    recipe: Recipe
    description: str = ""
    created: str = field(default_factory=lambda: time.strftime("%Y-%m-%d"))

    @property
    def key(self) -> str:
        return f"my_{self.id}"

    def to_json(self) -> str:
        data = {
            "format": FORMAT,
            "version": VERSION,
            "name": self.name,
            "description": self.description,
            "created": self.created,
            "recipe": self.recipe.to_dict(),
        }
        return json.dumps(data, indent=2) + "\n"


def parse(text: str, ident: str) -> UserEffect:
    """Read any supported ``.sfx`` version. Raises ``ValueError`` explaining what's wrong."""
    try:
        data: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"not valid JSON (line {exc.lineno}: {exc.msg})") from None
    if not isinstance(data, dict):
        raise ValueError("not a StaticFX effect file")

    if data.get("format") == "sfx":  # a 1.x plugin
        name = clean_name(str(data.get("name") or ident))
        return UserEffect(ident, name, recipe_from_plugin(data), str(data.get("description", "")))
    if data.get("format") != FORMAT:
        raise ValueError("not a StaticFX effect file")

    version = data.get("version", 0)
    if not isinstance(version, int) or version < 2:
        raise ValueError(f"unsupported version {version!r}")
    if version > VERSION:
        raise ValueError("made by a newer StaticFX - please upgrade")
    recipe = (
        Recipe.from_dict(data.get("recipe"))
        if version == VERSION
        else recipe_from_v2(data.get("recipe"))
    )

    return UserEffect(
        id=ident,
        name=clean_name(str(data.get("name", ""))) or "Untitled",
        recipe=recipe,
        description=str(data.get("description", ""))[:DESCRIPTION_LIMIT],
        created=str(data.get("created", "")),
    )


class EffectLibrary:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def path(self, ident: str) -> Path:
        return self.directory / f"{ident}{SUFFIX}"

    def unique_id(self, name: str) -> str:
        """A file stem for ``name`` that isn't taken yet (``sunrise``, ``sunrise_2``, ...).

        A leading "my" is dropped, so "My Sunrise" plays as ``my_sunrise``
        rather than ``my_my_sunrise``.
        """
        base = slugify(name)
        if base.startswith("my_") and len(base) > 3:
            base = base[3:]
        ident, number = base, 2
        while self.path(ident).exists():
            ident, number = f"{base}_{number}", number + 1
        return ident

    def load(self) -> tuple[list[UserEffect], list[str]]:
        """Every readable effect, plus a message for each file that wasn't."""
        effects: list[UserEffect] = []
        problems: list[str] = []
        if not self.directory.is_dir():
            return effects, problems
        for path in sorted(self.directory.glob(f"*{SUFFIX}")):
            try:
                effects.append(parse(path.read_text(encoding="utf-8"), path.stem))
            except (OSError, UnicodeDecodeError, ValueError) as exc:
                problems.append(f"{path.name}: {exc}")
        return effects, problems

    def save(self, effect: UserEffect) -> Path:
        path = self.path(effect.id)
        atomic_write(path, effect.to_json())
        return path

    def delete(self, ident: str) -> None:
        self.path(ident).unlink(missing_ok=True)

    def import_file(self, source: Path) -> UserEffect:
        """Validate ``source`` and copy it in under a fresh id (never overwriting)."""
        try:
            text = source.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise ValueError(f"can't read {source}: {exc}") from None
        effect = parse(text, "imported")
        effect.id = self.unique_id(effect.name)
        self.save(effect)
        return effect

    def import_legacy_plugins(self, folder: Path) -> tuple[int, list[str]]:
        """Copy 1.x plugins from ``folder`` into the library. Returns (count, problems)."""
        count, problems = 0, []
        for path in sorted(folder.glob(f"*{SUFFIX}")) if folder.is_dir() else []:
            try:
                effect = parse(path.read_text(encoding="utf-8"), path.stem)
            except (OSError, UnicodeDecodeError, ValueError) as exc:
                problems.append(f"plugins/{path.name}: {exc}")
                continue
            effect.id = self.unique_id(effect.name)
            self.save(effect)
            count += 1
        return count, problems


def export(effect: UserEffect, destination: Path) -> Path:
    atomic_write(destination, effect.to_json())
    return destination
