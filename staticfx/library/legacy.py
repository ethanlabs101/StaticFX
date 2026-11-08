"""Reading files written by StaticFX 1.x.

1.x had two incompatible formats that both used the ``.sfx`` extension:

* **Studio effects** (``"format": "staticfx-effect"``, version 2) stored the
  recipe with terse keys - ``tfs``, ``pal``, ``f``, ``cre`` - and kind names
  that were later renamed.
* **Plugins** (``"format": "sfx"``, version 1), read from a hidden
  ``plugins/`` folder, described a single generator from a second engine that
  no longer exists. They are translated to the nearest equivalent layer.

Both are converted to today's :class:`Recipe` on load; nothing is written
back until the user saves.
"""

from __future__ import annotations

from typing import Any

from staticfx.core.color import RGB, parse_hex
from staticfx.effects.engine.generate import filter_params, layer_params, warp_params
from staticfx.effects.engine.layers import LAYERS, MANDELBROT_SPOTS
from staticfx.effects.engine.recipe import CHARSETS, Palette, Recipe, Stage

RENAMED = {
    "kaleido": "kaleidoscope",
    "warp": "wave",
    "pixel": "pixelate",
    "mandel": "mandelbrot",
    "hex": "hexagons",
    "lissa": "lissajous",
    "vnoise": "noise",
    "saw": "sawtooth",
}
BLENDS = {
    "add": "average",
    "mul": "multiply",
    "max": "lighten",
    "min": "darken",
    "diff": "difference",
    "screen": "screen",
    "mod": "wrap",
    "warp": "displace",
}
METRICS = {"euclid": "circle", "manhattan": "diamond", "chebyshev": "square", "mink": "star"}
SHAPES = {"tri": "triangle"}
VORONOI = {"edge": "edges", "cell": "distance", "id": "cells"}

# Defaults for every original parameter, so partial files still convert.
WARP_DEFAULTS = {
    "rate": 0.2, "base": 1.5, "amp": 0.3, "zrate": 0.8, "n": 6, "rot": 0.2, "mode": "xy",
    "s": 2.0, "dx": 0.2, "dy": 0.1, "k": 2.0, "freq": 3.0, "c": 0.3, "ang": 0.7,
    "iters": 2, "q": 8.0, "rfreq": 10.0, "rrate": 2.0,
}  # fmt: skip
LAYER_DEFAULTS = {
    "f": 6.0, "f2": 6.0, "sp": 1.0, "n": 4, "k": 4, "metric": "euclid", "shape": "ring",
    "mode": "edge", "cre": -0.6, "cim": 0.2, "mpt": (-0.745, 0.113), "vseed": 1,
}  # fmt: skip
FILTER_DEFAULTS = {"g": 1.2, "n": 4, "k": 3, "pw": 1.0, "c": 0.3}


def _pairs(value: Any, what: str) -> list[tuple[str, dict]]:
    if not isinstance(value, list):
        raise ValueError(f"'{what}' must be a list")
    pairs = []
    for entry in value:
        if not (
            isinstance(entry, (list, tuple)) and len(entry) == 2 and isinstance(entry[1], dict)
        ):
            raise ValueError(f"each entry in '{what}' must be [kind, {{params}}]")
        kind = str(entry[0])
        pairs.append((RENAMED.get(kind, kind), entry[1]))
    return pairs


def _nearest_spot(point: Any) -> str:
    try:
        x, y = float(point[0]), float(point[1])
    except (TypeError, ValueError, IndexError):
        return "seahorse"
    return min(
        MANDELBROT_SPOTS,
        key=lambda s: abs(MANDELBROT_SPOTS[s][0] - x) + abs(MANDELBROT_SPOTS[s][1] - y),
    )


def recipe_from_v2(data: Any) -> Recipe:
    """Convert a 1.x Studio recipe. Raises ``ValueError`` when it can't be read."""
    if not isinstance(data, dict):
        raise ValueError("recipe must be an object")
    try:
        layers = []
        for kind, raw in _pairs(data.get("layers"), "layers"):
            v = {**LAYER_DEFAULTS, **raw}
            v["metric"] = METRICS.get(v["metric"], "circle")
            v["shape"] = SHAPES.get(v["shape"], v["shape"])
            v["mode"] = VORONOI.get(v["mode"], "edges")
            v["spot"] = _nearest_spot(v["mpt"])
            v["seed"] = v["vseed"]
            layers.append(Stage(kind, layer_params(kind, v, float(v["sp"]))))
        if not 1 <= len(layers) <= 3:
            raise ValueError("a recipe needs 1-3 layers")
        for layer, op in zip(layers[1:], data.get("ops", []), strict=False):
            layer.blend = BLENDS.get(op, "average")

        warps = [
            Stage(kind, warp_params(kind, {**WARP_DEFAULTS, **raw}))
            for kind, raw in _pairs(data.get("tfs", []), "tfs")
        ]
        filters = [
            Stage(kind, filter_params(kind, {**FILTER_DEFAULTS, **raw}))
            for kind, raw in _pairs(data.get("posts", []), "posts")
        ]

        pal = data.get("pal", ["theme"])
        if pal[0] == "rainbow":
            palette = Palette("rainbow", float(pal[1]), float(pal[2]), float(pal[3]) % 1.0)
        elif pal[0] == "duo":
            palette = Palette("duo", first=RGB(*map(int, pal[1])), second=RGB(*map(int, pal[2])))
        else:
            palette = Palette("angular" if pal[0] == "angular" else "theme")

        return Recipe(
            layers=layers,
            warps=warps[:3],
            filters=filters[:3],
            speed=min(6.0, max(0.05, float(data.get("speed", 1.0)))),
            charset=CHARSETS[int(data.get("ramp_pick", 0)) % len(CHARSETS)],
            glyph_rain=data.get("style") == "glyph",
            dither=bool(data.get("dither", False)),
            palette=palette,
            trail=min(0.98, max(0.0, float(data.get("trail", 0.0)))),
            pulse=float(data.get("pulse_rate", 2.0)) if data.get("pulse") else 0.0,
            scanlines=bool(data.get("scan", False)),
            glitch=bool(data.get("glitch", False)),
            sparkle=min(0.05, max(0.0, float(data.get("sparkle", 0.0)))),
            seed=int(data.get("seed", 0)),
        )
    except (KeyError, TypeError, IndexError) as exc:  # unknown kind, malformed value
        raise ValueError(f"unreadable 1.x recipe ({exc.__class__.__name__}: {exc})") from None


# The 1.x plugin engine's generators and the layer each now becomes.
PLUGIN_GENERATORS = {
    "field": "flow",
    "noise": "noise",
    "waves": "grid",
    "particles": "sources",
    "grid": "checker",
    "spiral": "spiral",
    "radial": "rings",
    "cellular": "voronoi",
}


def recipe_from_plugin(data: dict) -> Recipe:
    """Best-effort conversion of a 1.x plugin definition."""
    generator = data.get("generator")
    if generator not in PLUGIN_GENERATORS:
        raise ValueError(f"unknown plugin generator {generator!r}")
    kind = PLUGIN_GENERATORS[generator]
    params = data.get("parameters") or {}
    layer = {"speed": params.get("speed", 1.0)} if isinstance(params, dict) else {}
    if kind == "voronoi":
        layer["style"] = "cells"
    colours = []
    for text in data.get("palette") or []:
        try:
            colours.append(parse_hex(str(text)))
        except ValueError:
            continue
    palette = (
        Palette("duo", first=colours[0], second=colours[-1]) if len(colours) >= 2 else Palette()
    )
    seed = data.get("seed", 0)
    return Recipe(
        layers=[Stage(kind, LAYERS[kind].clean(layer))],
        palette=palette,
        seed=seed if isinstance(seed, int) and seed >= 0 else 0,
    )
