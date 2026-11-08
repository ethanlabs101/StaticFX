"""Colour, frames, rendering and key decoding."""

from __future__ import annotations

import pytest

from staticfx.core.color import RGB, gradient, hsv, lerp, parse_hex, rgb, to_hex
from staticfx.core.frame import Frame
from staticfx.core.keys import decode
from staticfx.core.renderer import Renderer, xterm256


def test_rgb_clamps_and_rounds() -> None:
    assert rgb(-5, 300.4, 127.6) == RGB(0, 255, 128)


def test_lerp_and_gradient_hit_their_ends() -> None:
    a, b = RGB(0, 0, 0), RGB(200, 100, 50)
    assert lerp(a, b, 0) == a and lerp(a, b, 1) == b and lerp(a, b, 2) == b
    stops = [(0.0, a), (0.5, RGB(10, 10, 10)), (1.0, b)]
    assert gradient(stops, -1) == a and gradient(stops, 1.5) == b
    assert gradient(stops, 0.5) == RGB(10, 10, 10)


@pytest.mark.parametrize(
    ("text", "color"),
    [
        ("#ff8000", RGB(255, 128, 0)),
        ("ff8000", RGB(255, 128, 0)),
        (" #FF8000 ", RGB(255, 128, 0)),
        ("#f80", RGB(255, 136, 0)),
    ],
)
def test_parse_hex(text: str, color: RGB) -> None:
    assert parse_hex(text) == color


@pytest.mark.parametrize("text", ["", "#12", "#gggggg", "#1234567"])
def test_parse_hex_rejects_garbage(text: str) -> None:
    with pytest.raises(ValueError):
        parse_hex(text)


def test_hex_round_trip_and_hsv() -> None:
    assert parse_hex(to_hex(RGB(1, 2, 3))) == RGB(1, 2, 3)
    assert hsv(0.0) == RGB(255, 0, 0) and hsv(1.0) == hsv(0.0)


@pytest.mark.parametrize("x", [-10, -1, 0, 5, 9, 10, 50])
def test_text_is_clipped_at_both_edges(x: int) -> None:
    frame = Frame(10, 2)
    frame.text(x, 0, "abcdef", RGB(1, 1, 1))
    expected = "".join("abcdef"[col - x] if 0 <= col - x < 6 else " " for col in range(10))
    assert frame.lines()[0] == expected


def test_out_of_range_writes_are_ignored() -> None:
    frame = Frame(3, 3)
    for x, y in [(-1, 0), (0, -1), (3, 0), (0, 3)]:
        frame.put(x, y, "#", RGB(1, 1, 1))
        frame.text(x, y, "#", RGB(1, 1, 1))
    frame.fill(-5, -5, 100, 1, "#")
    assert frame.lines() == ["   ", "   ", "   "]
    assert frame.char_at(-1, 0) == " "


def test_dim_skips_blank_cells_and_resize_clears() -> None:
    frame = Frame(2, 1)
    frame.put(0, 0, "#", RGB(100, 100, 100))
    frame.dim(0.5)
    assert frame.cells[0][0].color == RGB(50, 50, 50)
    frame.resize(4, 2)
    assert frame.lines() == ["    ", "    "]
    frame.resize(0, -3)
    assert (frame.width, frame.height) == (1, 1)


def test_diff_only_writes_changed_rows() -> None:
    renderer, frame = Renderer(), Frame(5, 3)
    frame.put(0, 0, "a", RGB(255, 0, 0))
    first = renderer.diff(frame)
    assert "\x1b[1;1H" in first and "\x1b[3;1H" in first
    assert renderer.diff(frame) == ""
    frame.put(1, 2, "b", RGB(0, 255, 0))
    second = renderer.diff(frame)
    assert "\x1b[3;1H" in second and "\x1b[1;1H" not in second
    renderer.invalidate()
    assert renderer.diff(frame).count("H") == 3


def test_colours_are_only_emitted_when_they_change() -> None:
    frame = Frame(4, 1)
    for x in range(4):
        frame.put(x, 0, "#", RGB(10, 20, 30))
    row = Renderer().full(frame)
    assert row.count("38;2;10;20;30") == 1
    assert "38;5;" in Renderer(truecolor=False).full(frame)


@pytest.mark.parametrize(
    ("color", "index"),
    [
        (RGB(0, 0, 0), 16),
        (RGB(255, 255, 255), 231),
        (RGB(255, 0, 0), 196),
        (RGB(128, 128, 128), 243),
    ],
)
def test_xterm256(color: RGB, index: int) -> None:
    assert xterm256(color) == index


@pytest.mark.parametrize(
    ("data", "keys"),
    [
        ("a?Z", ["a", "?", "Z"]),
        ("\x1b[A\x1b[B\x1b[C\x1b[D", ["up", "down", "right", "left"]),
        ("\x1bOA", ["up"]),
        (
            "\x1b[5~\x1b[6~\x1b[3~\x1b[H\x1b[F\x1b[Z",
            ["pageup", "pagedown", "delete", "home", "end", "shift-tab"],
        ),
        ("\x1b[1;5C", ["right"]),  # Ctrl+arrow: modifiers ignored
        ("\r\n\t \x7f", ["enter", "enter", "tab", "space", "backspace"]),
        ("\x03\x1a\x05", ["ctrl-c", "ctrl-z", "ctrl-e"]),
        ("\x1bx", ["escape", "x"]),  # Alt+x
        ("é✓", ["é", "✓"]),
        ("\x1b[99~", ["unknown"]),
    ],
)
def test_decode(data: str, keys: list[str]) -> None:
    assert decode(data) == (keys, "")


@pytest.mark.parametrize("partial", ["\x1b", "\x1b[", "\x1b[1;"])
def test_decode_keeps_incomplete_sequences(partial: str) -> None:
    assert decode("q" + partial) == (["q"], partial)


def test_every_theme_runs_dark_to_bright() -> None:
    from staticfx.themes import ALIASES, LABELS, STATIC_THEMES, normalize

    assert len(set(LABELS.values())) == len(LABELS)
    for theme in STATIC_THEMES.values():
        dark, light = sum(theme.lut[0]), sum(theme.lut[-1])
        assert dark < light and dark < 200, theme.key
    for alias, key in ALIASES.items():
        assert normalize(alias) == key
