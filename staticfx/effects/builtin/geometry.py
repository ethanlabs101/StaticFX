"""Small 3D helpers for the wireframe effects."""

from __future__ import annotations

import math
from collections.abc import Iterator
from typing import NamedTuple


class Vec3(NamedTuple):
    x: float
    y: float
    z: float


class Projected(NamedTuple):
    x: float
    y: float
    depth: float


def rotate(point: Vec3, ax: float = 0.0, ay: float = 0.0, az: float = 0.0) -> Vec3:
    """Rotate around the x, then y, then z axis (radians)."""
    x, y, z = point
    c, s = math.cos(ax), math.sin(ax)
    y, z = y * c - z * s, y * s + z * c
    c, s = math.cos(ay), math.sin(ay)
    x, z = x * c + z * s, -x * s + z * c
    c, s = math.cos(az), math.sin(az)
    x, y = x * c - y * s, x * s + y * c
    return Vec3(x, y, z)


def project(
    point: Vec3, width: int, height: int, focal: float, camera_z: float = 4.0
) -> Projected | None:
    """Perspective-project onto the screen; ``None`` if behind the camera.

    Vertical distances are halved because terminal cells are about twice as
    tall as they are wide.
    """
    depth = point.z + camera_z
    if depth <= 0.01:
        return None
    scale = focal / depth
    return Projected(width * 0.5 + point.x * scale, height * 0.5 - point.y * scale * 0.5, depth)


def cube_vertices(size: float) -> list[Vec3]:
    h = size / 2
    return [Vec3(x, y, z) for z in (-h, h) for y, x in ((-h, -h), (-h, h), (h, h), (h, -h))]


CUBE_EDGES = (
    (0, 1), (1, 2), (2, 3), (3, 0),  # back face
    (4, 5), (5, 6), (6, 7), (7, 4),  # front face
    (0, 4), (1, 5), (2, 6), (3, 7),  # joining edges
)  # fmt: skip


def line_points(x0: int, y0: int, x1: int, y1: int, limit: int = 4096) -> Iterator[tuple[int, int]]:
    """Bresenham line including both ends, capped at ``limit`` points."""
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    step_x = 1 if x0 < x1 else -1
    step_y = 1 if y0 < y1 else -1
    error = dx + dy
    for _ in range(limit):
        yield x0, y0
        if x0 == x1 and y0 == y1:
            return
        doubled = 2 * error
        if doubled >= dy:
            error += dy
            x0 += step_x
        if doubled <= dx:
            error += dx
            y0 += step_y
