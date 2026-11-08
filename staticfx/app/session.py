"""Running the app in a real terminal, and rendering it without one."""

from __future__ import annotations

import os
import sys
import time

from staticfx.app.app import App
from staticfx.core.clock import FrameClock
from staticfx.core.frame import Frame
from staticfx.core.keys import KeyReader
from staticfx.core.renderer import Renderer
from staticfx.core.terminal import CLEAR, Terminal

SAVE_INTERVAL = 1.0  # seconds; settings change on every effect switch, so batch the writes


def supports_truecolor() -> bool:
    """Best guess from the environment; ``staticfx`` can be told otherwise in Settings."""
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return True
    term = os.environ.get("TERM", "")
    return not ("256color" in term or term in ("linux", "screen", "xterm"))


def supports_utf8() -> bool:
    encoding = getattr(sys.stdout, "encoding", None) or ""
    return encoding.lower().replace("-", "") == "utf8"


def wants_truecolor(app: App) -> bool:
    colour = app.settings.colour
    return supports_truecolor() if colour == "auto" else colour == "truecolor"


def run(app: App, duration: float | None = None) -> None:
    """The interactive loop. Returns when the user quits or ``duration`` seconds pass."""
    renderer = Renderer()
    started = last_save = time.monotonic()
    try:
        with Terminal() as terminal:
            reader = KeyReader(terminal.fd)
            clock = FrameClock(app.settings.fps)
            frame = Frame(*terminal.size())
            app.resize(frame.width, frame.height)
            if app.notes:
                extra = len(app.notes) - 1
                more = f" (+{extra} more, listed when you quit)" if extra else ""
                app.toast(app.notes[0] + more, 6.0)

            while app.running:
                dt = clock.tick()
                for key in reader.read():
                    app.handle_key(key)
                if not app.running:
                    break
                if app.suspend_requested:
                    app.suspend_requested = False
                    terminal.suspend()

                size = terminal.size()
                if terminal.resized or size != (frame.width, frame.height):
                    terminal.resized = False
                    frame.resize(*size)
                    app.resize(*size)
                    renderer.invalidate()
                    terminal.write(CLEAR)

                clock.interval = 1.0 / app.settings.fps
                renderer.truecolor = wants_truecolor(app)
                app.update(dt)
                app.draw(frame)
                terminal.write(renderer.diff(frame))

                now = time.monotonic()
                if app.dirty and now - last_save >= SAVE_INTERVAL:
                    app.save_settings()
                    last_save = now
                if duration is not None and now - started >= duration:
                    break
                clock.wait()
    finally:
        app.save_settings()


def render_frames(app: App, frames: int, fps: float = 30.0) -> Frame:
    """Simulate ``frames`` frames headlessly and return the last one.

    Uses a fixed timestep and no adaptive resolution, so the same seed always
    gives the same picture.
    """
    frame = Frame(app.width, app.height)
    for _ in range(max(1, frames)):
        app.player.update(1.0 / fps)
    app.player.draw(frame)
    return frame
