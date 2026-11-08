"""Brightness filters (applied after layers are blended) and the blend modes."""

from __future__ import annotations

import math
from collections.abc import Callable

from staticfx.effects.engine.schema import Kind, Param, Params, registry

Filter = Callable[[float], float]
Field = Callable[[float, float], float]


def gamma(p: Params, t: float) -> Filter:
    g = p["gamma"]
    return lambda v: v**g


def posterize(p: Params, t: float) -> Filter:
    n = p["levels"]
    return lambda v: math.floor(v * n) / n


def contour(p: Params, t: float) -> Filter:
    k, sharp = p["lines"] * math.pi, p["sharpness"]
    return lambda v: abs(math.sin(v * k)) ** sharp


def invert(p: Params, t: float) -> Filter:
    return lambda v: 1.0 - v


def cycle(p: Params, t: float) -> Filter:
    offset = t * p["speed"]
    return lambda v: (v + offset) % 1.0


def pulse(p: Params, t: float) -> Filter:
    level = 0.7 + 0.3 * math.sin(t * p["rate"] * 3)
    return lambda v: v * level


def fold(p: Params, t: float) -> Filter:
    return lambda v: abs(2 * v - 1)


def sawtooth(p: Params, t: float) -> Filter:
    n = p["repeats"]
    return lambda v: (v * n) % 1.0


FILTERS = registry(
    Kind(
        "gamma",
        "Gamma",
        gamma,
        (Param("gamma", "Gamma", 1.2, 0.3, 3.0, 0.1),),
        summary="darken or lift the midtones",
    ),
    Kind(
        "posterize",
        "Posterize",
        posterize,
        (Param("levels", "Levels", 4, 2, 12, 1, integer=True),),
        summary="flatten into a few bands",
    ),
    Kind(
        "contour",
        "Contour lines",
        contour,
        (
            Param("lines", "Lines", 3, 1, 10, 1, integer=True),
            Param("sharpness", "Sharpness", 1.0, 0.3, 3.0, 0.1),
        ),
        summary="draw lines along brightness levels",
    ),
    Kind("invert", "Invert", invert, summary="swap dark and bright"),
    Kind(
        "cycle",
        "Cycle",
        cycle,
        (Param("speed", "Speed", 0.3, -1.0, 1.0, 0.05),),
        summary="slide brightness around over time",
    ),
    Kind(
        "pulse",
        "Pulse",
        pulse,
        (Param("rate", "Rate", 0.3, -1.0, 1.0, 0.05),),
        summary="fade in and out",
    ),
    Kind("fold", "Fold", fold, summary="brightest where it was mid-grey"),
    Kind(
        "sawtooth",
        "Sawtooth",
        sawtooth,
        (Param("repeats", "Repeats", 4, 2, 10, 1, integer=True),),
        summary="repeat the brightness range",
    ),
)


# A blend combines the value so far with the next layer, sampled at (x, y).
Blend = Callable[[float, Field, float, float], float]

BLENDS: dict[str, Blend] = {
    "average": lambda a, g, x, y: (a + g(x, y)) * 0.5,
    "multiply": lambda a, g, x, y: a * g(x, y) * 1.4,
    "lighten": lambda a, g, x, y: max(a, g(x, y)),
    "darken": lambda a, g, x, y: min(a, g(x, y)),
    "difference": lambda a, g, x, y: abs(a - g(x, y)),
    "screen": lambda a, g, x, y: 1.0 - (1.0 - a) * (1.0 - g(x, y)),
    "wrap": lambda a, g, x, y: (a + g(x, y)) % 1.0,
    "displace": lambda a, g, x, y: g(x + (a - 0.5) * 0.35, y + (a - 0.5) * 0.35),
}
