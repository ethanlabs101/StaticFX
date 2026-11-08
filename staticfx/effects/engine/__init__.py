"""The procedural engine: recipes of layered patterns, warps and filters.

Every generated effect and every effect made in the Studio is a
:class:`Recipe` drawn by :class:`EngineEffect`.
"""

from staticfx.effects.engine.effect import EngineEffect
from staticfx.effects.engine.generate import GENERATED_COUNT, describe, generate
from staticfx.effects.engine.recipe import Recipe

__all__ = ["GENERATED_COUNT", "EngineEffect", "Recipe", "describe", "generate"]
