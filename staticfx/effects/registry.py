"""Every effect the app can play, in a stable order."""

from __future__ import annotations

import random
from collections.abc import Iterator

from staticfx.effects.base import Effect
from staticfx.effects.builtin import builtin_specs
from staticfx.effects.curated import EXCLUDED, GALLERY
from staticfx.effects.engine import GENERATED_COUNT, describe, generate
from staticfx.effects.spec import BUILTIN, GENERATED, USER, EffectSpec, recipe_spec

GENERATED_CATEGORY = "Generated"
USER_CATEGORY = "My Effects"
USER_PREFIX = "my_"


def generated_key(seed: int) -> str:
    return f"proc_{seed:03d}"


class Registry:
    """Built-ins first, then generated effects, then the user's own.

    Generated effects that failed the quality gate (see ``tools/curate.py``)
    are left out entirely.
    """

    def __init__(self) -> None:
        self._specs: dict[str, EffectSpec] = {spec.key: spec for spec in builtin_specs()}
        for seed in range(GENERATED_COUNT):
            if seed not in EXCLUDED:
                recipe, label = generate(seed)
                key = generated_key(seed)
                self._specs[key] = recipe_spec(
                    key, label, describe(recipe), GENERATED_CATEGORY, GENERATED, recipe
                )
        self.gallery = tuple(generated_key(seed) for seed in GALLERY if seed not in EXCLUDED)

    def __contains__(self, key: object) -> bool:
        return key in self._specs

    def __len__(self) -> int:
        return len(self._specs)

    def __iter__(self) -> Iterator[str]:
        return iter(self._specs)

    def __getitem__(self, key: str) -> EffectSpec:
        return self._specs[key]

    def keys(self) -> list[str]:
        return list(self._specs)

    def specs(self) -> list[EffectSpec]:
        return list(self._specs.values())

    def count(self, kind: str) -> int:
        return sum(1 for spec in self._specs.values() if spec.kind == kind)

    def make(
        self, key: str, rng: random.Random, unicode: bool = False, ascii_only: bool = False
    ) -> Effect:
        return self._specs[key].create(rng, unicode=unicode, ascii_only=ascii_only)

    def resolve(self, name: str | int) -> str:
        """Turn what a user typed into a key; raises ``KeyError`` if nothing matches.

        Accepts, in order of preference: an exact key (``plasma``, ``proc_042``,
        ``my_sunrise``), the ``proc42`` shorthand, a position in the list, and
        a display name (``"Matrix Rain"``). Built-ins win name clashes, so a
        user effect called "Plasma" never hides the built-in one.
        """
        text = str(name).strip().lower()
        if text in self._specs:
            return text
        if text.startswith("proc") and text[4:].lstrip("_").isdigit():
            key = generated_key(int(text[4:].lstrip("_")))
            if key in self._specs:
                return key
        if text.isdigit() and int(text) < len(self._specs):
            return self.keys()[int(text)]
        for spec in self._specs.values():
            if spec.label.lower() == text:
                return spec.key
        if USER_PREFIX + text in self._specs:
            return USER_PREFIX + text
        raise KeyError(name)

    def put_user(self, spec: EffectSpec) -> None:
        """Add or replace one of the user's effects."""
        if spec.kind != USER or not spec.key.startswith(USER_PREFIX):
            raise ValueError(f"not a user effect: {spec.key}")
        self._specs[spec.key] = spec

    def remove_user(self, key: str) -> None:
        if self._specs[key].kind != USER:
            raise ValueError(f"only your own effects can be removed, not {key}")
        del self._specs[key]


__all__ = ["BUILTIN", "GENERATED", "GENERATED_CATEGORY", "USER", "USER_CATEGORY", "Registry"]
