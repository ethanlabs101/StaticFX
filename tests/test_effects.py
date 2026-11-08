"""Every effect must survive hostile sizes and timesteps, and actually draw something."""

from __future__ import annotations

import random

import pytest

from staticfx.core.frame import Frame
from staticfx.effects.builtin import CATALOGUE, CATEGORIES
from staticfx.effects.registry import Registry
from staticfx.themes import STATIC_THEMES, Strobe, rainbow

REGISTRY = Registry()
BUILTIN_KEYS = [row[0] for row in CATALOGUE]
GENERATED_SAMPLE = [key for key in REGISTRY if key.startswith("proc_")][::25]

SIZES = [(1, 1), (2, 1), (1, 40), (3, 3), (7, 2), (80, 24), (250, 70)]
STEPS = [0.0, 1 / 30, 1 / 30, 0.25, -1.0, 1 / 30]
THEME = STATIC_THEMES["matrix"]


def exercise(key: str, ascii_only: bool) -> None:
    effect = REGISTRY.make(key, random.Random(7), unicode=not ascii_only, ascii_only=ascii_only)
    for width, height in SIZES:
        effect.resize(width, height)
        frame = Frame(width, height)
        for dt in STEPS:
            effect.update(dt)
            frame.clear()
            effect.draw(frame, THEME)
            if ascii_only:
                assert all(line.isascii() for line in frame.lines()), f"{key} drew non-ASCII"
        effect.reset()


@pytest.mark.parametrize("key", BUILTIN_KEYS + GENERATED_SAMPLE)
@pytest.mark.parametrize("ascii_only", [False, True], ids=["unicode", "ascii"])
def test_survives_any_size_and_timestep(key: str, ascii_only: bool) -> None:
    exercise(key, ascii_only)


@pytest.mark.parametrize("key", BUILTIN_KEYS)
def test_draws_something(key: str) -> None:
    effect = REGISTRY.make(key, random.Random(3))
    effect.resize(100, 30)
    frame = Frame(100, 30)
    drawn = 0
    for _ in range(60):  # some effects start empty (fireworks before the first launch)
        effect.update(1 / 15)
        frame.clear()
        effect.draw(frame, THEME)
        drawn = max(drawn, sum(ch != " " for line in frame.lines() for ch in line))
    assert drawn >= 20, f"{key} drew only {drawn} cells in 4 seconds"


@pytest.mark.parametrize("key", ["snowfall", "matrix", "embers", "fireworks", "game_of_life"])
def test_long_running_effects_keep_going(key: str) -> None:
    effect = REGISTRY.make(key, random.Random(5))
    effect.resize(80, 24)
    for _ in range(240):  # a minute at the largest step the clock allows
        effect.update(0.25)
    frame = Frame(80, 24)
    effect.draw(frame, THEME)
    assert any(ch != " " for line in frame.lines() for ch in line)


def test_animated_themes_work_with_effects() -> None:
    effect = REGISTRY.make("plasma", random.Random(1))
    effect.resize(40, 12)
    strobe = Strobe(random.Random(2))
    for i in range(10):
        strobe.update(0.05)
        frame = Frame(40, 12)
        effect.draw(frame, rainbow(i / 10) if i % 2 else strobe.theme())


def test_catalogue_is_consistent() -> None:
    keys = [row[0] for row in CATALOGUE]
    assert len(keys) == len(set(keys)) == 50
    assert {row[2] for row in CATALOGUE} == set(CATEGORIES)
    labels = [row[1] for row in CATALOGUE]
    assert len(labels) == len(set(labels))
