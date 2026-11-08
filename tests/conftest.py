"""Shared fixtures: an App wired to a temporary data folder, driven key by key."""

from __future__ import annotations

import random
from collections.abc import Callable
from pathlib import Path

import pytest

from staticfx.app.app import App
from staticfx.core.frame import Frame
from staticfx.library.config import Settings

AppFactory = Callable[..., App]


@pytest.fixture
def make_app(tmp_path: Path) -> AppFactory:
    def make(width: int = 100, height: int = 30, utf8: bool = True, **settings) -> App:
        settings.setdefault("seen_welcome", True)
        app = App(Settings(**settings), tmp_path, utf8=utf8, rng=random.Random(1))
        app.start()
        app.resize(width, height)
        return app

    return make


@pytest.fixture
def app(make_app: AppFactory) -> App:
    return make_app()


def press(app: App, *keys: str) -> None:
    """Press keys one by one, letting a frame pass after each like the real loop."""
    for key in keys:
        app.handle_key(key)
        app.update(1 / 30)


def type_text(app: App, text: str) -> None:
    press(app, *("space" if ch == " " else ch for ch in text))


def screen(app: App) -> str:
    frame = Frame(app.width, app.height)
    app.draw(frame)
    return "\n".join(frame.lines())
