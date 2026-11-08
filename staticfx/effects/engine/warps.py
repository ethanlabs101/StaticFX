"""Coordinate warps, applied before the layers are sampled.

A warp moves the point a layer is sampled at, so it bends, repeats or
mirrors the whole pattern without the layer knowing.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from staticfx.effects.engine.schema import Kind, Param, Params, registry

Warp = Callable[[float, float], tuple[float, float]]

sin, cos, hypot, atan2 = math.sin, math.cos, math.hypot, math.atan2


def rotate(p: Params, t: float) -> Warp:
    angle = p["spin"] * t
    c, s = cos(angle), sin(angle)
    return lambda x, y: (x * c - y * s, x * s + y * c)


def zoom(p: Params, t: float) -> Warp:
    factor = p["zoom"] * (1 + p["pulse"] * sin(t * p["pulse_rate"]))
    return lambda x, y: (x * factor, y * factor)


def kaleidoscope(p: Params, t: float) -> Warp:
    wedge = math.tau / p["segments"]
    half = wedge / 2
    spin = p["spin"] * t

    def warp(x: float, y: float) -> tuple[float, float]:
        angle = atan2(y, x) % wedge
        if angle > half:
            angle = wedge - angle
        r = hypot(x, y)
        return r * cos(angle + spin), r * sin(angle + spin)

    return warp


def mirror(p: Params, t: float) -> Warp:
    axis = p["axis"]
    if axis == "x":
        return lambda x, y: (abs(x), y)
    if axis == "y":
        return lambda x, y: (x, abs(y))
    return lambda x, y: (abs(x), abs(y))


def tile(p: Params, t: float) -> Warp:
    n, ox, oy = p["tiles"], t * p["drift_x"], t * p["drift_y"]
    return lambda x, y: (((x * n + ox) % 1.0 - 0.5) * 2, ((y * n + oy) % 1.0 - 0.5) * 2)


def swirl(p: Params, t: float) -> Warp:
    twist = p["twist"] * sin(t * 0.7 + 1.0)

    def warp(x: float, y: float) -> tuple[float, float]:
        angle = twist * math.exp(-hypot(x, y) * 1.5)
        c, s = cos(angle), sin(angle)
        return x * c - y * s, x * s + y * c

    return warp


def wave(p: Params, t: float) -> Warp:
    amp, freq = p["strength"], p["frequency"]
    return lambda x, y: (x + amp * sin(y * freq + t), y + amp * sin(x * freq + t * 1.3))


def polar(p: Params, t: float) -> Warp:
    return lambda x, y: (hypot(x, y), atan2(y, x) / math.pi)


def fold(p: Params, t: float) -> Warp:
    offset, folds = p["offset"], p["folds"]
    angle = p["angle"] + 0.15 * sin(t * 0.4)
    c, s = cos(angle), sin(angle)

    def warp(x: float, y: float) -> tuple[float, float]:
        for _ in range(folds):
            x, y = abs(x) - offset, abs(y) - offset
            x, y = x * c - y * s, x * s + y * c
        return x, y

    return warp


def pixelate(p: Params, t: float) -> Warp:
    q = p["resolution"]
    return lambda x, y: (math.floor(x * q) / q, math.floor(y * q) / q)


def ripple(p: Params, t: float) -> Warp:
    amp, freq, phase = p["strength"] * 0.5, p["frequency"], p["speed"] * t

    def warp(x: float, y: float) -> tuple[float, float]:
        r = hypot(x, y) + 1e-6
        d = amp * sin(r * freq - phase)
        return x + x / r * d, y + y / r * d

    return warp


WARPS = registry(
    Kind(
        "rotate",
        "Rotate",
        rotate,
        (Param("spin", "Spin", 0.2, -1.5, 1.5, 0.05),),
        summary="spin the whole pattern",
    ),
    Kind(
        "zoom",
        "Zoom",
        zoom,
        (
            Param("zoom", "Zoom", 1.5, 0.5, 3.0, 0.1),
            Param("pulse", "Pulse", 0.3, 0.0, 0.8, 0.05),
            Param("pulse_rate", "Pulse rate", 0.8, 0.1, 3.0, 0.1),
        ),
        summary="scale in and out, breathing",
    ),
    Kind(
        "kaleidoscope",
        "Kaleidoscope",
        kaleidoscope,
        (
            Param("segments", "Segments", 6, 2, 16, 1, integer=True),
            Param("spin", "Spin", 0.2, -1.0, 1.0, 0.05),
        ),
        summary="mirror into wedges around the centre",
    ),
    Kind(
        "mirror",
        "Mirror",
        mirror,
        (Param("axis", "Axis", "xy", choices=("x", "y", "xy")),),
        summary="reflect across an axis",
    ),
    Kind(
        "tile",
        "Tile",
        tile,
        (
            Param("tiles", "Tiles", 2.0, 1.0, 6.0, 0.25),
            Param("drift_x", "Drift across", 0.2, -1.0, 1.0, 0.05),
            Param("drift_y", "Drift down", 0.1, -1.0, 1.0, 0.05),
        ),
        summary="repeat in a drifting grid",
    ),
    Kind(
        "swirl",
        "Swirl",
        swirl,
        (Param("twist", "Twist", 2.0, -6.0, 6.0, 0.25),),
        summary="twist the middle like stirred paint",
    ),
    Kind(
        "wave",
        "Wave",
        wave,
        (
            Param("strength", "Strength", 0.3, 0.0, 1.0, 0.05),
            Param("frequency", "Frequency", 3.0, 0.5, 10.0, 0.25),
        ),
        summary="wobble sideways in waves",
    ),
    Kind("polar", "Polar", polar, summary="unroll circles into lines"),
    Kind(
        "fold",
        "Fold",
        fold,
        (
            Param("offset", "Offset", 0.3, 0.0, 1.0, 0.05),
            Param("angle", "Angle", 0.7, 0.0, 3.14, 0.05),
            Param("folds", "Folds", 2, 1, 4, 1, integer=True),
        ),
        summary="fold space over on itself",
    ),
    Kind(
        "pixelate",
        "Pixelate",
        pixelate,
        (Param("resolution", "Resolution", 8.0, 2.0, 24.0, 1.0),),
        summary="chunky low-resolution blocks",
    ),
    Kind(
        "ripple",
        "Ripple",
        ripple,
        (
            Param("strength", "Strength", 0.3, 0.0, 1.0, 0.05),
            Param("frequency", "Frequency", 10.0, 2.0, 24.0, 0.5),
            Param("speed", "Speed", 2.0, -6.0, 6.0, 0.25),
        ),
        summary="rings travelling out from the centre",
    ),
)
