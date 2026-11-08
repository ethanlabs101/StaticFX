"""The real program in a pseudo-terminal: what a user actually sees.

These start ``python -m staticfx`` in a pty, type at it, and read the screen
back through a small emulator, so they catch problems the in-process tests
can't: terminal modes, signals, resizing, and leaving the terminal usable.
"""

from __future__ import annotations

import json
import signal
import sys
from pathlib import Path

import pytest
from pty_session import Session

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="needs a POSIX pty")

ALT_ON, ALT_OFF = "\x1b[?1049h", "\x1b[?1049l"


@pytest.fixture
def session(tmp_path: Path):
    sessions: list[Session] = []

    def start(*args: str, width: int = 100, height: int = 30) -> Session:
        s = Session(tmp_path, *args, width=width, height=height)
        sessions.append(s)
        s.pump(2.0)  # startup builds 1,000 recipes
        return s

    yield start
    for s in sessions:
        s.close()


def assert_terminal_restored(s: Session) -> None:
    assert not s.screen.alternate, "still in the alternate screen"
    assert s.screen.cursor_visible, "cursor left hidden"


def test_first_run_welcome_then_quit(session, tmp_path: Path) -> None:
    s = session()
    assert "Welcome to StaticFX" in s.screen.text()
    assert "Welcome" not in s.press("x")
    s.press("q")
    assert s.wait_exit() == 0
    assert_terminal_restored(s)
    assert json.loads((tmp_path / "config.json").read_text())["seen_welcome"] is True


def test_browse_search_and_play(session) -> None:
    s = session()
    s.press("x", "m")
    assert "Effects" in s.screen.text() and "/ to search" in s.screen.text()
    s.type("/galaxy")
    s.press("enter", "i")
    assert "Galaxy" in s.screen.text().splitlines()[-1]
    s.press("q")
    assert s.wait_exit() == 0


def test_ctrl_c_quits_but_not_out_of_the_studio(session) -> None:
    s = session()
    s.press("x", "n", "down", "right", "\x03")
    assert s.process.poll() is None, "Ctrl-C in the Studio must not kill the app"
    assert "Discard changes?" in s.screen.text()
    s.press("y", "\x03")
    assert s.wait_exit() == 0
    assert_terminal_restored(s)


def test_resize_and_too_small(session) -> None:
    s = session(width=100, height=30)
    s.press("x")
    assert "Terminal too small" in s.resize(30, 8)
    text = s.resize(70, 20)
    assert "too small" not in text
    s.press("m")
    assert "Effects" in s.screen.text()
    s.press("escape", "q")
    assert s.wait_exit() == 0


def test_sigterm_restores_the_terminal(session) -> None:
    s = session()
    s.process.send_signal(signal.SIGTERM)
    s.wait_exit()
    assert_terminal_restored(s)


def test_ctrl_z_hands_the_terminal_back_and_resumes(session) -> None:
    s = session()
    s.press("x")
    s.raw = ""
    s.press("\x1a", wait=0.8)
    # Without a job-control shell the stop signal is ignored, so the app comes
    # straight back; what matters is that it left and re-entered cleanly.
    assert ALT_OFF in s.raw and s.raw.rindex(ALT_ON) > s.raw.index(ALT_OFF)
    assert s.process.poll() is None
    s.press("q")
    assert s.wait_exit() == 0


def test_duration_exits_on_its_own(session) -> None:
    s = session("--duration", "1")
    assert s.wait_exit(timeout=6) == 0
    assert_terminal_restored(s)


def test_corrupt_config_still_starts_and_explains(session, tmp_path: Path) -> None:
    (tmp_path / "config.json").write_text('{"theme": 42, "effect": "gone", "seen_welcome": true}')
    s = session()
    assert "no longer exists" in s.screen.text() or "theme" in s.screen.text()
    s.press("q")
    assert s.wait_exit() == 0
    assert s.process.stderr is not None
    errors = s.process.stderr.read().decode()
    assert "theme" in errors and "gone" in errors
