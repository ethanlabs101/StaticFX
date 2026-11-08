"""Seeded recipe generation: ``generate(42)`` is the same effect forever.

The order of random draws below is load-bearing: changing it changes every
generated effect, which breaks people's favourites. Add new draws at the
end, never in the middle.
"""

from __future__ import annotations

import random

from staticfx.core.color import hsv
from staticfx.effects.engine.filters import BLENDS, FILTERS
from staticfx.effects.engine.layers import LAYERS, MANDELBROT_SPOTS
from staticfx.effects.engine.recipe import CHARSETS, Palette, Recipe, Stage
from staticfx.effects.engine.warps import WARPS

GENERATED_COUNT = 1000

ADJECTIVES = (
    "Quantum Neon Hyper Cosmic Liquid Fractal Crystal Solar Void Neural Plasma Cyber Astral Chrome"
    " Ghost Ionic Prism Turbo Zen Obsidian Electric Velvet Atomic Lunar Sonic Arctic Molten Digital"
    " Spectral Infinite Phantom Radiant Cryo Nova Titan Vapor Rogue Mythic Binary Ultra"
).split()


def _warp(r: random.Random) -> Stage:
    kind = r.choice(list(WARPS))
    v = {
        "rate": r.uniform(-0.6, 0.6),
        "base": r.uniform(0.8, 2.4),
        "amp": r.uniform(0.1, 0.5),
        "zrate": r.uniform(0.3, 1.5),
        "n": r.choice([3, 4, 5, 6, 7, 8, 10, 12]),
        "rot": r.uniform(-0.4, 0.4),
        "mode": r.choice(["xy", "x", "y"]),
        "s": r.uniform(1.2, 4.0),
        "dx": r.uniform(-0.5, 0.5),
        "dy": r.uniform(-0.5, 0.5),
        "k": r.uniform(-4, 4),
        "freq": r.uniform(1.5, 6.0),
        "c": r.uniform(0.15, 0.6),
        "ang": r.uniform(0.3, 1.2),
        "iters": r.choice([1, 2, 3]),
        "q": r.uniform(4, 14),
        "rfreq": r.uniform(5, 18),
        "rrate": r.uniform(1, 4),
    }
    return Stage(kind, warp_params(kind, v))


def warp_params(kind: str, v: dict) -> dict:
    """Map original-format warp values (``rate``, ``base``, ...) onto ``kind``'s params."""
    params = {
        "rotate": {"spin": v["rate"]},
        "zoom": {"zoom": v["base"], "pulse": v["amp"], "pulse_rate": v["zrate"]},
        "kaleidoscope": {"segments": v["n"], "spin": v["rot"]},
        "mirror": {"axis": v["mode"]},
        "tile": {"tiles": v["s"], "drift_x": v["dx"], "drift_y": v["dy"]},
        "swirl": {"twist": v["k"]},
        "wave": {"strength": v["amp"], "frequency": v["freq"]},
        "polar": {},
        "fold": {"offset": v["c"], "angle": v["ang"], "folds": v["iters"]},
        "pixelate": {"resolution": v["q"]},
        "ripple": {"strength": v["amp"], "frequency": v["rfreq"], "speed": v["rrate"]},
    }[kind]
    return WARPS[kind].clean(params)


def _layer(r: random.Random) -> Stage:
    kind = r.choice(list(LAYERS))
    speed = r.uniform(0.3, 2.0) * r.choice([-1, 1])
    v = {
        "f": r.uniform(2, 14),
        "f2": r.uniform(2, 14),
        "n": r.choice([2, 3, 4, 5, 6, 8, 12]),
        "k": r.choice([3, 4, 5, 6, 7]),
        "metric": r.choice(["circle", "diamond", "square", "star"]),
        "shape": r.choice(["box", "cross", "star", "triangle", "ring"]),
        "mode": r.choice(["edges", "distance", "cells"]),
        "cre": r.uniform(-0.85, -0.3),
        "cim": r.uniform(-0.6, 0.6),
        "spot": r.choice(list(MANDELBROT_SPOTS)),
        "seed": r.randrange(1 << 20),
    }
    return Stage(kind, layer_params(kind, v, speed))


def layer_params(kind: str, v: dict, speed: float) -> dict:
    """Map original-format layer values (``f``, ``n``, ``k``, ...) onto ``kind``'s params."""
    params = {
        "grid": {"scale": v["f"], "scale_y": v["f2"]},
        "rings": {"scale": v["f"], "shape": v["metric"]},
        "spiral": {"scale": v["f"], "arms": v["n"]},
        "rays": {"scale": v["f2"], "arms": v["n"]},
        "checker": {"scale": v["f"], "scale_y": v["f2"]},
        "moire": {"scale": v["f"]},
        "flow": {"scale": v["f"]},
        "blobs": {"count": v["k"]},
        "julia": {"c_real": v["cre"], "c_imag": v["cim"]},
        "mandelbrot": {"spot": v["spot"]},
        "voronoi": {"scale": v["f"], "count": v["k"], "style": v["mode"]},
        "hexagons": {"scale": v["f"]},
        "lissajous": {"scale": v["f"], "x_waves": v["k"], "y_waves": v["n"]},
        "tunnel": {"scale": v["f"], "arms": v["n"]},
        "sources": {"scale": v["f"], "count": v["k"]},
        "shape": {"scale": v["f"], "shape": v["shape"], "points": v["n"]},
        "noise": {"scale": v["f"], "seed": v["seed"]},
    }[kind]
    return LAYERS[kind].clean({**params, "speed": speed})


def _filter(r: random.Random) -> Stage:
    kind = r.choice(list(FILTERS))
    v = {
        "g": r.uniform(0.5, 2.2),
        "n": r.choice([3, 4, 5, 6, 8]),
        "k": r.choice([2, 3, 4, 6, 8]),
        "pw": r.uniform(0.4, 2.5),
        "c": r.uniform(-0.6, 0.6) or 0.3,
    }
    return Stage(kind, filter_params(kind, v))


def filter_params(kind: str, v: dict) -> dict:
    """Map original-format filter values (``g``, ``n``, ``pw``, ...) onto ``kind``'s params."""
    params = {
        "gamma": {"gamma": v["g"]},
        "posterize": {"levels": v["n"]},
        "contour": {"lines": v["k"], "sharpness": v["pw"]},
        "invert": {},
        "cycle": {"speed": v["c"]},
        "pulse": {"rate": v["c"]},
        "fold": {},
        "sawtooth": {"repeats": v["n"]},
    }[kind]
    return FILTERS[kind].clean(params)


def generate(seed: int) -> tuple[Recipe, str]:
    """The recipe for generated effect number ``seed`` and its display name."""
    r = random.Random((seed * 2654435761 + 977) % 2**32)
    speed = r.uniform(0.35, 1.9)
    adjective = ADJECTIVES[r.randrange(len(ADJECTIVES))]
    noun_index = r.randrange(3)

    warps = [_warp(r) for _ in range(r.choices([0, 1, 2, 3], [2, 5, 4, 1])[0])]
    layers = [_layer(r) for _ in range(r.choices([1, 2, 3], [3, 5, 2])[0])]
    for layer in layers[1:]:
        layer.blend = r.choice(list(BLENDS))
    filters = [_filter(r) for _ in range(r.choices([0, 1, 2], [3, 5, 2])[0])]

    glyph_rain = r.random() < 0.12
    charset = CHARSETS[r.randrange(1000) % len(CHARSETS)]
    dither = r.random() < 0.35
    roll = r.random()
    if roll < 0.72:
        palette = Palette("theme")
    elif roll < 0.84:
        palette = Palette("rainbow", r.uniform(0.3, 1.6), r.uniform(-0.3, 0.3), r.random())
    elif roll < 0.93:
        palette = Palette("duo", first=hsv(r.random()), second=hsv(r.random(), 0.9))
    else:
        palette = Palette("angular")
    trail = r.uniform(0.72, 0.94) if r.random() < 0.3 else 0.0
    scanlines = r.random() < 0.2
    glitch = r.random() < 0.15
    sparkle = r.uniform(0.002, 0.008) if r.random() < 0.2 else 0.0
    pulse_on = r.random() < 0.15
    pulse = r.uniform(1.0, 4.0) if pulse_on else 0.0

    recipe = Recipe(
        layers=layers,
        warps=warps,
        filters=filters,
        speed=speed,
        charset=charset,
        glyph_rain=glyph_rain,
        dither=dither,
        palette=palette,
        trail=trail,
        pulse=pulse,
        scanlines=scanlines,
        glitch=glitch,
        sparkle=sparkle,
        seed=seed,
    )
    if palette.kind == "rainbow":
        adjective = "Prismatic"
    noun = LAYERS[layers[0].kind].nouns[noun_index]
    return recipe, f"{adjective} {noun} {seed:03d}"


def describe(recipe: Recipe) -> str:
    """One line saying what a recipe is made of, e.g. 'spiral + voronoi, kaleidoscope warp'."""
    parts = [" + ".join(LAYERS[s.kind].label.lower() for s in recipe.layers)]
    if recipe.warps:
        parts.append(", ".join(WARPS[s.kind].label.lower() for s in recipe.warps) + " warp")
    if recipe.filters:
        parts.append(", ".join(FILTERS[s.kind].label.lower() for s in recipe.filters))
    if recipe.palette.kind != "theme":
        parts.append(f"{recipe.palette.kind} colours")
    return ", ".join(parts)
