"""The procedural engine: parameter schema, recipes, generation."""

from __future__ import annotations

import contextlib
import hashlib
import json
import random

import pytest

from staticfx.effects.engine import GENERATED_COUNT, Recipe, describe, generate
from staticfx.effects.engine.filters import FILTERS
from staticfx.effects.engine.layers import LAYERS
from staticfx.effects.engine.schema import Param
from staticfx.effects.engine.warps import WARPS

ALL_RECIPES = [generate(seed)[0] for seed in range(GENERATED_COUNT)]

# Hash of every generated recipe. If this changes, proc_NNN effects changed
# for everyone, and their favourites now point at different pictures. Only
# update it on purpose, and say so in the changelog.
GENERATED_FINGERPRINT = "03b3ee9d235cccaede1721a624e5ef8b"


def test_generated_effects_are_stable() -> None:
    payload = json.dumps([r.to_dict() for r in ALL_RECIPES], sort_keys=True).encode()
    assert hashlib.md5(payload).hexdigest() == GENERATED_FINGERPRINT


def test_generation_is_deterministic_and_named() -> None:
    first, name = generate(42)
    again, same = generate(42)
    assert first.to_dict() == again.to_dict() and name == same
    assert name.endswith(" 042")
    assert describe(first)


@pytest.mark.parametrize("recipe", ALL_RECIPES[::7])
def test_recipes_round_trip_through_json(recipe: Recipe) -> None:
    data = json.loads(json.dumps(recipe.to_dict()))
    assert Recipe.from_dict(data).to_dict() == recipe.to_dict()


def test_every_kind_has_valid_defaults() -> None:
    for kinds in (LAYERS, WARPS, FILTERS):
        for kind in kinds.values():
            assert kind.clean({}) == kind.defaults()
            assert kind.build(kind.defaults(), 1.0) is not None
            for param in kind.params:
                assert param.clean(param.default) == param.default, f"{kind.name}.{param.name}"


def test_param_clean_and_nudge() -> None:
    number = Param("n", "N", 5, 1, 10, 1, integer=True)
    assert number.clean(99) == 10 and number.clean(-4) == 1 and number.clean(3.6) == 4
    assert number.nudge(10, 1) == 10 and number.nudge(5, -1) == 4
    with pytest.raises(ValueError):
        number.clean("7")
    with pytest.raises(ValueError):
        number.clean(True)
    choice = Param("c", "C", "a", choices=("a", "b", "c"))
    assert choice.nudge("c", 1) == "a" and choice.nudge("zzz", 1) == "b"
    with pytest.raises(ValueError):
        choice.clean("d")


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (None, "must be an object"),
        ({}, "at least one layer"),
        ({"layers": [{"kind": "nope"}]}, "unknown layer kind"),
        ({"layers": "spiral"}, "must be a list"),
        ({"layers": [{"kind": "spiral"}] * 4}, "at most 3"),
        ({"layers": [{"kind": "spiral", "arms": "many"}]}, "arms must be a number"),
        ({"layers": [{"kind": "rings", "shape": "hexagon"}]}, "shape must be one of"),
        ({"layers": [{"kind": "spiral"}, {"kind": "grid", "blend": "smush"}]}, "unknown blend"),
        ({"layers": [{"kind": "spiral"}], "palette": {"kind": "plaid"}}, "palette kind"),
        ({"layers": [{"kind": "spiral"}], "palette": {"kind": "duo", "first": "#zz"}}, "hex"),
        ({"layers": [{"kind": "spiral"}], "charset": "abc"}, "charset"),
        ({"layers": [{"kind": "spiral"}], "speed": "fast"}, "'speed' must be a number"),
    ],
)
def test_bad_recipes_are_explained(data: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Recipe.from_dict(data)


def test_out_of_range_values_are_clamped_not_rejected() -> None:
    recipe = Recipe.from_dict(
        {"layers": [{"kind": "spiral", "arms": 500, "scale": -3}], "speed": 99, "trail": 5}
    )
    assert recipe.layers[0].params["arms"] == 12
    assert recipe.speed == 6.0 and recipe.trail == 0.98


def test_mutated_recipes_never_raise_anything_but_value_error() -> None:
    """Randomly corrupt real recipes; loading must fail cleanly or succeed."""
    rng = random.Random(0)
    junk = [None, -1, 1e9, "x", [], {}, True, [1, 2], {"kind": "spiral"}]
    for recipe in ALL_RECIPES[:200]:
        data = recipe.to_dict()
        key = rng.choice(list(data))
        data[key] = rng.choice(junk)
        for stage in data.get("layers", []) if isinstance(data.get("layers"), list) else []:
            if isinstance(stage, dict) and rng.random() < 0.3:
                stage[rng.choice(list(stage))] = rng.choice(junk)
        with contextlib.suppress(ValueError):
            Recipe.from_dict(data)
