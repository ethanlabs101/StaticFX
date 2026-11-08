"""What the registry knows about an effect before it is created."""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass

from staticfx.effects.base import Effect
from staticfx.effects.engine import EngineEffect, Recipe

Factory = Callable[..., Effect]

BUILTIN, GENERATED, USER = "builtin", "generated", "user"


@dataclass(frozen=True)
class EffectSpec:
    key: str
    label: str
    description: str
    category: str
    factory: Factory
    kind: str = BUILTIN
    tags: tuple[str, ...] = ()
    recipe: Recipe | None = None

    @property
    def editable(self) -> bool:
        """Recipe effects can be opened in the Studio; hand-written built-ins can't."""
        return self.recipe is not None

    def create(self, rng: random.Random, unicode: bool = False, ascii_only: bool = False) -> Effect:
        effect = self.factory(rng, unicode=unicode and not ascii_only)
        effect.ascii_only = ascii_only
        return effect

    def search_text(self) -> str:
        words = (self.label, self.key, self.category, self.description, *self.tags)
        return " ".join(words).lower()


def recipe_spec(
    key: str, label: str, description: str, category: str, kind: str, recipe: Recipe
) -> EffectSpec:
    """A spec for an effect drawn by the procedural engine."""

    def factory(rng: random.Random, unicode: bool = False) -> Effect:
        return EngineEffect(rng, unicode, recipe=recipe)

    return EffectSpec(key, label, description, category, factory, kind, recipe=recipe)
