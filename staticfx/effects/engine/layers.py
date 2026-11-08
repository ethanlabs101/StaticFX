"""Pattern generators: functions from a point to a brightness in 0..1.

Coordinates arrive centred on the screen, with y spanning about -1..1 and x
scaled to keep circles round on a terminal grid.
"""

from __future__ import annotations

import math
from collections.abc import Callable

from staticfx.effects.engine.schema import Kind, Param, Params, registry

Field = Callable[[float, float], float]

sin, cos, hypot, atan2, tau = math.sin, math.cos, math.hypot, math.atan2, math.tau

SCALE = Param("scale", "Scale", 6.0, 1.0, 20.0, 0.5)
SCALE_Y = Param("scale_y", "Scale (vertical)", 6.0, 1.0, 20.0, 0.5)
SPEED = Param("speed", "Motion", 1.0, -3.0, 3.0, 0.1)
ARMS = Param("arms", "Arms", 4, 1, 12, 1, integer=True)
COUNT = Param("count", "Count", 4, 2, 9, 1, integer=True)

DISTANCES: dict[str, Callable[[float, float], float]] = {
    "circle": hypot,
    "diamond": lambda x, y: abs(x) + abs(y),
    "square": lambda x, y: max(abs(x), abs(y)),
    "star": lambda x, y: (abs(x) ** 0.5 + abs(y) ** 0.5) ** 2,
}

# Interesting places to zoom into on the Mandelbrot set.
MANDELBROT_SPOTS: dict[str, tuple[float, float]] = {
    "seahorse": (-0.745, 0.113),
    "spiral": (-0.16, 1.04),
    "needle": (-1.25, 0.02),
    "elephant": (0.28, 0.008),
    "bulb": (-0.7, 0.3),
    "tendril": (-0.1, 0.65),
}

SHAPES: dict[str, Callable[[float, float, int], float]] = {
    "box": lambda x, y, n: max(abs(x), abs(y)),
    "cross": lambda x, y, n: min(abs(x), abs(y)),
    "star": lambda x, y, n: hypot(x, y) - 0.3 * cos(n * atan2(y, x)),
    "triangle": lambda x, y, n: max(abs(x) * 0.866 + y * 0.5, -y),
    "ring": lambda x, y, n: abs(hypot(x, y) - 0.5),
}


def _hash(ix: int, iy: int, seed: int) -> float:
    n = (ix * 374761393 + iy * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return (n ^ (n >> 16)) / 4294967295.0


def value_noise(x: float, y: float, seed: int) -> float:
    """Smooth 2D value noise in 0..1."""
    ix, iy = math.floor(x), math.floor(y)
    fx, fy = x - ix, y - iy
    ux, uy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
    a, b = _hash(ix, iy, seed), _hash(ix + 1, iy, seed)
    c, d = _hash(ix, iy + 1, seed), _hash(ix + 1, iy + 1, seed)
    top = a + (b - a) * ux
    return top + (c + (d - c) * ux - top) * uy


def grid(p: Params, t: float) -> Field:
    fx, fy, a = p["scale"], p["scale_y"], t * p["speed"]
    return lambda x, y: 0.5 + 0.25 * (sin(x * fx + a) + sin(y * fy - a))


def rings(p: Params, t: float) -> Field:
    dist, f, a = DISTANCES[p["shape"]], p["scale"], t * p["speed"] * 2
    return lambda x, y: 0.5 + 0.5 * sin(dist(x, y) * f - a)


def spiral(p: Params, t: float) -> Field:
    n, f, a = p["arms"], p["scale"] * 0.6, t * p["speed"] * 2
    return lambda x, y: 0.5 + 0.5 * sin(hypot(x, y) * f + n * atan2(y, x) - a)


def rays(p: Params, t: float) -> Field:
    n, twist, a = p["arms"], p["scale"] * 0.2, t * p["speed"]
    return lambda x, y: 0.5 + 0.5 * sin(n * atan2(y, x) + a + hypot(x, y) * twist)


def checker(p: Params, t: float) -> Field:
    fx, fy, a = p["scale"], p["scale_y"], t * p["speed"]
    b = a * 0.7
    return lambda x, y: 0.5 + 0.5 * max(-1.0, min(1.0, 3 * sin(x * fx + a) * sin(y * fy + b)))


def moire(p: Params, t: float) -> Field:
    f, a = p["scale"], t * p["speed"] * 0.5
    ax, ay, bx, by = 0.3 * cos(a), 0.3 * sin(a), -0.3 * cos(a * 0.7), 0.3 * sin(a * 1.3)
    return lambda x, y: (
        0.5 + 0.25 * (sin(hypot(x - ax, y - ay) * f) + sin(hypot(x - bx, y - by) * f * 1.04))
    )


def flow(p: Params, t: float) -> Field:
    f, a = p["scale"] * 0.25 + 0.5, t * p["speed"]

    def field(x: float, y: float) -> float:
        x, y = x * f, y * f
        return (
            sin(x * 1.7 + sin(y * 2.1 + a))
            + sin(y * 1.3 + sin(x * 2.7 - a * 1.3))
            + sin((x + y) * 1.1 + a * 0.7)
        ) / 6.0 + 0.5

    return field


def blobs(p: Params, t: float) -> Field:
    s = t * p["speed"]
    centres = [
        (
            0.6 * sin(s * (0.4 + i * 0.23) + i * 2.1),
            0.6 * cos(s * (0.3 + i * 0.19) + i * 1.3),
            (0.14 + 0.05 * (i % 3)) ** 2,
        )
        for i in range(p["count"])
    ]

    def field(x: float, y: float) -> float:
        total = 0.0
        for cx, cy, r2 in centres:
            dx, dy = x - cx, y - cy
            total += r2 / (dx * dx + dy * dy + 0.01)
        return min(1.0, total * 0.35)

    return field


def julia(p: Params, t: float) -> Field:
    a = t * p["speed"] * 0.3
    c = complex(p["c_real"] + 0.08 * sin(a), p["c_imag"] + 0.08 * cos(a))

    def field(x: float, y: float) -> float:
        z = complex(x * 1.6, y * 1.6)
        n = 0
        while n < 7 and z.real * z.real + z.imag * z.imag < 4.0:
            z = z * z + c
            n += 1
        return n / 7.0

    return field


def mandelbrot(p: Params, t: float) -> Field:
    px, py = MANDELBROT_SPOTS[p["spot"]]
    zoom = 0.9 * math.exp(-2.2 * (0.5 + 0.5 * sin(t * abs(p["speed"]) * 0.35)))

    def field(x: float, y: float) -> float:
        c = complex(px + x * zoom, py + y * zoom)
        z = 0j
        n = 0
        while n < 10 and z.real * z.real + z.imag * z.imag < 4.0:
            z = z * z + c
            n += 1
        return n / 10.0

    return field


def voronoi(p: Params, t: float) -> Field:
    s, f, style = t * p["speed"], p["scale"], p["style"]
    points = [
        (
            0.8 * sin(s * 0.5 * (0.5 + i * 0.17) + i * 1.9),
            0.8 * cos(s * 0.4 * (0.6 + i * 0.13) + i * 2.7),
        )
        for i in range(p["count"] + 2)
    ]
    count = len(points)

    def field(x: float, y: float) -> float:
        nearest = second = 9.0
        owner = 0
        for i, (px, py) in enumerate(points):
            d = hypot(x - px, y - py)
            if d < nearest:
                second, nearest, owner = nearest, d, i
            elif d < second:
                second = d
        if style == "edges":
            return 1.0 - min(1.0, (second - nearest) * f * 0.6)
        if style == "distance":
            return min(1.0, nearest * f * 0.35)
        return owner / count * 0.75 + min(0.25, nearest * 0.3)

    return field


def hexagons(p: Params, t: float) -> Field:
    f, a = p["scale"] * 0.6 + 2.0, t * p["speed"]
    return lambda x, y: (
        0.5
        + (cos(f * x + a) + cos(f * (0.5 * x + 0.866 * y) - a) + cos(f * (0.5 * x - 0.866 * y) + a))
        / 6.0
    )


def lissajous(p: Params, t: float) -> Field:
    fx, fy, f, a = p["x_waves"], p["y_waves"], p["scale"] * 0.3, t * p["speed"]
    return lambda x, y: 0.5 + 0.5 * sin(fx * x * f + a) * cos(fy * y * f - a)


def tunnel(p: Params, t: float) -> Field:
    n, f, a = p["arms"], p["scale"] * 0.5, t * p["speed"] * 1.5
    return lambda x, y: 0.5 + 0.5 * sin((0.3 / (hypot(x, y) + 0.02) - a) * f + n * atan2(y, x))


def sources(p: Params, t: float) -> Field:
    count, f, s = max(2, p["count"] - 1), p["scale"], t * p["speed"]
    a = s * 2
    points = [
        (0.7 * cos(s * 0.3 + i * tau / count), 0.7 * sin(s * 0.3 + i * tau / count))
        for i in range(count)
    ]
    return lambda x, y: (
        0.5 + 0.5 * sum(sin(hypot(x - px, y - py) * f - a) for px, py in points) / count
    )


def shape(p: Params, t: float) -> Field:
    dist, n, f, a = SHAPES[p["shape"]], p["points"], p["scale"] * 2, t * p["speed"] * 2
    return lambda x, y: 0.5 + 0.5 * sin(dist(x, y, n) * f - a)


def noise(p: Params, t: float) -> Field:
    f, a, seed = p["scale"] * 0.35 + 1.5, t * p["speed"] * 0.5, p["seed"]
    return lambda x, y: (
        value_noise(x * f + a, y * f - a * 0.7, seed) * 0.65
        + value_noise(x * f * 2.1 - a, y * f * 2.1 + a, seed + 7) * 0.35
    )


LAYERS = registry(
    Kind(
        "grid",
        "Grid",
        grid,
        (SCALE, SCALE_Y, SPEED),
        summary="crossing sine waves",
        nouns=("Lattice", "Mesh", "Weave"),
    ),
    Kind(
        "rings",
        "Rings",
        rings,
        (SCALE, SPEED, Param("shape", "Ring shape", "circle", choices=tuple(DISTANCES))),
        summary="concentric rings",
        nouns=("Ripples", "Halo", "Pulsar"),
    ),
    Kind(
        "spiral",
        "Spiral",
        spiral,
        (SCALE, SPEED, ARMS),
        summary="rotating spiral arms",
        nouns=("Vortex", "Nautilus", "Helix"),
    ),
    Kind(
        "rays",
        "Rays",
        rays,
        (Param("scale", "Twist", 6.0, 0.0, 20.0, 0.5), SPEED, ARMS),
        summary="light rays from the centre",
        nouns=("Sunburst", "Starburst", "Beacon"),
    ),
    Kind(
        "checker",
        "Checker",
        checker,
        (SCALE, SCALE_Y, SPEED),
        summary="sliding checkerboard",
        nouns=("Mosaic", "Chessboard", "Tiles"),
    ),
    Kind(
        "moire",
        "Moire",
        moire,
        (SCALE, SPEED),
        summary="two interfering ring sets",
        nouns=("Moire", "Interference", "Shimmer"),
    ),
    Kind(
        "flow",
        "Flow",
        flow,
        (SCALE, SPEED),
        summary="liquid domain-warped waves",
        nouns=("Aether", "Current", "Nebula"),
    ),
    Kind(
        "blobs",
        "Blobs",
        blobs,
        (SPEED, COUNT),
        summary="merging metaballs",
        nouns=("Lava", "Orbs", "Amoeba"),
    ),
    Kind(
        "julia",
        "Julia set",
        julia,
        (
            SPEED,
            Param("c_real", "Shape (real)", -0.6, -1.0, 0.5, 0.02),
            Param("c_imag", "Shape (imaginary)", 0.2, -1.0, 1.0, 0.02),
        ),
        summary="the Julia fractal, breathing",
        nouns=("Julia", "Mandala", "Filigree"),
    ),
    Kind(
        "mandelbrot",
        "Mandelbrot",
        mandelbrot,
        (SPEED, Param("spot", "Zoom target", "seahorse", choices=tuple(MANDELBROT_SPOTS))),
        summary="zooming into the Mandelbrot set",
        nouns=("Abyss", "Zoom", "Cardioid"),
    ),
    Kind(
        "voronoi",
        "Voronoi",
        voronoi,
        (
            SCALE,
            SPEED,
            COUNT,
            Param("style", "Style", "edges", choices=("edges", "distance", "cells")),
        ),
        summary="drifting cells",
        nouns=("Shards", "Cells", "Fracture"),
    ),
    Kind(
        "hexagons",
        "Hexagons",
        hexagons,
        (SCALE, SPEED),
        summary="honeycomb interference",
        nouns=("Honeycomb", "Hive", "Lace"),
    ),
    Kind(
        "lissajous",
        "Lissajous",
        lissajous,
        (
            SCALE,
            SPEED,
            Param("x_waves", "Waves across", 3, 1, 9, 1, integer=True),
            Param("y_waves", "Waves down", 4, 1, 12, 1, integer=True),
        ),
        summary="woven sine curves",
        nouns=("Loom", "Harmonic", "Oscillator"),
    ),
    Kind(
        "tunnel",
        "Tunnel",
        tunnel,
        (SCALE, SPEED, ARMS),
        summary="flying down a twisted tunnel",
        nouns=("Tunnel", "Portal", "Warp"),
    ),
    Kind(
        "sources",
        "Wave sources",
        sources,
        (SCALE, SPEED, COUNT),
        summary="circling wave emitters",
        nouns=("Sonar", "Chorus", "Wavefront"),
    ),
    Kind(
        "shape",
        "Shape",
        shape,
        (
            SCALE,
            SPEED,
            Param("shape", "Shape", "ring", choices=tuple(SHAPES)),
            Param("points", "Star points", 5, 2, 12, 1, integer=True),
        ),
        summary="outlines pulsing outwards",
        nouns=("Glyph", "Emblem", "Sigil"),
    ),
    Kind(
        "noise",
        "Noise",
        noise,
        (SCALE, SPEED, Param("seed", "Noise seed", 1, 0, 1 << 20, 1, integer=True)),
        summary="drifting cloudy noise",
        nouns=("Terrain", "Cloud", "Storm"),
    ),
)
